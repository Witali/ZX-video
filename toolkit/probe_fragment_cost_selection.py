"""Lossless fragment selection on a measured volume, with actual optimal ZX0.

The selector estimates a conservative portion of removed CPU work; it is
not a cycle-accurate player or release check. Pixel states, AY, native maps,
Huffman tables and player opcodes stay unchanged. Validate the entire movie
independently, and measure only the declared volume with cold bitmap maps.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np

from build_fap3_trd import sha
from causal_tile_z80 import motion_tstates,intra_tstates,fast_tstates
from probe_hybrid_tiles import OFFSETS
from reencode_bounded_fragments import encode,validate
from run_deferred_disk import ReadThroughBuilder


class Selector:
    def __init__(self,start,end,allowance,min_gain):
        self.start,self.end,self.allowance,self.min_gain=start,end,allowance,min_gain
        self.rows=[]

    def __call__(self,index,tile,vector,kind,payload,values,prediction,lengths):
        if not self.start<=index<self.end:return False
        changes=values!=prediction
        mask_bytes=int(np.count_nonzero(changes.reshape(2,8).any(axis=1)))
        extra=8*len(payload)-sum(lengths)-8*mask_bytes
        # 150 is below the current short bitmap primitive's minimum, and
        # long codes cost more. Omit all temporal patch/control costs here.
        old=150*len(lengths)
        if 1<=vector<=81:old+=motion_tstates(vector,OFFSETS,unrolled=True)
        elif vector>=82:old+=intra_tstates(vector,tile,len(lengths),extended=True)
        new=fast_tstates(kind,selector=payload[4] if kind==87 else 0,
                         split_literals=True,register_fragments=True)
        gain=old-new
        if extra>self.allowance or gain<self.min_gain:return False
        self.rows.append(dict(frame=index,tile=tile,old_mode=vector,new_mode=kind,
            heuristic_extra_bits=int(extra),heuristic_saved_tstates=int(gain)))
        return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('raw','states','metadata','zx0','output','report'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--allowances',type=int,nargs='+',default=[0,16,64])
    p.add_argument('--min-gain',type=int,default=400)
    args=p.parse_args();source=args.raw.read_bytes();meta=json.loads(args.metadata.read_bytes())
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if sha(source)!=meta['raw_sha256']:raise ValueError('wrong volume stream')
    start,end=meta['frame_start'],meta['frame_end_exclusive']
    args.output.mkdir(parents=True,exist_ok=True);args.report.parent.mkdir(parents=True,exist_ok=True)
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='94c2e6f',
        source_sha256=sha(source),states_sha256=sha(states.tobytes()),part=meta['part'],
        start=start,end=end,whole_movie_frames=len(states),tested_volume_frames=end-start,
        minimum_heuristic_saved_tstates=args.min_gain,player_opcodes_changed=False,
        actual_cpu_tstates_measured=False,full_player_verified=False,variants=[])
    def save():args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    memo={}
    def measure(data):
        builder=ReadThroughBuilder(data,states,args.zx0.resolve(),args.output/'zx0',cold_bitmaps=True)
        builder.read_cache=args.read_cache;builder.memo=memo
        stream,blocks=builder.stream(start,end)
        return dict(raw_bytes=len(data),sha256=sha(data),stream_bytes=len(stream),
            stream_sha256=sha(stream),blocks=len(blocks),sectors=(len(stream)+255)//256,
            all_zx0_blocks_exact=True)
    try:
        control,_=encode(source,states)
        if control!=source:raise AssertionError('baseline replay differs')
        result['baseline_reencode_byte_identical']=True
        original_audio=validate(source,states)
        result['baseline']=measure(source)
        if result['baseline']['stream_bytes']!=meta['video_bytes']:raise AssertionError('baseline cold stream size differs')
        save()
        for allowance in args.allowances:
            print(f'Select fragments: allowance {allowance} bits, volume {start}..{end}',flush=True)
            selector=Selector(start,end,allowance,args.min_gain)
            candidate,detail=encode(source,states,fragment_selector=selector)
            if validate(candidate,states)!=original_audio:raise AssertionError('AY differs')
            path=args.output/f'allowance-{allowance}.raw';path.write_bytes(candidate)
            row=dict(allowance_bits=allowance,raw_file=path.name,selected_tiles=len(selector.rows),
                selected_frames=len({r['frame'] for r in selector.rows}),
                modes=dict(Counter(r['new_mode'] for r in selector.rows)),
                heuristic_saved_tstates=sum(r['heuristic_saved_tstates'] for r in selector.rows),
                whole_movie_scalar_video_ay_exact=True,**measure(candidate))
            row['stream_delta_bytes']=row['stream_bytes']-result['baseline']['stream_bytes']
            row['sector_delta']=row['sectors']-result['baseline']['sectors']
            result['variants'].append(row);save();print(json.dumps(row),flush=True)
        result['complete']=True
    except Exception as exc:result['failure']=repr(exc);save();raise
    save()


if __name__=='__main__':main()
