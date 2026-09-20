"""Compare packet prefetch attempts and count their instruction-table overhead.

Unequal failed prefixes are reported separately, never as total CPU savings.
The scheduler costs exclude called routines, wait loops, IRQ, ULA and disk.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from assess_frame_jitter import assess


def routing(report, *, pending=True, ready=True, remaining=2):
    """Path after drawing: remaining=0/1/>1, with nonempty entry count."""
    labels=report['clock_labels']; rows=report['instruction_listing']
    total=0; executed=[]
    for row in rows:
        if not labels['play_one']<=row['address']<labels['wait_published']: continue
        name=row['instruction']; ticks=row['tstates']
        if isinstance(ticks,list):
            take=(name.startswith('CALL NZ') and remaining>0)
            if 'read next packet' in name: take=remaining>1
            if 'read required packet' in name: take=not pending
            ticks=ticks[1 if take else 0]
        total+=ticks; executed.append(dict(instruction=name,tstates=ticks))
        if name=='JP Z,wait_published':
            previous=executed[-2]['instruction']
            # First test is remaining!=0; second tests remaining-1.
            tests=sum(x['instruction']==name for x in executed)
            if tests==1 and remaining==0: break
            if tests==2 and remaining==1: break
            if previous=='OR A' and tests==3 and not ready: break
    return dict(tstates=total,instructions=executed)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--always',type=Path,required=True)
    p.add_argument('--idle',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); paths=(args.before,args.always,args.idle)
    reports=[json.loads(path.read_text(encoding='utf-8')) for path in paths]
    for key in ('raw_sha256','states_sha256','compressed_bytes','frames_expected'):
        if len({r[key] for r in reports})!=1: raise ValueError('different '+key)
    if any(r.get('complete') or 'failure' not in r for r in reports):
        raise ValueError('this summary expects terminal failure recordings')
    common=min(r['checked']['publish'] for r in reports)
    trials=[]
    for path,r in zip(paths,reports):
        trials.append(dict(report=path.name,sha256=sha256(path.read_bytes()).hexdigest(),
            checked=r['checked'],complete=r['complete'],failure=r['failure'],
            foreground_tstates=r['foreground_tstates'],foreground_stages=r['foreground_stages'],
            irq_tstates=r['irq_tstates'],played_ay_ticks=r['played_ay_ticks'],
            timing=assess(r['publications']),common_prefix_timing=assess(r['publications'][:common]),
            routing_steady=routing(r),routing_tail=routing(r,remaining=0),
            code_and_state_bytes=sum(len(bytes.fromhex(x['code_hex'])) for x in r['code_regions'])
                +len(bytes.fromhex(r['wrapper_code_hex']))+len(bytes.fromhex(r['output_code_hex']))))
    idle=reports[2]
    costs=dict(native_map_before_tstates=10+10+80*16,
        native_map_after_tstates=10+10+80*16+10,
        new_map_call_tstates=17,frame_mask_transfer_delta_tstates=27,
        combined_packet_entry_extra_tstates=10,
        separated_parser_removed_prepare_call_tstates=17,
        idle_pending_already_published=routing(idle,pending=True,ready=False),
        idle_required_read_already_published=routing(idle,pending=False,ready=False))
    for trial in trials[1:]:
        trial['steady_routing_delta_tstates']=trial['routing_steady']['tstates']-trials[0]['routing_steady']['tstates']
        trial['steady_total_glue_delta_tstates']=trial['steady_routing_delta_tstates']-17+27
        trial['code_and_state_delta_bytes']=trial['code_and_state_bytes']-trials[0]['code_and_state_bytes']
    result=dict(scope=__doc__,release=False,complete=False,common_publications=common,
        compressed_stream_bytes=reports[0]['compressed_bytes'],compressed_stream_delta_bytes=0,
        disk_delivery_verified=False,ula_verified=False,local_costs=costs,trials=trials)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(report=t['report'],checked=t['checked'],timing=t['timing'],
        routing_tstates=t['routing_steady']['tstates'],code_bytes=t['code_and_state_bytes']) for t in trials],indent=2))


if __name__=='__main__': main()
