"""Collect fully verified FHS1 storage and the two full causal CPU runs.

Storage margins include the previous unchanged AY estimate, but not new
volume/code overhead. CPU queues exclude all stages except reconstruction.
Neither an offline size margin nor a CPU-only queue proves a release.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from summarize_context_cpu import minimum_capacity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    load = lambda name: json.loads((args.reports/name).read_text(encoding='utf-8'))
    baseline_size = load('bounded_motion_age3_fht_zx0.json')
    if not baseline_size['complete']:
        raise ValueError('incomplete baseline size')
    inputs = [
        ('spatial_context_measurements.json', 'above_16', 'spatial_context_above_16_zx0.json'),
        ('spatial_context_measurements.json', 'above_64', 'spatial_context_above_64_zx0.json'),
        ('spatial_tiles_measurements.json', 'motion_16', 'spatial_tiles_motion_16_zx0.json'),
        ('spatial_tiles_measurements.json', 'above_16', 'spatial_tiles_above_16_zx0.json'),
        ('spatial_tiles_cost_measurements.json', 'iteration_1', 'spatial_tiles_cost_1_zx0.json'),
        ('spatial_tiles_cost_measurements.json', 'iteration_2', 'spatial_tiles_cost_2_zx0.json'),
        ('spatial_predictors_measurements.json', None, 'spatial_predictors_zx0.json'),
        ('spatial_predictors_cost_measurements.json', 'iteration_1', 'spatial_predictors_cost_1_zx0.json'),
        ('spatial_predictors_cost_measurements.json', 'iteration_2', 'spatial_predictors_cost_2_zx0.json'),
    ]
    report = dict(scope=__doc__, baseline_commit='e7727cd', complete=True,
        candidate_sha256='4b9e90d22df2809a70c1cb09890de0a9bb0a23d1b1e357b3f6c29ff830cc9c3b',
        baseline_video_bytes=baseline_size['zx0_with_headers_bytes'],
        unchanged_ay_estimate_bytes=77696, preliminary_three_trd_budget_bytes=1937664,
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False, rows=[])
    for source_name, name, storage_name in inputs:
        source, storage = load(source_name), load(storage_name)
        row = source if name is None else next(r for r in source['rows'] if r['name'] == name)
        size = sum(b['zx0_bytes']+4 for b in storage['blocks'])
        if (not source['complete'] or not storage['complete']
                or source['states_sha256'] != report['candidate_sha256']
                or row['sha256'] != storage['input_sha256']
                or len(storage['blocks']) != storage['blocks_expected']
                or storage['encoder_mode'] != 'optimal ZX0 v2' or storage['block_bytes'] != 8192
                or size != storage['zx0_with_headers_bytes']
                or sum(b['decoded_bytes'] for b in storage['blocks']) != row['raw_bytes']):
            raise ValueError(f'incomplete/different storage: {storage_name}')
        report['rows'].append(dict(source=source_name, variant=name, storage_report=storage_name,
            raw_bytes=row['raw_bytes'], bits=row['bits'], zx0_bytes_with_headers=size,
            blocks=len(storage['blocks']), sha256=row['sha256'],
            delta_to_baseline_video_bytes=size-report['baseline_video_bytes'],
            video_plus_ay_estimate_bytes=size+77696,
            preliminary_margin_before_overhead_bytes=1937664-size-77696))
    report['verified_zx0_blocks'] = sum(r['blocks'] for r in report['rows'])
    cpu_rows = []
    for stem, storage_name in (('spatial_tiles_baseline', 'bounded_motion_age3_fht_zx0.json'),
                                ('spatial_tiles_motion_16', 'spatial_tiles_motion_16_zx0.json')):
        cpu, zx0, storage = load(stem+'_cpu.json'), load(stem+'_zx0_cpu.json'), load(storage_name)
        if (not cpu['complete'] or not zx0['complete'] or len(cpu['frames']) != 4971
                or cpu['states_sha256'] != report['candidate_sha256']
                or cpu['input_sha256'] != storage['input_sha256'] or zx0['input_sha256'] != storage['input_sha256']):
            raise ValueError('CPU coverage differs')
        totals = [f['total_tstates'] for f in cpu['frames']]
        histogram_total = sum(x['tstates']*x['count'] for x in cpu['instruction_histogram'])
        stages = Counter()
        for i, frame in enumerate(cpu['frames']):
            if frame['index'] != i or sum(frame['stages'].values()) != frame['total_tstates']:
                raise AssertionError('CPU frame/stage sum differs')
            stages.update(frame['stages'])
        if (histogram_total != sum(totals) or sum(totals) != cpu['summary']['total_tstates']
                or sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']):
            raise AssertionError('CPU totals differ')
        cpu_rows.append(dict(name=stem, frames=4971, code_bytes=cpu['code_bytes'], state_bytes=cpu['state_bytes'],
            **{k: cpu['summary'][k] for k in ('total_tstates', 'mean_frame_tstates', 'max_frame_tstates', 'worst_frame', 'frames_over_nominal_425448')},
            stages=dict(stages), zx0_cpu=zx0['summary'],
            two_stage_total_tstates=sum(totals)+zx0['summary']['total_tstates'],
            idealized_queue=[dict(budget_tstates=b, minimum_complete_frame_capacity=minimum_capacity(totals, b))
                for b in (425448, 350000, 300000, 250000)]))
    old, new = cpu_rows
    report['cpu'] = cpu_rows
    report['cpu_delta'] = dict(total_tstates=new['total_tstates']-old['total_tstates'],
        two_stage_tstates=new['two_stage_total_tstates']-old['two_stage_total_tstates'],
        code_bytes=new['code_bytes']-old['code_bytes'],
        stages={k: new['stages'].get(k, 0)-old['stages'].get(k, 0) for k in set(old['stages']) | set(new['stages'])})
    report['intra_formula'] = '1057 T top tile stripe /1099 T other stripes +25 T per correction, including RET; Huffman and external CALL separate'
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(rows=report['rows'], cpu=cpu_rows, delta=report['cpu_delta']), indent=2), flush=True)


if __name__ == '__main__':
    main()
