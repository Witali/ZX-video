"""Compare AY update rates against one fixed, independent audio metric grid.

This is an offline experiment, not a disk/player format. Keeping evaluation
at 25/3 Hz prevents a rate change from silently changing the acceptance test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np

import ay_fidelity as ay
import build_long_video_trd as video
import compare_ay_fidelity as quality


def delta_states(states):
    """Lossless byte-change mask followed by changed register-state bytes."""
    previous=bytes(9);result=bytearray()
    for state in states:
        mask=sum(1<<i for i,(old,new) in enumerate(zip(previous,state)) if old!=new)
        result+=mask.to_bytes(2,'little')
        result+=bytes(new for i,new in enumerate(state) if mask & (1<<i))
        previous=state
    return bytes(result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--zx0',type=Path)
    p.add_argument('--delta-only',action='store_true',help='compress only byte deltas; faster for large high-rate trials')
    p.add_argument('--duration',type=float,default=120)
    p.add_argument('--pad-end',action='store_true',help='pad final partial video interval with silence')
    p.add_argument('--rates',type=video.parse_rate,nargs='+',default=[25/3,25,50])
    args=p.parse_args()
    if not args.ffmpeg:p.error('ffmpeg is required')
    args.output.mkdir(parents=True,exist_ok=True)
    sample_rate=22050;metric_rate=25/3
    samples=video.decode_analysis_audio(args.ffmpeg,args.input_video,0,args.duration,sample_rate,True,pad_end=args.pad_end)
    reference=quality.features(samples,sample_rate,metric_rate,round(args.duration*metric_rate))
    report=dict(scope='offline synthesis only; no claim of playback compatibility',
                metric_rate_hz=metric_rate,onset_tolerance_seconds=1/metric_rate,
                source_pcm_sha256=hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest(),
                duration_seconds=args.duration,pad_end=args.pad_end,rates=[])
    for rate in args.rates:
        count=round(args.duration*rate)
        magnitude,rms=ay.spectra(samples,sample_rate,rate,count)
        amplitude,explained=ay.decompose(magnitude,sample_rate)
        periods,volumes,notes=ay.arrange(amplitude,rms,explained)
        noise,volumes,_=ay.arrange_noise(magnitude,rms,explained,volumes,sample_rate)
        # Canonicalise irrelevant tone registers exactly as the released encoder.
        previous=1
        for i in range(count):
            if noise[i]:periods[i,1]=previous
            else:previous=periods[i,1]
        frames=[video.AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n))
                for p,v,n in zip(periods,volumes,noise)]
        rendered=ay.render(frames,rate,sample_rate)
        metrics=quality.compare(reference,quality.features(rendered,sample_rate,metric_rate,len(reference[2])))
        directory=args.output/f'{rate:g}Hz';directory.mkdir(exist_ok=True)
        raw=b''.join(frame.serialize() for frame in frames)
        delta=delta_states([frame.serialize() for frame in frames])
        sizes={}
        for name,data in (('raw',raw),('delta',delta)):
            path=directory/f'{name}.bin';path.write_bytes(data)
            sizes[name]=len(data)
            if args.zx0 and not (args.delta_only and name=='raw'):
                packed=path.with_suffix('.zx0')
                subprocess.run([str(args.zx0.resolve()),'-f',str(path.resolve()),str(packed.resolve())],check=True,capture_output=True)
                sizes[name+'_zx0']=packed.stat().st_size
        quality.write_wav(directory/'preview.wav',rendered,sample_rate)
        np.savez(directory/'analysis.npz',amplitude=amplitude,explained=explained,
                 rms=rms,periods=periods,volumes=volumes,noise=noise,notes=notes)
        record=dict(update_rate_hz=rate,states=count,noise_states=int(np.count_nonzero(noise)),
                    sizes=sizes,metrics=metrics)
        report['rates'].append(record)
        (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(record),flush=True)


if __name__=='__main__':main()
