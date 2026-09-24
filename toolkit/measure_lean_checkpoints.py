"""Full Fuse comparison for the checkpoint experiment, with archived evidence.

Reuses previous full measurements only when their TRD SHA matches the freshly
built image. Changed disks run sequentially. CPU instruction counts from the
short probe are archived separately and never presented as full disk timing.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_fap3_trd import sha
from profile_fap3 import summarize_fuse


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','baseline','raw','states','fuse','evidence','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cpu-build',type=Path,action='append',default=[])
    p.add_argument('--timeout',type=float,default=300)
    args=p.parse_args(); args.evidence.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    report=dict(complete=False,release=False,full_pixel_comparison=False,pixel_samples_per_frame=80,
        physical_drive_verified=False,disks=[],cpu_evidence=[],cpu_comparison=[])
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def archive(data, name):
        path=args.evidence/name; path.parent.mkdir(parents=True,exist_ok=True)
        blob=(json.dumps(data,separators=(',',':'))+'\n').encode('utf-8'); path.write_bytes(blob)
        return dict(file=path.relative_to(args.evidence).as_posix(),sha256=sha(blob))
    def summary(data):
        result=summarize_fuse(data)
        for key in ('missed_nominal_frame_indices','publication_intervals_tstates','late_runs'): result.pop(key)
        pubs=data['publications']
        result.update(actual_fps=(len(pubs)-1)*3546900/(pubs[-1]['tstate']-pubs[0]['tstate']),
            recovered_late_runs=sum(r['recovered_at'] is not None for r in data['late_runs']),
            unrecovered_late_runs=sum(r['recovered_at'] is None for r in data['late_runs']))
        return result
    save()
    records=json.loads((args.build/'cold-bitmaps/volumes.json').read_text(encoding='utf-8'))
    for record in records:
        part=record['part']; old_meta=json.loads((args.build/'baseline'/record['metadata']).read_text())
        old_path=args.baseline/f'fuse_part{part:02}.json'
        old=json.loads(old_path.read_text(encoding='utf-8'))
        if not old['complete'] or old['trd_sha256']!=old_meta['trd_sha256']:
            raise ValueError('old evidence differs from rebuilt baseline image')
        trd=args.build/'cold-bitmaps'/record['file']; metadata=trd.with_suffix('.json')
        if sha(trd.read_bytes())!=record['sha256']: raise ValueError('new image differs from manifest')
        reused=record['sha256']==old['trd_sha256']
        if reused:
            data=old
        else:
            target=trd.parent/f'fuse_part{part:02}.json'
            subprocess.run([sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
                '--fuse',str(args.fuse.resolve()),'--trd',str(trd.resolve()),
                '--metadata',str(metadata.resolve()),'--raw',str(args.raw.resolve()),
                '--states',str(args.states.resolve()),'--output',str(target.resolve()),
                '--timeout',str(args.timeout)],check=True)
            data=json.loads(target.read_text(encoding='utf-8'))
        if not data['complete'] or data['trd_sha256']!=record['sha256']:
            raise ValueError('new measurement is incomplete or does not match image')
        row=dict(part=part,frames=data['frames'],ay_ticks=data['ay_ticks'],
            evidence=archive(data,f'fuse_part{part:02}.json'),
            baseline_file=old_path.as_posix(),baseline_trd_sha256=old['trd_sha256'],
            new_trd_sha256=data['trd_sha256'],reused_identical_image_evidence=reused,
            baseline=summary(old),cold_bitmaps=summary(data),
            read_attempts=data['read_attempts'],fast_read_retries=data['fast_read_retries'])
        report['disks'].append(row); save()
        print(json.dumps(dict(part=part,baseline_fps=row['baseline']['actual_fps'],
            new_fps=row['cold_bitmaps']['actual_fps'],missed=row['cold_bitmaps']['missed_nominal_frames'])),flush=True)
    for build in args.cpu_build:
        for name in ('baseline','cold-bitmaps'):
            for path in sorted((build/name).glob('cpu_part*.json')):
                data=json.loads(path.read_text(encoding='utf-8'))
                report['cpu_evidence'].append(archive(data,f'cpu/{build.name}/{name}/{path.name}'))
        for path in sorted((build/'baseline').glob('cpu_part*.json')):
            old=json.loads(path.read_text(encoding='utf-8'))
            new=json.loads((build/'cold-bitmaps'/path.name).read_text(encoding='utf-8'))
            if old['instruction_listing']!=new['instruction_listing']:
                raise AssertionError('checkpoint-only experiment changed instruction listing')
            stages=set(old['foreground_stages'])|set(new['foreground_stages'])
            report['cpu_comparison'].append(dict(build=build.name,frames=old['frames'],
                frame_start=old['frame_start'],instruction_listing_identical=True,
                baseline_foreground_tstates=old['foreground_tstates'],new_foreground_tstates=new['foreground_tstates'],
                delta_foreground_tstates=new['foreground_tstates']-old['foreground_tstates'],
                delta_stages={s:new['foreground_stages'].get(s,0)-old['foreground_stages'].get(s,0) for s in sorted(stages)},
                baseline_prime_tstates=old['prime']['tstates'],new_prime_tstates=new['prime']['tstates'],
                delta_prime_tstates=new['prime']['tstates']-old['prime']['tstates']))
    report['complete']=True; save()


if __name__=='__main__': main()
