"""Small PC-only screen of unchanged-player mu-law waveform encoding."""
import argparse
import json
from pathlib import Path
import sys
import wave
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from mulaw_waveform_encoder import encode,saved_timeline
from convert_mulaw_audio import filter_signal
from verify_mulaw import reference
from g711_codec import encode as plain
from assess_snr import ratio

def main():
    p=argparse.ArgumentParser();p.add_argument('--ffmpeg',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    folder=Path(__file__).resolve().parents[1]/'mulaw-trd/qualified'
    with wave.open(str(folder/'source-preview.wav'),'rb') as w:pcm=np.frombuffer(w.readframes(8192),'<i2').copy()
    pcm[-128:]=0;t=saved_timeline(folder)[:len(pcm)*8+1];t-=t[0]
    original=filter_signal((pcm.astype(float)+32768)/65536,np.arange(len(pcm)+1)*3546900/8000,a.ffmpeg,768000)
    rows=[]
    for settings in (None,(8,16,8,.1),(32,32,8,.03),(32,32,8,.1),(32,32,8,.3)):
        stats={};b=plain(pcm,'mulaw',a.ffmpeg) if settings is None else encode(pcm,t,*settings,statistics=stats)
        y=filter_signal(reference(b)[1][:len(pcm)*8],t,a.ffmpeg,768000)
        n=min(len(original),len(y));cut=slice(4410,n-4410)
        row=dict(settings=settings,snr=ratio(original[cut],(y[:n]-original[:n])[cut]),stats=stats)
        rows.append(row);print(json.dumps(row),flush=True)
        (a.output/'probe.json').write_text(json.dumps(dict(scope='PC screen, not a new executable proof',rows=rows),indent=2))
if __name__=='__main__':main()
