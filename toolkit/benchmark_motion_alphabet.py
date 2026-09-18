"""Compare register XOR with an exact predictor-conditioned Z80 lookup.

Entry-to-RET primitive only, B=predicted byte, C=correction byte, A=result.
Lookup has an aligned 256-byte table at H:00, destroys D/L/flags.
Both preserve B/C/H. Excludes CALL, input/output, traversal, paging, IRQ,
ULA, ROM, disk and ZX0. This is not the complete frame decoder.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_two_bit_lookup import exhaustive, primitive
from probe_lossless_layouts import sha
from probe_motion_alphabet import INPUT_STATES_SHA, counts_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alphabet-report', type=Path, required=True)
    parser.add_argument('--motion-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.alphabet_report.read_text(encoding='utf-8'))
    with np.load(args.motion_cache) as saved:
        states, residual = saved['states'], saved['residual']
    if not source['complete'] or sha(states.tobytes()) != INPUT_STATES_SHA:
        raise ValueError('incomplete or unexpected input')
    if counts_for(states, residual).tolist() != source['predicted_to_actual_counts']:
        raise ValueError('residual does not match the measured alphabet')
    changed = np.count_nonzero(residual[:, :3072], axis=1)
    code, listing = primitive()
    ticks = sum(row['tstates'] for row in listing)
    xor_symbols = np.array([[p ^ c for c in range(4)] for p in range(4)], dtype=np.uint8)
    before_listing = [dict(instruction='LD A,B', code=[0x78], tstates=4),
                      dict(instruction='XOR C', code=[0xa9], tstates=4),
                      dict(instruction='RET', code=[0xc9], tstates=10)]
    before_code = bytes(b for row in before_listing for b in row['code'])
    before = sum(row['tstates'] for row in before_listing)
    result = dict(scope=__doc__, baseline_commit='8dd09de',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        timing_pages=[71, 74, 158, 160, 162, 209, 285],
        input_report_sha256=sha(args.alphabet_report.read_bytes()),
        input_states_sha256=INPUT_STATES_SHA,
        reference_listing=before_listing, reference=exhaustive(before_code, xor_symbols, before),
        code_hex=code.hex(), code_bytes=len(code), listing=listing,
        primitive_before_tstates=before, primitive_after_tstates=ticks,
        primitive_delta_tstates=ticks - before, variants={},
        bitmap_corrections_per_frame_mean=float(changed.mean()),
        bitmap_corrections_per_frame_max=int(changed.max()),
        bitmap_corrections_total=int(changed.sum()),
        estimated_extra_primitive_tstates_per_frame_mean=float(changed.mean() * (ticks - before)),
        estimated_extra_primitive_tstates_per_frame_max=int(changed.max() * (ticks - before)),
        player_changed=False, integrated_player_delta_tstates=0,
        full_decoder_tstates_measured=False)
    for row in source['rows']:
        symbols = np.array(row['symbols'], dtype=np.uint8)
        if symbols.shape != (4, 4) or any(sorted(r.tolist()) != list(range(4)) or r[0] != p
                                          for p, r in enumerate(symbols)):
            raise ValueError('invalid correction alphabet')
        result['variants'][row['name']] = exhaustive(code, symbols, ticks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if 'listing' not in k}), flush=True)


if __name__ == '__main__':
    main()
