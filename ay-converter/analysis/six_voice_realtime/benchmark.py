"""Execute every one-second control block and a complete Z80 audio schedule."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
TOOLKIT = CORE.parent / 'toolkit'
sys.path.insert(0, str(TOOLKIT))
from build_zxv_trd import MiniAssembler
from validate_fast_sparse import CPU as BaseCPU
from zx0_codec import decompress, emit_decoder

ORIGIN, INPUT, FLAT, STACK, STOP = 0x8000, 0x9000, 0xb000, 0xbef0, 0x8ff0
BUFFERS = (0xc000, 0xc400)
CLOCK, FIELD = 3546900, 70908
HEADER = struct.Struct('<4sBBHIIIdfHBB')


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CPU(BaseCPU):
    """Allow an IRQ between LDIR iterations; capture a hypothetical 19-reg bus.

    The repository validator normally collapses LDIR into one host step.
    Splitting it into 21-T repeats and a final 16-T iteration preserves its
    timing while exposing the real interrupt boundaries. The virtual device
    uses AY-style address/data port writes and an extra atomic commit register;
    it is not an actual AY/Yamaha chip or audio implementation.
    """
    def __init__(self, code):
        super().__init__(b'', b'')
        for i, value in enumerate(code):
            self.write8(ORIGIN + i, value)
        self.sp = STACK
        self.device = bytearray(19)
        self.selected = 0
        self.commits = []
        self.deadline = None

    def instruction(self):
        if self.read8(self.pc) == 0xed and self.read8(self.pc + 1) == 0xb0:
            self.write8(self.de(), self.read8(self.hl()))
            self.set_hl(self.hl() + 1)
            self.set_de(self.de() + 1)
            self.set_bc(self.bc() - 1)
            if self.bc():
                return 21
            self.pc += 2
            return 16
        if self.read8(self.pc) == 0xed and self.read8(self.pc + 1) == 0x79:
            if self.bc() == 0xfffd:
                self.selected = self.a
            elif self.bc() == 0xbffd:
                if self.selected == 19:
                    assert self.a == 1
                    self.commits.append((self.tstates + 12, bytes(self.device), self.deadline))
                else:
                    assert self.selected < 19
                    self.device[self.selected] = self.a
        return super().instruction()


def program(variant):
    a = MiniAssembler(ORIGIN)
    # Job input is the four-byte block header at INPUT. Derive the inactive
    # buffer from the cursor: both buffers have low byte0 and differ by0400h.
    # A/BC/DE/HL/flags are clobbered; a completed buffer becomes
    # visible to the IRQ only after every decoded byte has been written.
    a.label('job')
    a.emit(0x21); a.word(INPUT)             # LD HL,INPUT:10 T.
    a.emit(*([0x23] * 4))                  # Skip trusted length header:24 T.
    a.abs16((0xed, 0x5b), 'cursor')
    a.emit(0x1e, 0, 0x7a, 0xee, 4, 0x57)  # DE=(cursor high XOR04h):00.
    a.abs16((0xed, 0x53), 'next_buffer')    # LD (next_buffer),DE:20 T.
    a.abs16(0xcd, f'dzx0_{variant}')
    a.emit(0x3e, 1); a.abs16(0x32, 'ready'); a.emit(0xc9)
    a.label('init')
    a.abs16(0xcd, 'job')
    a.abs16(0x2a, 'next_buffer'); a.abs16(0x22, 'cursor')
    a.emit(0xaf); a.abs16(0x32, 'ready')
    a.emit(0x3e, 0x84, 0xed, 0x47, 0xed, 0x5e, 0xfb, 0xc9)

    def output(label, columnar):
        # HL: first low-period byte of this update. Output all 19 register
        # values then atomically latch them. Clobbers A/BC/DE/HL/flags.
        # Per register: select7+OUT12+load7+LD B7+OUT12+LD B7 =52 T.
        # Columnar stride50 adds18*11 T; flat stride1 adds18*6 T.
        # Commit costs52 T. Setup/RET: columnar30 T, flat20 T.
        a.label(label)
        a.emit(0x01); a.word(0xfffd)
        if columnar:
            a.emit(0x11); a.word(50)
        for register in range(19):
            a.emit(0x3e, register, 0xed, 0x79, 0x7e, 0x06, 0xbf, 0xed, 0x79, 0x06, 0xff)
            if register != 18:
                a.emit(0x19 if columnar else 0x23)
        a.emit(0x3e, 19, 0xed, 0x79, 0x3e, 1, 0x06, 0xbf, 0xed, 0x79, 0x06, 0xff, 0xc9)

    output('output_columnar', True)
    output('output_flat', False)
    # IRQ preserves all main registers/flags used by ZX0. Shadow/IX registers
    # are untouched. After update50, switch only to a completely ready buffer.
    # Switch immediately before the first field of the new block, so the
    # producer can use the entire previous second. Normal body1505 T, switch
    # body1605 T; IM2 entry19 T and vector stub JP10 T are separate.
    # ZX0 runs with IRQs enabled.
    a.label('irq')
    a.emit(0xf5, 0xc5, 0xd5, 0xe5)
    a.abs16(0x3a, 'left'); a.emit(0xb7); a.rel8(0x20, 'irq_output')
    a.abs16(0x3a, 'ready'); a.emit(0xb7); a.rel8(0x28, 'no_ready')
    a.abs16(0x2a, 'next_buffer'); a.abs16(0x22, 'cursor')
    a.emit(0x3e, 50); a.abs16(0x32, 'left')
    a.emit(0xaf); a.abs16(0x32, 'ready'); a.rel8(0x18, 'irq_output')
    a.label('no_ready')
    a.abs16(0x3a, 'eof'); a.emit(0xb7); a.rel8(0x20, 'irq_end')
    a.emit(0x3e, 1); a.abs16(0x32, 'underflow'); a.rel8(0x18, 'irq_end')
    a.label('irq_output')
    a.abs16(0x2a, 'cursor'); a.emit(0xe5)
    a.abs16(0xcd, 'output_columnar')
    a.emit(0xe1, 0x23); a.abs16(0x22, 'cursor')
    a.abs16(0x3a, 'left'); a.emit(0x3d); a.abs16(0x32, 'left')
    a.label('irq_end')
    a.emit(0xe1, 0xd1, 0xc1, 0xf1, 0xfb, 0xed, 0x4d)
    emit_decoder(a, variant)
    for name, initial in (('cursor', BUFFERS[1]), ('next_buffer', BUFFERS[0])):
        a.label(name); a.word(initial)
    for name, initial in (('left', 50), ('ready', 0), ('eof', 0), ('underflow', 0)):
        a.label(name); a.emit(initial)
    # A full257-byte IM2 table handles any interrupt vector byte. Each entry
    # points to8383h, whose JP reaches the handler. Keep table/stub/code in the
    # same uncontended fixed bank2; include all padding in the RAM footprint.
    assert a.pc <= 0x8383
    a.emit(*bytes(0x8383 - a.pc)); a.label('im2_stub'); a.abs16(0xc3, 'irq')
    a.emit(*bytes(0x8400 - a.pc)); a.label('im2_table'); a.emit(*([0x83] * 257))
    return a.resolve(), a.labels


def vector(cpu):
    assert cpu.im == 2 and cpu.i == 0x84
    return cpu.read8(0x84ff) | cpu.read8(0x8500) << 8


def place(cpu, address, data):
    for i, value in enumerate(data):
        cpu.write8(address + i, value)


def invoke(cpu, label):
    cpu.pc = label; cpu.push(STOP)
    start = cpu.tstates
    while cpu.pc != STOP:
        cpu.step()
        assert cpu.tstates - start < 1000000
    assert cpu.sp == STACK
    return cpu.tstates - start


def blocks(stream):
    magic, layout, flags, hz, ticks, *_ = HEADER.unpack_from(stream)
    assert magic == b'S6P1' and layout == 1 and flags == 15 and hz == 50 and ticks == 1500
    pos = HEADER.size
    result = []
    while pos < len(stream):
        size, length = struct.unpack_from('<HH', stream, pos)
        frame = stream[pos:pos + 4 + length]
        assert size == 950 and len(frame) == 4 + length
        raw = decompress(frame[4:], limit=size)
        assert len(raw) == size
        result.append((frame, raw))
        pos += len(frame)
    assert pos == len(stream) and len(result) == 30
    return result


def interrupt_stress(code, labels, frame, raw, index, baseline):
    """Interrupt at a different point inside each real block's decoder."""
    cpu = CPU(code)
    place(cpu, INPUT, frame); place(cpu, BUFFERS[1], raw)
    cpu.i = 0x84; cpu.im = 2
    cpu.iff1 = True; cpu.pc = labels['job']; cpu.push(STOP)
    target = baseline * (20 + (index * 17) % 65) // 100
    injected = False
    while cpu.pc != STOP:
        if not injected and cpu.tstates >= target:
            snapshot = (cpu.pc, cpu.sp, cpu.a, cpu.bc(), cpu.de(), cpu.hl(), cpu.z, cpu.carry)
            start = cpu.tstates; delay = start - target
            cpu.deadline = target; cpu.push(cpu.pc); cpu.pc = vector(cpu); cpu.iff1 = False
            cpu.tstates += 19
            while cpu.pc != snapshot[0]:
                cpu.step()
            assert snapshot == (cpu.pc, cpu.sp, cpu.a, cpu.bc(), cpu.de(), cpu.hl(), cpu.z, cpu.carry)
            assert cpu.iff1 and cpu.tstates - start == 1534
            injected = True
        else:
            cpu.step()
    assert injected and cpu.sp == STACK
    assert bytes(cpu.read8(BUFFERS[0] + i) for i in range(950)) == raw
    assert cpu.tstates == baseline + 1534
    return dict(requested_irq_tstate=target, admission_delay_tstates=delay,
                main_registers_flags_stack_restored=True, all_950_bytes_exact=True)


