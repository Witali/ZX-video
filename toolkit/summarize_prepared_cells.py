"""Summarize complete B2 consumer measurements separately from queue estimates."""
import argparse
import json
from pathlib import Path
from probe_lossless_layouts import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','schedule','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); paths=[args.before,args.after,args.schedule]
    before,after,schedule=[json.loads(path.read_text()) for path in paths]
    if not all(r['complete'] for r in (before,after,schedule)): raise ValueError('incomplete reports')
    if any(len(r['frames'])!=4221 for r in (before,after)): raise ValueError('incomplete movie')
    if any(before[k]!=r[k] for r in (after,schedule) for k in ('raw_sha256','states_sha256')):
        raise ValueError('source mismatch')
    if before['summary']['baseline_tstates']!=after['summary']['baseline_tstates']: raise ValueError('baseline differs')
    best=schedule['scenarios'][0]; runs=best['late_runs']
    result=dict(scope=__doc__,complete=True,release=False,player_changed=False,frames_verified=4221,
        input_reports=[dict(file=p.name,sha256=sha(p.read_bytes())) for p in paths],
        exact_native_screen_verification='CPU run compared both entire 6912-byte screens after each frame; visible/border writes guarded',
        disk_stream_delta_bytes=0,producer_measured=False,actual_cadence_verified=False,ay_playback_verified=False,
        disk_delivery_verified=False,baseline_output_tstates=after['summary']['baseline_tstates'],
        b2_ldir_tstates=before['summary']['total_tstates'],b2_unrolled_tstates=after['summary']['total_tstates'],
        unrolling_delta_tstates=after['summary']['total_tstates']-before['summary']['total_tstates'],
        best_consumer_delta_to_baseline=after['summary']['delta_tstates'],
        best_consumer_change_percent=after['summary']['change_percent'],by_screen_bank=after['summary']['by_bank'],
        code_bytes=dict(baseline=771,b2_ldir=before['code_bytes'],b2_unrolled=after['code_bytes']),
        copy_formulas=dict(ldir='21*n-5',unrolled_with_call_return='75+16*n+18*ceil(n/32)',positive_length_only=True),
        optimistic_model=dict(estimated_only=True,first_late=best['first_late'],late_frames=best['late_frames'],
            frames_outside_20ms=best['frames_outside_20ms'],max_late_fields=best['max_late_fields'],
            intervals_outside_5_7=best['intervals_outside_5_7'],late_runs=len(runs),
            recovered_runs=sum(r['recovered_at_frame'] is not None for r in runs),
            max_consecutive_late_frames=max((r['frames'] for r in runs),default=0),
            unrecovered_at_end=bool(runs and runs[-1]['recovered_at_frame'] is None)),
        decision='Keep the current renderer. This B2 queue adds CPU and its optimistic model misses deadlines. '
            'Do not integrate this producer before reducing reconstruction/transport costs. No claim about all possible queues.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
