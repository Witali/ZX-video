"""Verify the LZ4 candidate with independent full-flags Z80 and LZ4 cores.

Archived video slices must match the guarded banked CPU instruction counts.
Synthetic IM1 runs verify coroutine register preservation, not actual AY timing.
Hand-built valid blocks exercise short/extended lengths and overlapping matches.
"""
import argparse,gzip,json,random,struct
from pathlib import Path
from unittest.mock import patch
import lz4.block
import benchmark_inplace_slot as base
from benchmark_row_lz4 import fixture
from build_fap3_trd import sha
from build_five_level_test_trd import save
from inplace_zx0 import layout
from verify_lzsa2_dispatch import execute
import lz4_stream
import resumable_lz4


def extension(n):
    return bytes([255])*(n//255)+bytes([n%255])


def sequence(literals,offset=None,match=0):
    n=len(literals);low=0 if offset is None else min(match-4,15)
    result=bytes([(min(n,15)<<4)|low])
    if n>=15:result+=extension(n-15)
    result+=literals
    if offset is not None:
        result+=struct.pack('<H',offset)
        if match>=19:result+=extension(match-19)
    return result


def edge_blocks():
    rng=random.Random(930)
    noise=lambda n:bytes(rng.randrange(256) for _ in range(n))
    for n in (1,2,3,4,5,14,15,16,254,255,256,257,269,270,271,1024,15872):
        raw=noise(n)
        yield f'literals-{n}',sequence(raw),raw
    tail=noise(12)
    for n in (4,5,6,7,14,15,18,19,20,254,255,256,257,273,274,275,1024,15840):
        yield f'match-{n}',sequence(b'Q',1,n)+sequence(tail),b'Q'*(n+1)+tail
    for distance in (1,2,255,256,257,511,512,4096,8192,15000):
        seed=noise(distance);match=(seed*256)[:256]
        yield f'offset-{distance}',sequence(seed,distance,256)+sequence(tail),seed+match+tail
    # Zero literal count between matches, using both direct and extended paths.
    yield 'zero-literals',sequence(b'R',1,4)+sequence(b'',1,18)+sequence(b'',1,19)+sequence(tail),b'R'*42+tail


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('baseline','candidate','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--archive',type=Path,default=Path('toolkit/modern_codec_evidence/lz4_hc12.stream.gz'))
    p.add_argument('--raw',type=Path,required=True)
    a=p.parse_args();stream=gzip.decompress(a.archive.read_bytes());raw=a.raw.read_bytes()
    blocks=[];at=out=0
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        payload=stream[at:at+size];expected=raw[out:out+n]
        assert lz4.block.decompress(payload,uncompressed_size=n)==expected
        blocks.append((payload,expected));at+=size;out+=n
    assert at==len(stream) and out==len(raw)
    variants={}
    for name,fast,file in (('baseline',False,a.baseline),('candidate',True,a.candidate)):
        reference=json.loads(file.read_bytes())
        assert reference['stream_sha256']==sha(stream) and reference['raw_sha256']==sha(raw)
        regions,labels,native=resumable_lz4.build(fast_short=fast)
        assert native==reference['native']
        rows=[]
        for i,(payload,expected) in enumerate(blocks):
            row=execute(regions,labels,native,payload,expected)
            assert row['slices']==reference['blocks'][i]['slice_tstates'],(name,i)
            irq=execute(regions,labels,native,payload,expected,interrupts=True)
            rows.append(dict(block=i,**row,interrupt_run=irq))
        variants[name]=dict(blocks=rows,total_tstates=sum(r['tstates'] for r in rows),
            injected_interrupts=sum(r['interrupt_run']['injected_interrupts'] for r in rows))
        assert variants[name]['injected_interrupts']>0
        print(name,variants[name]['total_tstates'],'T; all slices exact',flush=True)
    edge_stream=bytearray();cases=list(edge_blocks())
    for name,payload,expected in cases:
        assert lz4.block.decompress(payload,uncompressed_size=len(expected))==expected,name
        decoded,proof=lz4_stream.trace(payload,limit=len(expected))
        assert decoded==expected,name
        space=layout(len(payload),len(expected),proof['minimum_input_start'],len(edge_stream))
        assert space['sector_aligned_fits'],(name,space)
        lz4_stream.trace(payload,limit=len(expected),input_start=space['input_start'])
        edge_stream+=struct.pack('<HH',len(expected),len(payload))+payload
    edges={}
    for name,fast in (('baseline',False),('candidate',True)):
        h,native=fixture(edge_stream,57,fast_short=fast)
        regions,labels,_=resumable_lz4.build(fast_short=fast)
        independent=[]
        with patch.object(base,'trace',lz4_stream.trace):
            for i,(case,payload,expected) in enumerate(cases):
                row=h.block(payload,expected,i,short=i==1);row['case']=case
                check=execute(regions,labels,native,payload,expected,source=0x1000)
                assert check['slices']==row['slice_tstates'],(name,case)
                irq=execute(regions,labels,native,payload,expected,interrupts=True,source=0x1000)
                independent.append(dict(case=case,**check,interrupt_run=irq))
        edges[name]=dict(**h.finish(),cases=h.results,independent=independent,
            minimum_decoder_sp=h.cpu.minimum_sp,
            max_slice_tstates=max(t for r in h.results for t in r['slice_tstates']))
        print(name,len(cases),'edge cases exact',flush=True)
    bad=[(b'',1),(b'\x10',1),(b'\xf0',16),(b'\xf0\xff',16),
         (b'\x10X\x00\x00',6),(b'\x10X\x02\x00',6),
         (b'\x1fX\x01\x00\xff',20),(b'\x20XX',1),(b'\x10XY',1)]
    for payload,n in bad:
        try:lz4_stream.trace(payload,limit=n)
        except ValueError:pass
        else:raise AssertionError(('invalid host input accepted',payload))
    assert lz4_stream.trace(b'\0',limit=0)[0]==b'' # valid host-only empty block
    report=dict(complete=True,release=False,scope=__doc__,variants=variants,edges=edges,
        edge_cases_per_variant=len(cases),invalid_host_inputs_rejected=len(bad),
        stream_sha256=sha(stream),raw_sha256=sha(raw),author_decoder_version=lz4.__version__)
    save(a.output,report)


if __name__=='__main__':main()
