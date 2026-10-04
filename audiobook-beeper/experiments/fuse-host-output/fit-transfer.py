"""Diagnostic stationary-filter fit, trained on one interval and tested on another.

No fitted/stretched signal is delivered or used for codec quality acceptance.
"""
import argparse,json,wave
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();out=a.directory
def read(name):
 with wave.open(str(out/name),'rb') as f:return np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
x=read('internal-speech.wav');y=read('speaker-speech.wav');n=min(len(x),len(y));x=x[:n];y=y[:n]
margin=128;lags=np.arange(-margin,margin+1);start=48000;end=10*48000
center=x[start:end];auto=np.array([np.dot(center,x[start-k:end-k]) for k in range(-2*margin,2*margin+1)])
matrix=auto[lags[:,None]-lags[None,:]+2*margin]
rhs=np.array([np.dot(x[start-k:end-k],y[start:end]) for k in lags])
matrix+=np.eye(len(lags))*auto[2*margin]*1e-6
h=np.linalg.solve(matrix,rhs)
prediction=np.convolve(x,h,'same')
snr=lambda a,b:float(10*np.log10(np.sum(a*a)/np.sum(b*b)))
score={}
for name,lo,hi in [('train',start,end),('test',end,n-margin)]:
 error=y[lo:hi]-prediction[lo:hi];score[name+'_residual_db']=snr(prediction[lo:hi],error)
gains=[]
for start in range(4800,n-4800,4800):
 ref=prediction[start:start+4800];actual=y[start:start+4800]
 if np.std(ref)<.003:continue
 gains.append(float(ref@actual/(ref@ref)))
frequencies=np.array([70,200,500,1000,2000,3000,5000,10000])
response=abs(np.exp(-2j*np.pi*frequencies[:,None]/48000*lags)@h)
report=dict(scope=__doc__,fir_taps=len(h),train_seconds=[1,10],**score,
 relative_gain_percentiles=np.percentile(gains,[5,50,95]).tolist(),
 response=[dict(hz=int(f),gain=float(g)) for f,g in zip(frequencies,response)])
(out/'transfer.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
