"""Measure short level holes against the exact processed listening reference."""
import argparse
import json
from pathlib import Path
import wave
import numpy as np


def read(path):
    with wave.open(str(path),'rb') as audio:
        assert audio.getsampwidth()==2 and audio.getnchannels()==1
        return np.frombuffer(audio.readframes(audio.getnframes()),'<i2').astype(float)/32768,audio.getframerate()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('build',type=Path);args=parser.parse_args()
    source,rate=read(args.build/'original-preview.wav');model,mrate=read(args.build/'ay-preview.wav')
    reference=np.sqrt(np.mean(source.reshape(-1,rate//50)**2,axis=1))
    observed=np.sqrt(np.mean(model.reshape(-1,mrate//50)**2,axis=1))
    active=reference>10**(-45/20)
    difference=20*np.log10(np.maximum(observed,1e-12)/np.maximum(reference,1e-12))
    missing=active&(difference < -15)
    indices=np.flatnonzero(missing)
    runs=np.split(indices,np.flatnonzero(np.diff(indices)>1)+1) if len(indices) else []
    result=dict(method='20-ms PCM16 RMS, processed reference above -45 dBFS, model more than 15 dB below reference',
        ticks=len(reference),active_ticks=int(active.sum()),strong_drop_ticks=int(missing.sum()),
        maximum_drop_run_ms=max(map(len,runs),default=0)*20,
        zero_active_ticks=int((active&(observed<1e-5)).sum()),
        active_level_mae_db=float(abs(difference[active]).mean()) if active.any() else 0,
        source_rms=float(np.sqrt(np.mean(source**2))),model_rms=float(np.sqrt(np.mean(model**2))),
        model_peak=float(abs(model).max()),clipped_samples=int((abs(model)>=32767/32768).sum()),
        runs=[dict(start_seconds=float(run[0]/50),ticks=len(run)) for run in runs])
    (args.build/'level-drops.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))


if __name__=='__main__':main()
