"""Run actual interleaved bounded ZX0 and Huffman on the complete FPE1 stream.

Huffman emits at most --quota bytes into A400; its 13-byte state survives
caller register clobber. ZX0 emits in 128-byte targets into 6000..7FFF,
with its existing saved-stack decoder. Compressed blocks reside in bank 0;
Huffman tables in bank 6. Paging and decoder calls execute on the Z80.

Host parses FPE1 headers/masks, supplies compressed blocks and drains the
output queue. Those tasks, table loading, disk/ROM/ULA/AY/IRQ, motion and
screen drawing are NOT modeled as player work. No release RAM/schedule claim.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from build_zxv_trd import MiniAssembler
from benchmark_huffman_z80 import FPE_SHA, transition_tables
import incremental_huffman
import incremental_zx0
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader, decode, groups, EXPECTED_SHA
from validate_fast_sparse import CPU

INPUT, OUTPUT, STACK, STOP, TABLE = 0x6000, 0xa400, 0xbff0, 0x8f00, 0xc000


class GuardCPU(CPU):
    mode = None
    huffman_state = (0, 0)
    zx0_code_end = 0
    quota = 32

    def write8(self, address, value):
        if self.mode:
            allowed = STACK-96 <= address < STACK
            if self.mode == 'huffman':
                allowed |= OUTPUT <= address < OUTPUT+self.quota
                allowed |= self.huffman_state[0] <= address < self.huffman_state[1]
            elif self.mode == 'zx0':
                allowed |= INPUT <= address < INPUT+8192
                allowed |= 0x9000 <= address < self.zx0_code_end
                allowed |= 0x9e00 <= address < 0x9e80
            if not allowed:
                raise AssertionError(f'{self.mode}: unexpected write {address:04x}')
        super().write8(address, value)


def word(cpu, address, value=None):
    if value is None:
        return cpu.read8(address) | cpu.read8(address+1) << 8
    cpu.write8(address, value)
    cpu.write8(address+1, value >> 8)


class Harness:
    def __init__(self, lengths, quota=32):
        self.quota = quota
        self.cpu = GuardCPU(b'', b'')
        self.cpu.quota = quota
        self.cpu.sp = STACK
        self.cpu.port_7ffd = 0x16
        self.tables, self.states = transition_tables(lengths)
        self.code, self.labels, self.listing = incremental_huffman.build(quota, max(lengths))
        self.timings = {row['address']: row['tstates'] for row in self.listing}
        self.histogram = Counter()
        self.quantum_histogram = Counter()
        self.cpu.huffman_state = (self.labels['state'], self.labels['state_end'])
        for address, data in ((0x8000, self.code), (TABLE, self.tables)):
            for i, b in enumerate(data):
                self.cpu.write8(address+i, b)

    def set(self, name, value):
        if name in ('byte', 'phase', 'status'):
            self.cpu.write8(self.labels[name], value)
        else:
            word(self.cpu, self.labels[name], value)

    def get(self, name):
        if name in ('byte', 'phase', 'status'):
            return self.cpu.read8(self.labels[name])
        return word(self.cpu, self.labels[name])

    def begin(self, count):
        if not 0 <= count <= 65535:
            raise ValueError('unsupported group size')
        for key, value in dict(source=INPUT, input_left=0, output=OUTPUT,
                               remaining=count, node=TABLE, byte=0, phase=0, status=0).items():
            self.set(key, value)

    def window(self, pointer, count):
        if self.get('input_left') or not INPUT <= pointer <= INPUT+8192 or not 0 <= count <= INPUT+8192-pointer:
            raise ValueError('cannot replace active or invalid input window')
        self.set('source', pointer)
        self.set('input_left', count)

    def poison(self):
        cpu = self.cpu
        cpu.set_bc(0xd372); cpu.set_de(0x182b); cpu.set_hl(0xf659)
        cpu.a, cpu.ix, cpu.z, cpu.carry = 0xa6, 0x1122, True, True
        cpu.alt_a, cpu.alt_b, cpu.alt_c = 0xb9, 0x35, 0x41
        cpu.alt_d, cpu.alt_e, cpu.alt_h, cpu.alt_l = 0x81, 0x69, 0x92, 0xce
        cpu.alt_z, cpu.alt_carry = True, True

    def run(self, interrupt=None):
        cpu = self.cpu
        self.set('output', OUTPUT)
        for i in range(self.quota):
            cpu.write8(OUTPUT+i, 0)
        source, left, remaining = (self.get(n) for n in ('source', 'input_left', 'remaining'))
        self.poison()
        cpu.pc = self.labels['run']
        cpu.push(STOP)
        cpu.mode = 'huffman'
        before, steps, extra = cpu.tstates, 0, 0
        modes = set()
        while cpu.pc != STOP:
            pc, ticks = cpu.pc, cpu.tstates
            if pc == self.labels['checked_select']:
                modes.add('checked')
            if pc == self.labels['fast_select']:
                modes.add('fast')
            cpu.step()
            steps += 1
            cost = cpu.tstates-ticks
            allowed = self.timings[pc]
            if cost not in (allowed if isinstance(allowed, list) else [allowed]):
                raise AssertionError(f'timing-table mismatch at {pc:04x}')
            self.histogram[pc, cost] += 1
            if steps > 20000:
                raise AssertionError('unbounded producer call')
            if interrupt and cpu.pc != STOP:
                extra += interrupt(cpu)
        cpu.mode = None
        elapsed = cpu.tstates-before-extra
        self.quantum_histogram[elapsed] += 1
        size = self.get('output')-OUTPUT
        used = self.get('source')-source
        if not 0 <= size <= self.quota or not 0 <= used <= left or cpu.sp != STACK:
            raise AssertionError('buffer/input/stack contract broken')
        if self.get('remaining') != remaining-size or self.get('input_left') != left-used:
            raise AssertionError('incorrect persistent counters')
        status = self.get('status')
        if status == 0 and (size != self.quota or not self.get('remaining')):
            raise AssertionError('invalid quota stop')
        if status == 1 and self.get('input_left'):
            raise AssertionError('spurious input request')
        if status == 2 and self.get('remaining'):
            raise AssertionError('premature finish')
        if status not in (0, 1, 2):
            raise AssertionError('unknown status')
        output = bytes(cpu.read8(OUTPUT+i) for i in range(size))
        return output, dict(tstates=elapsed, irq_tstates=extra, bytes=size, input_bytes=used,
                            status=status, path=next(iter(modes), 'empty'))


def build_zx0_driver():
    a = MiniAssembler(0x9000)
    # Wrapper includes bank switches, CALL and RET. CPU decoder is suspended
    # in the existing private stack while the Huffman producer runs.
    for name, target in [('begin_wrapper', 'slice_begin'), ('resume_wrapper', 'slice_until')]:
        a.label(name)
        a.emit(0x01, 0xfd, 0x7f, 0x3e, 0x10, 0xed, 0x79)
        a.abs16(0xcd, target)
        a.emit(0x01, 0xfd, 0x7f, 0x3e, 0x16, 0xed, 0x79, 0xc9)
    incremental_zx0.emit_decoder(a, output_base=INPUT, input_base=TABLE, stack_top=0x9e80)
    incremental_zx0.emit_variables(a)
    for label in ('block_end', 'block_stored', 'block_length'):
        a.label(label); a.word(0)
    a.label('fatal'); a.emit(0xc9)
    return a.resolve(), a.labels


class Provider:
    def __init__(self, harness, raw, storage, cache):
        self.harness, self.cpu = harness, harness.cpu
        self.raw, self.storage, self.cache = raw, storage, cache
        self.code, self.labels = build_zx0_driver()
        if 0x9000+len(self.code) > 0x9d00:
            raise ValueError('ZX0 code reaches reserved stack space')
        self.cpu.zx0_code_end = 0x9000+len(self.code)
        for i, b in enumerate(self.code):
            self.cpu.write8(0x9000+i, b)
        self.index, self.ready, self.calls = -1, 0, []
        self.block_rows = []

    def load_next(self):
        self.index += 1
        block = self.storage['blocks'][self.index]
        self.expected = self.raw[self.index*8192:self.index*8192+block['decoded_bytes']]
        if sha(self.expected) != block['sha256']:
            raise ValueError('storage report block mismatch')
        payload = (self.cache / (block['sha256'] + '.zx0')).read_bytes()
        if len(payload) != block['zx0_bytes'] or len(payload) > 16384:
            raise ValueError('invalid compressed block')
        self.cpu.port_7ffd = 0x10  # Host supplies disk data; timing is excluded.
        for i, b in enumerate(payload):
            self.cpu.write8(TABLE+i, b)
        self.cpu.port_7ffd = 0x16
        word(self.cpu, self.labels['block_end'], INPUT+len(self.expected))
        word(self.cpu, self.labels['block_stored'], 0)
        word(self.cpu, self.labels['block_length'], len(self.expected))
        self.ready = 0
        self.block_rows.append(dict(index=self.index, bytes=len(self.expected), tstates=0, calls=0))

    def advance(self, target):
        while self.ready < target:
            limit = min(len(self.expected), self.ready+128)
            word(self.cpu, self.labels['slice_target'], INPUT+limit)
            saved = bytes(self.cpu.read8(i) for i in range(*self.cpu.huffman_state))
            self.harness.poison()
            self.cpu.pc = self.labels['begin_wrapper' if not self.ready else 'resume_wrapper']
            self.cpu.push(STOP)
            self.cpu.mode = 'zx0'
            before, steps = self.cpu.tstates, self.cpu.steps
            while self.cpu.pc != STOP:
                if self.cpu.pc == self.labels['fatal'] or self.cpu.steps-steps > 20000:
                    raise AssertionError('ZX0 failure or unbounded quantum')
                self.cpu.step()
            self.cpu.mode = None
            elapsed = self.cpu.tstates-before
            if self.cpu.sp != STACK or self.cpu.port_7ffd != 0x16:
                raise AssertionError('ZX0 did not restore caller stack/table bank')
            if saved != bytes(self.cpu.read8(i) for i in range(*self.cpu.huffman_state)):
                raise AssertionError('ZX0 damaged suspended Huffman state')
            if word(self.cpu, self.labels['slice_output']) != INPUT+limit:
                raise AssertionError('wrong ZX0 output boundary')
            if bytes(self.cpu.read8(INPUT+i) for i in range(self.ready, limit)) != self.expected[self.ready:limit]:
                raise AssertionError('ZX0 bytes changed')
            self.calls.append(elapsed)
            self.block_rows[-1]['calls'] += 1
            self.block_rows[-1]['tstates'] += elapsed
            self.ready = limit

    def through(self, position):
        # Ensure all stream bytes before position, including metadata, have
        # really passed through the Z80. Metadata parsing itself stays on PC.
        if position <= 0:
            return
        block = (position-1)//8192
        while self.index < block:
            if self.index >= 0:
                self.advance(len(self.expected))
            self.load_next()
        self.advance(position-self.index*8192)

    def window(self, position, end):
        self.through(position+1)
        offset = position-self.index*8192
        return INPUT+offset, min(self.ready-offset, end-position)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpe', type=Path, required=True)
    p.add_argument('--storage-report', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--quota', type=int, default=32, choices=(16, 32, 64))
    args = p.parse_args()
    data = args.fpe.read_bytes()
    storage = json.loads(args.storage_report.read_text())
    baseline = json.loads(args.baseline.read_text())
    if sha(data) != FPE_SHA or not storage['complete'] or storage['input_sha256'] != FPE_SHA:
        raise ValueError('unexpected FPE/storage data')
    if not baseline['complete'] or baseline['input_sha256'] != FPE_SHA:
        raise ValueError('unexpected full-film baseline')
    original = decode(data)
    if sha(original) != EXPECTED_SHA:
        raise ValueError('unexpected movie')
    header, parsed = groups(original)
    reader = Reader(data)
    if reader.take(5) != b'FPE1\xff':
        raise ValueError('not Huffman FPE')
    lengths = reader.take(reader.u16())
    if reader.take(reader.u16()) != header:
        raise ValueError('header mismatch')
    harness = Harness(lengths, args.quota)
    provider = Provider(harness, data, storage, args.cache)
    report = dict(scope=__doc__, baseline_commit='a111b58', input_sha256=sha(data),
        baseline_report_sha256=sha(args.baseline.read_bytes()), quota=args.quota,
        huffman_code_and_state_bytes=len(harness.code), state_bytes=13,
        code_sha256=sha(harness.code), tables_bytes=len(harness.tables), tables_sha256=sha(harness.tables),
        zx0_code_and_state_bytes=len(provider.code), zx0_code_sha256=sha(provider.code),
        zx0_target_step=128, input_history_bytes=8192, output_queue_bytes=args.quota,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        instructions=harness.listing, complete=False, groups=[],
        player_changed=False, integrated_player_delta_tstates=0, full_delivery_measured=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    paths, statuses, maximum = Counter(), Counter(), 0
    for index, (fixed, expected) in enumerate(parsed):
        if reader.take(len(fixed)) != fixed:
            raise AssertionError('fixed group fields differ')
        bits = int.from_bytes(reader.take(4), 'little')
        position = reader.pos
        encoded = reader.take((bits+7)//8)
        end = reader.pos
        provider.through(position)
        harness.begin(len(expected))
        output = bytearray()
        calls, total, top, refills = 0, 0, 0, 0
        while True:
            if not harness.get('input_left') and position < end:
                pointer, available = provider.window(position, end)
                harness.window(pointer, available)
                refills += 1
            chunk, row = harness.run()
            output += chunk
            position += row['input_bytes']
            calls += 1; total += row['tstates']; top = max(top, row['tstates'])
            paths[row['path']] += 1; statuses[row['status']] += 1
            if row['status'] == 2:
                break
            if row['status'] == 1 and position == end:
                raise AssertionError('unexpected compressed-input exhaustion')
        if bytes(output) != expected or position != end or harness.get('input_left'):
            raise AssertionError('group was not reconstructed exactly')
        before = baseline['groups'][index]['huffman_tstates']
        report['groups'].append(dict(index=index, values=len(expected), bits=bits, calls=calls,
            refills=refills, before_tstates=before, after_tstates=total, delta_tstates=total-before,
            max_quantum_tstates=top))
        maximum = max(maximum, top)
        if index % 25 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'Interleaved Z80 verified group {index+1}/{len(parsed)}', flush=True)
    reader.end()
    provider.through(len(data))
    if provider.index+1 != storage['blocks_expected']:
        raise AssertionError('not every ZX0 block executed')
    if bytes(harness.cpu.read8(TABLE+i) for i in range(len(harness.tables))) != harness.tables:
        raise AssertionError('lookup table changed')
    total = sum(row['after_tstates'] for row in report['groups'])
    counted = sum(ticks*count for (pc, ticks), count in harness.histogram.items())
    if counted != total:
        raise AssertionError('timing histogram differs from measured calls')
    report['complete'] = True
    report['instruction_execution_counts'] = [dict(address=pc, tstates=ticks, count=count)
        for (pc, ticks), count in sorted(harness.histogram.items())]
    report['quantum_histogram'] = dict(sorted(harness.quantum_histogram.items()))
    report['zx0_blocks'] = provider.block_rows
    report['summary'] = dict(groups=len(parsed), values=sum(len(v) for _, v in parsed),
        huffman_calls=sum(paths.values()), paths=dict(paths), statuses=dict(statuses),
        huffman_before_tstates=sum(row['before_tstates'] for row in report['groups']),
        huffman_after_tstates=total, huffman_delta_tstates=sum(row['delta_tstates'] for row in report['groups']),
        huffman_max_quantum_tstates=maximum, zx0_calls=len(provider.calls),
        zx0_total_tstates=sum(provider.calls), zx0_max_quantum_tstates=max(provider.calls),
        combined_measured_stages_tstates=total+sum(provider.calls))
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
