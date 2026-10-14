"""Build a true-native source prefix with the same authenticated50-Hz AY fit."""
import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'toolkit'))
import convert_video as converter
import convert_cb41
import build_long_video_trd as video
import ay_interrupt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('prepared',type=Path);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--frames',type=int,default=300)
    p.add_argument('--image-cache',type=Path)
    for name in ('ffmpeg','ffprobe','node','zx0','lzsa','fuse','trdos-rom'):p.add_argument('--'+name,required=True)
    args=p.parse_args();old=args.prepared/'work';core=old/'ay-core'
    if args.output.exists():raise ValueError('output must be new')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    duration=args.frames/10;selected=args.output.parent/(args.output.name+'-source.mkv')
    if selected.exists():raise ValueError('selected clip must be new')
    filters="setpts=PTS-STARTPTS,fps=10:start_time=0:round=up:eof_action=pass,scale=w='max(1,round(min(256,144*dar)))':h='max(1,round(min(144,256/dar)))':flags=area,setsar=1,pad=256:144:(ow-iw)/2:(oh-ih)/2:black"
    native_source=subprocess.check_output([args.ffmpeg,'-v','error','-nostdin','-i',str(args.source),'-map','0:v:0',
        '-an','-vf',filters,'-frames:v',str(args.frames),'-pix_fmt','rgb24','-f','rawvideo','-'])
    rgb_input=args.output.parent/(args.output.name+'-native-source.rgb');rgb_input.write_bytes(native_source)
    # Materialize already-decoded RGB rather than take a second YUV->BGR
    # conversion path: those paths can round differently even in FFV1.
    command=[args.ffmpeg,'-v','error','-nostdin','-f','rawvideo','-pixel_format','rgb24','-video_size','256x144',
        '-framerate','10','-i',str(rgb_input),'-f','f32le','-ar','22050','-ac','1',
        '-i',str(old/'audio-source.f32'),'-map','0:v:0','-map','1:a:0',
        '-t',str(duration),'-frames:v',str(args.frames),'-c:v','ffv1','-pix_fmt','bgr0','-level','3','-c:a','flac',str(selected)]
    subprocess.run(command,check=True)
    decoded=subprocess.check_output([args.ffmpeg,'-v','error','-nostdin','-i',str(selected),'-map','0:v:0','-an',
        '-pix_fmt','rgb24','-f','rawvideo','-'])
    assert decoded == native_source and len(decoded) == args.frames*256*144*3
    original_decode=converter.decode_video
    def exact_source(*values,**options):
        assert options.get('native_pixels')
        images,report=original_decode(*values,**options)
        assert images.tobytes() == native_source
        report.update(original_source_native_prefix_exact=True,original_source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest())
        return images,report
    converter.decode_video=exact_source
    if args.image_cache:
        import native_video
        import native_lineart
        cached_rgb=np.fromfile(args.image_cache/'work/frames.rgb',np.uint8).reshape(-1,144,256,3)
        cached_states=np.load(args.image_cache/'work/native-states.npy')
        cached_quality=json.loads((args.image_cache/'video-quality.json').read_bytes())
        assert cached_quality['parameters']==native_lineart.PARAMETERS and cached_quality['dark_fills']
        def cached(images,directory,*,dark_fills=True):
            assert dark_fills and len(images)==args.frames==len(cached_states)
            np.testing.assert_array_equal(images,cached_rgb)
            np.save(directory/'native-states.npy',cached_states)
            print(f'Reused exact source-native preparation: {len(images)} frames',flush=True)
            return cached_states,cached_quality
        native_video.prepare_frames=cached
    saved=json.loads((core/'analysis.json').read_bytes());size=saved['packed_state_bytes'];raw=(core/'ay.bin').read_bytes()
    audio=[video.AyFrame.deserialize(raw[i:i+size]) for i in range(0,args.frames*5*size,size)]
    assert len(audio) == args.frames*5
    with wave.open(str(old/'audio-preview.wav'),'rb') as source_wav:
        assert (source_wav.getnchannels(),source_wav.getsampwidth(),source_wav.getframerate()) == (1,2,22050)
        model_bytes=source_wav.readframes(args.frames*5*441)
    def reused_audio(source,ffmpeg,directory,picture,sound,count,fps,**options):
        assert count==args.frames and fps==Fraction(10) and options.get('chip')=='AY-3-8910'
        assert options.get('dynamics')=='compact'
        (directory/'ay.bin').write_bytes(b''.join(f.serialize() for f in audio))
        with wave.open(str(directory/'audio-preview.wav'),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(22050);stream.writeframes(model_bytes)
        report=deepcopy(saved);report.update(exported_prefix_ticks=len(audio),continuous_analysis_ticks=len(raw)//size)
        return audio,dict(source_audio=True,ticks=len(audio),chip='AY-3-8910',continuous_audio_prefix_exact=True,
            controls_sha256=hashlib.sha256(b''.join(ay_interrupt.registers(f) for f in audio)).hexdigest(),chip_fit=report,
            scope='Exact prefix of the original continuous fit and unchanged chip-model WAV; no audio refit.')
    converter.convert_audio=reused_audio
    original_plan=convert_cb41.plan_volumes
    def single(*values,**options):
        bound=inspect.signature(original_plan).bind(*values,**options)
        bound.arguments['volume_cuts']=[args.frames];bound.arguments['target_volumes']=None
        return original_plan(*bound.args,**bound.kwargs)
    convert_cb41.plan_volumes=single
    argv=[str(selected),'--output',str(args.output),'--prefix','ZX-video-sea-foam-native-lineart',
        '--video-codec','cb47','--fps','10','--colour-policy','lineart','--lineart-dark-fills',
        '--ay-chip','AY-3-8910','--ay-dynamics','compact','--verify','fuse','--verification-timeout','120']
    for name in ('ffmpeg','ffprobe','node','zx0','lzsa','fuse','trdos-rom'):argv += ['--'+name,getattr(args,name.replace('-','_'))]
    converter.main(argv)
    source_report=dict(date='2026-10-14',source=str(args.source.resolve()),source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
        source_interval_seconds=[0,duration],native_rgb_prefix_sha256=hashlib.sha256(native_source).hexdigest(),
        native_rgb_prefix_exact=True,active_resolution=[256,144],fps=10,source_clip_command=command,
        continuous_original_ay_prefix_exact=True,model_wav_prefix_exact=True,frames=args.frames,ay_ticks=args.frames*5)
    (args.output/'source.json').write_text(json.dumps(source_report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
