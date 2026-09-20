"""Repack integer contours without retracing, then reselect exact hybrid modes.

Direction/run bytes encode orthogonal edges; short dx/dy share a byte for
general polygons. All frames/attributes/AY roundtrip. No Z80 speed claim.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np
import integer_contours as codec
from cell_audio_stream import take_tick
from probe_integer_contours import levels
from probe_lossless_layouts import sha,measure


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('states','source-report','cache','output'): p.add_argument('--'+k,type=Path,required=True)
    args=p.parse_args(); source=json.loads(args.source_report.read_text())
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    if not source['complete'] or source['states_sha256']!=sha(states.tobytes()): raise ValueError('source mismatch')
    inputs={}
    for name in ('grid','polygon'):
        blob=(args.cache/(name+'.raw')).read_bytes()
        if sha(blob)!=source['streams'][name]['sha256']: raise ValueError('wrong saved stream')
        r=codec.Reader(blob); header=r.take(10); inputs[name]=r
    streams={name:bytearray(header) for name in ('compact_grid','compact_polygon','compact_hybrid')}
    previous=[np.zeros((72,128),dtype=np.uint8) for _ in range(2)]
    attrs_previous=[np.ones(576,dtype=np.uint8) for _ in range(2)]
    rows=[]
    for i,state in enumerate(states):
        value=levels(state); variants={}; common=None; ay_ticks=None
        for name,r in inputs.items():
            br=codec.Reader(r.take(struct.unpack('<I',r.take(4))[0]))
            ticks=[take_tick(br) for _ in range(6)]; attrs=codec.read_attributes(br,attrs_previous[i%2])
            prefix=br.data[:br.pos]
            if common is not None and (prefix!=common or ticks!=ay_ticks): raise AssertionError('common records differ')
            common=prefix; ay_ticks=ticks
            if not np.array_equal(attrs,state[3168:3744]): raise AssertionError('attributes differ')
            original=br.take(len(br.data)-br.pos)
            variants['compact_'+name]=codec.compact_contours(original,grid=name=='grid')
        candidates=list(variants.items())+[
            ('rectangles',codec.rectangle_packet(value,previous[i%2])[0]),('raster',codec.packed_packet(value))]
        choice,hybrid=min(candidates,key=lambda item:len(item[1]))
        for name,data in [*variants.items(),('compact_hybrid',hybrid)]:
            decoded=codec.decode_pixels(data,previous[i%2])
            if not np.array_equal(decoded,value): raise AssertionError(('compact contours differ',i,name))
            body=common+data; streams[name]+=struct.pack('<I',len(body))+body
        rows.append(dict(index=i,mode=choice,pixel_bytes=len(hybrid),
            grid_bytes=len(variants['compact_grid']),polygon_bytes=len(variants['compact_polygon']),
            final_pixel_errors=0,attribute_errors=0,ay_errors=0))
        previous[i%2]=value; attrs_previous[i%2]=attrs.copy()
        if i%500==0: print(f'Compact contours verified {i+1}/{len(states)}',flush=True)
    for r in inputs.values(): r.end()
    result=dict(scope=__doc__,complete=True,release=False,player_changed=False,player_delta_tstates=0,
        checked_frames=len(rows),checked_ay_ticks=len(rows)*6,states_sha256=source['states_sha256'],raw_sha256=source['raw_sha256'],
        source_report_sha256=sha(args.source_report.read_bytes()),
        modes=dict(Counter(r['mode'] for r in rows)),streams={},speed_measured=False,cadence_verified=False)
    for name,stream in streams.items():
        (args.cache/(name+'.raw')).write_bytes(stream)
        result['streams'][name]=dict(raw_bytes=len(stream),sha256=sha(stream),deflate_8192_layout_screen=measure(stream,8192))
    prefix=json.dumps(result,indent=2)
    args.output.write_text(prefix[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(r) for r in rows)+'\n  ]\n}\n',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
