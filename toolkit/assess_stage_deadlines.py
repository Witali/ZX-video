"""Locate CPU bursts in a fully executed frame-stage report.

These are isolated stage costs, not measured publication deadlines. ZX0,
IRQ/ULA, disk and the capacity/cost of any future queue are excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pipelined_frame_harness import FIELD


def assess(report):
    rows=report['frames']
    if (not report['complete'] or not report['full_compact_and_both_native_exact']
            or report['checked_frames']!=len(rows)
            or [r['frame'] for r in rows]!=list(range(len(rows)))):
        raise ValueError('requires a complete ordered frame-stage execution')
    costs=[r['tstates'] for r in rows];budget=6*FIELD
    if sum(costs)!=report['tstates']:raise ValueError('stage total differs')
    prefix=[0]
    for value in costs:prefix.append(prefix[-1]+value)
    excess=lambda start,end:prefix[end]-prefix[start]-(end-start)*budget
    windows=[]
    for size in (1,2,4,8,16,32,64,128):
        if size>len(costs):continue
        start=max(range(len(costs)-size+1),key=lambda i:excess(i,i+size))
        windows.append(dict(frames=size,start=start,end_exclusive=start+size,
            stage_tstates=prefix[start+size]-prefix[start],available_tstates=size*budget,
            excess_tstates=excess(start,start+size)))
    # Maximum sum of (stage cost - nominal budget) over any contiguous run.
    low=0;low_index=0;best=0;interval=None
    for end in range(1,len(prefix)):
        adjusted=prefix[end]-end*budget
        if adjusted-low>best:
            best=adjusted-low;interval=dict(start=low_index,end_exclusive=end,frames=end-low_index,
                stage_tstates=prefix[end]-prefix[low_index],available_tstates=(end-low_index)*budget,
                excess_tstates=best,excess_fields=(best+FIELD-1)//FIELD)
        if adjusted<low:low=adjusted;low_index=end
    over=[dict(frame=i,tstates=t,excess_tstates=t-budget) for i,t in enumerate(costs) if t>budget]
    return dict(complete=True,release=False,scope=__doc__,frames=len(rows),field_tstates=FIELD,
        frame_budget_tstates=budget,total_stage_tstates=sum(costs),total_nominal_tstates=len(rows)*budget,
        over_budget_frames=over,over_budget_count=len(over),worst_fixed_windows=windows,
        maximum_excess_interval=interval,queue_feasibility_proven=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cpu',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();raw=args.cpu.read_bytes();report=json.loads(raw)
    result=assess(report);result['cpu_report_sha256']=hashlib.sha256(raw).hexdigest()
    result['states_sha256']=report['states_sha256'];result['options']=report['options']
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('over_budget_frames','options')},indent=2))


if __name__=='__main__':main()
