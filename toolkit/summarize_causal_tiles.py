"""Compare full causal Z80 variants and check mask-skip timing independently.

Queue bounds exclude screen drawing, metadata/ZX0, refill, IRQ/ULA/ROM/disk.
Even a passing bound would not prove 25/3 fps. Same-input baseline vs
skip_empty is an isolated hot-path comparison; prior value-only wrappers
are a different, narrower scope.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_split_metadata import header
from summarize_context_cpu import minimum_capacity, queue_bound


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpd', type=Path, required=True)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    before, after = [json.loads((args.reports/name).read_text(encoding='utf-8')) for name in (
        'causal_tiles_cpu_measurements.json', 'causal_tiles_skip_empty_cpu_measurements.json')]
    data = args.fpd.read_bytes()
    if any(not report['complete'] or report['input_sha256'] != sha(data) for report in (before, after)):
        raise ValueError('incomplete/different CPU inputs')
    r = Reader(data)
    _, remaining = header(r)
    start, counts, frame_deltas = 0, Counter(), []
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        r.take(vl)
        masks = restore(r.take(ml), n, 480, 4)
        bits = int.from_bytes(r.take(4), 'little'); r.take((bits+7)//8)
        for frame in range(n):
            row = Counter()
            for tile in range(192):
                a, b = masks[frame*384+tile*2:frame*384+tile*2+2]
                row['both_bitmap_halves' if a and b else 'first_bitmap_half' if a else 'second_bitmap_half' if b else 'empty_bitmap_tile'] += 1
                attr = masks[n*384+frame*96+tile//2]
                nibble = (attr >> 4) if tile % 2 == 0 else attr & 15
                row['nonempty_attribute_nibble' if nibble else 'empty_attribute_nibble'] += 1
            delta = (46*row['both_bitmap_halves']-159*row['first_bitmap_half']-169*row['second_bitmap_half']
                     +21*row['nonempty_attribute_nibble']-78*row['empty_attribute_nibble'])
            old, new = before['frames'][start+frame], after['frames'][start+frame]
            if (new['total_tstates']-old['total_tstates'] != delta
                    or new['bits'] != old['bits'] or new['values'] != old['values']
                    or any(old['stages'].get(k, 0) != new['stages'].get(k, 0) for k in ('huffman', 'cache', 'motion', 'control'))):
                raise AssertionError(f'timing/coverage differs at frame {start+frame}')
            frame_deltas.append(delta); counts.update(row)
        start += n; remaining -= n
    r.end()
    if start != 4971 or len(before['frames']) != start or len(after['frames']) != start:
        raise ValueError('incomplete movie')
    if any(row['stages']['cache'] != 58792 for report in (before, after) for row in report['frames']):
        raise AssertionError('row-cache instruction formula differs')
    result = dict(scope=__doc__, baseline_commit='2f3ce3f', complete=True, input_sha256=sha(data),
        before=before['summary'], after=after['summary'],
        old_code_bytes=before['code_bytes'], new_code_bytes=after['code_bytes'],
        measured_delta_tstates=after['summary']['total_tstates']-before['summary']['total_tstates'],
        independent_formula_delta_tstates=sum(frame_deltas), mask_counts=dict(counts),
        formula='46*both_bitmap_halves -159*first_only -169*second_only +21*nonempty_attr_nibbles -78*empty_attr_nibbles',
        cache_tstates_per_frame=58792,
        cache_formula='96*(533+27+13)+24*21+12*5 + 8*(356+27+13)+2*21+2*5; excludes external CALLs counted in control',
        old_two_compact_frames_bytes=7680, new_frame_and_cache_bytes=4864, history_memory_delta_bytes=-2816,
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        idealized_queue=[])
    for budget in (425448, 350000, 300000, 250000):
        work = [row['total_tstates'] for row in after['frames']]
        result['idealized_queue'].append(dict(budget_tstates=budget,
            baseline_minimum_capacity=minimum_capacity([r['total_tstates'] for r in before['frames']], budget),
            optimized_minimum_capacity=minimum_capacity(work, budget),
            rows=[queue_bound(work, k, budget) for k in range(1, 17)]))
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'idealized_queue'}, indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k != 'rows'} for r in result['idealized_queue']]))


if __name__ == '__main__':
    main()
