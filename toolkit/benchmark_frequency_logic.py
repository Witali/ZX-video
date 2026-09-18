"""Exact fixed frequency-alphabet reconstruction without a lookup table.

For one pixel, p=(ph,pl) predicts the level and c=(ch,cl) is its code:
qh = ph XOR cl XOR (ph AND (ch XOR cl))
ql = pl XOR (ch AND NOT(ph AND pl)) XOR (cl AND (ph OR pl)).
The Z80 computes four pixels in parallel in alternating bit positions.
Two variants: freely uses D/E/H/L, or preserves B/C/E/H like the lookup
and only destroys D/L/flags. A=result. Entry-to-RET only. Loads/stores,
CALL, traversal, paging, ZX0, IRQ, ULA, ROM, disk and full-frame scheduling
are excluded. Fixed alphabet only; not a general replacement for any table.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_two_bit_lookup import exhaustive, primitive
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU

SYMBOLS = np.array([[0, 2, 1, 3], [1, 2, 0, 3], [2, 3, 1, 0], [3, 2, 1, 0]], dtype=np.uint8)


def logic_primitive(preserve=False):
    instructions = [
        ('LD A,B', [0x78], 4), ('RRCA', [0x0f], 4), ('LD D,A', [0x57], 4),
        ('OR B', [0xb0], 4), ('AND C', [0xa1], 4), ('LD E,A', [0x5f], 4),
        ('LD A,C', [0x79], 4), ('RRCA', [0x0f], 4), ('LD H,A', [0x67], 4),
        ('LD A,D', [0x7a], 4), ('AND B', [0xa0], 4), ('XOR FFh', [0xee, 255], 7),
        ('AND H', [0xa4], 4), ('XOR E', [0xab], 4), ('XOR B', [0xa8], 4),
        ('LD L,A', [0x6f], 4),
        ('LD A,H', [0x7c], 4), ('XOR C', [0xa9], 4), ('AND D', [0xa2], 4),
        ('XOR C', [0xa9], 4), ('XOR D', [0xaa], 4), ('ADD A,A', [0x87], 4),
        ('XOR L', [0xad], 4), ('AND AAh', [0xe6, 0xaa], 7), ('XOR L', [0xad], 4),
        ('RET', [0xc9], 10)]
    if preserve:
        instructions = [
            ('LD A,B', [0x78], 4), ('RRCA', [0x0f], 4), ('LD D,A', [0x57], 4),
            ('OR B', [0xb0], 4), ('AND C', [0xa1], 4), ('LD L,A', [0x6f], 4),
            ('LD A,D', [0x7a], 4), ('AND B', [0xa0], 4), ('CPL', [0x2f], 4),
            ('RRC C', [0xcb, 0x09], 8), ('AND C', [0xa1], 4), ('XOR L', [0xad], 4),
            ('XOR B', [0xa8], 4), ('LD L,A', [0x6f], 4),
            ('LD A,C', [0x79], 4), ('RLC C', [0xcb, 0x01], 8),
            ('XOR C', [0xa9], 4), ('AND D', [0xa2], 4), ('XOR C', [0xa9], 4),
            ('XOR D', [0xaa], 4), ('ADD A,A', [0x87], 4), ('XOR L', [0xad], 4),
            ('AND AAh', [0xe6, 0xaa], 7), ('XOR L', [0xad], 4), ('RET', [0xc9], 10)]
    listing = [dict(instruction=m, code=code, tstates=t) for m, code, t in instructions]
    return bytes(b for _, code, _ in instructions for b in code), listing


def check_logic(code, expected_tstates, preserve=False):
    cpu = CPU(b'', b'')
    for index, byte in enumerate(code):
        cpu.write8(0x8000 + index, byte)
    for predicted in range(256):
        for correction in range(256):
            expected = sum(int(SYMBOLS[(predicted >> shift) & 3, (correction >> shift) & 3]) << shift
                           for shift in (6, 4, 2, 0))
            cpu.b, cpu.c = predicted, correction
            # Poison all scratch registers; no state from the previous call is needed.
            cpu.a, cpu.d, cpu.e, cpu.h, cpu.l = 0xc7, 0x32, 0x91, 0xee, 0x1b
            cpu.pc, cpu.sp = 0x8000, 0xbff0
            cpu.push(0x5f00)
            start, steps = cpu.tstates, cpu.steps
            while cpu.pc != 0x5f00:
                if cpu.steps - steps > 64:
                    raise AssertionError('kernel did not return')
                cpu.step()
            if cpu.a != expected or cpu.tstates - start != expected_tstates:
                raise AssertionError((predicted, correction, expected, cpu.a, cpu.tstates - start))
            if (cpu.b, cpu.c, cpu.sp) != (predicted, correction, 0xbff0):
                raise AssertionError('register/stack contract broken')
            if preserve and (cpu.e, cpu.h) != (0x91, 0xee):
                raise AssertionError('E/H changed')
    return dict(input_pairs=65536, tstates=expected_tstates, lookup_bytes=0, complete=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alphabet-report', type=Path, required=True)
    parser.add_argument('--previous-cpu-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.alphabet_report.read_text())
    previous = json.loads(args.previous_cpu_report.read_text())
    frequency = next(row for row in source['rows'] if row['name'] == 'frequency')
    if not source['complete'] or frequency['symbols'] != SYMBOLS.tolist():
        raise ValueError('the fixed logic does not match the measured alphabet')
    if previous['input_report_sha256'] != sha(args.alphabet_report.read_bytes()):
        raise ValueError('unmatched correction frequency counts')
    code, listing = logic_primitive(preserve=True)
    ticks = sum(row['tstates'] for row in listing)
    free_code, free_listing = logic_primitive()
    free_ticks = sum(row['tstates'] for row in free_listing)
    reference, reference_listing = primitive()
    before = sum(row['tstates'] for row in reference_listing)
    report = dict(scope=__doc__, baseline_commit='cb7031f',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        timing_pages=[71, 145, 158, 160, 162, 175, 209, 213, 226, 285],
        alphabet_report_sha256=sha(args.alphabet_report.read_bytes()),
        previous_cpu_report_sha256=sha(args.previous_cpu_report.read_bytes()),
        symbols=SYMBOLS.tolist(), code_hex=code.hex(), code_bytes=len(code), listing=listing,
        previous=exhaustive(reference, SYMBOLS, before), current=check_logic(code, ticks, preserve=True),
        freely_clobbering=dict(code_hex=free_code.hex(), code_bytes=len(free_code), listing=free_listing,
                              verification=check_logic(free_code, free_ticks), preserved=['B', 'C']),
        primitive_before_tstates=before, primitive_after_tstates=ticks,
        primitive_delta_tstates=ticks-before,
        previous_preserved=['B', 'C', 'E', 'H'], current_preserved=['B', 'C', 'E', 'H'],
        register_contract_matches=True,
        estimated_primitive_saving_per_frame_mean=previous['bitmap_corrections_per_frame_mean'] * (before-ticks),
        estimated_primitive_saving_per_frame_max=previous['bitmap_corrections_per_frame_max'] * (before-ticks),
        player_changed=False, integrated_player_delta_tstates=0, full_decoder_tstates_measured=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'listing'}), flush=True)


if __name__ == '__main__':
    main()
