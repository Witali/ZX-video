"""Run complete cold/native/Fuse and actual EOF continuation gates on a set.

Native jobs may run concurrently. All Fuse processes, including full-screen
captures, run serially. A failed deadline is recorded and never called a pass.
Existing complete reports are reused only with exact TRD/metadata identities.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import subprocess
import sys

from build_fap3_trd import sha
from convert_video import write_json

ROOT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_bytes())


def run(script,args,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w',encoding='utf-8') as out:
        result=subprocess.run([sys.executable,str(ROOT/script)]+[str(x) for x in args],stdout=out,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'{script} failed: {log}')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--fuse',type=Path,required=True)
    p.add_argument('--native-jobs',type=int,default=2);p.add_argument('--resume',action='store_true')
    a=p.parse_args();a.build=a.build.resolve();volumes=read(a.build/'volumes.json')
    built=read(a.build/'build.json');assert built['complete'] and len(volumes)==len(built['checks'])
    assert 1<=a.native_jobs<=4
    def paths(v):
        return a.build/v['file'],a.build/v['metadata'],a.build/v['states'],a.build/'work'/Path(v['file']).stem
    def native(v):
        trd,meta,states,work=paths(v);target=work/'cpu.json'
        if a.resume and target.exists():
            r=read(target)
            if r.get('complete') and r.get('trd_sha256')==sha(trd.read_bytes()) and r.get('metadata_sha256')==sha(meta.read_bytes()):return r
        run('verify_cached_cell_player.py',['--trd',trd,'--metadata',meta,'--states',states,'--output',target],work/'cpu.log')
        return read(target)
    results=dict(complete=False,release=False,cold=[],native=[],continuations=[],source_sha256_lf={
        n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in ('check_cached_cell_set.py','capture_cell_codebook_full.py')})
    def save():write_json(a.build/'checks.json',results)
    save()
    with ThreadPoolExecutor(max_workers=a.native_jobs) as pool:
        jobs={pool.submit(native,v):i for i,v in enumerate(volumes,1)}
        for i,v in enumerate(volumes,1):
            trd,meta,states,work=paths(v);m=read(meta);timing=work/'timing.json';screens=work/'screens.json'
            reuse=False
            if a.resume and timing.exists():
                r=read(timing)
                reuse=r.get('complete') and r.get('trd_sha256')==sha(trd.read_bytes()) and r.get('integrated_bootstrap_metadata_sha256')==sha(meta.read_bytes())
            if not reuse:
                run('measure_fap3_fuse.py',['--fuse',a.fuse,'--trd',trd,'--metadata',meta,'--states',states,
                    '--raw',a.build/'work/stream.raw','--output',timing,'--trace-pipeline','--timeout',600],work/'timing.log')
            r=read(timing)
            reuse=False
            if a.resume and screens.exists():
                s=read(screens);reuse=s.get('complete') and s.get('trd_sha256')==sha(trd.read_bytes()) and s.get('timing_sha256')==sha(timing.read_bytes())
            if not reuse:
                run('capture_cell_codebook_full.py',['--fuse',a.fuse,'--trd',trd,'--metadata',meta,'--states',states,
                    '--timing',timing,'--work',work/'captures','--output',screens,'--timeout',600],work/'screens.log')
            s=read(screens)
            results['cold'].append(dict(part=i,frames=m['frames'],used_sectors=m['used_sectors'],
                nominal_late_frames=r['nominal_late_frames'],max_actual_deviation_tstates=r['max_actual_deviation_tstates'],
                bad_actual_intervals=r['bad_actual_intervals'],late_runs=r['late_runs'],screens_exact=s['full_screens_exact'],
                ay_exact=r['ay_records_exact'],audio_underruns=r['audio_underruns']))
            save();print(json.dumps(dict(cold=results['cold'][-1])),flush=True)
        # This executes real prompt/load code with mismatched disk/set cases.
        cont=a.build/'continuation'
        run('verify_cell_codebook_continuation.py',['--build',a.build,'--fuse',a.fuse,'--raw',a.build/'work/stream.raw',
            '--output',cont,'--mode','mock'],cont/'mock.log')
        run('verify_cell_codebook_continuation.py',['--build',a.build,'--fuse',a.fuse,'--raw',a.build/'work/stream.raw',
            '--output',cont,'--mode','fuse'],cont/'fuse.log')
        for i,v in enumerate(volumes,1):
            trd,meta,states,work=paths(v);target=cont/f'part-{i}-screens.json'
            args=['--fuse',a.fuse,'--trd',trd,'--metadata',meta,'--states',states,
                '--timing',cont/f'part-{i}.json','--work',cont/f'captures-{i}','--output',target,'--timeout',600]
            if i>1:args+=['--continuation-snapshot',cont/f'resume-{i}.szx']
            run('capture_cell_codebook_full.py',args,cont/f'part-{i}-screens.log')
            r=read(cont/f'part-{i}.json');s=read(target)
            results['continuations'].append(dict(part=i,from_previous_eof=i>1,
                nominal_late_frames=r['nominal_late_frames'],max_actual_deviation_tstates=r['max_actual_deviation_tstates'],
                bad_actual_intervals=r['bad_actual_intervals'],late_runs=r['late_runs'],screens_exact=s['full_screens_exact'],
                ay_exact=r['ay_records_exact'],audio_underruns=r['audio_underruns']))
            save();print(json.dumps(dict(continuation=results['continuations'][-1])),flush=True)
        for job in as_completed(jobs):
            r=job.result();assert r['complete'] and r['all_native_screens_exact']
            results['native'].append(dict(part=jobs[job],frames=r['frames_checked'],screens_exact=True))
            save();print(json.dumps(dict(native=results['native'][-1])),flush=True)
    results['native'].sort(key=lambda x:x['part'])
    results.update(complete=True,all_nominal_deadlines_met=all(x['nominal_late_frames']==0 and x['bad_actual_intervals']==0
        for x in results['cold']+results['continuations']))
    save();print(json.dumps(dict(complete=True,all_nominal_deadlines_met=results['all_nominal_deadlines_met'])),flush=True)


if __name__=='__main__':main()
