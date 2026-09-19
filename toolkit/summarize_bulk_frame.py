"""Compare complete FAP1/FAP2 CPU runs and separate failed clock trials."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'cpu', 'old-storage', 'storage', 'clock', 'zero-copy-clock', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    old, new = read(args.baseline), read(args.cpu)
    before, after = read(args.old_storage), read(args.storage)
    if not all(r['complete'] for r in (old, new, before, after)):
        raise ValueError('complete CPU and storage reports required')
    if (old['states_sha256'] != new['states_sha256']
            or len(old['frames']) != len(new['frames'])
            or new['raw_sha256'] != after['input_sha256']
            or old['raw_sha256'] != before['input_sha256']):
        raise ValueError('inconsistent comparison inputs')
    for a, b in zip(old['frames'], new['frames']):
        for stage in ('audio', 'metadata', 'reconstruct', 'output'):
            if a['stages'][stage] != b['stages'][stage]:
                raise AssertionError(('unexpected stage change', a['index'], stage))
        if b['stages']['handoff']-a['stages']['handoff'] != 6:
            raise AssertionError('dynamic source pointer timing differs')
    stages = {s: dict(before=t, after=new['summary']['stages'][s],
        delta=new['summary']['stages'][s]-t) for s, t in old['summary']['stages'].items()}
    size1, size2 = (r['zx0_with_headers_bytes'] for r in (before, after))
    clocks = []
    for name, path in [('copy', args.clock), ('zero_copy', args.zero_copy_clock)]:
        r = read(path)
        late = [dict(frame=i, fields=row['late_fields']) for i, row in enumerate(r['publications'])
                if row['late_fields']]
        clocks.append(dict(variant=name, report=path.name, complete=r['complete'],
            verified_frames=len(r['frames']), failure=r.get('failure'), late_frames=len(late),
            first_late=late[0] if late else None, max_late_fields=max((row['fields'] for row in late), default=0)))
    # This option has an exact local instruction delta, not a full-film run.
    projected = [r['tstates']-4481 for r in new['frames']]
    report = dict(scope=__doc__, complete=True, release=False, disk_delivery_verified=False,
        states_sha256=new['states_sha256'], frames=len(projected), measured_stages=stages,
        before=old['summary'], after=new['summary'],
        measured_delta_tstates=new['summary']['total_tstates']-old['summary']['total_tstates'],
        storage=dict(before=size1, after=size2, delta=size2-size1,
            sectors_before=(size1+255)//256, sectors_after=(size2+255)//256,
            preliminary_three_disk_allowance=1937664, preliminary_margin=1937664-size2,
            actual_release_capacity_verified=False),
        zero_copy_projection=dict(measured_full_run=False, delta_per_frame=-4481,
            total_tstates=sum(projected), mean_tstates=sum(projected)/len(projected),
            max_tstates=max(projected), frames_above_425448=sum(t>425448 for t in projected)),
        clock_trials=clocks)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
