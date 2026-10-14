import gzip,json
from pathlib import Path
import numpy as np
from clock_control import prepare,PARAMETERS
from general import models,timeline
from ima_codec import decode
from verify_direct import reference
from probe_reconstruction_error import wav8
from build_pdm import CPU_CLOCK
r=Path('audiobook-beeper/experiments/song-snr/evidence');scratch=Path('.tmp/audit');report=[]
model=dict(models())[PARAMETERS['model_name']]
for name in ('steps','loud3000','silence','quiet440'):
 source=wav8(r/'general/inputs'/(name+'.wav'));times=timeline(len(source),'pentagon')
 desired,features,ids,nxt,_=prepare(source,times,model);queries=((times[:-1]+times[1:])/2).reshape(-1,16)[:len(ids)]/CPU_CLOCK
 interp_reference=np.interp(queries.ravel(),np.arange(len(np.load(Path('.tmp/clock-joint')/(name+'-reference.npy'))))/44100,np.load(Path('.tmp/clock-joint')/(name+'-reference.npy'))).reshape(-1,16)
 cut=(queries>.1)&(queries<queries[-1,-1]-.1)
 for method in ('compensation','joint'):
  path=r/('clock-'+method)/name;packed=gzip.decompress((path/'soundtrack.ima.gz').read_bytes());pcm,_=decode(packed)
  state=np.zeros(6);q=16;observed=np.empty_like(desired);weights=np.empty_like(desired)
  for i,fid in enumerate(ids):
   aa,ll,rr,bb,w=features[fid];level=(int(pcm[i])+32768)//1024;k=level*32+q
   observed[i]=ll@state+rr[k];state=aa@state+bb[k];q=int(nxt[level,q]);weights[i]=w
  array=np.load(Path('.tmp/clock-'+method)/(name+'-'+method+'-actual.npy'))
  sampled=np.interp(queries.ravel(),np.arange(len(array))/44100,array).reshape(-1,16)
  sig=np.sum(weights[cut]*desired[cut]**2);noise=np.sum(weights[cut]*(observed[cut]-desired[cut])**2)
  rms=lambda x:float(np.sqrt(np.mean(x[cut]**2)))
  rows=dict(source=name,method=method,model_snr_db=float(10*np.log10(sig/noise)) if sig else None,search_signal_rms=rms(desired),search_error_rms=rms(observed-desired),actual_model_mismatch_rms=rms(sampled-observed),reference_model_mismatch_rms=rms(interp_reference-desired),actual_rms=rms(sampled),model_rms=rms(observed),observed_min=float(observed.min()),observed_max=float(observed.max()))
  report.append(rows);print(json.dumps(rows),flush=True)
(scratch/'report.json').write_text(json.dumps(report,indent=2))
