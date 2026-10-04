"""Bounded 4.096-second speech probe; host model only, not a disk release."""
import argparse,gzip,json,time
from pathlib import Path
import numpy as np
from ima_waveform_encoder import prepare,encode_waveform
from probe_reconstruction_error import wav8,filtered
from verify_direct import reference
from build_pdm import reconstruct,write_wav
from assess_snr import ratio
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--ffmpeg',required=True)
a=p.parse_args()
base=a.reference
meta,t,words,nxt,source,desired,features,ids=prepare(base)
prior=wav8(base/'compensated-pcm.wav');n=32768+128
source=source[:n].copy();source[-128:]=128;prior=prior[:n].copy();prior[-128:]=128
t=t[:n*16+1];desired=desired[:n-128];ids=ids[:n-128]
ffmpeg=a.ffmpeg
period=3546900/8000;segments=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(segments)*period,t[-1]]
values=np.pad(source/256,(0,max(0,segments-n)),constant_values=.5)[:segments]
original=filtered(reconstruct(values,edges),ffmpeg)
out=a.output;out.mkdir(parents=True,exist_ok=True);rows=[]
for name,horizon,commit,history in [('baseline',128,128,0),('overlap',128,64,0),('history',128,64,128)]:
 started=time.monotonic();packed=encode_waveform(prior,desired,features,ids,nxt,256,horizon,.03,history,
                    allowed_codes=np.arange(0,16,2),level_bounds=meta['model']['level_bounds'],commit_size=commit)
 _,_,_,bits=reference(packed,cycles=1,model=meta['model'])
 actual=filtered(reconstruct(bits[:n*16],t),ffmpeg)
 row=dict(name=name,snr_db=ratio(original[4410:-4410],actual[4410:-4410]-original[4410:-4410]),seconds=time.monotonic()-started)
 (out/(name+'.ima.gz')).write_bytes(gzip.compress(packed,mtime=0));write_wav(out/(name+'.wav'),actual)
 rows.append(row);print(json.dumps(row),flush=True);(out/'report.json').write_text(json.dumps(rows,indent=2))
