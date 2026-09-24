"""Re-encode changed compact frames with existing FAP3 motion/table choices.

Keeps all AY bytes, raw-attribute decisions and existing fast fragments.
Recomputes causal corrections against the actual new previous/current frame.
An unavailable Huffman symbol escapes to an existing whole-tile literal.
An exact baseline replay must reproduce the input file before comparison.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from bulk_frame_stream import read_packet, unpack, WINDOW
import cell_audio_stream
import frame_packet_stream
from probe_cell_output_masks import masks
from probe_fast_fragments import pack_fragment
from probe_fine_motion import shifted_candidates
from probe_hybrid_tiles import OFFSETS, Writer
from probe_lossless_layouts import sha
from probe_bounded_fragments import write_report
from probe_motion_entropy import codes_for, Reader
from probe_motion_metadata import transform
from probe_motion_residual_order import field_order
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
import raw_attribute_stream


def encode(source,states,*,new_simple=False):
    r=Reader(source); _,_,count,mapping,tables=read_header(r,magic=b'FAP3')
    if states.shape!=(count,3840):raise ValueError('different frame count')
    out=bytearray(source[:r.pos]);order=field_order(8).reshape(192,20)[:,:16]
    codes=[codes_for(255,t) for t in tables]
    native=masks(states)[0].reshape(count,80)
    previous=np.zeros(3840,np.uint8);stats=Counter();rows=[]
    for index,current in enumerate(states):
        _,detail=read_packet(r,stored_guards=False)
        ay=b''.join(detail['ticks']);base=len(ay)+8
        vv=np.frombuffer(detail['payload'][base:base+192],np.uint8).copy()
        old_native=np.frombuffer(detail['payload'][base+192+detail['mask_bytes']:detail['coded_offset']],np.uint8)
        preds=shifted_candidates(previous[:3072],OFFSETS)
        spatial=[];picture=current[:3072].reshape(96,32)
        for vector in (82,83,84):
            image=np.zeros_like(picture)
            if vector==83:image[:,1:]=picture[:,:-1]
            else:
                dy=1 if vector==82 else 2;image[dy:]=picture[:-dy]
            spatial.append(image.reshape(3072))
        writer=Writer();literal=bytearray();active=np.zeros((192,16),bool)
        escaped=converted=0
        for tile,addresses in enumerate(order):
            values=current[addresses];v=int(vv[tile]);kind,payload=pack_fragment(values)
            if v<85:
                prediction=(preds[v] if v<=81 else spatial[v-82])[addresses]
                changes=np.flatnonzero(values!=prediction)
                lengths=[tables[mapping[int(prediction[f])]][int(values[f])] for f in changes]
                missing=any(n==0 for n in lengths)
                cheap_simple=(new_simple and kind!=85 and len(payload)*8<=sum(lengths)+8*np.count_nonzero(
                    (values!=prediction).reshape(2,8).any(axis=1)))
                if missing or cheap_simple:
                    v=kind;escaped+=missing;converted+=cheap_simple and not missing
                else:
                    active[tile,changes]=True
                    for f in changes:writer.put(*codes[mapping[int(prediction[f])]][int(values[f])])
            if v>=85:
                v=kind;literal+=payload
            vv[tile]=v;stats[str(v)]+=1
        delta=current[3072:]^previous[3072:]
        raw=bool(detail['flags']&64)
        if raw:at=bytes(96);literal+=current[3072:].tobytes()
        else:
            at=np.packbits(delta!=0).tobytes()
            for field in np.flatnonzero(delta):writer.put(*codes[-1][int(delta[field])])
        mm=transform(np.packbits(active.reshape(-1)).tobytes()+at,480,4)
        encoded=writer.finish();motion=bool(np.any((vv>0)&(vv<81)))
        flags=(128*motion)|(64*raw)|(writer.bits&7)
        cache=detail['cache'] if motion else bytes(3)
        # Keep harmless old overdraw and add any newly required cell updates.
        output_map=(old_native|native[index]).tobytes()
        body=ay+struct.pack('<BHH',flags,len(mm),len(encoded))+cache+vv.tobytes()+mm+output_map+encoded+literal
        if len(body)>=WINDOW:raise ValueError(f'frame {index} exceeds input window')
        out+=struct.pack('<H',len(body))+body
        rows.append(dict(index=index,payload_bytes=len(body),missing_symbol_escapes=escaped,simple_substitutions=converted))
        previous=current
        if index%500==0:print(f'Re-encode FAP3: {index}/{count}',flush=True)
    r.end()
    return bytes(out),dict(frames=count,modes=dict(stats),packets=rows)


def validate(data,states):
    av=unpack_cache(frame_packet_stream.unpack(unpack(data)),32,4)
    video,ay,_=cell_audio_stream.unpack(av)
    if raw_attribute_stream.decode(video)!=states.tobytes():raise AssertionError('causal frame decode differs')
    return ay


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','baseline','candidate','output','report'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();source=args.source.read_bytes()
    with np.load(args.baseline,allow_pickle=False) as z:baseline=z['states']
    with np.load(args.candidate,allow_pickle=False) as z:candidate=z['states']
    control,_=encode(source,baseline)
    if control!=source:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        (args.output.parent/'control.raw').write_bytes(control)
        raise AssertionError('baseline re-encode is not byte-identical')
    result,detail=encode(source,candidate,new_simple=True)
    if validate(source,baseline)!=validate(result,candidate):raise AssertionError('AY changed')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(result)
    report=dict(complete=True,release=False,baseline_sha256=sha(source),candidate_sha256=sha(result),
        raw_bytes=len(result),raw_delta=len(result)-len(source),exact_baseline_reencode=True,
        independent_causal_replay=True,exact_ay_records=True,**detail)
    write_report(args.report,report,'packets')
    print(json.dumps({k:v for k,v in report.items() if k!='packets'}),flush=True)


if __name__=='__main__':main()
