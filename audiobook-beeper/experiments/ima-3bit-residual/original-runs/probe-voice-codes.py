"""Bounded host-only probe of frequency-weighted waveform coding."""
import gzip,json,time
from pathlib import Path
import numpy as np
from ima_waveform_encoder import prepare,WaveformModel,encode_waveform
from probe_reconstruction_error import wav8,filtered
from build_pdm import reconstruct,write_wav
from verify_direct import reference
from assess_snr import ratio

base=Path('audiobook-beeper/experiments/ima-3bit-overlap/qualified')
out=Path('.tmp/voice-codes-probe');out.mkdir(exist_ok=True)
ffmpeg='C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/bin/ffmpeg.exe'
meta,t,words,nxt,source,desired,features,ids=prepare(base)
n=32768+128;prior=wav8(base/'compensated-pcm.wav')[:n].copy();prior[-128:]=128
source=source[:n].copy();source[-128:]=128;t=t[:n*16+1];ids=ids[:n-128];desired=desired[:n-128]
holds=np.diff(t)[:(n-128)*16].reshape(-1,16)
unique,local_ids=np.unique(holds,axis=0,return_inverse=True)
signed=np.unpackbits(words.astype('>u2').view('u1'),axis=1).reshape(-1,16).astype(float)*2-1
dm=WaveformModel();dm.c=dm.c@dm.coefficients[1]*(8000/(2*np.pi*1000))
queries=((t[:(n-128)*16]+t[1:(n-128)*16+1])/2).reshape(n-128,16)
dtarget=dm.reference(wav8(base/'source-preview.wav'),queries)
dfeatures=[]
for row in unique:
 a,b,l,r=dm.packet(row);dfeatures.append((l,signed@r.T))
period=3546900/8000;segments=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(segments)*period,t[-1]]
values=np.pad(source/256,(0,max(0,segments-n)),constant_values=.5)[:segments]
original=filtered(reconstruct(values,edges),ffmpeg);write_wav(out/'source.wav',original)
def metrics(y):
 ref=original[4410:-4410];err=y[4410:-4410]-ref;size=8192;w=np.hanning(size);f=np.fft.rfftfreq(size,1/44100)
 sp=np.zeros(len(f));ep=sp.copy()
 for j in range(0,len(ref)-size,size//2):
  sp+=abs(np.fft.rfft(ref[j:j+size]*w))**2;ep+=abs(np.fft.rfft(err[j:j+size]*w))**2
 bands={}
 for lo,hi in [(70,1000),(1000,2000),(2000,3000),(3000,4000)]:
  use=(f>=lo)&(f<hi);bands[f'{lo}-{hi}']=float(10*np.log10(sp[use].sum()/ep[use].sum()))
 return dict(snr_db=ratio(ref,err),bands=bands)
rows=[]
for name,reg,weight in [('ima4',.03,0)]:
 started=time.monotonic();newfeatures=[]
 for j,row in enumerate(unique):
  at=np.flatnonzero(local_ids==j)[0];aa,ll,rr,bb,ww=features[ids[at]];dl,dr=dfeatures[j]
  newfeatures.append((aa,np.concatenate((ll,dl)),np.concatenate((rr,dr),axis=1),bb,np.r_[ww,ww*weight]))
 target=np.concatenate((desired,dtarget),axis=1)
 packed=encode_waveform(prior,target,newfeatures,local_ids,nxt,width=256,block_size=128,
  commit_size=64,regularization=reg,allowed_codes=None,level_bounds=meta['model']['level_bounds'])
 _,_,_,bits=reference(packed,cycles=1,model=meta['model'])
 y=filtered(reconstruct(bits[:len(t)-1],t),ffmpeg)
 row=dict(name=name,regularization=reg,slope_weight=weight,seconds=time.monotonic()-started,**metrics(y))
 write_wav(out/(name+'.wav'),y);(out/(name+'.ima.gz')).write_bytes(gzip.compress(packed,mtime=0))
 rows.append(row);(out/'report.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
