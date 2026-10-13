"""Select a conservative one-disk prefix using the existing video codec.

Analyse at most 120 source seconds, charge each 32-frame local book, then
perform actual capacity and complete playback checks on the selected prefix.
An estimate is never a release qualification or a maximum-duration proof.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;TOOLKIT=HERE.parents[1];sys.path.insert(0,str(TOOLKIT))
from convert_video import probe_media,decode_video,convert_frames,write_json
from generic_cell_codebook import prepare_frames
from guarded_cb46 import representation
from convert_cb41 import pack_blocks,VIDEO_BUDGET
from probe_adaptive_block_codecs import ExternalCodec


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--ffmpeg',required=True);parser.add_argument('--ffprobe',required=True)
    parser.add_argument('--lzsa',type=Path,required=True);parser.add_argument('--seconds',type=int,default=120)
    args=parser.parse_args();out=args.output
    if out.exists() and any(out.iterdir()):raise ValueError('output must be empty')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    # FFV1/FLAC retains the downloaded picture and decoded audio without a
    # second lossy codec. The user authorizes a beginning-of-source excerpt.
    prefix=out/'analysis-prefix.mkv'
    clip=[args.ffmpeg,'-v','error','-nostdin','-i',str(args.source),'-t',str(args.seconds),
        '-map','0:v:0','-map','0:a:0','-c:v','ffv1','-level','3','-c:a','flac',str(prefix)]
    subprocess.run(clip,check=True)
    probe,picture,sound=probe_media(prefix,args.ffprobe)
    images,decoded=decode_video(prefix,args.ffmpeg,out,probe,picture,sound,Fraction(10))
    compact,_=convert_frames(images,out);frames,quality=prepare_frames(images,compact,out)
    cache=out/'lzsa';cache.mkdir()
    codec=ExternalCodec('lzsa2',args.lzsa,args.lzsa,'explicit executable; exact source hash recorded')
    amount=0.;selected=0;windows=[]
    for lo in range(0,len(frames),32):
        hi=min(lo+32,len(frames));encoded=representation(frames,lo,hi)
        packed,_=pack_blocks(encoded['raw'],codec,cache);cost=len(packed)/(hi-lo)
        available=max(0,int((VIDEO_BUDGET-amount)//max(cost,1)))
        accepted=min(hi-lo,available)
        windows.append(dict(start_frame=lo,end_frame=hi,bytes=len(packed),per_frame_estimate=cost,
            selected_frames=accepted))
        print(json.dumps(dict(stage='one_disk_window',lo=lo,hi=hi,bytes=len(packed),selected=accepted)),flush=True)
        selected+=accepted;amount+=cost*accepted
        if accepted<hi-lo:break
    if selected<2:raise ValueError('no usable independently bootable video prefix')
    seconds=selected/10;target=out/'selected-prefix.mkv'
    command=clip.copy();command[command.index('-t')+1]=str(seconds);command[-1]=str(target)
    subprocess.run(command,check=True)
    with args.source.open('rb') as stream:source_sha=hashlib.file_digest(stream,'sha256').hexdigest()
    write_json(out/'plan.json',dict(complete=True,release=False,date='2026-10-13',source=str(args.source.resolve()),
        source_sha256=source_sha,source_interval_seconds=[0,seconds],analysis_seconds=args.seconds,
        frames=selected,ay_ticks=selected*5,fps=10,video_budget_bytes=VIDEO_BUDGET,
        estimated_video_bytes=amount,windows=windows,clip_command=command,decoded=decoded,
        quality=quality,selected_input=str(target.resolve()),elapsed_seconds=time.perf_counter()-started,
        limitations='Conservative window estimate only. Audio/RAM/actual disk capacity and all native/Fuse fields/screens still need full qualification. No maximum-duration claim.'))
    print(json.dumps(dict(complete=True,frames=selected,seconds=seconds,selected_input=str(target))),flush=True)


if __name__=='__main__':main()
