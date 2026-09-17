"""Test note-transition penalties at 50 Hz using cached harmonic evidence.

Run benchmark_ay_rate.py first. The reference PCM is decoded again and its
hash must match that experiment, preventing stale/mismatched audio caches.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

import ay_fidelity as ay
import build_long_video_trd as video
import compare_ay_fidelity as quality


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--rate-build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--scales',type=float,nargs='+',default=[1,2,3,6])
    args=p.parse_args()
    experiment=json.loads((args.rate_build/'comparison.json').read_text())
    duration=experiment['duration_seconds'];rate=50;sample_rate=22050
    samples=video.decode_analysis_audio(args.ffmpeg,args.input_video,0,duration,sample_rate,True)
    digest=hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest()
    if digest!=experiment['source_pcm_sha256']:raise ValueError('reference PCM does not match cached analysis')
    saved=np.load(args.rate_build/'50Hz/analysis.npz')
    magnitude,rms=ay.spectra(samples,sample_rate,rate,round(duration*rate))
    reference=quality.features(samples,sample_rate,25/3,round(duration*25/3))
    args.output.mkdir(parents=True,exist_ok=True)
    results=[]
    for scale in args.scales:
        periods,volumes,notes=ay.arrange(saved['amplitude'],rms,saved['explained'],transition_scale=scale)
        noise,volumes,_=ay.arrange_noise(magnitude,rms,saved['explained'],volumes)
        previous=1
        for i in range(len(noise)):
            if noise[i]:periods[i,1]=previous
            else:previous=periods[i,1]
        frames=[video.AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n)) for p,v,n in zip(periods,volumes,noise)]
        rendered=ay.render(frames,rate,sample_rate)
        metrics=quality.compare(reference,quality.features(rendered,sample_rate,25/3,len(reference[2])))
        result=dict(transition_scale=scale,metrics=metrics,melody_changes=int(np.count_nonzero(np.diff(notes[:,2]))))
        results.append(result)
        quality.write_wav(args.output/f'scale_{scale:g}.wav',rendered,sample_rate)
        (args.output/'comparison.json').write_text(json.dumps(dict(source_pcm_sha256=digest,
            update_rate_hz=50,metric_rate_hz=25/3,results=results),indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result),flush=True)


if __name__=='__main__':main()
