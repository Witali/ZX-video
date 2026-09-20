"""Execute every movie packet read on Z80 and isolate the copy-loop saving.

Complete byte/reader coverage only: no video reconstruction, cadence, ULA,
disk or AY. Request lengths follow FAP3, actual block/header/ZX0 processing
is executed by the reader. Baseline copy costs are cross-checked against the
recorded complete movie CPU histogram, excluding the startup header.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha
from stream_reader_harness import Harness
from stream_reader_z80 import copy_tstates


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw','storage-report','cache','baseline','output'):
        p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes()
    storage=json.loads(args.storage_report.read_text()); old=json.loads(args.baseline.read_text())
    if not storage['complete'] or storage['input_sha256']!=sha(raw) or not old['complete'] or old['raw_sha256']!=sha(raw):
        raise ValueError('wrong/incomplete inputs')
    reader=Reader(raw); _,_,frames,_,_=read_header(reader,magic=b'FAP3'); header_end=reader.pos
    requests=[]
    for index in range(frames):
        start=reader.pos; _,detail=read_packet(reader,stored_guards=False)
        requests.extend((2,reader.pos-start-2))
    reader.end()
    ring=bytearray(); pos=0; ends=[]
    for block in storage['blocks']:
        data=raw[pos:pos+block['decoded_bytes']]; pos+=len(data); ends.append(pos)
        packed=(args.cache/(block['sha256']+'.zx0')).read_bytes()
        if sha(data)!=block['sha256'] or len(packed)!=block['zx0_bytes']: raise ValueError('cache differs')
        ring+=struct.pack('<HH',len(data),len(packed))+packed
    if pos!=len(raw): raise ValueError('incomplete block list')
    h=Harness(bytes(ring),token_boundaries=True,unrolled_copy=True)
    pos=0
    while pos<header_end:
        n=min(4704,header_end-pos)
        if h.take(n)!=raw[pos:pos+n]: raise AssertionError('header differs')
        pos+=n
    h.histogram.clear(); h.rows.clear(); counts=Counter(); block=0
    report=dict(scope=__doc__,complete=False,release=False,raw_sha256=sha(raw),
        compressed_bytes=len(ring),compressed_stream_delta_bytes=0,frames=frames,requests=len(requests),
        reader_labels=h.r,code_regions=[dict(base=b,code_hex=c.hex()) for b,c in h.regions],
        instruction_listing=list(h.instructions.values()),disk_delivery_verified=False,ula_verified=False)
    for index,n in enumerate(requests):
        if h.take(n)!=raw[pos:pos+n]: raise AssertionError(('packet bytes differ',index))
        remaining=n
        while remaining:
            while pos==ends[block]: block+=1
            part=min(remaining,ends[block]-pos); counts[part]+=1
            pos+=part; remaining-=part
        if index%1000==0: print(f'Z80 packet reads checked {pos}/{len(raw)} bytes',flush=True)
    if pos!=len(raw) or h.cpu.consumed!=len(ring) or h.blocks!=len(ends): raise AssertionError('EOF differs')
    before=sum(copy_tstates(n)*k for n,k in counts.items())
    after=sum(copy_tstates(n,unrolled=True)*k for n,k in counts.items())
    measured=sum(t*k for (pc,t),k in h.histogram.items() if h.r['copy']<=pc<h.r['copy_end'])
    old_copy={r['address'] for r in old['instruction_listing'] if 0xdb00<=r['address']<0xdc00 and r['instruction']=='LDIR'}
    recorded=sum(r['tstates']*r['count'] for r in old['instruction_histogram'] if r['address'] in old_copy)
    if (before,after)!=(recorded,measured): raise AssertionError(('copy timing differs',before,recorded,after,measured))
    report.update(complete=True,decoded_bytes=pos,packet_copy_counts=dict(sorted(counts.items())),
        copy_before_tstates=before,copy_after_tstates=after,copy_delta_tstates=after-before,
        packet_bytes=len(raw)-header_end,header_bytes=header_end,header_excluded_from_costs=True,
        reader_tstates=sum(r['stages']['reader'] for r in h.rows),
        banked_zx0_tstates=sum(r['stages'].get('banked_zx0',0) for r in h.rows),
        instruction_histogram=[dict(address=a,tstates=t,count=k) for (a,t),k in sorted(h.histogram.items())])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k.endswith('tstates') or k in ('complete','decoded_bytes')}))


if __name__=='__main__': main()
