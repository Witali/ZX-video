"""Host-only WAV-IMA3 recurrence control, on the unchanged saved PDM clock.

Private module copies isolate the experiment; no production module is edited.
The input/output host carrier still holds c3<<1 in each nibble.
"""
import gzip,itertools,json,time,types
from pathlib import Path
import numpy as np
from ima_waveform_encoder import prepare
from probe_reconstruction_error import wav8,filtered
from build_pdm import reconstruct,write_wav
from assess_snr import ratio

def module(name,file):
 code=Path('audiobook-beeper',file).read_text().replace('(step>>3)+','(step>>2)+').replace('(steps>>3)+','(steps>>2)+').replace('(steps >> 3)', '(steps >> 2)')
 code=code.replace('pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)', 'pcm,indices=decode(packed)')
 m=types.ModuleType(name);exec(compile(code,str(Path('audiobook-beeper',file)), 'exec'),m.__dict__)
 m.INDEX=(-1,-1,-1,-1,1,4,2,8)
 return m
codec=module('wav3_codec','ima_codec.py')
pcm_encoder=module('wav3_pcm_encoder','ima_beam.py')
encoder=module('wav3_waveform','ima_waveform_encoder.py')
encoder.decode=codec.decode;encoder.require_unclipped=codec.require_unclipped;encoder.encode_pcm=pcm_encoder.encode
base=Path('audiobook-beeper/experiments/ima-3bit-overlap/qualified')
out=Path('.tmp/voice-standard3-probe');out.mkdir(exist_ok=True)
meta,t,words,nxt,source,desired,features,ids=prepare(base)
n=32768+128;prior=wav8(base/'compensated-pcm.wav')[:n].copy();prior[-128:]=128
source=source[:n].copy();source[-128:]=128;t=t[:n*16+1];ids=ids[:n-128];desired=desired[:n-128]
started=time.monotonic()
packed=encoder.encode_waveform(prior,desired,features,ids,nxt,width=256,block_size=128,commit_size=64,
 regularization=.03,allowed_codes=np.arange(0,16,2),level_bounds=meta['model']['level_bounds'])
pcm,indices=codec.decode(packed)
# Unlike the subset, WAV-IMA3 has no zero-delta code at index zero.
# Constrain the last six silent-guard samples to end at predictor/index 0/0.
assert indices[-7]==0
paths=np.asarray(list(itertools.product((0,2,8,10),repeat=6)),dtype='u1')
differences=np.where(paths&8,-1,1)*np.where(paths&2,4,1)
predictions=int(pcm[-7])+np.cumsum(differences,axis=1)
valid=np.flatnonzero(predictions[:,-1]==0)
chosen=valid[np.argmin(np.sum(predictions[valid]**2,axis=1))]
tail=paths[chosen];packed=packed[:-3]+bytes((tail[::2]|(tail[1::2]<<4)).tolist())
pcm,indices=codec.decode(packed);assert (pcm[-1],indices[-1])==(0,0)
codec.require_unclipped(packed)
state=16;packets=[]
for p in pcm:
 level=(int(p)+32768)//512;packets.append(words[level,state]);state=int(nxt[level,state])
bits=np.unpackbits(np.asarray(packets,dtype='>u2').view('u1'))
ffmpeg='C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/bin/ffmpeg.exe'
y=filtered(reconstruct(bits,t),ffmpeg)
period=3546900/8000;segments=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(segments)*period,t[-1]]
values=np.pad(source/256,(0,max(0,segments-n)),constant_values=.5)[:segments]
original=filtered(reconstruct(values,edges),ffmpeg)
ref=original[4410:-4410];err=y[4410:-4410]-ref;size=8192;w=np.hanning(size);freq=np.fft.rfftfreq(size,1/44100)
sp=np.zeros(len(freq));ep=sp.copy()
for j in range(0,len(ref)-size,size//2):
 sp+=abs(np.fft.rfft(ref[j:j+size]*w))**2;ep+=abs(np.fft.rfft(err[j:j+size]*w))**2
bands={}
for lo,hi in [(70,1000),(1000,2000),(2000,3000),(3000,4000)]:
 use=(freq>=lo)&(freq<hi);bands[f'{lo}-{hi}']=float(10*np.log10(sp[use].sum()/ep[use].sum()))
report=dict(scope=__doc__,samples=n,seconds=time.monotonic()-started,snr_db=ratio(ref,err),bands=bands,player_verified=False)
(out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0));write_wav(out/'result.wav',y)
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
