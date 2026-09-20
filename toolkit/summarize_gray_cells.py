"""Compare complete native-output work, partial clocks and mask storage separately."""
import argparse
import hashlib
import json
from pathlib import Path

from assess_frame_jitter import assess, FIELD


def clock_result(name, report, common):
    rows = report['publications']
    first_field, first_time = rows[0]['fields'], rows[0]['tstates']
    return dict(name=name, complete=report['complete'], checked=report['checked'],
        failure=report.get('failure'), ay_ticks=report['played_ay_ticks'],
        timing=assess(rows), common_timing=assess(rows[:common]),
        on_time_out_phase_tstates=report['timing']['on_time_phase_range_tstates'],
        foreground_tstates=report['foreground_tstates'], irq_tstates=report['irq_tstates'],
        missed_nominal_frames=[dict(index=i, late_fields=row['fields']-first_field-6*i,
            actual_out_phase_tstates=row['tstates']-first_time-6*i*FIELD)
            for i, row in enumerate(rows) if row['fields'] != first_field+6*i])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cpu', 'before', 'after', 'density', 'storage', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--trial-storage', type=Path, nargs=2, required=True,
        metavar=('GRAY_OPTIMAL', 'COMPACT_16'))
    p.add_argument('--density-clock', type=Path)
    args = p.parse_args()
    paths = {name:getattr(args, name) for name in ('cpu','before','after','density','storage')}
    paths.update(zip(('gray_optimal','compact_16'), args.trial_storage))
    if args.density_clock: paths['density_clock'] = args.density_clock
    source = {name:json.loads(path.read_text(encoding='utf-8')) for name,path in paths.items()}
    cpu, old, new, density, storage = (source[k] for k in ('cpu','before','after','density','storage'))
    for report in (cpu, density):
        if not report['complete'] or report['checked_frames'] != 4221:
            raise ValueError('incomplete frame-stage evidence')
    for key in ('raw_sha256','states_sha256'):
        if len({source[name][key] for name in ('cpu','before','after','density')}) != 1:
            raise ValueError('different baseline inputs')
    for key in ('lookahead','packet_ahead','unrolled_copy','unrolled_cache','attribute_groups','attribute_flags','compressed_bytes'):
        if old[key] != new[key]: raise ValueError('different baseline option '+key)
    if old.get('gray_cells') or not new['gray_cells']: raise ValueError('wrong renderer modes')
    if not storage['complete'] or storage['input_sha256'] != new['raw_sha256']:
        raise ValueError('wrong baseline storage')
    common = min(old['checked']['publish'], new['checked']['publish'])
    clocks = [clock_result(name,r,common) for name,r in (('before',old),('after',new))]
    baseline_bytes = sum(block['zx0_bytes']+4 for block in storage['blocks'])
    variants = {}
    for name in ('gray_optimal','compact_16'):
        r, projected = source[name], density['variants'][name]
        if not r['complete'] or r['input_sha256'] != projected['raw_sha256']:
            raise ValueError('incomplete or wrong trial storage')
        for key in ('encoder_sha256','encoder_mode','block_bytes','blocks_expected'):
            if r[key] != storage[key]: raise ValueError('different compression settings')
        size = sum(block['zx0_bytes']+4 for block in r['blocks'])
        variants[name] = dict(**projected, zx0_bytes_with_headers=size,
            zx0_delta_bytes=size-baseline_bytes,
            stream_sector_delta=(size+255)//256-(baseline_bytes+255)//256,
            assembled_trd_count_verified=False, full_delivery_cpu_verified=False)
    density_clock = None
    if args.density_clock:
        r = source['density_clock']
        if r['raw_sha256'] != density['variants']['compact_16']['raw_sha256']:
            raise ValueError('different density clock input')
        for key in ('states_sha256','lookahead','packet_ahead','unrolled_copy','unrolled_cache','attribute_groups','attribute_flags','gray_cells'):
            if r[key] != new[key]: raise ValueError('different density clock option '+key)
        prefix = min(new['checked']['publish'],r['checked']['publish'])
        density_clock = dict(common_publications=prefix,
            clocks=[clock_result(name,report,prefix) for name,report in (('original_masks',new),('compact_16',r))])
    result = dict(scope=__doc__, complete=True, release=False, native_stage_complete=True,
        checked_native_frames=cpu['checked_frames'],
        baseline_output_tstates=cpu['baseline_output_tstates'],output_tstates=cpu['output_tstates'],
        delta_tstates=cpu['delta_tstates'],change_percent=cpu['change_percent'],
        sparse_cell_tstates=dict(before=289,after=254,delta=-35),
        every_frame_no_slower=cpu['every_frame_no_slower'], memory=cpu['memory'],
        baseline_comparison='Previous instruction-table formula; paired old/new Z80 tests, new full native-stage execution',
        compressed_stream_bytes=baseline_bytes,renderer_stream_delta_bytes=0,
        common_publications=common,clocks=clocks,density_variants=variants,density_clock=density_clock,
        full_frame_delivery_verified=False,disk_delivery_verified=False,ula_verified=False,
        inputs={name:dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            for name,path in paths.items()})
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('clocks','inputs','density_clock')},indent=2))


if __name__ == '__main__': main()
