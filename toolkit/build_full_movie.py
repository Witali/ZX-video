"""Build the complete source through EOF, with 50 Hz AY and numbered TRDs.

Stage outputs and hashes are recorded in manifest.json. --stage permits
restarting a failed stage; earlier stage files must match their saved hashes.
The final interval is extended by less than one video frame, never truncated.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import numpy as np

import build_long_video_trd as video
from retune_ay_build import replace_ay_states

HERE=Path(__file__).resolve().parent


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def full_duration(probe,fps=Fraction(25,3)):
    durations=[Fraction(s['duration']) for s in probe['streams']
               if s['codec_type'] in ('audio','video') and s.get('duration') not in (None,'N/A')]
    if not durations:
        durations=[Fraction(probe['format']['duration'])]
    source_duration=max(durations)
    frames=math.ceil(source_duration*fps)
    return source_duration,frames,Fraction(frames,1)/fps


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',type=Path,required=True)
    p.add_argument('--ffprobe',type=Path,required=True)
    p.add_argument('--zx0',type=Path,required=True)
    p.add_argument('--stage',choices=('all','audio','video','disks'),default='all')
    p.add_argument('--resume-video',action='store_true',help='reuse a hashed conversion checkpoint and repeat verification')
    p.add_argument('--store-over-bytes',type=int,default=0)
    p.add_argument('--separate-stored',action='store_true')
    p.add_argument('--max-volume-frames',type=int,default=0)
    p.add_argument('--minimum-planned-queue',type=int,default=0)
    p.add_argument('--compression-cache',type=Path)
    p.add_argument('--zx0-minimum-match',type=int,default=0,choices=(0,2,3,4,5,6,8,12,16))
    p.add_argument('--zx0-speed-over-bytes',type=int,default=0)
    p.add_argument('--volume-end-frame',type=int,action='append',default=[])
    p.add_argument('--store-frame',type=int,action='append',default=[])
    args=p.parse_args()
    src=args.input_video.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    ffmpeg=args.ffmpeg.resolve();os.environ['PATH']=str(ffmpeg.parent)+os.pathsep+os.environ['PATH']
    probe=json.loads(subprocess.check_output([str(args.ffprobe.resolve()),'-v','error',
        '-show_entries','format=duration:stream=codec_type,duration','-of','json',str(src)]))
    source_seconds,count,duration=full_duration(probe)
    settings=dict(source=str(src),source_sha256=digest(src),source_duration_seconds=float(source_seconds),
        frame_rate=25/3,frames=count,audio_rate_hz=50,audio_ticks=count*6,
        encoded_duration_seconds=float(duration),tail_extension_seconds=float(duration-source_seconds),
        fixed_center_zoom=1.25,dither='ordered4',feedback_sector_budget=6,feedback_max_error_ratio=1.25,
        block_bytes=6144,full_source=True)
    manifest_path=out/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(settings=settings,stages={})
    if manifest['settings']!=settings:raise ValueError('output belongs to a different source/settings')
    def save():manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    save();print(json.dumps(settings),flush=True)
    def run(name,arguments):
        print(f'Starting {name}; log: {out/(name+".log")}',flush=True)
        with (out/(name+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,*map(str,arguments)],stdout=log,stderr=subprocess.STDOUT,check=True)
    def record(name,paths):
        manifest['stages'][name]={str(path.relative_to(out)):digest(path) for path in paths};save()
        print(f'Completed {name}',flush=True)
    def require(name):
        files=manifest['stages'].get(name)
        if not files or any(not (out/path).is_file() or digest(out/path)!=sha for path,sha in files.items()):
            raise ValueError(f'{name} stage missing or changed')
    sound=out/'audio';source=out/'source';disks=out/'disks'
    if args.stage in ('all','audio'):
        run('audio',[HERE/'benchmark_ay_rate.py','--input-video',src,'--output',sound,
            '--ffmpeg',ffmpeg,'--duration',float(duration),'--rates','50','--pad-end'])
        record('audio',[sound/'50Hz/raw.bin',sound/'comparison.json'])
    if args.stage in ('all','video'):
        require('audio');source.mkdir(exist_ok=True)
        raw=(sound/'50Hz/raw.bin').read_bytes()
        if len(raw)!=count*6*9:raise ValueError('audio count differs from full duration')
        frames=[video.AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),54)]
        checkpoint=source/'conversion.npz'
        if args.resume_video:
            require('video_candidate')
            with np.load(checkpoint) as saved:
                stream=saved['stream'].tobytes()
                states=[state.tobytes() for state in saved['states']]
                stats=json.loads(str(saved['stats']));reframe=json.loads(str(saved['reframe']))
        else:
            windows,reframe=video.build_fixed_center_reframe(float(duration),25/3,1.25)
            tones=video.analyse_tone_ranges(src,0,float(duration),25/3,3,97,4,windows,pad_end=True)
            stream,packets,states,stats=video.build_video(src,0,float(duration),25/3,25/3,
                tones,frames,windows,100_000,'ordered4',True,6,1.25,source/'preview.mp4',pad_end=True)
            np.savez(checkpoint,stream=np.frombuffer(stream,dtype=np.uint8),
                states=np.frombuffer(b''.join(states),dtype=np.uint8).reshape(count,video.STATE_BYTES),
                stats=json.dumps(stats),reframe=json.dumps(reframe))
            record('video_candidate',[checkpoint,source/'preview.mp4'])
        video.verify_video(stream,states)
        if len(states)!=count:raise ValueError('full source frame count mismatch')
        stream=replace_ay_states(stream,frames)
        (source/'VIDEO_full.C.bin').write_bytes(stream)
        video.write_contact_sheet(source/'contact_sheet.png',states)
        video.write_contact_sheet(source/'ending_contact_sheet.png',states[-min(len(states),250):])
        metadata=dict(source=settings,stats=stats,fixed_center_crop=reframe,
            logical_states_sha256=hashlib.sha256(b''.join(states)).hexdigest(),
            last_state_sha256=hashlib.sha256(states[-1]).hexdigest(),
            ay=dict(update_rate_hz=50,source=str(sound/'50Hz/raw.bin'),sha256=digest(sound/'50Hz/raw.bin')))
        (source/'build_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
        record('video',[source/'VIDEO_full.C.bin',source/'build_metadata.json'])
    if args.stage in ('all','disks'):
        require('audio');require('video')
        manifest['disk_settings']=dict(store_over_bytes=args.store_over_bytes,max_volume_frames=args.max_volume_frames,
            minimum_planned_queue=args.minimum_planned_queue,separate_stored=args.separate_stored,
            minimum_match=args.zx0_minimum_match,speed_over_frame_bytes=args.zx0_speed_over_bytes,
            volume_end_frames=sorted(set(args.volume_end_frame)),stored_frames=sorted(set(args.store_frame)))
        save()
        run('disks',[HERE/'build_fast_sparse_trd.py','--source-build',source,'--output',disks,
            '--name-prefix','ZX-video-full-50Hz','--ay-50hz',sound/'50Hz/raw.bin',
            '--packing','zx0','--zx0',args.zx0.resolve(),'--drawing','registers',
            '--disk-reader','trdos503-irq','--disk-layout','interleaved','--pacing','deadline',
            '--zx0-decoding','incremental','--motor-keepalive-fields','64','--prefetch-quota','3',
            '--rom-clock','full','--disk-seek','cached','--packet-lookahead','--uncontended',
            '--read-reserve','64','--memory-clock','--direct-input','--wrapped-input','--block-bytes','6144',
            '--store-over-bytes',args.store_over_bytes,'--max-volume-frames',args.max_volume_frames,
            '--minimum-planned-queue',args.minimum_planned_queue,
            '--zx0-minimum-match',args.zx0_minimum_match,'--zx0-speed-over-bytes',args.zx0_speed_over_bytes,
            *[argument for end in args.volume_end_frame for argument in ('--volume-end-frame',end)],
            *[argument for frame in args.store_frame for argument in ('--store-frame',frame)],
            *(['--separate-stored'] if args.separate_stored else []),
            *(['--compression-cache',args.compression_cache.resolve()] if args.compression_cache else [])])
        meta=json.loads((disks/'build_metadata.json').read_text())
        if meta['frames']!=count:raise ValueError('disk set does not cover the source')
        record('disks',[disks/'build_metadata.json',disks/'PLAYER.C.bin',
                        *(disks/v['trd_name'] for v in meta['volumes'])])
        print(f'Complete source: {count} frames, {count*6} audio ticks, {len(meta["volumes"])} disks',flush=True)


if __name__=='__main__':main()
