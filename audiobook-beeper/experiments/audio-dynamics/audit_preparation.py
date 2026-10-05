"""Audit the actual audiobook: off-mode compatibility and continuous gentle gain."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import wave

import numpy as np
from audio_dynamics import normalize_file
from build_pdm import write_wav
from ima4_series import plan_parts

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--ffmpeg',required=True)
a=p.parse_args();out=a.output;out.mkdir(exist_ok=False,parents=True)
base=Path(__file__).resolve().parent.parent/'ima4-full-disk'
manifest=json.loads((base/'artifact-hashes.json').read_bytes())
digest=lambda blob:hashlib.sha256(blob).hexdigest()
track=json.loads((a.build/'track.json').read_bytes())
oldtrack=json.loads((base/'release/track.json').read_bytes())
raw=a.build/'track-decoded.f32'
assert digest(raw.read_bytes())==oldtrack['sha256']
started=time.perf_counter()
gain,info=normalize_file(raw,out/'peak-only.f32',a.ffmpeg,'off')
elapsed=time.perf_counter()-started
assert digest((out/'peak-only.f32').read_bytes())==oldtrack['sha256'] and gain==oldtrack['gain']
old=np.memmap(out/'peak-only.f32',dtype='<f4',mode='r')
new=np.memmap(a.build/'track.f32',dtype='<f4',mode='r')
assert len(old)==len(new)==track['samples']
rows=[]
for number,part in enumerate(plan_parts(len(old))[:5],1):
    def prepare(values,amplitude):
        y=values[part['start']:part['stop']].astype(float)*amplitude
        y[:80]*=np.linspace(0,1,80);y[-80:]*=np.linspace(1,0,80)
        pcm=np.full(part['samples'],128,dtype='u1')
        pcm[:len(y)]=np.clip(np.rint(y*128+128),0,255).astype('u1')
        return pcm
    before=prepare(old,gain);after=prepare(new,track['gain'])
    name=f'selected/part-{number:05d}/source-preview.wav';blob=(base/name).read_bytes()
    assert digest(blob)==manifest[name]
    with wave.open(str(base/name),'rb') as w:reference=w.readframes(w.getnframes())
    assert before.tobytes()==reference
    rms=lambda pcm:float(np.sqrt(np.mean(((pcm.astype(float)-128)/128)**2)))
    rows.append(dict(part=number,samples=len(after),off_byte_exact=True,
        before_rms=rms(before),after_rms=rms(after),rms_gain_db=20*np.log10(rms(after)/rms(before)),
        source_sha256=digest(after.tobytes()),off_sha256=digest(before.tobytes())))
    if number==1:
        for name,pcm in [('before-first8.wav',before),('gentle-first8.wav',after)]:
            write_wav(out/name,(pcm[:64000].astype(float)-128)/128,8000)
del old,new
report=dict(date='2026-10-05',all_five_off_sources_byte_exact=True,
    full_selected_track_samples=track['samples'],track_dynamics=track['dynamics'],parts=rows,
    off_copy_scan_seconds=elapsed,scope='Source preparation only; not encoding throughput or PDM SNR.')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(report),flush=True)
