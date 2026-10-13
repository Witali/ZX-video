"""Authenticate complete cold auditions, archive their evidence and report."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

HERE=Path(__file__).resolve().parent
CORE=HERE.parents[1]


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--node',required=True)
    args=parser.parse_args()
    root=args.build
    report=json.loads((root/'report.json').read_bytes())
    raw=gzip.decompress((root/'registers.gz').read_bytes())
    packed=gzip.decompress((root/'soundtrack.ay9.gz').read_bytes())
    assert report['ticks']==15000 and len(raw)==165000 and len(packed)==135000
    assert sha(raw)==report['registers_sha256'] and sha(packed)==report['packed_sha256']
    proofs=[]; joined=[]
    for number in (1,2):
        part=root/f'part{number:02d}'
        proof=json.loads((part/'verification.json').read_bytes())
        assert proof['complete'] and proof['native']['complete'] and proof['native']['registers_exact']
        fuse=proof['fuse']
        assert fuse['complete'] and fuse['cold_boot'] and fuse['every_register_exact']
        assert fuse['ticks']==7500 and fuse['register_writes']==82500
        assert not fuse['missing_or_duplicate_fields'] and fuse['runtime_disk_reads']==0
        assert fuse['recording']['complete'] and fuse['recording']['cycles']==1
        assert sha((part/'audio-preview.trd').read_bytes())==fuse['trd_sha256']
        joined.append(gzip.decompress((part/'registers.gz').read_bytes()))
        proofs.append(dict(number=number,native=proof['native'],fuse=fuse))
    assert b''.join(joined)==raw
    for name,rate in (('ay-preview.wav',44100),('original-preview.wav',22050)):
        with wave.open(str(root/name),'rb') as audio:
            assert audio.getframerate()==rate and audio.getnframes()==300*rate
    report.update(all_disks_fuse_verified=True,verification=proofs,
        native_ticks_verified=sum(p['native']['ticks'] for p in proofs),
        fuse_ticks_verified=sum(p['fuse']['ticks'] for p in proofs),
        fuse_register_writes_verified=sum(p['fuse']['register_writes'] for p in proofs),
        python_version=sys.version,node_version=subprocess.check_output([args.node,'--version']).decode().strip())
    import numpy as np
    report['numpy_version']=np.__version__
    sources=[*sorted(CORE.glob('*.py')),*sorted(CORE.glob('*.js')),CORE/'ay-player.asm',CORE/'vendor/ayumi-js/ayumi.js',
             HERE/'build.py',HERE/'render_group.js',HERE/'finish.py',HERE/'fast_mixer.py',HERE/'check_shortlist.py']
    report['producer_sources_sha256_lf']={p.relative_to(CORE).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for p in sources}
    report['baseline_commit']='e7450386'
    report['date']='2026-10-13'
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    target=HERE/'evidence'
    shutil.copytree(root,target,dirs_exist_ok=True)
    logs={'build.log':'bbb-five-minute-shortlist.log','part01-verification.log':'bbb-five-minute-part01-verify.log',
          'part02-verification.log':'bbb-five-minute-part02-verify.log','interrupted-render-only.log':'bbb-five-minute-auto-build.log',
          'interrupted-column-pool.log':'bbb-five-minute-auto-parallel.log',
          'interrupted-bounded-full-search.log':'bbb-five-minute-final.log'}
    for destination,name in logs.items():
        shutil.copyfile(root.parent/name,target/destination)
    if report.get('resumed_complete_noise_stage'):
        shutil.copyfile(root.parent/'bbb-complete-noise.json',target/'resume-noise.json')
    shortlist=json.loads((root.parent/'bbb-shortlist-check/report.json').read_bytes())
    assert shortlist['complete'] and len(shortlist['cases'])==5
    assert all(x['shortlist_error_db']<=x['seed_error_db'] for x in shortlist['cases'].values())
    shutil.copytree(root.parent/'bbb-shortlist-check',target/'shortlist-validation',dirs_exist_ok=True)
    shutil.copyfile(root.parent/'bbb-shortlist-check.log',target/'shortlist-validation/run.log')
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
           for p in sorted(target.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (target/'manifest.json').write_text(json.dumps(dict(date=report['date'],files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    for name,expected in files.items():
        data=(target/name).read_bytes()
        assert len(data)==expected['bytes'] and sha(data)==expected['sha256'],name
    print(json.dumps(dict(complete=True,seconds=300,ticks=15000,disks=2,
                         fuse_register_writes=165000,archived_files=len(files),archive_bytes=sum(x['bytes'] for x in files.values()))))


if __name__=='__main__': main()
