"""Archive completed IMA4 comparison, including the rejected candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def read(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path)
    p.add_argument('--verify',action='store_true');a=p.parse_args();manifest=HERE/'manifest.json'
    if a.verify:
        saved=read(manifest)
        for name,digest in saved.items():assert sha(ROOT/name)==digest,name
        print(f'Verified {len(saved)} archived artifacts');return
    if not a.work:p.error('--work is required for archive creation')
    work=a.work.resolve();report=read(work/'report.json');assert report['complete']
    dest=HERE/'evidence'
    for name in ('identity.json','cached-input-audit.json','report.json','boundary-diagnostics.json'):
        copy(work/name,dest/name)
    for name in ('disk-overlap','disk-no-overlap','selected'):
        source=work/name
        for path in source.iterdir():
            if path.is_file():copy(path,dest/name/path.name)
        for directory in ('assembly','producer-source'):
            if (source/directory).exists():shutil.copytree(source/directory,dest/name/directory,dirs_exist_ok=True)
        proof=read(source/'fuse.json');native=read(source/'native.json')
        assert proof['cold_boot'] and proof['complete'] and proof['cycles_verified']==2
        assert proof['trd_sha256']==sha(source/'audiobook-preview.trd')
        assert native['memory_guards_passed'] and native['every_pdm_bit_exact'] and native['every_predictor_and_index_exact']
        assert native['every_output_port_uncontended'] and proof['runtime_disk_reads']==0
        if name!='selected':
            selected=read(source/'report.json')['selected']
            shutil.copytree(source/selected/'verification-work',dest/name/'verification-work',dirs_exist_ok=True)
            if (source/'calibration/calibration.json').exists():
                copy(source/'calibration/calibration.json',dest/name/'calibration.json')
                for phase in (source/'calibration').glob('phase-*'):
                    for filename in ('phase-probe.json','phase-debugger.txt','phase-trace.txt','phase-stderr.txt','player.json'):
                        if (phase/filename).exists():copy(phase/filename,dest/name/'phase-probes'/phase.name/filename)
    for name in ('stable','recording','encode-no-overlap'):
        shutil.copytree(work/name,dest/name,dirs_exist_ok=True)
    old=HERE.parent/'ima-quality/paused/speech4-refined'
    shutil.copytree(old/'encode-1',dest/'encode-overlap',dirs_exist_ok=True)
    copy(old/'identity.json',dest/'encode-overlap/original-identity.json')
    for name in ('convert_mulaw_audio.py','build_pdm.py','assess_snr.py','analyze_ima_boundaries.py'):
        copy(HERE.parents[1]/name,dest/'measurement-source'/name)
    copy(HERE/'run.py',dest/'measurement-source/run.py')
    target=ROOT/'ZX-audiobook-IMA4-PDM-search-test.trd'
    copy(work/'selected/audiobook-preview.trd',target)
    assert sha(target)==report['trd_sha256']
    assert read(work/'recording/report.json')['source_trd_sha256']==report['trd_sha256']
    files=sorted(path for path in dest.rglob('*') if path.is_file())+[target]
    hashes={str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in files}
    manifest.write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    print(f'Archived {len(files)} artifacts')


if __name__=='__main__':main()
