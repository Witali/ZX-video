"""Build and fully measure deferred disk variants on identical FAP3 volumes.

Run one Fuse process at a time because Windows Fuse uses shared stdout.txt.
Images/traces remain in --output; the compact, reproducible summary is saved
to --report. This is an experiment, not a release or a physical-drive check.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from build_fap3_trd import Builder, sha
from profile_fap3 import summarize_fuse
from zx0_codec import decompress


class ReadThroughBuilder(Builder):
    read_cache=()

    def compress(self,data):
        digest=sha(data)
        if digest not in self.memo:
            for cache in self.read_cache:
                path=cache/(digest+'.zx0')
                if path.is_file():
                    encoded=path.read_bytes()
                    if decompress(encoded,limit=len(data))!=data: raise AssertionError('cached block differs')
                    self.memo[digest]=encoded
                    break
        return super().compress(data)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','zx0','fuse','output','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--limits',default='0,64,248')
    p.add_argument('--keepalive-fields',type=int,default=0)
    p.add_argument('--frame-service',action='store_true')
    p.add_argument('--timeout',type=float,default=300)
    p.add_argument('--ends',default='1269,2334,3195,4221')
    args=p.parse_args()
    limits=[int(s) for s in args.limits.split(',')]; ends=[int(s) for s in args.ends.split(',')]
    if len(set(limits))!=len(limits) or any(n<0 or n>248 for n in limits): p.error('invalid limits')
    raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as saved: states=saved['states']
    if ends!=sorted(set(ends)) or not ends or ends[0]<=0 or ends[-1]!=len(states): p.error('invalid ends')
    report=dict(baseline_commit='7aca091',complete=False,release=False,
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),frames=len(states),ends=ends,
        compact_frames_changed=False,ay_bytes_changed=False,full_pixel_comparison=False,
        pixel_samples_per_frame=80,physical_drive_verified=False,keepalive_fields=args.keepalive_fields,
        frame_service=args.frame_service,variants=[])
    args.output.mkdir(parents=True,exist_ok=True); args.report.parent.mkdir(parents=True,exist_ok=True)
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    for limit in limits:
        directory=args.output/f'limit-{limit:03}'; directory.mkdir(exist_ok=True)
        builder=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',
            fast_disk=True,cached_seek=True,interleaved=True,deferred_limit=limit,
            keepalive_fields=args.keepalive_fields if limit else 0,frame_service=args.frame_service if limit else False)
        builder.read_cache=args.read_cache; builder.ends=ends
        variant=dict(limit=limit,complete=False,volumes=[]); report['variants'].append(variant)
        records=[]; start=0
        for part,end in enumerate(ends,1):
            print(f'Build deferred={limit}, disk={part}: frames {start}..{end-1}',flush=True)
            image,meta=builder.volume(start,end,part)
            if image is None: raise ValueError('volume does not fit')
            stem=f'ZX-video-optimized-preview_part{part:02}'
            trd=directory/(stem+'.trd'); metadata=directory/(stem+'.json')
            trd.write_bytes(image); metadata.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
            records.append(dict(part=part,file=trd.name,metadata=metadata.name,
                frame_start=start,frame_end_exclusive=end,sha256=sha(image)))
            target=directory/f'fuse_part{part:02}.json'
            subprocess.run([sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
                '--fuse',str(args.fuse.resolve()),'--trd',str(trd.resolve()),
                '--metadata',str(metadata.resolve()),'--raw',str(args.raw.resolve()),
                '--states',str(args.states.resolve()),'--output',str(target.resolve()),
                '--timeout',str(args.timeout)],check=True)
            measured=json.loads(target.read_text(encoding='utf-8'))
            summary=summarize_fuse(measured)
            for key in ('missed_nominal_frame_indices','publication_intervals_tstates','late_runs'):
                summary.pop(key)
            pub=measured['publications']; elapsed=pub[-1]['tstate']-pub[0]['tstate']
            summary.update(actual_fps=(len(pub)-1)*3546900/elapsed,
                recovered_late_runs=sum(r['recovered_at'] is not None for r in measured['late_runs']),
                unrecovered_late_runs=sum(r['recovered_at'] is None for r in measured['late_runs']))
            row=dict(part=part,frames=end-start,video_bytes=meta['video_bytes'],
                used_sectors=meta['used_sectors'],free_sectors=meta['free_sectors'],
                trd_sha256=meta['trd_sha256'],read_attempts=measured['read_attempts'],
                fast_read_retries=measured['fast_read_retries'],
                keepalive_calls=sum(s['kind']=='keepalive' for s in measured['seek_calls']),
                full_report=f'limit-{limit:03}/fuse_part{part:02}.json',timing=summary)
            variant['volumes'].append(row); save(); print(json.dumps(row),flush=True)
            start=end
        (directory/'volumes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
        variant['complete']=True; save()
    report['complete']=True; save()


if __name__=='__main__': main()
