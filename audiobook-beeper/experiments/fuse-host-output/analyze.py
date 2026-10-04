"""Measure the host output transport; these fitted scores are not codec SNR."""
import argparse,gzip,json,re,subprocess,wave
from pathlib import Path
import numpy as np
from build_pdm import write_wav
from record_pcm import read_fmf
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--ffmpeg',required=True);a=p.parse_args();out=a.directory
report=json.loads((out/'report.json').read_text());rate=report['source_frequency']
if report.get('warnings'):raise ValueError('Capture has discontinuities; do not infer playback jitter from this recording')
ffmpeg=a.ffmpeg
def read(path):
 with wave.open(str(path),'rb') as w:
  return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float).reshape(-1,w.getnchannels()).mean(axis=1)/32768
x=read(out/'internal.wav');y=read(out/'loopback.wav')
trace=(out/'stdout.txt').read_text()
values=[int(v,0) for v in re.findall(r'(?m)^(-?\d+|0x[\da-fA-F]+)\s*$',trace)]
if not values:raise ValueError('No execution markers')
ready=values.index(100);frame,tick=values[ready+1:ready+3]
blob=((out/'capture.fmf').read_bytes() if (out/'capture.fmf').exists()
      else gzip.decompress((out/'capture.fmf.gz').read_bytes()))
if rate==44100:_,chunks,_=read_fmf(blob)
else:
 import types
 m=types.ModuleType('rate_reader');s=Path('audiobook-beeper/record_pcm.py').read_text()
 exec(compile(s.replace('rate != 44100',f'rate != {rate}'),'<reader>','exec'),m.__dict__)
 _,chunks,_=m.read_fmf(blob)
chunk=next(c for c in chunks if c[0]==frame);start=chunk[1]+round(chunk[2]*tick/70908)
x=x[start:]
result=subprocess.run([ffmpeg,'-v','error','-f','f64le','-ar',str(rate),'-ac','1','-i','-',
 '-ar','48000','-f','f64le','-'],input=x.astype('<f8').tobytes(),capture_output=True,check=True)
x=np.frombuffer(result.stdout,'<f8')
def corr(signal,reference):
 n=len(signal)+len(reference)-1;nfft=1<<(n-1).bit_length()
 return np.fft.irfft(np.fft.rfft(signal,nfft)*np.fft.rfft(reference[::-1],nfft),nfft)[len(reference)-1:len(signal)]
# Speech inside the first part avoids the long nearly silent disk-loader prefix.
offset=48000;fragment=x[offset:offset+96000]
c=corr(y,fragment);global_start=int(np.argmax(c))-offset
rows=[];last=global_start;window=4800;search=1440
for pos in range(4800,min(len(x)-window,22*48000),4800):
 ref=x[pos:pos+window];left=max(0,last+pos-search);right=min(len(y),last+pos+window+search)
 if np.std(ref)<.002:continue
 signal=y[left:right];xc=corr(signal,ref)
 power=np.convolve(signal**2,np.ones(window),'valid')
 normalized=xc/np.sqrt(np.maximum(power*np.sum(ref**2),1e-30))
 peak=int(np.argmax(normalized));lag=left+peak-pos
 seg=y[lag+pos:lag+pos+window];gain=float(np.dot(seg,ref)/np.dot(ref,ref))
 residual=seg-gain*ref
 snr=float(10*np.log10(np.sum((gain*ref)**2)/max(1e-30,np.sum(residual**2))))
 rows.append(dict(second=pos/48000,lag_samples=lag-global_start,correlation=float(normalized[peak]),gain=gain,residual_db=snr))
 last=lag
slice_y=y[global_start:global_start+len(x)]
n=min(len(slice_y),len(x));trim=4800;ref=x[trim:n-trim];actual=slice_y[trim:n-trim]
gain=float(np.dot(ref,actual)/np.dot(ref,ref))
error=actual-gain*ref
summary=dict(scope=__doc__,start_sample=global_start,output_gain=gain,
 fixed_lag_residual_db=float(10*np.log10(np.sum((gain*ref)**2)/np.sum(error**2))),
 minimum_correlation=min(r['correlation'] for r in rows),
 lag_range_samples=[min(r['lag_samples'] for r in rows),max(r['lag_samples'] for r in rows)],
 lag_range_ms=(max(r['lag_samples'] for r in rows)-min(r['lag_samples'] for r in rows))/48,
 median_window_residual_db=float(np.median([r['residual_db'] for r in rows])),windows=rows)
(out/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
# Preserve the captured gain. Do not pass fitted or stretched audio to the user.
write_wav(out/'speaker-speech.wav',slice_y[:min(n,20*48000)],rate=48000)
write_wav(out/'internal-speech.wav',x[:min(n,20*48000)],rate=48000)
print(json.dumps({k:v for k,v in summary.items() if k!='windows'}),flush=True)
