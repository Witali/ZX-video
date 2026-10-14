"""Build a shorter one-disk prefix from authenticated continuous preparation.

Reuse exact source RGB/PCM and the already fitted AY prefix after the resident
forest cap splits a longer candidate. Do not fit changed PCM with old cached
costs: the exported reference remains the same processed PCM prefix.
"""
from copy import deepcopy
from fractions import Fraction
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave
import numpy as np

HERE=Path(__file__).resolve().parent;TOOLKIT=HERE.parents[1];ROOT=TOOLKIT.parent
sys.path.insert(0,str(TOOLKIT))
import convert_video as converter
import build_long_video_trd as video
import ay_interrupt
import compare_ay_fidelity as quality


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prepared',type=Path);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--frames',type=int,default=507)
    for name in ('ffmpeg','ffprobe','node','zx0','lzsa','fuse','trdos-rom'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();old=args.prepared/'work';core=old/'ay-core'
    saved=json.loads((core/'analysis.json').read_bytes());state_bytes=saved['packed_state_bytes']
    raw=(core/'ay.bin').read_bytes();total=len(raw)//state_bytes
    if not 0<args.frames*5<=total:raise ValueError('invalid prefix extent')
    frames=[video.AyFrame.deserialize(raw[i:i+state_bytes]) for i in range(0,args.frames*5*state_bytes,state_bytes)]
    records=b''.join(ay_interrupt.registers(frame) for frame in frames)
    selected=args.output.parent/(args.output.name+'-source.mkv')
    if selected.exists():raise ValueError('selected source already exists')
    command=[args.ffmpeg,'-v','error','-nostdin','-f','rawvideo','-pixel_format','rgb24','-video_size','128x72',
        '-framerate','10','-i',str(old/'frames.rgb'),'-f','f32le','-ar','22050','-ac','1','-i',str(old/'audio-source.f32'),
        '-map','0:v:0','-map','1:a:0','-t',str(args.frames/10),'-frames:v',str(args.frames),
        '-c:v','ffv1','-pix_fmt','bgr0','-level','3','-c:a','flac',str(selected)]
    subprocess.run(command,check=True)
    # Prove video preparation is an exact RGB prefix before any native coding.
    decoded=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-i',str(selected),'-map','0:v:0',
        '-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True,check=True).stdout
    with (old/'frames.rgb').open('rb') as stream:expected=stream.read(args.frames*128*72*3)
    if decoded!=expected:raise ValueError('prefix source changes pixels')
    sys.path.insert(0,str(ROOT/'ay-converter'))
    import pcm_levels
    full_pcm=np.fromfile(old/'audio-source.f32','<f4').astype(float)
    prepared,normalization=pcm_levels.process(full_pcm,dynamics='compact')
    stored=json.loads((core/'pcm-level.json').read_bytes())
    assert normalization==stored
    reference=prepared[:args.frames*5*441]
    with wave.open(str(old/'audio-preview.wav'),'rb') as stream:
        assert stream.getframerate()==22050 and stream.getsampwidth()==2 and stream.getnchannels()==1
        model_bytes=stream.readframes(len(reference))
    model=np.frombuffer(model_bytes,'<i2').astype(float)/32768
    def reused_audio(source,ffmpeg,directory,picture,sound,count,fps,**options):
        assert count==args.frames and fps==Fraction(10)
        assert options.get('chip')=='AY-3-8910' and options.get('dynamics')=='compact'
        (directory/'ay.bin').write_bytes(b''.join(frame.serialize() for frame in frames))
        with wave.open(str(directory/'audio-preview.wav'),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(22050);stream.writeframes(model_bytes)
        quality.write_wav(directory/'processed-reference.wav',reference,22050)
        snapshot=directory/'continuous-audio-fit';shutil.copytree(core,snapshot)
        fit=deepcopy(saved)
        fit.update(exported_prefix_ticks=args.frames*5,continuous_analysis_ticks=total,
            scope='Exact leading controls from continuous original PCM fit; same processed reference and fixed output calibration. No recomputed partial-fit claim.')
        fit['noise_ticks']=sum(any(frame.volumes[c] and not frame.mixer&(1<<(c+3)) for c in range(3)) for frame in frames)
        return frames,dict(source_audio=True,ticks=args.frames*5,noise_ticks=fit['noise_ticks'],profile='auto',
            synthesis='Shared real-AY controls, exact continuous prefix reuse',chip_fit=fit,
            metrics=quality.compare(quality.features(reference,22050,10,args.frames),quality.features(model,22050,10,args.frames)),
            reuse=dict(continuous_fit_ticks=total,exported_ticks=args.frames*5,controls_sha256=hashlib.sha256(records).hexdigest(),
                reference_pcm_sha256=hashlib.sha256(reference.astype('<f8').tobytes()).hexdigest(),rgb_prefix_exact=True))
    converter.convert_audio=reused_audio
    argv=[str(selected),'--output',str(args.output),'--prefix','ZX-video-sea-foam','--video-codec','cb41',
        '--fps','10','--guarded-cb46','--ay-chip','AY-3-8910','--ay-dynamics','compact','--verify','fuse']
    for name in ('ffmpeg','ffprobe','node','zx0','lzsa','fuse','trdos-rom'):argv+=['--'+name,getattr(args,name.replace('-','_'))]
    converter.main(argv)
    plan=json.loads(args.plan.read_bytes())
    plan.update(source_interval_seconds=[0,args.frames/10],frames=args.frames,ay_ticks=args.frames*5,
        selected_input=str(selected.resolve()),selection_reason='First resident-forest-valid prefix from the longer three-part plan',
        source_clip_command=command,exact_prepared_rgb_prefix=True,continuous_audio_prefix_reused=True)
    (args.output/'selected-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
