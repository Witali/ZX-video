import gzip,json,time,shutil,hashlib
from pathlib import Path
import numpy as np
from clock_control import prepare,PARAMETERS,score
from general import models,timeline
from ima_codec import decode
from ima_waveform_encoder import encode_waveform
from precompensate_voice import compensate
from probe_reconstruction_error import wav8
from build_pdm import CPU_CLOCK
r=Path('audiobook-beeper/experiments/song-snr/evidence');scratch=Path('.tmp/audit');model=dict(models())[PARAMETERS['model_name']];rows=[]
for name in ('steps','loud3000'):
 source=wav8(r/'general/inputs'/(name+'.wav'));times=timeline(len(source),'pentagon');desired,features,ids,nxt,_=prepare(source,times,model);target=compensate(source,times[::16],period=CPU_CLOCK/8000)
 for width,reg in ((128,.1),(256,.1),(32,1.),(32,.03)):
  start=time.monotonic();packed=encode_waveform(target,desired,features,ids,nxt,width=width,block_size=128,commit_size=64,regularization=reg)
  metrics,_,_=score(source,packed,model,times,shutil.which('ffmpeg'),scratch);row=dict(source=name,width=width,regularization=reg,seconds=time.monotonic()-start,metrics=metrics,packed_sha256=hashlib.sha256(packed).hexdigest(),packed_bytes=len(packed))
  (scratch/(f'{name}-w{width}-r{reg}.ima.gz')).write_bytes(gzip.compress(packed,mtime=0));rows.append(row);(scratch/'width-benchmark.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
