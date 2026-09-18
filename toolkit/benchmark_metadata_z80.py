"""Z80 primitive for an eight-byte sparse mask, with exact instruction counts.

Input C=presence flags (MSB first), HL=nonzero bytes, DE=output; RET restores
the caller stack. At most eight bytes are read/written. No persistent decoder
state or private stack: caller supplies flag/addresses for the next packet.
Model excludes caller setup/CALL, paging, ZX0, IRQ, ULA, ROM and disk.
It is a building block, not a full FPM1 reader or release schedule.
"""
import argparse
import json
from pathlib import Path

from build_zxv_trd import MiniAssembler
from probe_lossless_layouts import sha
from probe_motion_metadata import split, sparse
from benchmark_huffman_z80 import FPE_SHA
from validate_fast_sparse import CPU


def build():
    a = MiniAssembler(0x8000)
    listing = []

    def emit(name, values, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks))
        a.emit(*values)

    emit('LD B,8', [0x06, 8], 7)
    a.label('bit')
    emit('XOR A', [0xaf], 4)
    emit('RLC C', [0xcb, 0x01], 8)
    listing.append(dict(address=a.pc, instruction='JR NC,zero', tstates=[7, 12]))
    a.rel8(0x30, 'zero')
    emit('LD A,(HL)', [0x7e], 7)
    emit('INC HL', [0x23], 6)
    a.label('zero')
    emit('LD (DE),A', [0x12], 7)
    emit('INC DE', [0x13], 6)
    listing.append(dict(address=a.pc, instruction='DJNZ bit', tstates=[8, 13]))
    a.rel8(0x10, 'bit')
    emit('RET', [0xc9], 10)
    return a.resolve(), listing


class Harness:
    def __init__(self):
        self.cpu = CPU(b'', b'')
        self.cpu.sp = 0xbff0
        self.code, self.listing = build()
        self.timings = {r['address']: r['tstates'] for r in self.listing}
        for i, b in enumerate(self.code):
            self.cpu.write8(0x8000+i, b)

    def run(self, flags, values):
        if flags.bit_count() != len(values) or any(not b for b in values):
            raise ValueError('invalid sparse packet')
        cpu = self.cpu
        for i, b in enumerate(values):
            cpu.write8(0x6000+i, b)
        for i in range(10):
            cpu.write8(0xa400+i, 0xa5)
        cpu.set_hl(0x6000); cpu.set_de(0xa400); cpu.c = flags
        cpu.pc = 0x8000; cpu.push(0x8f00)
        before = cpu.tstates
        while cpu.pc != 0x8f00:
            pc, ticks = cpu.pc, cpu.tstates
            cpu.step()
            expected = self.timings[pc]
            if cpu.tstates-ticks not in (expected if isinstance(expected, list) else [expected]):
                raise AssertionError('instruction timing mismatch')
        elapsed = cpu.tstates-before
        if (elapsed != 412+8*len(values) or cpu.hl() != 0x6000+len(values)
                or cpu.de() != 0xa408 or cpu.sp != 0xbff0 or cpu.c != flags):
            raise AssertionError('primitive contract/timing mismatch')
        if bytes(cpu.read8(0xa408+i) for i in range(2)) != b'\xa5\xa5':
            raise AssertionError('output overrun')
        output = bytes(cpu.read8(0xa400+i) for i in range(8))
        return output, elapsed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpe', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.fpe.read_bytes()
    if sha(data) != FPE_SHA:
        raise ValueError('unexpected full movie')
    _, groups = split(data)
    h = Harness()
    # Exhaust all flag patterns on real Z80 instructions; later sum the exact
    # verified formula over the whole movie. Full film CPU execution is NOT claimed.
    verified = 0
    for flags in range(256):
        for values in (bytes([1])*flags.bit_count(),
                       bytes((i*37+1) % 255+1 for i in range(flags.bit_count()))):
            out, _ = h.run(flags, values)
            iterator = iter(values)
            expected = bytes(next(iterator) if flags & (128 >> i) else 0 for i in range(8))
            if out != expected:
                raise AssertionError('sparse output mismatch')
            verified += 1
    totals = {name: dict(packets=0, nonzero=0, padded_output_bytes=0, tstates=0)
              for name in ('mask_bytes', 'mask_presence_bytes')}
    rows = []
    for index, (n, _, masks, _) in enumerate(groups):
        flags, _ = sparse(masks)
        group = dict(index=index, frames=n)
        for name, raw in (('mask_bytes', masks), ('mask_presence_bytes', flags)):
            packets, nonzero = (len(raw)+7)//8, sum(b != 0 for b in raw)
            ticks = 412*packets+8*nonzero
            group[name+'_tstates'] = ticks
            for key, value in dict(packets=packets, nonzero=nonzero,
                                   padded_output_bytes=packets*8, tstates=ticks).items():
                totals[name][key] += value
        rows.append(group)
    mask_bytes = sum(len(g[2]) for g in groups)
    # Reference LD A,B / OR C / RET Z / LDIR / RET = 21*N+18, N>0.
    before = 21*mask_bytes+18*len(groups)
    one = totals['mask_bytes']['tstates']
    two = one+totals['mask_presence_bytes']['tstates']
    report = dict(scope=__doc__, input_sha256=sha(data), frames=4971, groups=len(groups),
        complete=True, coverage='512 actual Z80 fixtures; full-film totals use the verified formula',
        z80_fixtures_verified=verified, code_bytes=len(h.code), code_sha256=sha(h.code),
        instructions=h.listing, formula='412 + 8*nonzero; caller CALL adds 17 T',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        totals=totals, groups_detail=rows, summary=dict(copy_before_tstates=before,
            sparse1_tstates=one, sparse1_delta_tstates=one-before,
            sparse2_tstates=two, sparse2_delta_tstates=two-before,
            max_quantum_tstates=476, per_call_instruction='RET included; caller setup/CALL excluded'),
        full_player_measured=False, integrated_player_delta_tstates=0)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
