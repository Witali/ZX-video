"""Build real independent-boot pairs and fully measure smaller table startup.

Also assemble a three-volume size control; overfull images are not written.
All frame and AY packets are identical within each baseline/filtered pair.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from build_fap3_trd import sha
from run_deferred_disk import ReadThroughBuilder
from profile_fap3 import summarize_fuse
from test_fap3_disk import DiskCPU
from test_warm_continuation import player,until
from zx0_codec import decompress
import fap3_disk_z80 as disk
from probe_startup_tables import undifference


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw','states','zx0','fuse','output','report'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--timeout',type=float,default=300)
    p.add_argument('--ends',default='1269,2334,3195,4221')
    p.add_argument('--three-ends',default='1614,2920,4221')
    args=p.parse_args();raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as saved:states=saved['states']
    args.output.mkdir(parents=True,exist_ok=True);args.report.parent.mkdir(parents=True,exist_ok=True)
    report=dict(baseline_commit='b77a756',complete=False,release=False,frames=len(states),
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),pixel_changes=False,ay_changes=False,
        player_hot_path_changed=False,player_hot_path_delta_tstates=0,
        fixed_table_restore_tstates=541426,variants=[],size_controls=[])
    def save():args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    previous=None
    for filtered in (False,True):
        name='delta' if filtered else 'baseline';directory=args.output/name;directory.mkdir(exist_ok=True)
        builder=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',
            fast_disk=True,cached_seek=True,interleaved=True,cold_bitmaps=True,startup_delta=filtered)
        builder.read_cache=args.read_cache
        builder.ends=[int(v) for v in args.ends.split(',')]
        if previous is not None:builder.memo=previous.memo
        variant=dict(name=name,complete=False,volumes=[]);report['variants'].append(variant);records=[]
        for part,(start,end) in enumerate(zip([0]+builder.ends,builder.ends),1):
            image,m=builder.volume(start,end,part)
            if image is None:raise ValueError('measurement volume does not fit')
            stream_sha=sha(builder.stream(start,end)[0])
            if filtered and stream_sha!=report['variants'][0]['volumes'][part-1]['video_sha256']:
                raise AssertionError('startup filter changed video packets')
            stem=f'ZX-video-startup-delta_part{part:02}'
            trd=directory/(stem+'.trd');metadata=trd.with_suffix('.json')
            trd.write_bytes(image);metadata.write_text(json.dumps(m,indent=2)+'\n')
            records.append(dict(part=part,file=trd.name,metadata=metadata.name,frame_start=start,frame_end_exclusive=end,sha256=sha(image)))
            # Real opcode boot with mocked sector services, full bank-6 data.
            cpu=DiskCPU(player(image),image);until(cpu,disk.DRIVER)
            table=next(s for s in m['sections'] if s['bank']==6)
            at=table['sector']*256;stored=decompress(image[at:at+table['compressed_bytes']],limit=16384)
            expected=undifference(stored) if table.get('startup_delta') else stored
            if sha(expected)!=table['sha256'] or bytes(cpu.banks[6])!=expected:raise AssertionError('boot table differs')
            target=directory/f'fuse_part{part:02}.json'
            print(f'Full Fuse {name} part {part}',flush=True)
            subprocess.run([sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
                '--fuse',str(args.fuse.resolve()),'--trd',str(trd.resolve()),'--metadata',str(metadata.resolve()),
                '--raw',str(args.raw.resolve()),'--states',str(args.states.resolve()),'--output',str(target.resolve()),
                '--timeout',str(args.timeout)],check=True)
            data=json.loads(target.read_text());timing=summarize_fuse(data)
            for key in ('missed_nominal_frame_indices','publication_intervals_tstates','late_runs'):timing.pop(key)
            pubs=data['publications']
            timing.update(actual_fps=(len(pubs)-1)*3546900/(pubs[-1]['tstate']-pubs[0]['tstate']),
                recovered_late_runs=sum(r['recovered_at'] is not None for r in data['late_runs']),
                unrecovered_late_runs=sum(r['recovered_at'] is None for r in data['late_runs']))
            variant['volumes'].append(dict(part=part,frames=end-start,video_bytes=m['video_bytes'],
                used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],trd_sha256=m['trd_sha256'],
                table=table,boot_table_all_bytes_exact=True,boot_mocked_tstates=cpu.tstates,
                video_sha256=stream_sha,
                full_report=f'{name}/fuse_part{part:02}.json',timing=timing));save()
        (directory/'volumes.json').write_text(json.dumps(records,indent=2)+'\n')
        variant['complete']=True;save()
        builder.ends=[int(v) for v in args.three_ends.split(',')];control=dict(name=name,ends=builder.ends,volumes=[])
        for part,(start,end) in enumerate(zip([0]+builder.ends,builder.ends),1):
            image,m=builder.volume(start,end,part)
            control['volumes'].append({k:m[k] for k in ('part','frames','used_sectors','free_sectors','video_bytes')})
        control.update(all_fit=all(v['free_sectors']>=0 for v in control['volumes']),
            total_used_sectors=sum(v['used_sectors'] for v in control['volumes']))
        report['size_controls'].append(control);save();previous=builder
    report['complete']=True;save()


if __name__=='__main__':main()
