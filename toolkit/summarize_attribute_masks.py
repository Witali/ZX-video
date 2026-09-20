"""Separate complete attribute-tail measurements from player timing evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from assess_frame_jitter import assess,FIELD


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cpu','before','after','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); source={k:json.loads(getattr(args,k).read_text(encoding='utf-8'))
        for k in ('cpu','before','after')}
    cpu,old,new=(source[k] for k in ('cpu','before','after'))
    if not cpu['complete'] or cpu['checked_frames']!=4221: raise ValueError('incomplete attribute stage')
    for key in ('raw_sha256','states_sha256'):
        if len({v[key] for v in source.values()})!=1: raise ValueError('different inputs')
    for key in ('lookahead','packet_ahead','unrolled_copy','unrolled_cache','attribute_groups','compressed_bytes'):
        if old[key]!=new[key]: raise ValueError('different baseline option '+key)
    if old.get('attribute_flags') or not new['attribute_flags']: raise ValueError('wrong modes')
    common=min(old['checked']['publish'],new['checked']['publish']); clocks=[]
    for name,r in (('before',old),('after',new)):
        pubs=r['publications']; field=pubs[0]['fields']; time=pubs[0]['tstates']
        clocks.append(dict(name=name,complete=r['complete'],checked=r['checked'],failure=r.get('failure'),
            ay_ticks=r['played_ay_ticks'],timing=assess(pubs),common_timing=assess(pubs[:common]),
            on_time_out_phase_tstates=r['timing']['on_time_phase_range_tstates'],
            foreground_tstates=r['foreground_tstates'],irq_tstates=r['irq_tstates'],
            missed_nominal_frames=[dict(index=i,late_fields=v['fields']-field-6*i,
                actual_out_phase_tstates=v['tstates']-time-6*i*FIELD)
                for i,v in enumerate(pubs) if v['fields']!=field+6*i]))
    stages={name:{k:v[k] for k in ('tstates','stages','reconstruction_bytes','code_end','controller_end')}
        for name,v in cpu['variants'].items()}
    result=dict(scope=__doc__,complete=False,release=False,attribute_stage_complete=True,checked_attribute_frames=4221,
        stages=stages,delta_tstates=cpu['delta_tstates'],change_percent=cpu['change_percent'],
        delta_formula=cpu['delta_formula'],slower_frames=cpu['slower_frames'],max_extra_tstates=cpu['max_extra_tstates'],
        compressed_stream_bytes=new['compressed_bytes'],compressed_stream_delta_bytes=0,
        additional_ring_or_framebuffer_bytes=0,common_publications=common,clocks=clocks,
        full_frame_delivery_verified=new['complete'],disk_delivery_verified=False,ula_verified=False,
        inputs={k:dict(file=getattr(args,k).name,sha256=hashlib.sha256(getattr(args,k).read_bytes()).hexdigest()) for k in source})
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('clocks','inputs','scope')},indent=2))


if __name__=='__main__': main()
