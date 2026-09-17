"""Compare original audio with approximate AY synthesis driven by Fuse ticks.

Register states and every write are checked first. Tick-end timestamps place
the batches on the measured clock; writes within a batch are treated as
simultaneous. This is not captured PCM or cycle-exact AY/analogue emulation.
For multiple disks each volume is aligned separately to its original offset;
padding/cropping at disk ends is reported, never claimed as continuous play.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import ay_fidelity as ay
import build_long_video_trd as video
import compare_ay_fidelity as quality
import verify_ay_trace


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--timing',type=Path,required=True)
    p.add_argument('--ay-50hz',type=Path,required=True)
    p.add_argument('--rate-report',type=Path,required=True)
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    metadata=json.loads((args.build/'build_metadata.json').read_text())
    timing=json.loads(args.timing.read_text());raw=args.ay_50hz.read_bytes()
    verified=verify_ay_trace.verify_build(metadata,timing,raw)
    experiment=json.loads(args.rate_report.read_text())
    fps=metadata['frame_rate'];count=metadata['frames'];sample_rate=22050
    original=video.decode_analysis_audio(args.ffmpeg,args.input_video,0,count/fps,sample_rate,True,pad_end=experiment.get('pad_end',False))
    digest=hashlib.sha256(original.astype('<f8').tobytes()).hexdigest()
    if digest!=experiment['source_pcm_sha256']:raise ValueError('reference PCM differs from rate experiment')
    frames=[video.AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),9)]
    rendered=np.zeros(len(original));volumes=[]
    for volume,trace in zip(metadata['volumes'],timing):
        first,last=volume['frame_start']*6,volume['frame_end']*6
        ticks=np.array(trace['audio_ticks'],dtype=np.int64)
        interval=float(np.median(np.diff(ticks))) if len(ticks)>1 else trace['clock_hz']/50
        boundaries=np.rint(np.r_[ticks-ticks[0],ticks[-1]-ticks[0]+interval]*sample_rate/trace['clock_hz']).astype(np.int64)
        samples=ay.render(frames[first:last],50,sample_rate,sample_boundaries=boundaries,clock_hz=trace['clock_hz']/2)
        start,end=round(first*sample_rate/50),round(last*sample_rate/50)
        copied=min(end-start,len(samples));rendered[start:start+copied]=samples[:copied]
        volumes.append(dict(frame_start=volume['frame_start'],measured_audio_seconds=len(samples)/sample_rate,
                            nominal_seconds=(last-first)/50,end_padding_ms=(end-start-len(samples))*1000/sample_rate,
                            synthesis_clock_hz=trace['clock_hz']/2))
    reference=quality.features(original,sample_rate,fps,count)
    metrics=quality.compare(reference,quality.features(rendered,sample_rate,fps,count))
    args.output.mkdir(parents=True,exist_ok=True)
    quality.write_wav(args.output/'measured_timing.wav',rendered,sample_rate)
    # Equal-RMS listening excerpts at the same offset used by the earlier report.
    lo,hi=60*sample_rate,84*sample_rate
    excerpts={'original':original[lo:hi],'measured_timing':rendered[lo:hi]}
    rms={name:float(np.sqrt(np.mean(samples*samples))) for name,samples in excerpts.items()}
    level=min(.1,*(.9*rms[name]/max(float(np.max(np.abs(samples))),1e-12) for name,samples in excerpts.items()))
    for name,samples in excerpts.items():quality.write_wav(args.output/f'{name}_excerpt.wav',samples*level/max(rms[name],1e-12),sample_rate)
    report=dict(source_pcm_sha256=digest,metrics=metrics,verified_audio=verified,volumes=volumes,
        model=__doc__,metric_rate_hz=fps,onset_tolerance_seconds=1/fps,
        required_metrics_pass=metrics['chroma_cosine']>=.95 and metrics['loudness_correlation']>=.95,
        rhythm_required=False,continuous_single_disk=len(volumes)==1)
    (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
