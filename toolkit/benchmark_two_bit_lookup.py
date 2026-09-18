"""Exhaustively check a Z80 lookup primitive for four packed 2-bit pixels.

B and C hold two aligned input bytes; H points to an aligned 256-byte lookup
page. Result A, clobbers D/L/flags; B/C/H preserved. Entry-to-RET only.
Excluded: CALL, loading/alignment of input bytes, output stores, loops, paging,
IRQ, ULA, ROM, disk, ZX0 and scheduling. This is NOT an integrated player.
Timings: Zilog UM008011-0816 pp.71,74,158,160,209,285.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_halfpel_motion import blend_table
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU


def primitive():
    rows = []

    def add(mnemonic, code, tstates):
        rows.append(dict(instruction=mnemonic, code=code, tstates=tstates))

    def swap():
        for _ in range(4):
            add('RRCA', [0x0f], 4)

    add('LD A,C', [0x79], 4); swap()
    add('AND 0Fh', [0xe6, 0x0f], 7)
    add('LD L,A', [0x6f], 4)
    add('LD A,B', [0x78], 4)
    add('AND F0h', [0xe6, 0xf0], 7)
    add('OR L', [0xb5], 4)
    add('LD L,A', [0x6f], 4)
    add('LD A,(HL)', [0x7e], 7); swap()
    add('LD D,A', [0x57], 4)
    add('LD A,B', [0x78], 4); swap()
    add('AND F0h', [0xe6, 0xf0], 7)
    add('LD L,A', [0x6f], 4)
    add('LD A,C', [0x79], 4)
    add('AND 0Fh', [0xe6, 0x0f], 7)
    add('OR L', [0xb5], 4)
    add('LD L,A', [0x6f], 4)
    add('LD A,(HL)', [0x7e], 7)
    add('OR D', [0xb2], 4)
    add('RET', [0xc9], 10)
    return bytes(byte for row in rows for byte in row['code']), rows


def expand_table(symbols):
    return bytes((int(symbols[a >> 2, b >> 2]) << 2) | int(symbols[a & 3, b & 3])
                 for a in range(16) for b in range(16))


def exhaustive(code, symbols, expected_tstates):
    cpu = CPU(b'', b'')
    for index, value in enumerate(code):
        cpu.write8(0x8000 + index, value)
    table = expand_table(symbols)
    for index, value in enumerate(table):
        cpu.write8(0xa400 + index, value)
    # Independent whole-byte expectation; no nibble-table expansion used here.
    values = np.arange(256, dtype=np.uint16)
    expected = np.zeros((256, 256), dtype=np.uint16)
    for shift in (6, 4, 2, 0):
        expected |= symbols[(values[:, None] >> shift) & 3, (values[None, :] >> shift) & 3].astype(np.uint16) << shift
    for first in range(256):
        for second in range(256):
            cpu.b, cpu.c, cpu.h = first, second, 0xa4
            cpu.pc, cpu.sp = 0x8000, 0xbff0
            cpu.push(0x5f00)
            before = cpu.tstates
            steps = cpu.steps
            while cpu.pc != 0x5f00:
                if cpu.steps - steps > 64:
                    raise AssertionError('kernel did not return')
                cpu.step()
            if cpu.a != expected[first, second] or cpu.tstates - before != expected_tstates:
                raise AssertionError((first, second, cpu.a, expected[first, second], cpu.tstates - before))
            if (cpu.b, cpu.c, cpu.h, cpu.sp) != (first, second, 0xa4, 0xbff0):
                raise AssertionError('register/stack contract broken')
    return dict(input_pairs=65536, cpu_tstates=expected_tstates,
                lookup_bytes=len(table), lookup_sha256=sha(table), complete=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--motion-report', type=Path)
    parser.add_argument('--motion-cache', type=Path)
    args = parser.parse_args()
    code, listing = primitive()
    ticks = sum(row['tstates'] for row in listing)
    identity = np.broadcast_to(np.arange(4, dtype=np.uint8)[:, None], (4, 4))
    reference = exhaustive(bytes([0x78, 0xc9]), identity, 14)
    report = dict(scope=__doc__, timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
                  baseline_commit='8dd09de', code_bytes=len(code), code_hex=code.hex(),
                  listing=listing, table_counted_tstates=ticks,
                  primitive_before_tstates=14, primitive_after_tstates=ticks,
                  primitive_delta_tstates=ticks - 14, reference=reference,
                  variants={name: exhaustive(code, blend_table(upper), ticks)
                            for name, upper in [('lower', False), ('upper', True)]},
                  player_changed=False, integrated_player_delta_tstates=0,
                  full_decoder_tstates_measured=False)
    if args.motion_report:
        if not args.motion_cache:
            parser.error('--motion-cache required with --motion-report')
        motion_report = json.loads(args.motion_report.read_text())
        report['motion_report_sha256'] = sha(args.motion_report.read_bytes())
        report['motion_frequency'] = []
        for row in motion_report['rows']:
            vectors = np.load(args.motion_cache / (row['name'] + '.npz'))['vectors']
            kinds = np.array([(x & 1) + 2 * (y & 1) for x, y in row['offsets']] + [0])
            selected = kinds[vectors]
            per_frame = np.count_nonzero(selected, axis=1)
            report['motion_frequency'].append(dict(name=row['name'], frames=len(vectors),
                integer_or_zero_tiles=int(np.count_nonzero(selected == 0)),
                horizontal_half_tiles=int(np.count_nonzero(selected == 1)),
                vertical_half_tiles=int(np.count_nonzero(selected == 2)),
                both_half_tiles=int(np.count_nonzero(selected == 3)),
                fractional_tiles_per_frame_mean=float(np.mean(per_frame)),
                fractional_tiles_per_frame_max=int(per_frame.max())))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'listing'}), flush=True)


if __name__ == '__main__':
    main()
