import gzip,json,subprocess,wave
from pathlib import Path
import numpy as np
from ima_codec import decode
from build_pdm import reconstruct,write_wav
from probe_reconstruction_error import wav8,filtered
from analyze_ima_boundaries import read_wav
from assess_snr import ratio

out=Path('.tmp/voice-stage2');out.mkdir(exist_ok=True)
root=Path('audiobook-beeper/experiments/ima-3bit-overlap')
base=root/'qualified';ffmpeg='C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/bin/ffmpeg.exe'
source=wav8(base/'source-preview.wav');pcm,_=decode(gzip.decompress((base/'soundtrack.ima.gz').read_bytes()))
t=np.frombuffer(gzip.decompress((root/'verification/cold-0001/part-01-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
n=(len(source)-128)//8*8;t=t[:n*16+1];bounds=t[::16]
f=np.arange(0,t[-1],3546900/8000);uniform=np.r_[f,t[-1]]
signals={
 'source':filtered(reconstruct(np.pad(source/256,(0,max(0,len(f)-len(source))),constant_values=.5)[:len(f)],uniform),ffmpeg),
 'ima':filtered(reconstruct((pcm[:n].astype(float)+32768)/65536,bounds),ffmpeg),
 'levels':filtered(reconstruct((np.floor((pcm[:n].astype(float)+32768)/512)+.5)/128,bounds),ffmpeg),
 'pdm':read_wav(root/'verification/cold-0001/part-01-output.wav'),
}
count=min(map(len,signals.values()));signals={k:v[:count] for k,v in signals.items()}
def metrics(y,s):
 s=s[4410:-4410];y=y[4410:-4410];e=y-s
 sizes=8192;w=np.hanning(sizes);freq=np.fft.rfftfreq(sizes,1/44100);sp=np.zeros(len(freq));ep=sp.copy()
 for i in range(0,len(s)-sizes,sizes//2):
  sp+=abs(np.fft.rfft(s[i:i+sizes]*w))**2;ep+=abs(np.fft.rfft(e[i:i+sizes]*w))**2
 bands=[]
 for lo,hi in [(70,300),(300,1000),(1000,2000),(2000,3000),(3000,4000),(4000,6000),(6000,10000),(10000,20000)]:
  use=(freq>=lo)&(freq<hi);bands.append(dict(band=[lo,hi],snr_db=float(10*np.log10(sp[use].sum()/ep[use].sum()))))
 phase=(np.arange(len(e))+4410)*3546900/44100%70908
 groups=np.minimum(99,(phase/70908*100).astype(int));error=np.bincount(groups,weights=e*e);power=np.bincount(groups,weights=s*s)
 return dict(snr_db=ratio(s,e),bands=bands,field_noise_ratio=(error/power).tolist(),field_max_to_min=float((error/power).max()/(error/power).min()))
report={}
for name,y in signals.items():
 write_wav(out/(name+'.wav'),y)
 if name!='source':report[name]=metrics(y,signals['source'])
report['pdm_vs_ima']=metrics(signals['pdm'],signals['ima'])
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:{q:v[q] for q in ('snr_db','bands','field_max_to_min')} for k,v in report.items()},indent=2))
