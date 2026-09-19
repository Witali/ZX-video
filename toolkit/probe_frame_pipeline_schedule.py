"""Offline scheduling bound for separating reconstruction from native drawing.

This does not execute a changed Z80 player. It adds measured manual ISR costs
per six fields to frame work; actual IRQ phases, new control code, ULA, disk
and lookahead resumption overhead are excluded. A second variant removes
all ZX0 work (an intentionally impossible free-decoding lower bound).
Preparing frame 1 before publishing frame 0 permits drawing frame i and
reconstructing i+1 while the ready native frame i waits for its deadline.
Publication inside the IRQ and safe shared page state would need new code.
"""
import argparse
import json
from pathlib import Path


def simulate(preparation, drawing, irqs, *, pipeline):
    period = 6*70908
    ready = 0
    delays = []
    # Start clock with frame zero native and, for pipeline, frame one compact.
    for i in range(1,len(preparation)):
        due = i*period
        if pipeline:
            ready = max(ready,(i-1)*period)+drawing[i]+irqs[i]
            delays.append(max(0,ready-due))
            if i+1 < len(preparation): ready += preparation[i+1]
        else:
            ready = max(ready,(i-1)*period)+preparation[i]+drawing[i]+irqs[i]
            delays.append(max(0,ready-due))
    return dict(late_frames=sum(bool(t) for t in delays),max_late_tstates=max(delays,default=0),
        first_late_frame=next((i+1 for i,t in enumerate(delays) if t),None),
        worst_frame=delays.index(max(delays))+1 if delays else None)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','noop-summary','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    old=json.loads(args.baseline.read_text(encoding='utf-8'))
    summary=json.loads(args.noop_summary.read_text(encoding='utf-8'))
    if not old['complete'] or old['states_sha256'] != summary['states_sha256']:
        raise ValueError('matching full reports required')
    draw=[r['stages']['output'] for r in old['frames']]
    irq=[r['irq_tstates'] for r in old['frames']]
    pre=[r['tstates']-d-4481+s['reconstruction_delta']
        for r,d,s in zip(old['frames'],draw,summary['frame_deltas'])]
    lower=[p-r['stages']['banked_zx0'] for p,r in zip(pre,old['frames'])]
    scenarios=[]
    for name,costs in [('fixed_measured_ZX0_cost',pre),('free_ZX0_lower_bound',lower)]:
        for pipeline in (False,True):
            scenarios.append(dict(input=name,pipeline=pipeline,
                **simulate(costs,draw,irq,pipeline=pipeline)))
    report=dict(scope=__doc__,complete=True,estimated_only=True,release=False,
        player_changed=False,player_delta_tstates=0,states_sha256=old['states_sha256'],
        frames=len(pre),scenarios=scenarios)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