class Underflow(Exception):
    def __init__(self, evidence):
        self.evidence = evidence


def pipeline(code, labels, encoded, expected, variant, lead_fields=2):
    cpu = CPU(code)
    place(cpu, INPUT, encoded[0][0])
    startup = invoke(cpu, labels['init'])
    assert bytes(cpu.read8(BUFFERS[0] + i) for i in range(950)) == encoded[0][1]
    origin = cpu.tstates
    cpu.iff1 = True
    irq_rows = []
    jobs = []

    def irq():
        index = len(irq_rows)
        deadline = origin + index * FIELD
        admission = cpu.tstates - deadline
        assert 0 <= admission <= 21
        cpu.deadline = deadline
        return_pc = cpu.pc
        start = cpu.tstates
        cpu.push(return_pc); cpu.pc = vector(cpu); cpu.iff1 = False
        cpu.tstates += 19  # IM2 vector/PC push; no ROM or ULA delays.
        while cpu.pc != return_pc:
            cpu.step()
        assert cpu.iff1
        if cpu.read8(labels['underflow']):
            raise Underflow(dict(variant=variant, lead_fields=lead_fields, complete=False,
                                 decision='Rejected preparation window: native buffer underflow.',
                                 first_missing_field=index, previous_fields_verified=len(irq_rows),
                                 current_job_block=block, current_job_elapsed_tstates=cpu.tstates - job_start))
        body = cpu.tstates - start - 19 - 10
        assert body == (1605 if index and index % 50 == 0 else 1505)
        assert len(cpu.commits) == index + 1 and cpu.commits[-1][1] == expected[index]
        irq_rows.append([index, deadline - origin, admission, cpu.commits[-1][0] - origin, body])

    def idle_until(target):
        # HALT/idle waiting consumes wall time but no useful CPU budget. Wake
        # at each exact field edge; active instructions are never truncated.
        while origin + len(irq_rows) * FIELD <= target:
            cpu.tstates = origin + len(irq_rows) * FIELD
            irq()
        cpu.tstates = max(cpu.tstates, target)

    for block in range(1, 30):
        # Start100 T before the lead_fields-th interrupt preceding the new
        # block. Real IRQs interrupt the decoder; no instruction is truncated.
        start_at = origin + (block * 50 - lead_fields) * FIELD - 100
        idle_until(start_at)
        buffer = BUFFERS[block % 2]
        assert cpu.read8(labels['ready']) == 0
        place(cpu, INPUT, encoded[block][0])
        cpu.pc = labels['job']; cpu.push(STOP)
        start = cpu.tstates; job_start = start; irq_count = len(irq_rows)
        while cpu.pc != STOP:
            if cpu.iff1 and cpu.tstates >= origin + len(irq_rows) * FIELD:
                irq()
            else:
                cpu.step()
        assert cpu.sp == STACK and cpu.read8(labels['ready']) == 1
        assert bytes(cpu.read8(buffer + i) for i in range(950)) == encoded[block][1]
        deadline = origin + block * 50 * FIELD
        assert cpu.tstates < deadline
        jobs.append(dict(block=block, elapsed_tstates=cpu.tstates - start,
                         intervening_irqs=len(irq_rows) - irq_count,
                         ready_margin_tstates=deadline - cpu.tstates))
    cpu.write8(labels['eof'], 1)
    idle_until(origin + 1499 * FIELD)
    assert len(cpu.commits) == len(irq_rows) == 1500
    assert cpu.read8(labels['underflow']) == 0 and cpu.min_sp >= STACK - 64
    trace = json.dumps(irq_rows, separators=(',', ':')).encode() + b'\n'
    return dict(variant=variant, lead_fields=lead_fields, startup_tstates=startup, all_1500_fields_exact=True,
                missing_fields=0, underflows=0, interrupted_jobs=jobs,
                max_irq_admission_delay_tstates=max(r[2] for r in irq_rows),
                max_commit_after_edge_tstates=max(r[3] - r[1] for r in irq_rows),
                max_commit_after_edge_ms=max(r[3] - r[1] for r in irq_rows) * 1000 / CLOCK,
                max_irq_body_tstates=max(r[4] for r in irq_rows),
                total_irq_with_entry_tstates=sum(r[4] + 19 + 10 for r in irq_rows),
                minimum_ready_margin_tstates=min(j['ready_margin_tstates'] for j in jobs),
                minimum_stack_address=cpu.min_sp,
                commit_interval_min_tstates=min(b[3] - a[3] for a, b in zip(irq_rows, irq_rows[1:])),
                commit_interval_max_tstates=max(b[3] - a[3] for a, b in zip(irq_rows, irq_rows[1:])),
                trace_columns=['field', 'nominal_edge_tstates', 'admission_delay_tstates', 'commit_tstates', 'irq_body_tstates']), trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('use a new output directory')
    source = CORE / 'analysis/six_voice_storage/evidence/columnar-50.zx0'
    encoded = blocks(source.read_bytes())
    control_path = CORE / 'analysis/six_voice_spectral/evidence/selectable-controls.npz'
    with np.load(control_path) as saved:
        p = saved['periods']
        cmd = saved['volumes'] | saved['shapes'] << 4 | saved['modes'] << 6
        expected = [bytes(row) for row in np.column_stack((p & 255, p >> 8, cmd, saved['noise_periods'])).astype(np.uint8)]
    assert b''.join(raw for _, raw in encoded) == b''.join(np.array([list(v) for v in expected[i:i + 50]], dtype=np.uint8).T.copy().tobytes() for i in range(0, 1500, 50))
    args.output.mkdir(parents=True)
    runs = []
    rejected = []
    for variant in ('standard', 'turbo'):
        code, labels = program(variant)
        measurements = []
        for index, (frame, raw) in enumerate(encoded):
            cpu = CPU(code); place(cpu, INPUT, frame)
            total = invoke(cpu, labels['job'])
            assert bytes(cpu.read8(BUFFERS[0] + i) for i in range(950)) == raw
            assert cpu.hl() == INPUT + len(frame)
            # Calibrate the split LDIR timing against the existing aggregate
            # timing-table interpreter on every actual block, not a toy input.
            reference = BaseCPU(b'', b''); reference.sp = STACK
            place(reference, ORIGIN, code); place(reference, INPUT, frame)
            bulk_total = invoke(reference, labels['job'])
            assert bulk_total == total
            assert bytes(reference.read8(BUFFERS[0] + i) for i in range(950)) == raw
            measurements.append(dict(block=index, coded_bytes=len(frame), tstates=total,
                                     ms=total * 1000 / CLOCK, all_950_bytes_exact=True,
                                     aggregate_ldir_reference_tstates=bulk_total,
                                     interrupt_stress=interrupt_stress(code, labels, frame, raw, index, total)))
        cpu = CPU(code); place(cpu, BUFFERS[0], encoded[0][1]); cpu.set_hl(BUFFERS[0])
        columnar = invoke(cpu, labels['output_columnar'])
        assert columnar == 1268 and cpu.commits[-1][1] == expected[0]
        cpu = CPU(code); place(cpu, FLAT, expected[0]); cpu.set_hl(FLAT)
        flat = invoke(cpu, labels['output_flat'])
        assert flat == 1168 and cpu.commits[-1][1] == expected[0]
        # Retain the failed one-field standard test; it is not a full pass.
        try:
            short, short_trace = pipeline(code, labels, encoded, expected, variant, lead_fields=1)
        except Underflow as failure:
            rejected.append(failure.evidence)
            short = None
        result, trace = pipeline(code, labels, encoded, expected, variant, lead_fields=2)
        if short is not None:
            short_trace_name = f'{variant}-one-field.json.gz'
            short_data = gzip.compress(short_trace, mtime=0)
            (args.output / short_trace_name).write_bytes(short_data)
            short.update(trace_file=short_trace_name, trace_sha256=sha(short_data))
            result['additional_one_field_complete_run'] = short
        trace_name = f'{variant}-fields.json.gz'
        trace_data = gzip.compress(trace, mtime=0)
        (args.output / trace_name).write_bytes(trace_data)
        (args.output / f'{variant}.code').write_bytes(code)
        result.update(blocks=measurements, code_bytes=len(code), code_sha256=sha(code),
                      trace_file=trace_name, trace_sha256=sha(trace_data),
                      mean_block_tstates=sum(r['tstates'] for r in measurements) / 30,
                      max_block_tstates=max(r['tstates'] for r in measurements),
                      max_block_ms=max(r['ms'] for r in measurements),
                      columnar_output_tstates=columnar, flat_output_tstates=flat,
                      output_path_delta_tstates=columnar - flat)
        result['total_decode_tstates'] = sum(r['tstates'] for r in measurements)
        result['decode_plus_irq_cpu_percent'] = (result['total_decode_tstates'] + result['total_irq_with_entry_tstates']) / (1500 * FIELD) * 100
        runs.append(result)
        print(json.dumps({k: result[k] for k in ('variant', 'mean_block_tstates', 'max_block_ms', 'decode_plus_irq_cpu_percent', 'max_commit_after_edge_ms', 'minimum_ready_margin_tstates')}), flush=True)
    report = dict(complete=True, date='2026-10-13', seconds=30, fields=1500,
                  target='ZX Spectrum 128; deterministic instruction-table Z80 simulation',
                  clock_hz=CLOCK, field_tstates=FIELD, instruction_timings='Repository validate_fast_sparse.CPU, based on Zilog UM0080',
                  instruction_boundary_ldir=True, im2_entry_tstates=19, im2_stub_tstates=10,
                  hypothetical_19_register_plus_commit_device=True,
                  real_chip_or_fuse_or_disk_verified=False, native_release_changed=False,
                  source_stream_sha256=sha(source.read_bytes()), source_controls_sha256=sha(control_path.read_bytes()),
                  input_max_bytes=max(len(frame) for frame, _ in encoded), decoded_buffers_bytes=1900,
                  stack_reserved_bytes=64, ram_placement='Code/input/stack in fixed uncontended bank2; two950-byte buffers in paged uncontended bank0; no paging during decode.',
                  complete_benchmark_working_ram_bytes=1281 + max(len(frame) for frame, _ in encoded) + 1900 + 64,
                  python_version=sys.version, numpy_version=np.__version__,
                  exclusions=['TR-DOS/physical disk or tape delivery', 'video workload', 'ULA/IO contention', 'actual sound synthesis or hardware transitions'],
                  runs=runs, rejected_partial_schedules=rejected,
                  initial_harness_attempt='Standard one-field preparation with eager swap after the old final field underflowed; corrected swap to occur before the new first field, then reran all measurements.',
                  turbo_vs_standard_mean_delta_tstates=runs[1]['mean_block_tstates'] - runs[0]['mean_block_tstates'],
                  producer_sources_sha256_lf={name: sha(path.read_bytes().replace(b'\r\n', b'\n')) for name, path in
                      [('benchmark.py', Path(__file__)), ('build_zxv_trd.py', TOOLKIT / 'build_zxv_trd.py'),
                       ('validate_fast_sparse.py', TOOLKIT / 'validate_fast_sparse.py'),
                       ('validate_streaming_player.py', TOOLKIT / 'validate_streaming_player.py'),
                       ('zx0_codec.py', TOOLKIT / 'zx0_codec.py'),
                       ('dzx0_standard.asm', TOOLKIT / 'third_party/zx0/dzx0_standard.asm'),
                       ('dzx0_turbo.asm', TOOLKIT / 'third_party/zx0/dzx0_turbo.asm')]})
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
