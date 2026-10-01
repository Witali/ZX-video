"""Renumber CB46 dictionaries without changing packets' renderer operations.

Measure one cached window, not multiple movie builds. Require exact host
screens; compare native LZSA2 cycles before considering a candidate useful.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from build_fap3_trd import sha
from convert_video import write_json
from dynamic_row_dictionary import decode_check
from inplace_zx0 import layout
from probe_adaptive_block_codecs import ExternalCodec
from verify_lzsa2_dispatch import execute
import lzsa2_stream
import resumable_lzsa2


def locations(raw):
    assert raw[:4]==b'CB46';at=2056;row_bytes=[];book_bytes=[]
    while at<len(raw):
        n=struct.unpack_from('<H',raw,at)[0];at+=2
        if n&0x8000:
            assert 1<=n&0x7fff<=256
            row_bytes.extend(range(at,at+3*(n&0x7fff),3));at+=3*(n&0x7fff);continue
        stop=at+n;cells=sum(b.bit_count() for b in raw[at:at+72]);attrs=sum(b.bit_count() for b in raw[at+72:at+144])
        modes=raw[at+144:at+144+(cells+3)//4];cursor=at+144+len(modes)
        for i in range(cells):
            mode=(modes[i//4]>>(2*(i%4)))&3
            if mode==0:row_bytes.extend(range(cursor,cursor+4));cursor+=4
            elif mode==1:book_bytes.append(cursor);cursor+=1
            elif mode==3:assert raw[cursor]<4;row_bytes.append(cursor+1);cursor+=2
        assert cursor+attrs==stop;at=stop
    assert at==len(raw)
    return row_bytes,book_bytes


def permutation(counts,wishes,*,black=False):
    result={0:0} if black else {};available=set(range(256))-set(result.values())
    order=sorted(range(256),key=lambda i:(-counts[i],i))
    for i in order:
        if i in result:continue
        desired=next((v for v in wishes[i] if v in available),None)
        if desired is not None:result[i]=desired;available.remove(desired)
    for i in order:
        if i in result:continue
        value=i if i in available else min(available);result[i]=value;available.remove(value)
    assert set(result)==set(result.values())==set(range(256))
    return result


def remap(raw,rows,kind):
    rp,bp=locations(raw);table=bytes.fromhex(rows['tables_hex']);book=[raw[8+i*8:16+i*8] for i in range(256)]
    rf=Counter(raw[p] for p in rp);bf=Counter(raw[p] for p in bp)
    rm=permutation(rf,{i:[table[i],table[256+i]] for i in range(256)},black=True)
    wishes={}
    for i,key in enumerate(book):
        uniform=[rm[j] for j in range(256) if key==bytes([table[j],table[256+j]])*4]
        wishes[i]=uniform+([i] if kind=='flat' else [v for v,_ in Counter(key).most_common()])
    bm=permutation(bf,wishes) if kind in ('aligned','flat') else {i:i for i in range(256)}
    data=bytearray(raw);newtable=bytearray(512);words=[0]*256
    for old,new in rm.items():
        newtable[new]=table[old];newtable[new+256]=table[old+256];words[new]=rows['words'][old]
    for old,new in bm.items():data[8+8*new:16+8*new]=book[old]
    for p in rp:data[p]=rm[raw[p]]
    for p in bp:data[p]=bm[raw[p]]
    return bytes(data),dict(rows,words=words,tables_hex=newtable.hex(),sha256=sha(newtable)),dict(rows=rm,book=bm)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('metadata','lzsa','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--variants',nargs='+',choices=('rows','aligned','flat'),default=['rows','aligned'])
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'lzsa').mkdir(exist_ok=True)
    m=json.loads(a.metadata.read_bytes());work=a.metadata.parent/'work'/a.metadata.stem
    raw=(work/'codebook.raw').read_bytes();oldstream=(work/'codebook.stream').read_bytes();rows=json.loads((work/'rows.json').read_bytes())
    with np.load(work/'states.npz',allow_pickle=False) as f:frames=f['states']
    codec=ExternalCodec('lzsa2',a.lzsa.resolve(),a.lzsa.resolve(),'existing pinned LZSA2')
    regions,z,native=resumable_lzsa2.build(core=m['decoder_labels']['start'],core_limit=0x8e80)
    oldblocks=[];at=out=0
    while at<len(oldstream):
        n,size=struct.unpack_from('<HH',oldstream,at);at+=4;payload=oldstream[at:at+size];at+=size
        result=execute(regions,z,native,payload,raw[out:out+n]);oldblocks.append(result);out+=n
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='bc615ab',variants={},
        baseline_bytes=len(oldstream),baseline_sectors=(len(oldstream)+255)//256,
        baseline_decoder_tstates=sum(b['tstates'] for b in oldblocks),baseline_blocks=oldblocks,
        raw_sha256=sha(raw),stream_sha256=sha(oldstream),metadata_sha256=sha(a.metadata.read_bytes()))
    if (a.output/'report.json').exists():
        old=json.loads((a.output/'report.json').read_bytes())
        assert old['metadata_sha256']==report['metadata_sha256'] and old['stream_sha256']==report['stream_sha256']
        report['variants']=old['variants']
    for kind in a.variants:
        data,newrows,maps=remap(raw,rows,kind)
        proof=decode_check(data,frames,m['frame_start'],m['frame_end_exclusive'],newrows)
        stream=bytearray();blocks=[]
        for index,lo in enumerate(range(0,len(data),15872)):
            part=data[lo:lo+15872];coded=codec.encode_verified(part,None,a.output/'lzsa')
            restored,overlap=lzsa2_stream.trace(coded,limit=len(part));assert restored==part
            place=layout(len(coded),len(part),overlap['minimum_input_start'],len(stream));assert place['sector_aligned_fits']
            lzsa2_stream.trace(coded,limit=len(part),input_start=place['input_start'])
            cpu=execute(regions,z,native,coded,part)
            blocks.append(dict(index=index,decoded_bytes=len(part),compressed_bytes=len(coded),native=cpu,
                inplace_layout=place,sha256=sha(part),codec='lzsa2',inplace_proof=overlap,raw_start=lo,raw_end=lo+len(part)))
            stream+=struct.pack('<HH',len(part),len(coded))+coded
        folder=a.output/kind;folder.mkdir(exist_ok=True)
        (folder/'video.raw').write_bytes(data);(folder/'video.stream').write_bytes(stream);write_json(folder/'rows.json',newrows)
        cpu=sum(b['native']['tstates'] for b in blocks)
        row=dict(bytes=len(stream),sectors=(len(stream)+255)//256,decoder_tstates=cpu,
            bytes_delta=len(stream)-len(oldstream),decoder_delta_tstates=cpu-report['baseline_decoder_tstates'],
            raw_sha256=sha(data),stream_sha256=sha(stream),maps=maps,proof=proof,blocks=blocks,
            renderer_instruction_delta_tstates=0,renderer_operations_unchanged=True,
            host_candidate_eligible=len(stream)<len(oldstream) and cpu<=report['baseline_decoder_tstates'])
        report['variants'][kind]=row;write_json(a.output/'report.json',report)
        print(kind,{k:row[k] for k in ('bytes','sectors','bytes_delta','decoder_delta_tstates','host_candidate_eligible')},flush=True)
    report['complete']=True;report['source_sha256_lf']=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    write_json(a.output/'report.json',report)


if __name__=='__main__':main()
