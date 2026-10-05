"""Archive completed SD2 proofs and reproduce each published binary exactly."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from ima3_direct_player import build_disk
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MODULES=HERE.parents[1]
ROOT=MODULES.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',required=True,type=Path)
    a=p.parse_args();base=a.build.resolve();evidence=HERE/'evidence'
    evidence.mkdir(exist_ok=True);rebuilt=[]
    for name,path in [('pilot',base/'run/pilot'),('unreset-search',base/'run/candidate'),
                      ('guarded',base/'reset-candidate')]:
        meta=json.loads((path/'player.json').read_bytes())
        packed=gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
        fuse=json.loads((path/'fuse.json').read_bytes())
        native=json.loads((path/'native.json').read_bytes())
        assert fuse['complete'] and native['complete'] and fuse['cycles_verified']==2
        assert fuse['every_pdm_bit_exact'] and fuse['every_predictor_and_index_exact']
        assert sha(path/'audiobook-preview.trd')==fuse['trd_sha256']
        with tempfile.TemporaryDirectory() as tmp:
            disk,_=build_disk(packed,Path(tmp),meta['model'],meta['hot_indices'],
                              meta['loop_idle_pairs'],meta['loop_idle_pad_tstates'])
        assert disk==(path/'audiobook-preview.trd').read_bytes()
        dest=evidence/name;dest.mkdir(exist_ok=True)
        for f in path.iterdir():
            if f.is_file():shutil.copy2(f,dest/f.name)
        assembly=dest/'assembly';assembly.mkdir(exist_ok=True)
        for f in (path/'assembly').iterdir():
            if f.suffix!='.lst':shutil.copy2(f,assembly/f.name)
        selected=json.loads((path/'report.json').read_bytes())['selected']
        trace=path/selected/'verification-work'
        target=dest/'verification-work';target.mkdir(exist_ok=True)
        for f in trace.iterdir():
            if f.name=='fuse-trace.txt':
                (target/'fuse-trace.txt.gz').write_bytes(gzip.compress(f.read_bytes(),mtime=0))
            else:shutil.copy2(f,target/f.name)
        shutil.copy2(path/'calibration/calibration.json',dest/'calibration.json')
        rebuilt.append(dict(name=name,trd_sha256=sha(path/'audiobook-preview.trd'),
                            current_source_rebuild_byte_exact=True))
    for name in ('preflight.json','final-tests.log','final-tests-elevated.log','reset.log'):
        shutil.copy2(base/name,evidence/name)
    for name in ('identity.json','model.json','state-certificate.json','ideal-controls.json','report.json'):
        shutil.copy2(base/'run'/name,evidence/('initial-'+name))
    shutil.copytree(base/'run/encode',evidence/'encode',dirs_exist_ok=True)
    for name in ('sound-128',):
        shutil.copytree(base/'run'/name,evidence/('initial-'+name),dirs_exist_ok=True)
    shutil.copytree(base/'reset-sound',evidence/'guarded-sound',dirs_exist_ok=True)
    recording=json.loads((base/'reset-sound/report.json').read_bytes())
    assert recording['recording_complete'] and recording['paging_latches_match']
    assert recording['source_trd_sha256']==rebuilt[-1]['trd_sha256']
    for name,path in [('source-preview.wav',base/'reset-candidate/source-preview.wav'),
                      ('result-preview.wav',base/'reset-sound/fuse-preview.wav')]:
        shutil.copy2(path,HERE/name)
    shutil.copy2(base/'reset-candidate/audiobook-preview.trd',ROOT/'ZX-audiobook-SD2-128-test.trd')
    producers=HERE/'producers';producers.mkdir(exist_ok=True)
    for f in MODULES.iterdir():
        if f.suffix in ('.py','.asm'):
            (producers/(f.name+'.gz')).write_bytes(gzip.compress(f.read_bytes(),mtime=0))
    save(evidence/'rebuild.json',dict(date='2026-10-05',rebuilt=rebuilt,
        scope='Final sources reproduce all three executed binaries byte for byte. Original run identity is retained separately; the guarded disk has its own complete native/Fuse proof.'))
    files=[p for p in HERE.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
    save(HERE/'manifest.json',dict(artifacts={p.relative_to(HERE).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(files)},
        root_disk=dict(path='ZX-audiobook-SD2-128-test.trd',sha256=sha(ROOT/'ZX-audiobook-SD2-128-test.trd'))))
    print(json.dumps(dict(artifacts=len(files),rebuilt=rebuilt)),flush=True)


if __name__=='__main__':main()
