"""Bound the benefit of whole-row zero/uniform tests on the exact movie.

Read the saved compact states and archived-stream native-mask profile. Check
every dense row against the executed CPU profile, including each frame and
independent-volume warmup. No new Z80 or playback is executed. The optimistic
bounds charge only the first failed test and make successful fills free;
positive deltas therefore reject these particular dispatch strategies.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from build_fap3_trd import sha
from cell_screen_z80 import build

ROOT = Path(__file__).parent


def candidates(zero, same, row_tstates):
    """Lower bounds, not predicted costs of a complete implementation."""
    # Zero: LD A,(HL) 7; OR A 4; JP NZ,normal 10. No cursor restoration.
    # Uniform: LD A,(HL) 7; INC L 4; CP (HL) 7; JP Z,scan_more 10;
    # DEC L 4 on the first unequal pair, falling through to normal output.
    return [
        dict(name='whole_zero_row', immediate_failures=zero[0], successes=zero[32],
             failed_test_tstates=21,
             optimistic_delta_tstates=21*zero[0]-row_tstates*zero[32]),
        dict(name='whole_uniform_row', immediate_failures=same[1], successes=same[32],
             failed_test_tstates=32,
             optimistic_delta_tstates=32*same[1]-row_tstates*same[32]),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--states', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'flat_dense_rows_profile.json')
    args = parser.parse_args()
    names = ('frame_hotspot_profile.json', 'dense_band_threshold_profile.json')
    profile, masks = [json.loads((ROOT/name).read_bytes()) for name in names]
    if not (profile['complete'] and profile['full_compact_and_both_native_exact']
            and masks['complete']):
        raise ValueError('incomplete reference evidence')
    if sha((ROOT/'cell_screen_z80.py').read_bytes()) != profile['source_sha256']['cell_screen_z80.py']:
        raise ValueError('renderer differs from executed baseline')
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    if (states.dtype != np.uint8 or states.shape != (profile['checked_frames'], 3840)
            or sha(states.tobytes()) != profile['states_sha256']):
        raise ValueError('different compact states')
    _, labels, listing, _ = build(fast_mask_dispatch=True, constant_attribute_borders=True,
                                  skip_black_borders=True, gray_cells=True)
    pixel_rows = [row for row in listing if row['stage'] == 'dense_pixels']
    row_tstates = sum(row['tstates'] for row in pixel_rows)
    if row_tstates != 32*51 or pixel_rows[0]['address'] != labels['dense_row']:
        raise ValueError('dense-row instruction baseline differs')
    report = dict(scope=__doc__, complete=False, release=False, baseline_commit='7a1d5de',
        cpu_profile_configuration='HL-reader; compact cursor does not change native output',
        implemented=False, actual_new_playback_measured=False, new_z80_executed=False,
        states_sha256=sha(states.tobytes()),
        reference_sha256={name: sha((ROOT/name).read_bytes()) for name in names},
        source_sha256={name: sha((ROOT/name).read_bytes()) for name in
                       ('profile_flat_dense_rows.py', 'cell_screen_z80.py')},
        compressed_stream_delta_bytes=0, actual_player_cpu_delta_tstates=0,
        compact_row_pixels=128, native_row_pixels=256,
        compact_row_bytes=32, native_rows_per_compact_row=2,
        baseline_dense_row_tstates=row_tstates,
        histogram_key='First nonzero/different byte offset; 32 means all zero/all equal',
        optimistic_assumptions=[
            'Only whole-row replacement; unsuccessful tests retain the complete existing pixel body.',
            'Common dense row/page/band control is unchanged.',
            'Charge only rows rejected by the first test; all later tests and failures cost zero.',
            'Successful tests and their 64 native-byte fills cost zero, removing all 1632 pixel T.',
            'Ignore placement, bootstrap bytes, IRQ, contention and disk effects.',
        ],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', volumes=[])
    all_zero, all_same = Counter(), Counter()
    first = 0
    for volume, maps in zip(profile['volumes'], masks['volumes'], strict=True):
        if (volume['part'] != maps['part'] or volume['start'] != first
                or len(maps['frames']) != volume['end']-first):
            raise ValueError('volume boundaries differ')
        zero, same, frames = Counter(), Counter(), []
        for old, mask in zip(volume['frames'], maps['frames'], strict=True):
            index = first+mask['local_frame']
            if old['frame'] != index or len(mask['bands']) != 18:
                raise ValueError('frame/band coverage differs')
            z, s = Counter(), Counter()
            for band, (common, marked, parity) in enumerate(mask['bands'], 1):
                if parity != band & 1 or (common == 255) != (marked == 32):
                    raise ValueError('dense mask summary differs')
                if common != 255:
                    continue
                # Native map band zero begins at compact row eight. Visible
                # bands 1..18 therefore cover compact rows 12..83.
                for row in range(8+4*band, 12+4*band):
                    data = states[index, row*32:(row+1)*32].tobytes()
                    z[next((i for i, value in enumerate(data) if value), 32)] += 1
                    s[next((i for i, value in enumerate(data) if value != data[0]), 32)] += 1
            count = sum(z.values())
            actual = old['stages'].get('output/dense_pixels', 0)
            if count != sum(s.values()) or actual != count*row_tstates:
                raise ValueError(('dense row count differs from executed frame', index, count, actual))
            zero.update(z)
            same.update(s)
            frames.append(dict(frame=index, dense_rows=count, all_zero_rows=z[32],
                uniform_rows=s[32], first_byte_nonzero=z[0], first_pair_unequal=s[1],
                baseline_pixel_tstates=actual,
                candidates=candidates(z, s, row_tstates)))
        saved = dict(part=volume['part'], start=first, end=volume['end'],
            frames=frames, dense_rows=sum(zero.values()),
            baseline_pixel_tstates=sum(f['baseline_pixel_tstates'] for f in frames),
            first_nonzero_histogram=dict(sorted(zero.items())),
            first_difference_histogram=dict(sorted(same.items())),
            candidates=candidates(zero, same, row_tstates))
        for candidate in saved['candidates']:
            if candidate['optimistic_delta_tstates'] != sum(
                    next(c['optimistic_delta_tstates'] for c in f['candidates']
                         if c['name'] == candidate['name']) for f in frames):
                raise AssertionError('per-frame candidate arithmetic differs')
        report['volumes'].append(saved)
        all_zero.update(zero)
        all_same.update(same)
        first = volume['end']
    if first != len(states) or first != masks['frames']:
        raise ValueError('incomplete movie coverage')
    report.update(complete=True, checked_frames=first, dense_rows=sum(all_zero.values()),
        baseline_pixel_tstates=sum(all_zero.values())*row_tstates,
        first_nonzero_histogram=dict(sorted(all_zero.items())),
        first_difference_histogram=dict(sorted(all_same.items())),
        candidates=candidates(all_zero, all_same, row_tstates))
    report['decision'] = ('Reject both whole-row tests before implementation; even their optimistic '
                          'whole-movie deltas are positive. This is not a bound for other fill methods.'
                          if all(c['optimistic_delta_tstates'] > 0 for c in report['candidates'])
                          else 'Measure full test/fill costs before considering implementation.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({key: report[key] for key in
                     ('complete', 'checked_frames', 'dense_rows', 'candidates', 'decision')}, indent=2))


if __name__ == '__main__':
    main()
