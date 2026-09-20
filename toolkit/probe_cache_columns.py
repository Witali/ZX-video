"""Check narrower four-row motion-cache fills; storage and access probe only.

C164/C084 replace each FAP3 three-byte coverage map by 6/12 bytes. All
other packet fields are unchanged. Exact FAP3 roundtrip and every motion
source read are checked. Copy T savings are an optimistic 16 T/byte ceiling;
dispatch, parser, extra ZX0/sector costs still require Z80 measurement.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_sparse_motion_cache import coverage,verify_cache
from probe_lossless_layouts import sha,measure


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','cache','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3')
    if len(states)!=count: raise ValueError('frame count differs')
    outputs={n:bytearray((b'C164' if n==16 else b'C084')+raw[4:r.pos]) for n in (16,8)}
    rows=[]; previous=bytes(3840)
    for i,state in enumerate(states):
        _,packet=read_packet(r,stored_guards=False); payload=packet['payload']
        start=sum(map(len,packet['ticks']))+5; vectors=payload[start+3:start+195]
        fine=coverage(vectors,8).reshape(24,4,4).any(axis=1)
        whole=fine.any(axis=1)
        if np.packbits(whole).tobytes()!=packet['cache']: raise AssertionError(('original map differs',i))
        row=dict(index=i,whole_groups=int(whole.sum()),baseline_copy_bytes=int(whole.sum())*128)
        for n in (16,8):
            groups=fine if n==8 else fine.reshape(24,2,2).any(axis=2)
            packed=np.packbits(groups).tobytes()
            body=payload[:start]+packed+payload[start+3:]
            outputs[n]+=struct.pack('<H',len(body))+body
            # Independently unpack the extra map and restore the old bytes.
            decoded=np.unpackbits(np.frombuffer(body[start:start+len(packed)],dtype=np.uint8)).reshape(24,32//n)
            restored=body[:start]+np.packbits(decoded.any(axis=1)).tobytes()+body[start+len(packed):]
            if restored!=payload: raise AssertionError(('FAP3 payload differs',i,n))
            reads=verify_cache(previous,vectors,np.repeat(decoded,4,axis=0),n)
            row[str(n)]=dict(groups=int(groups.sum()),copy_bytes=int(groups.sum())*4*n,verified_reads=reads)
        previous=state.tobytes(); rows.append(row)
        if i%500==0: print(f'Column cache verified {i+1}/{count}',flush=True)
    r.end(); args.cache.mkdir(parents=True,exist_ok=True)
    original=sum(row['baseline_copy_bytes'] for row in rows)
    result=dict(scope=__doc__,complete=True,release=False,cpu_measured=False,raw_sha256=sha(raw),
        states_sha256=sha(states.tobytes()),frames=count,baseline_raw_bytes=len(raw),
        baseline_copied_bytes=original,baseline_deflate_layout_screen=measure(raw,8192),variants={})
    for n,data in outputs.items():
        saved=args.cache/f'cache_{n}.raw'; saved.write_bytes(data)
        copied=sum(row[str(n)]['copy_bytes'] for row in rows)
        result['variants'][str(n)]=dict(raw_file=saved.name,raw_bytes=len(data),raw_delta_bytes=len(data)-len(raw),
            sha256=sha(data),copied_bytes=copied,saved_copy_bytes=original-copied,
            copy_tstates_saving_ceiling=16*(original-copied),deflate_layout_screen=measure(data,8192),
            exact_payload_roundtrip=True,verified_motion_reads=sum(row[str(n)]['verified_reads'] for row in rows))
    prefix=json.dumps(result,indent=2)
    args.output.write_text(prefix[:-2]+',\n  "frames_detail": [\n'+',\n'.join('    '+json.dumps(row) for row in rows)+'\n  ]\n}\n',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
