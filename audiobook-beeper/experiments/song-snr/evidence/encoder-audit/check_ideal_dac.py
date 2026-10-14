import json,shutil
from pathlib import Path
import numpy as np
from general import timeline
from study import filtered,metrics,uniform
from probe_reconstruction_error import wav8
from build_pdm import CPU_CLOCK
r=Path('audiobook-beeper/experiments/song-snr/evidence');scratch=Path('.tmp/audit');rows=[]
for name in ('loud3000','steps','quiet440','multitone'):
 source=wav8(r/'general/inputs'/(name+'.wav'));times=timeline(len(source),'pentagon');at=(len(source)-3)*16+15;edges=np.r_[times[:at:16],times[at-1]];positions=(edges[:-1]+edges[1:])/(2*(CPU_CLOCK/8000))-.5
 centers=np.floor(positions).astype(np.int64);indices=centers[:,None]+np.arange(-15,17);d=positions[:,None]-indices;w=np.sinc(d)*np.sinc(d/16);vals=np.where((indices>=0)&(indices<len(source)),source[np.clip(indices,0,len(source)-1)].astype(float)-128,0.);target=(np.sum(w*vals,axis=1)/w.sum(axis=1)+128)/256
 actual=filtered(target,edges,shutil.which('ffmpeg'),scratch);v,e=uniform(source/256,edges[-1]);wanted=filtered(v,e,shutil.which('ffmpeg'),scratch);m=metrics(wanted,actual)
 err=(actual-wanted)[4410:-4410];window=np.hanning(len(err));f=np.fft.rfftfreq(len(err),1/44100);power=abs(np.fft.rfft(err*window))**2;top=np.argsort(power)[-8:][::-1]
 row=dict(source=name,ideal_compensated_multilevel_dac=m,error_power_fraction_above4000_hz=float(power[f>4000].sum()/power.sum()),top_error_bins=[dict(hz=float(f[i]),power_fraction=float(power[i]/power.sum())) for i in top]);rows.append(row);print(json.dumps(row),flush=True)
(scratch/'ideal-compensated-dac.json').write_text(json.dumps(rows,indent=2))
