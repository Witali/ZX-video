"""Save qualified winners and rejected bounded probes with content hashes."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];MODULES=HERE.parents[1]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(source,dest):
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)

def candidate(source,dest):
    for path in source.iterdir():
        if path.is_file():copy(path,dest/path.name)
    for name in ('assembly','producer-source'):
        if (source/name).is_dir():shutil.copytree(source/name,dest/name,dirs_exist_ok=True)
    proof=read(source/'fuse.json');native=read(source/'native.json')
    assert proof['complete'] and proof['cold_boot'] and proof['cycles_verified']==2
    assert native['complete'] and native['memory_guards_passed'] and native['every_pdm_bit_exact']
    assert proof['runtime_disk_reads']==0
    if 'trd_sha256' in proof:assert proof['trd_sha256']==sha(source/'audiobook-preview.trd')
    work=source/'verification-work'
    if not work.exists() and (source/'report.json').exists():
        selected=read(source/'report.json').get('selected')
        if isinstance(selected,str):work=source/selected/'verification-work'
    if work.exists():shutil.copytree(work,dest/'verification-work',dirs_exist_ok=True)
    calibration=source/'calibration'
    if (calibration/'calibration.json').exists():
        copy(calibration/'calibration.json',dest/'calibration.json')
        for phase in calibration.glob('phase-*'):
            for name in ('phase-probe.json','phase-debugger.txt','phase-trace.txt','phase-stderr.txt','player.json'):
                if (phase/name).exists():copy(phase/name,dest/'phase-probes'/phase.name/name)

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path);p.add_argument('--verify',action='store_true')
    a=p.parse_args();manifest=HERE/'manifest.json'
    if a.verify:
        hashes=read(manifest)
        for name,digest in hashes.items():assert sha(ROOT/name)==digest,name
        print(f'Verified {len(hashes)} archived artifacts');return
    if not a.work:p.error('--work is required')
    work=a.work.resolve();dest=HERE/'evidence'
    cases={'ima3':('ima3',['cached-first','third','selected']),
           'ima4':('ima4',['third','selected']),
           'mulaw-joint':('mulaw',['control','timing-control','waveform-8','waveform-32','selected']),
           'mulaw':('rejected-first-clock',['control','waveform-8','waveform-32','selected'])}
    summary={};targets=[]
    for folder,(name,variants) in cases.items():
        source=work/folder;report=read(source/'report.json');assert report['complete']
        for path in source.iterdir():
            if path.is_file():copy(path,dest/name/path.name)
        for variant in variants:candidate(source/variant,dest/name/variant)
        for sub in ('stable','recording'):
            if (source/sub).exists():
                for path in (source/sub).rglob('*'):
                    if path.is_file() and path.suffix!='.fmf':copy(path,dest/name/sub/path.relative_to(source/sub))
        if name!='rejected-first-clock':
            target=ROOT/f'ZX-audiobook-max-{name.upper() if name.startswith("ima") else name}.trd'
            copy(source/'selected/audiobook-preview.trd',target);targets.append(target)
            assert sha(target)==report['trd_sha256']
            assert read(source/'recording/report.json')['source_trd_sha256']==sha(target)
            summary[name]=report
    for name in ('ima3-host','ima4-host','mulaw-probe','mulaw-probe-wide','mulaw-probe-timed'):
        shutil.copytree(work/name,dest/name,dirs_exist_ok=True)
    cli=work/'mulaw-cli'
    assert read(cli/'report.json')['complete'] and read(cli/'report.json')['quality_profile']=='best'
    candidate(cli,dest/'mulaw-cli')
    for name in ('control','timing-control','waveform-8','waveform-32'):candidate(cli/name,dest/'mulaw-cli'/name)
    sources=list(MODULES.glob('*.py'))+list(MODULES.glob('*player.asm'))
    for path in sources:
        target=dest/'producer-source'/(path.name+'.gz');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(gzip.compress(path.read_bytes().replace(b'\r\n',b'\n'),mtime=0))
    # The failed first-clock prototype loaded these two older modules.
    for path in (HERE/'rejected-first-clock-source').glob('*.py'):
        copy(path,dest/'rejected-first-clock-source'/path.name)
    (HERE/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
    files=sorted(path for path in dest.rglob('*') if path.is_file())+targets+[HERE/'results.json']
    manifest.write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files},indent=2)+'\n')
    print(f'Archived {len(files)} artifacts')
if __name__=='__main__':main()
