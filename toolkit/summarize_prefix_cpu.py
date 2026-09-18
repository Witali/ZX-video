"""Compare measured Huffman/ZX0 stages and optimistic full-frame queue bounds.

The old run uses frequency values with 64 bitmap contexts; the new run uses
direct bitmap bytes with 16 contexts. Same masks, motion, frames and number
of values, but DIFFERENT codes/streams. This is a candidate pipeline-stage
comparison, not an isolated same-input decoder benchmark or playback test.
"""
import argparse
import json
from pathlib import Path

from summarize_context_cpu import minimum_capacity, queue_bound


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        r = json.loads((args.reports/name).read_text(encoding='utf-8'))
        if not r['complete']:
            raise ValueError(f'incomplete {name}')
        return r

    old = load('context_huffman_unrolled_cpu_measurements.json')
    new = load('prefix_huffman_cpu_measurements.json')
    old_zx0 = load('context_masks_group_split_zx0_cpu_measurements.json')
    new_zx0 = load('direct_16_zx0_cpu_measurements.json')
    storage = load('direct_values_summary.json')
    selected = next(r for r in storage['rows'] if r['name'] == 'direct_16')
    if (old['fpr1_sha256'] != new['fpr1_sha256'] or old['states_sha256'] != new['states_sha256']
            or new['input_sha256'] != new_zx0['input_sha256'] or selected['sha256'] != new['input_sha256']
            or new['summary']['values'] != 1688733 or len(new['frames']) != 4971
            or [r['values'] for r in new['frames']] != [r['values'] for r in old['frames']]
            or new['summary']['wrapper_tstates'] != old['summary']['wrapper_tstates']):
        raise ValueError('incomparable inputs/coverage')
    result = dict(scope=__doc__, baseline_commit='fbf351e', complete=True,
        old=old['summary'], new=new['summary'],
        old_code_bytes=old['code_bytes'], new_code_bytes=new['code_bytes'],
        old_primitive_bytes=old['primitive_bytes'], new_primitive_bytes=new['primitive_bytes'],
        old_zx0=old_zx0['summary'], new_zx0=new_zx0['summary'],
        zx0_delta_tstates=new_zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates'],
        video_storage_bytes_before=storage['baseline_bytes'], video_storage_bytes_after=selected['zx0_with_headers_bytes'],
        storage_delta_bytes=selected['delta_vs_fpc3_bytes'],
        primitive_delta_tstates=new['summary']['primitive_tstates']['total']-old['summary']['primitive_tstates']['total'],
        bounded_delta_tstates=new['summary']['total_tstates']['total']-old['summary']['total_tstates']['total'],
        removed_bitmap_reconstruction=dict(values=1652491, previously_measured_primitive_tstates=117,
            estimated_removed_tstates=1652491*117, note='Separate prior frequency primitive, excludes external CALL/loading/storing; not added to the Huffman-only queue simulation.'),
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        idealized_queue=[])
    work = [r['total_tstates'] for r in new['frames']]
    primitive = [r['primitive_tstates'] for r in new['frames']]
    for budget in (425448, 350000, 300000, 250000, 200000, 150000):
        capacity = minimum_capacity(work, budget)
        result['idealized_queue'].append(dict(budget_tstates=budget,
            first_passing_capacity=capacity, primitive_only_minimum_capacity=minimum_capacity(primitive, budget),
            hypothetical_compact_frame_queue_bytes=capacity*3840,
            rows=[queue_bound(work, k, budget) for k in range(1, 17)]))
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'idealized_queue'}, indent=2))
    print(json.dumps([{k:v for k,v in row.items() if k != 'rows'} for row in result['idealized_queue']]))


if __name__ == '__main__':
    main()
