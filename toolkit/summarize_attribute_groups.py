"""Separate full attribute-stage evidence from incomplete player cadence."""
import argparse
import hashlib
import json
from pathlib import Path
from assess_frame_jitter import assess,FIELD


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cpu','initial','before','after','fac1','fac2','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); sources={k:json.loads(getattr(args,k).read_text(encoding='utf-8'))
        for k in ('cpu','initial','before','after','fac1','fac2')}
    cpu=sources['cpu']; old,new=sources['before'],sources['after']
    if not cpu['complete'] or cpu['frames_verified']!=4221: raise ValueError('incomplete stage')
    if len({sources[k]['raw_sha256'] for k in ('cpu','initial','before','after')})!=1:
        raise ValueError('different input stream')
    if len({sources[k]['states_sha256'] for k in ('cpu','initial','before','after')})!=1:
        raise ValueError('different source pictures')
    if not new['attribute_groups'] or old['compressed_bytes']!=new['compressed_bytes']:
        raise ValueError('different stream or mode')
    if any(old[k]!=new[k] for k in ('lookahead','packet_ahead','unrolled_copy','unrolled_cache')):
        raise ValueError('different playback options')
    common=min(old['checked']['publish'],new['checked']['publish']); clocks=[]
    for name,r in (('before',old),('after',new)):
        rows=r['publications']; first_time=rows[0]['tstates']; first_field=rows[0]['fields']
        clocks.append(dict(name=name,complete=r['complete'],checked=r['checked'],failure=r.get('failure'),
            played_ay_ticks=r['played_ay_ticks'],timing=assess(rows),common_timing=assess(rows[:common]),
            on_time_out_phase_tstates=r['timing']['on_time_phase_range_tstates'],
            foreground_tstates=r['foreground_tstates'],irq_tstates=r['irq_tstates'],
            missed_nominal_frames=[dict(index=i,late_fields=v['fields']-first_field-6*i,
                actual_out_phase_tstates=v['tstates']-first_time-6*i*FIELD)
                for i,v in enumerate(rows) if v['fields']!=first_field+6*i]))
    base=old['compressed_bytes']; candidates=[]
    for name in ('fac1','fac2'):
        r=sources[name]
        if not r['complete'] or r['block_bytes']!=8192 or r['encoder_mode']!='optimal ZX0 v2':
            raise ValueError('incomplete/nonmatching storage experiment')
        size=r['zx0_with_headers_bytes']
        candidates.append(dict(format=name.upper(),bytes=size,delta_bytes=size-base,
            delta_continuous_stream_sectors=(size+255)//256-(base+255)//256,
            preliminary_three_trd_margin=1937664-size,decision='not integrated; exceeds preliminary size budget'))
    result=dict(scope=__doc__,complete=False,release=False,attribute_stage_complete=True,
        frames_verified=cpu['frames_verified'],initial_stage=sources['initial']['summary'],final_stage=cpu['summary'],
        full_attribute_copy_tstates=9778,sparse_draw_formula='51 + min(9778, 64 + sum(32 if n=0 else 31+285*n))',
        prepare_formula='warmup=150; raw=155; coded=760+152*nonempty_flags+18*groups; outer CALL adds 17',
        compressed_stream_bytes=base,compressed_stream_delta_bytes=0,storage_candidates=candidates,
        memory=cpu['memory'],common_publications=common,clocks=clocks,
        all_native_attribute_bytes_verified=True,bitmap_stream_unchanged=True,ay_bytes_unchanged=True,
        full_bitmap_render_cpu_frames=new['checked']['native'],
        full_frame_delivery_verified=False,disk_delivery_verified=False,ula_verified=False,
        inputs={k:dict(file=getattr(args,k).name,sha256=hashlib.sha256(getattr(args,k).read_bytes()).hexdigest()) for k in sources})
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('clocks','inputs')},indent=2))


if __name__=='__main__': main()
