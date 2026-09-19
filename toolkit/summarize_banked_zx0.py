"""Compare measured banked ZX0 stages, without implying a playback schedule."""
import argparse
import json
from pathlib import Path


def summarize(simple, fast, pipeline):
    if not all(r['complete'] for r in (simple, fast, pipeline)):
        raise ValueError('complete reports required')
    if simple['input_sha256'] != fast['input_sha256']:
        raise ValueError('different compressed inputs')
    labels = fast['labels']
    starts = [('bounded_control', labels['begin']), ('zx0_core', labels['dzx0_turbo']),
              ('literal_boundary', labels['literal']), ('refill_control', labels['refill']),
              ('ring_copy', labels['ring_copy']), ('paging', labels['ring_page']),
              ('end', labels['fatal'])]
    stages = {name: sum(r['count']*r['tstates'] for r in fast['instruction_histogram']
                       if first <= r['address'] < last)
              for (name, first), (_, last) in zip(starts, starts[1:])}
    total = fast['summary']['total_tstates']
    if sum(stages.values()) != total:
        raise AssertionError('incomplete instruction coverage')
    frames = pipeline['frames']
    measured = sum(r['total_tstates'] for r in frames)
    return dict(scope='Separate full-stream CPU sums; packet input, outer calls, AY, ULA and disk excluded.',
        complete=True, input_sha256=fast['input_sha256'], optimized_stages_tstates=stages,
        simple= simple['summary'], optimized=fast['summary'],
        optimized_minus_simple_tstates=total-simple['summary']['total_tstates'],
        reconstruction_output_metadata_tstates=measured, frames=len(frames),
        separate_cpu_sum_tstates=measured+total,
        separate_cpu_mean_tstates=(measured+total)/len(frames),
        nominal_mean_remaining_tstates=425448-(measured+total)/len(frames),
        disk_delivery_verified=False, release=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('simple', 'fast', 'pipeline', 'output'):
        p.add_argument('--'+arg, type=Path, required=True)
    args = p.parse_args()
    result = summarize(*(json.loads(getattr(args, n).read_text(encoding='utf-8'))
                         for n in ('simple', 'fast', 'pipeline')))
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
