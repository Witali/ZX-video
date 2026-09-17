"""Test short median filters against one unchanged reference audio metric.

One-tick level/colour fluctuations may make false attacks and waste space.
These are candidate arrangements, not automatically accepted improvements.
Noise filtering stays inside noise-only runs; tone/noise switching is kept.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import ay_events
import ay_fidelity as ay
import ay_interrupt
import build_long_video_trd as video
import compare_ay_fidelity as quality


def median(values,width):
    padded=np.pad(values,(width//2,width//2),mode='edge')
    return np.median(np.lib.stride_tricks.sliding_window_view(padded,width),axis=1).astype(int)


def smooth(frames,volume_width=1,noise_width=1):
    volumes=np.array([f.volumes for f in frames]);noise=np.array([f.noise_period for f in frames])
    if volume_width>1:
        for voice in range(3):volumes[:,voice]=median(volumes[:,voice],volume_width)
    if noise_width>1:
        active=noise>0
        edges=np.flatnonzero(np.diff(np.r_[False,active,False]))
        for first,last in zip(edges[::2],edges[1::2]):noise[first:last]=median(noise[first:last],noise_width)
    return [video.AyFrame(f.periods,tuple(map(int,v)),int(n)) for f,v,n in zip(frames,volumes,noise)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--ay-50hz',type=Path,required=True)
    p.add_argument('--rate-report',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    experiment=json.loads(args.rate_report.read_text())
    raw=args.ay_50hz.read_bytes()
    if len(raw)%9:raise ValueError('partial AY frame')
    frames=[video.AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),9)]
    sample_rate=22050;metric_rate=25/3
    samples=video.decode_analysis_audio(args.ffmpeg,args.input_video,0,len(frames)/50,sample_rate,True)
    digest=hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest()
    if digest!=experiment['source_pcm_sha256']:raise ValueError('different reference PCM')
    reference=quality.features(samples,sample_rate,metric_rate,round(len(frames)/6))
    report=dict(source_pcm_sha256=digest,audio_sha256=hashlib.sha256(raw).hexdigest(),results=[])
    for volume_width,noise_width in ((1,1),(3,1),(5,1),(1,5),(3,5),(5,5)):
        candidate=smooth(frames,volume_width,noise_width)
        rendered=ay.render(candidate,50,sample_rate)
        metrics=quality.compare(reference,quality.features(rendered,sample_rate,metric_rate,len(reference[2])))
        label=f'volume{volume_width}_noise{noise_width}'
        (args.output/f'{label}.bin').write_bytes(b''.join(f.serialize() for f in candidate))
        quality.write_wav(args.output/f'{label}.wav',rendered,sample_rate)
        record=dict(volume_median_ticks=volume_width,noise_median_ticks=noise_width,metrics=metrics,
                    register_writes=sum(r[0] for r in ay_interrupt.encode_ticks(candidate)),
                    semantic_bytes=sum(map(len,ay_events.encode_ticks(candidate))))
        report['results'].append(record)
        (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(record),flush=True)


if __name__=='__main__':main()
