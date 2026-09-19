"""Project the constant 3240-T saving from measured output loops; audit real IRQ playback separately."""
import argparse
import json
from pathlib import Path

from assess_frame_jitter import assess
from frame_output_pipeline import Harness,frames
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('profile','baseline','clock','cells','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args()
    profile,baseline,clock = [json.loads(path.read_text(encoding='utf-8'))
        for path in (args.profile,args.baseline,args.clock)]
    if (not profile['complete'] or not baseline['complete'] or not clock['constant_attribute_borders']
            or any(profile['states_sha256'] != row['states_sha256'] for row in (baseline,clock))
            or baseline['raw_sha256'] != clock['raw_sha256']
            or profile['frames'] != len(baseline['frames'])
            or profile['globally_constant_cells'] != 192
            or profile['constant_cell_value_counts'] != {'1':192}
            or profile['runs'] != [dict(first=0,length=96,constant=True),
                dict(first=96,length=576,constant=False),dict(first=672,length=96,constant=True)]):
        raise ValueError('full matching constant-border profile and CPU baseline required')
    for row in clock['frames']:
        before = baseline['frames'][row['index']]['stages']
        for stage in ('metadata','reconstruct','output','handoff'):
            if row['stages'][stage] != before[stage]-(3240 if stage == 'output' else 0):
                raise AssertionError(('clock phase differs',row['index'],stage))
    source = args.cells.read_bytes(); tables,mapping,packets = frames(source)
    if len(packets) != profile['frames']: raise ValueError('wrong cells')
    runs = [Harness(tables,mapping,raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,
        selective_cache=True,constant_attribute_borders=enabled) for enabled in (False,True)]
    cold = [h.init_result['total_tstates'] for h in runs]
    if cold[1]-cold[0] != 32284: raise AssertionError('cold init formula differs')
    projected = [r['tstates']-3240 for r in baseline['frames']]
    report = dict(scope=__doc__,complete=True,baseline_commit='469402c',release=False,
        frames=len(projected),states_sha256=profile['states_sha256'],cells_sha256=sha(source),
        compression_change_bytes=0,stream_extra_sectors=0,extra_initializer_code_bytes=26,
        attribute_loop_tstates=dict(before=12960,after=9720,delta=-3240),
        attribute_stage_tstates=dict(before=13018,after=9778,delta=-3240),
        cold_init_tstates=dict(before=cold[0],after=cold[1],delta=cold[1]-cold[0]),
        code_sizes=dict(renderer=[len(h.draw_code) for h in runs],cold_init=[len(h.init_code) for h in runs]),
        new_buffers_bytes=0,
        instruction_table_projection=dict(full_execution_measured=False,
            baseline_foreground_tstates=baseline['summary']['total_tstates'],
            total_tstates=sum(projected),total_delta=-3240*len(projected),
            mean_tstates=sum(projected)/len(projected),max_tstates=max(projected),
            worst_frame=projected.index(max(projected)),frames_above_425448=sum(t>425448 for t in projected),
            output_before=baseline['summary']['stages']['output'],
            output_after=baseline['summary']['stages']['output']-3240*len(projected)),
        measured_cadence=dict(complete=clock['complete'],verified_frames=len(clock['frames']),
            failure=clock.get('failure'),audit=assess(clock['publications'])),
        exact_static_border_profile=True,actual_disk_delivery_verified=False,ula_included=False,
        sources={name:dict(path=getattr(args,name).name,sha256=sha(getattr(args,name).read_bytes()))
            for name in ('profile','baseline','clock')})
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
