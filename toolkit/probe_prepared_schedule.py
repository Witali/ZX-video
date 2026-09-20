"""Optimistic B2 queue schedule using measured consumer and old decoder costs.

Not a Z80 scheduler. Ideal disk, free arbitrary producer preemption, zero
queue management, no IRQ/ULA; a completed pending compact frame may wait
outside the FIFO. Two native screens and FIFO/pending are prepared before
time zero. Extra producer costs are sensitivity parameters, not measurements.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

FIELD=70908
PERIOD=6*FIELD


def simulate(produce,draw,sizes,budget,extra=0):
    count=len(sizes)
    if count<2 or len(draw)!=count or len(produce)!=count or max(sizes)>budget:
        raise ValueError('invalid schedule input')
    costs=[p+extra for p in produce]
    if min(costs)<0 or min(draw)<0: raise ValueError('negative work')
    ready=set(); used=0; next_frame=2
    while next_frame<count and used+sizes[next_frame]<=budget:
        ready.add(next_frame); used+=sizes[next_frame]; next_frame+=1
    # An additional compact prediction state can be completed at startup;
    # real transfer to the ring still needs implementation and measurement.
    predecoded=min(count,next_frame+1); remaining=0
    work_before_start=sum(costs[:predecoded]); work_after_start=0
    t=0; maximum_used=used; first_wait=None
    def produce_until(deadline,needed=None):
        nonlocal next_frame,remaining,t,used,maximum_used,work_after_start
        while next_frame<count:
            if needed is not None and needed in ready: return
            if remaining==0:
                if used+sizes[next_frame]>budget: return
                ready.add(next_frame); used+=sizes[next_frame]; maximum_used=max(maximum_used,used)
                next_frame+=1
                if next_frame==count: return
                remaining=costs[next_frame]
            elif t<deadline:
                part=min(remaining,deadline-t); remaining-=part; t+=part; work_after_start+=part
            else: return
    rows=[dict(index=0,late_fields=0,publication_tstates=0)]
    for i in range(1,count):
        if i>=2:
            if i not in ready:
                if first_wait is None: first_wait=i
                produce_until(float('inf'),i)
                if i not in ready: raise AssertionError('head could not be produced')
            t+=draw[i]; ready.remove(i); used-=sizes[i]
        publication=max(i*PERIOD,((t+FIELD-1)//FIELD)*FIELD)
        produce_until(publication); t=publication
        if not 0<=used<=budget: raise AssertionError('queue capacity differs')
        rows.append(dict(index=i,late_fields=(publication-i*PERIOD)//FIELD,publication_tstates=publication))
    if ready or used or next_frame!=count or remaining or work_before_start+work_after_start!=sum(costs):
        raise AssertionError('incomplete EOF or work accounting')
    late_runs=[]; active=None
    for row in rows:
        if row['late_fields']:
            if active is None: active=dict(first_frame=row['index'],frames=0,max_fields=0,recovered_at_frame=None); late_runs.append(active)
            active['frames']+=1; active['max_fields']=max(active['max_fields'],row['late_fields'])
        elif active is not None: active['recovered_at_frame']=row['index']; active=None
    intervals=Counter((b['publication_tstates']-a['publication_tstates'])//FIELD for a,b in zip(rows,rows[1:]))
    return dict(estimated_only=True,budget=budget,extra_producer_tstates_per_frame=extra,
        predecoded_frames_before_start=predecoded,producer_work_before_start=work_before_start,
        producer_work_after_start=work_after_start,maximum_queue_bytes=maximum_used,first_wait_for_queue=first_wait,
        late_frames=sum(r['late_fields']>0 for r in rows),first_late=next((r['index'] for r in rows if r['late_fields']),None),
        max_late_fields=max(r['late_fields'] for r in rows),late_field_histogram=dict(Counter(r['late_fields'] for r in rows)),
        interval_field_histogram=dict(intervals),intervals_outside_5_7=sum(n for k,n in intervals.items() if not 5<=k<=7),
        frames_outside_20ms=sum(r['late_fields']>1 for r in rows),late_runs=late_runs,
        nominal_schedule_passes_estimate=not any(r['late_fields'] for r in rows),eof_accounting_verified=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('consumer','reservoir','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); consumer=json.loads(args.consumer.read_text()); old=json.loads(args.reservoir.read_text())
    if not consumer['complete'] or not old['complete'] or any(consumer[k]!=old[k] for k in ('raw_sha256','states_sha256')):
        raise ValueError('incomplete or different input')
    rows=consumer['frames']; base=old['frames_detail']
    if len(rows)!=len(base): raise ValueError('different frame counts')
    produce=[r['foreground_after_copy_tstates']-r['output_tstates'] for r in base]
    draw=[r['tstates'] for r in rows]; sizes=[r['record_bytes'] for r in rows]
    result=dict(scope=__doc__,complete=True,release=False,estimated_only=True,frames=len(rows),
        raw_sha256=consumer['raw_sha256'],states_sha256=consumer['states_sha256'],
        consumer_report=args.consumer.name,old_work_report=args.reservoir.name,
        scenarios=[simulate(produce,draw,sizes,30720,extra) for extra in (0,20000,40000,60000)],
        decision='A failed optimistic scenario is evidence against this specific queue/cost model. '
            'A passing scenario is not CPU, disk, AY or release verification.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for row in result['scenarios']:
        print(json.dumps({k:v for k,v in row.items() if k not in ('late_runs','late_field_histogram','interval_field_histogram')}))


if __name__=='__main__': main()
