"""Save the completed PC-only study and authenticate its outputs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import wave

import numpy as np
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MODULES=HERE.parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True,type=Path)
    a=p.parse_args();base=a.build.resolve();ev=HERE/'evidence';ev.mkdir(exist_ok=True)
    proof=json.loads((base/'snr30-ima-sim/verification.json').read_bytes())
    assert proof['complete'] and all(c['selected_output_bits_checked'] for c in proof['controls'])
    for dest,src in [('assessment','snr30-ima-v2'),('simulation','snr30-ima-sim'),('failed-initial','snr30-ima')]:
        shutil.copytree(base/src,ev/dest,dirs_exist_ok=True)
    for name in ('snr30-ima.log','snr30-ima-v2.log','snr30-ima-sim.log','snr30-ima-verify-selected.log'):
        shutil.copy2(base/name,ev/name)
    wav_checks=[]
    for codec in ('ima3','ima4'):
        for kind in ('best-preview','reference-same-gain'):
            name=codec+'-'+kind+'.wav';shutil.copy2(base/'snr30-ima-sim'/name,HERE/name)
            with wave.open(str(HERE/name),'rb') as w:
                pcm=np.frombuffer(w.readframes(w.getnframes()),'<i2')
                assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,44100)
            assert not np.any((pcm==32767)|(pcm==-32767)|(pcm==-32768))
            wav_checks.append(dict(file=name,samples=len(pcm),full_scale_samples=0))
    save(ev/'wav-checks.json',wav_checks)
    producers=HERE/'producers';producers.mkdir(exist_ok=True)
    for name in ('assess_snr.py','build_pdm.py','ima_beam.py','ima_codec.py','ima_waveform_encoder.py',
                 'probe_reconstruction_error.py','verify_direct.py','convert_audio.py'):
        (producers/(name+'.gz')).write_bytes(gzip.compress((MODULES/name).read_bytes(),mtime=0))
    files=[f for f in HERE.rglob('*') if f.is_file() and f.name!='manifest.json' and '__pycache__' not in f.parts]
    save(HERE/'manifest.json',dict(artifacts={f.relative_to(HERE).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(files)}))
    print(json.dumps(dict(artifacts=len(files),wav_checks=wav_checks)))


if __name__=='__main__':main()
