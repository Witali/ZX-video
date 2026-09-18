"""Compare complete context-decoder CPU runs and idealized value-queue bounds.

Queue simulation counts only measured bounded Huffman work. The first K
frames are predecoded before time zero; frame i displays at i*budget.
At most K finished frames wait, plus the frame being produced. It excludes
all other player/ZX0/IRQ/ULA/disk work and is an optimistic bound, not proof
of actual frame delivery or a release RAM allocation.
"""
import argparse
import json
from pathlib import Path


def queue_bound(work, capacity, budget):
    finished, worst, first = 0, 0, None
    for frame in range(capacity, len(work)):
        finished = max(finished, (frame-capacity)*budget)+work[frame]
        late = finished-frame*budget
        if late > 0 and first is None:
            first = frame
        worst = max(worst, late)
    return dict(prefilled_frames=capacity, max_lateness_tstates=worst, first_late_frame=first)


def minimum_capacity(work, budget):
    low, high = 1, len(work)
    while low < high:
        middle = (low+high)//2
        if queue_bound(work, middle, budget)['max_lateness_tstates']:
            low = middle+1
        else:
            high = middle
    return low


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        report = json.loads((args.reports/name).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError(f'incomplete {name}')
        return report

    compact = load('context_huffman_compact_cpu_measurements.json')
    fast = load('context_huffman_unrolled_cpu_measurements.json')
    zx0 = load('prediction_64_zx0_cpu_measurements.json')
    old_zx0 = load('motion_metadata_zx0_cpu_measurements.json')
    old_huffman = load('huffman_z80_measurements.json')
    bounded = load('incremental_huffman_measurements.json')
    for report in (compact, fast):
        if (report['input_sha256'] != zx0['input_sha256'] or len(report['frames']) != 4971
                or report['summary']['values'] != 1688733 or report['summary']['bits'] != 8418269):
            raise ValueError('incomparable inputs/coverage')
    if compact['summary']['wrapper_tstates'] != fast['summary']['wrapper_tstates']:
        raise ValueError('different bounded wrapper work')
    result = dict(scope=__doc__, baseline_commit='8e0812b', input_sha256=fast['input_sha256'],
        complete=True, player_changed=False, integrated_player_delta_tstates=0,
        compact=compact['summary'], unrolled=fast['summary'],
        primitive_delta_tstates=fast['summary']['primitive_tstates']['total']-compact['summary']['primitive_tstates']['total'],
        bounded_delta_tstates=fast['summary']['total_tstates']['total']-compact['summary']['total_tstates']['total'],
        code_bytes_before=compact['code_bytes'], code_bytes_after=fast['code_bytes'],
        zx0_before=old_zx0['summary'], zx0_after=zx0['summary'],
        zx0_delta_tstates=zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates'],
        prior_global_huffman_contiguous_tstates=old_huffman['summary']['huffman_tstates']['total'],
        prior_global_huffman_bounded_tstates=bounded['summary']['huffman_after_tstates'],
        prior_decoder_scope_note='Global Huffman has no context lookup. Its bounded reader checks split windows; the new wrapper reads predictor pairs but assumes contiguous input. Totals are contextual baselines, not isolated algorithm deltas.',
        idealized_value_queue=[])
    work = [row['total_tstates'] for row in fast['frames']]
    primitive = [row['primitive_tstates'] for row in fast['frames']]
    for budget in (425448, 350000, 300000, 250000, 200000, 150000):
        rows = [queue_bound(work, k, budget) for k in range(1, 17)]
        passing = minimum_capacity(work, budget)
        result['idealized_value_queue'].append(dict(budget_tstates=budget, first_passing_capacity=passing,
            primitive_only_minimum_capacity=minimum_capacity(primitive, budget), rows=rows))
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'idealized_value_queue'}, indent=2))
    print(json.dumps([{k:v for k,v in row.items() if k != 'rows'} for row in result['idealized_value_queue']]))


if __name__ == '__main__':
    main()
