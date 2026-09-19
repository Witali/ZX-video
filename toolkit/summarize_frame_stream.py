"""Check combined CPU totals, unchanged video stages and failed clock attempts."""
import argparse
from collections import Counter
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cpu','baseline','clock','ahead','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args()
    def read(path): return json.loads(path.read_text(encoding='utf-8'))
    actual, baseline = read(args.cpu), read(args.baseline)
    if (not actual['complete'] or not baseline['complete'] or actual['states_sha256'] != baseline['states_sha256']
            or len(actual['frames']) != len(baseline['frames'])):
        raise ValueError('complete matching CPU reports required')
    stages = Counter()
    for row, old in zip(actual['frames'],baseline['frames']):
        if row['index'] != old['index']: raise ValueError('frame index differs')
        for name in ('metadata','reconstruct','output'):
            if row['stages'][name] != old['stages'][name]: raise AssertionError('old video path changed')
        if row['stages']['handoff'] != old['stages']['handoff']+10: raise AssertionError('deferred RET differs')
        stages.update(row['stages'])
    total = sum(row['tstates'] for row in actual['frames'])
    if total != sum(stages.values()) or total != actual['summary']['total_tstates']:
        raise AssertionError('stage sum differs')
    if sum(r['tstates']*r['count'] for r in actual['instruction_histogram']) != total:
        raise AssertionError('instruction histogram differs')
    counts = [r['tstates'] for r in actual['frames']]
    attempts = []
    for path in (args.clock,args.ahead):
        result = read(path)
        if result['complete'] or result['raw_sha256'] != actual['raw_sha256'] or not result.get('failure'):
            raise ValueError('expected saved incomplete clock failure')
        late = [(i,r['late_fields']) for i,r in enumerate(result['publications']) if r['late_fields']]
        attempts.append(dict(report=path.name,lookahead=result.get('lookahead',False),
            verified_frames=len(result['frames']),first_late_frame=late[0][0] if late else None,
            late_frames=len(late),max_late_fields=max((n for _,n in late),default=0),failure=result['failure']))
    old_total = sum(row['total_tstates'] for row in baseline['frames'])
    summary = dict(scope=__doc__,complete=True,baseline_commit='1963bab',frames=len(counts),
        raw_sha256=actual['raw_sha256'],states_sha256=actual['states_sha256'],
        total_foreground_tstates=total,stages=dict(stages),mean_tstates=total/len(counts),
        max_tstates=max(counts),worst_frame=counts.index(max(counts)),
        frames_above_425448=sum(t>425448 for t in counts),baseline_video_tstates=old_total,
        added_input_audio_bridge_tstates=total-old_total,added_deferred_ret_tstates=10*len(counts),
        manual_irq_tstates=sum(r.get('irq_tstates',r.get('manual_irq_tstates',0)) for r in actual['frames']),
        mean_remaining_before_irq_ula_disk=425448-total/len(counts),clock_attempts=attempts,
        pixel_and_ay_data_verified=True,video_cadence_verified=False,disk_delivery_verified=False,release=False)
    args.output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__': main()
