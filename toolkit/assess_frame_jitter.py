"""Audit the user-authorized 0..1-field late budget without accepting drift.

Field counters are necessary, but do not establish publication at the IRQ
boundary. Exact T-state phase errors are also reported. Existing recordings
do not establish safe ULA/disk delivery and remain non-release evidence.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

FIELD=70908


def assess(rows):
    if not rows: raise ValueError('no publications')
    first_field,first_time=rows[0]['fields'],rows[0]['tstates']
    phase=[r['fields']-first_field-6*i for i,r in enumerate(rows)]
    intervals=[b['fields']-a['fields'] for a,b in zip(rows,rows[1:])]
    time_phase=[r['tstates']-first_time-6*i*FIELD for i,r in enumerate(rows)]
    time_intervals=[b['tstates']-a['tstates'] for a,b in zip(rows,rows[1:])]
    bad=[i for i,n in enumerate(phase) if n not in (0,1)]
    bad_intervals=[i+1 for i,n in enumerate(intervals) if not 5<=n<=7]
    runs=[]; start=None
    for i,n in enumerate(phase+[0]):
        if n>0 and start is None: start=i
        elif n<=0 and start is not None:
            runs.append(dict(first_frame=start,frames=i-start,
                recovered_at_frame=i if i<len(phase) else None))
            start=None
    return dict(checked_publications=len(rows),late_field_histogram=dict(sorted(Counter(phase).items())),
        interval_field_histogram=dict(sorted(Counter(intervals).items())),
        frames_outside_field_budget=len(bad),first_outside_field_budget=bad[0] if bad else None,
        intervals_outside_budget=len(bad_intervals),
        passes_field_budget=not bad and not bad_intervals,
        late_runs=runs,max_consecutive_late_frames=max((r['frames'] for r in runs),default=0),
        unrecovered_at_recording_end=bool(phase[-1]>0),
        min_phase_tstates=min(time_phase),max_phase_tstates=max(time_phase),
        intervals_below_5_fields=sum(t<5*FIELD for t in time_intervals),
        intervals_above_7_fields=sum(t>7*FIELD for t in time_intervals),
        phase_above_20ms=sum(t>FIELD for t in time_phase),
        irq_boundary_publication_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--clock',type=Path,nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); trials=[]
    for path in args.clock:
        data=path.read_bytes(); r=json.loads(data)
        trials.append(dict(report=path.name,sha256=sha256(data).hexdigest(),
            complete=r['complete'],failure=r.get('failure'),**assess(r['publications'])))
    report=dict(scope=__doc__,complete=True,release=False,
        authorized_video_jitter_fields=1,authorized_video_jitter_ms=20,
        nominal_period_fields=6,allowed_intervals_fields=[5,6,7],ay_rate_hz=50,
        recovery_policy='next ready frame returns to the original absolute deadlines; never reset the schedule origin',
        player_changed=False,player_delta_tstates=0,trials=trials)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
