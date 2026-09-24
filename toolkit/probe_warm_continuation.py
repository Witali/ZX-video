"""Measure and rebalance real warm-continuation TRDs; no release claim."""
import argparse
import json
from pathlib import Path

import numpy as np
from build_fap3_trd import sha
from run_deferred_disk import ReadThroughBuilder
from probe_lean_checkpoints import verify_stream


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','zx0','output','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--ends',default='1619,2919,4221')
    p.add_argument('--rebalance',action='store_true')
    args=p.parse_args()
    raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as saved: states=saved['states']
    ends=[int(s) for s in args.ends.split(',')]
    if not ends or ends!=sorted(set(ends)) or ends[0]<=0 or ends[-1]!=len(states): p.error('invalid ends')
    args.output.mkdir(parents=True,exist_ok=True); args.report.parent.mkdir(parents=True,exist_ok=True)
    report=dict(baseline_commit='e356874',complete=False,release=False,
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),frames=len(states),
        initial_ends=list(ends),attempts=[],volumes=[],pixel_changes=False,ay_changes=False,
        player_hot_path_changed=False,player_hot_path_delta_tstates=0,
        full_cpu_run=False,full_disk_run=False,physical_drive_verified=False)
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    b=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',
        fast_disk=True,cached_seek=True,interleaved=True,cold_bitmaps=True,warm_continuation=True)
    b.read_cache=args.read_cache; b.ends=ends
    save()
    # Bounded local rebalance. Each acceptance uses a real assembled volume;
    # it is a fit search near --ends, not a proof of optimal partitioning.
    if args.rebalance:
        for i in range(len(ends)-1):
            start=ends[i-1] if i else 0
            candidates=[]
            for end in range(max(start+1,ends[i]-32),min(ends[i]+17,ends[i+1])):
                b.ends=ends[:i]+[end]+ends[i+1:]
                _,m=b.volume(start,end,i+1)
                row=dict(part=i+1,start=start,end=end,used_sectors=m['used_sectors'])
                report['attempts'].append(row)
                print(json.dumps(row),flush=True)
                if m['used_sectors']<=2544: candidates.append(end)
                save()
            if not candidates: raise ValueError('no nearby fitting boundary')
            ends[i]=max(candidates)
    b.ends=ends; report['ends']=ends
    records=[]
    for part,(start,end) in enumerate(zip([0]+ends,ends),1):
        image,m=b.volume(start,end,part)
        stem=f'ZX-video-warm-preview_part{part:02}'
        (args.output/(stem+'.json')).write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
        if image: (args.output/(stem+'.trd')).write_bytes(image)
        record=dict(part=part,file=stem+'.trd',metadata=stem+'.json',frame_start=start,
            frame_end_exclusive=end,sha256=m.get('trd_sha256'))
        records.append(record)
        row={k:m[k] for k in ('part','frame_start','frame_end_exclusive','frames','video_bytes','video_start_sector',
            'video_sectors','layout_padding_sectors','used_sectors','free_sectors','sections',
            'warm_reset_ranges','warm_immutable_sha256','warm_compact_checkpoint_sha256','independently_bootable')}
        row.update(fits=image is not None,trd_sha256=m.get('trd_sha256'),stream_verification=verify_stream(b,start,end))
        report['volumes'].append(row);save()
        print(json.dumps({k:row[k] for k in ('part','frames','used_sectors','free_sectors','fits')}),flush=True)
    (args.output/'volumes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    cold=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',
        fast_disk=True,cached_seek=True,interleaved=True,cold_bitmaps=True)
    cold.read_cache=args.read_cache; cold.ends=ends; cold.memo=b.memo
    report['independent_baseline']=[]
    for part,(start,end) in enumerate(zip([0]+ends,ends),1):
        _,m=cold.volume(start,end,part)
        report['independent_baseline'].append({k:m[k] for k in ('part','used_sectors','free_sectors','video_bytes','sections')})
    report.update(complete=True,all_fit=all(v['fits'] for v in report['volumes']),
        total_used_sectors=sum(v['used_sectors'] for v in report['volumes']))
    save()


if __name__=='__main__':main()
