"""Archive direct-byte G.711 simulations and their numerical audit."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MODULES=HERE.parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True,type=Path)
    a=p.parse_args();base=a.build.resolve();out=HERE/'evidence';out.mkdir(exist_ok=True)
    proof=json.loads((base/'xlaw-stream/verification.json').read_bytes())
    assert proof['complete'] and proof['finer_selected']['target_30_db_passed']
    for name,path in [('initial',base/'xlaw-pc'),('stream',base/'xlaw-stream')]:
        shutil.copytree(path,out/name,dirs_exist_ok=True)
    for f in base.glob('xlaw-*.log'):shutil.copy2(f,out/f.name)
    for name in ('mulaw','alaw','pcm8'):
        shutil.copy2(base/'xlaw-stream'/(name+'-verified-preview.wav'),HERE/(name+'-preview.wav'))
    shutil.copy2(base/'xlaw-stream/reference-verified-preview.wav',HERE/'reference-preview.wav')
    for law in ('mulaw','alaw'):shutil.copy2(base/'xlaw-stream'/('soundtrack.'+law),HERE/('soundtrack.'+law))
    producers=HERE/'producers';producers.mkdir(exist_ok=True)
    for name,path in [('g711_codec.py',MODULES/'g711_codec.py'),('build_pdm.py',MODULES/'build_pdm.py'),
                      ('assess_snr.py',MODULES/'assess_snr.py'),('assess.py',HERE.parent/'snr30-ima/assess.py'),
                      ('probe_reconstruction_error.py',MODULES/'probe_reconstruction_error.py')]:
        (producers/(name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    files=[f for f in HERE.rglob('*') if f.is_file() and f.name!='manifest.json' and '__pycache__' not in f.parts]
    save(HERE/'manifest.json',dict(artifacts={f.relative_to(HERE).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(files)}))
    print(json.dumps(dict(artifacts=len(files),selected=proof['selected_high_precision'])))


if __name__=='__main__':main()
