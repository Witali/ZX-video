"""Item 01: complete native LZSA2 comparison; no ULA/ROM/disk timing."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'libraries/lzsa/src'))
sys.path.insert(0, str(ROOT/'libraries/zx0/src'))
from lzsa import decompress, encode
from lzsa.native import execute
from lzsa.resumable import build
from zx0 import banked
from z80 import Z80Machine


def noncanonical_cases():
    # The format assigns the final 16-bit value without a >=256 restriction.
    # Cover short literal/match encodings already accepted by the host and
    # baseline native decoder; their LDIR paths must never underflow.
    for n in (3,4,15,16,17,18,24,255):
        raw=bytes(i%251 for i in range(n))
        yield f'word-literal-{n}',bytes.fromhex('5f ff ef')+n.to_bytes(2,'little')+raw+bytes.fromhex('00 e8'),raw
    for n in (2,3,8,9,15,16,17,23,24,255):
        raw=b'A'*(n+1)
        yield f'word-match-{n}',bytes.fromhex('0f 41 ff e9')+n.to_bytes(2,'little')+bytes.fromhex('47 00 f0 e8'),raw


def sha(data):
    return hashlib.sha256(data).hexdigest()


def samples():
    evidence=ROOT/'toolkit/row_lzsa_evidence'
    stream=gzip.decompress((evidence/'video.stream.gz').read_bytes())
    raw=gzip.decompress((evidence/'video.raw.gz').read_bytes())
    # Authenticate against the previously checked full fixture, not a newly
    # calculated hash that could silently accept a changed input.
    reference=json.loads(gzip.decompress((evidence/'lzsa2-cpu.json.gz').read_bytes()))
    assert sha(stream)==reference['stream_sha256'] and sha(raw)==reference['raw_sha256']
    at=out=index=0
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        yield f'real-{index}',stream[at:at+size],raw[out:out+n]
        at+=size;out+=n;index+=1
    assert out==len(raw)
    for n in (1,2,3,17,18,237,238,239,255,256,257,511,800,4096,15872):
        raw=bytes(i%251 for i in range(n));yield f'literal-{n}',encode(raw,[]),raw
    for distance in (1,2,32,33,511,512,513,8704,8705):
        raw=bytes(i%251 for i in range(distance))
        raw+=(raw*(15872//distance+1))[:15872-distance]
        yield f'match-{distance}',encode(raw,[(distance,15872-distance,distance)]),raw
    rng=random.Random(20261013)
    for index in range(32):
        raw=bytearray();matches=[]
        for _ in range(24):
            raw.extend(rng.randbytes(rng.choice((1,2,3,17,18,23,24,255,256,257))))
            distance=rng.randint(1,len(raw));start=len(raw)
            length=rng.choice((2,3,8,9,23,24,25,255,256,257))
            for _ in range(length):raw.append(raw[-distance])
            matches.append((start,length,distance))
        raw=bytes(raw);yield f'random-{index}',encode(raw,matches),raw
    yield from noncanonical_cases()


def compare(payload,raw,baseline,candidate):
    assert decompress(payload,limit=len(raw))==raw
    old=execute(*baseline,payload,raw,source=0x2000)
    new=execute(*candidate,payload,raw,source=0x2000)
    irq=execute(*candidate,payload,raw,source=0x2000,interrupts=True)
    assert len(old['slices'])==len(new['slices'])
    delta=[b-a for a,b in zip(old['slices'],new['slices'])]
    assert not any(t>0 for t in delta)
    return dict(payload_bytes=len(payload),raw_bytes=len(raw),payload_sha256=sha(payload),
        raw_sha256=sha(raw),baseline_tstates=old['tstates'],candidate_tstates=new['tstates'],
        delta_tstates=new['tstates']-old['tstates'],slices=len(delta),
        slower_slices=sum(t>0 for t in delta),largest_slice_delta=max(delta),
        exact=True,interrupt_exact=irq['exact'],injected_interrupts=irq['injected_interrupts'])


def existing_zx0_refill():
    blob,labels=banked.build(fast_refill=True);rows=[]
    for count in (1,31,255,256):
        m=Z80Machine();m.set_memory_block(banked.CODE,blob)
        raw=bytes(i&255 for i in range(count));m.set_memory_block(0x6000,raw)
        m.hl,m.de,m.bc=0x6000,0x9000,count;m.sp=0xaff0
        m.set_memory_block(m.sp,b'\x00\x01');m.pc=labels['ring_copy_bytes']
        m.set_breakpoint(0x100);m.ticks_to_stop=10000
        while m.pc!=0x100:assert not m.run()&m._TICKS_LIMIT_HIT
        assert bytes(m.memory[0x9000:0x9000+count])==raw
        measured=10000-m.ticks_to_stop;baseline=21*count-5+10
        assert measured==(4251 if count==256 else baseline+20)
        rows.append(dict(bytes=count,baseline_tstates=baseline,candidate_tstates=measured,
            delta_tstates=measured-baseline,exact=True))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    baseline=build();candidate=build(long_copy=True,core_limit=0x9000)
    rows=[dict(case=name,**compare(payload,raw,baseline,candidate)) for name,payload,raw in samples()]
    def layout(profile):
        regions,labels,report=profile
        return dict(core_end=report['core_end'],prefix_end=report['prefix_end'],
            code_bytes=report['code_bytes'],state_bytes=labels['end']-labels['state'],
            private_stack=report['private_stack'],output_base=report['output_base'],
            regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in regions])
    report=dict(complete=True,release=False,baseline_revision='6168ba14',
        scope=__doc__,random_seed=20261013,baseline=layout(baseline),candidate=layout(candidate),
        existing_zx0_refill=existing_zx0_refill(),
        summary=dict(cases=len(rows),real_blocks=sum(r['case'].startswith('real-') for r in rows),
            decoded_bytes=sum(r['raw_bytes'] for r in rows),
            baseline_tstates=sum(r['baseline_tstates'] for r in rows),
            candidate_tstates=sum(r['candidate_tstates'] for r in rows),
            real_delta_tstates=sum(r['delta_tstates'] for r in rows if r['case'].startswith('real-')),
            delta_tstates=sum(r['delta_tstates'] for r in rows),
            slower_blocks=sum(r['delta_tstates']>0 for r in rows),
            slower_slices=sum(r['slower_slices'] for r in rows),
            injected_interrupts=sum(r['injected_interrupts'] for r in rows)),blocks=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary']))


if __name__=='__main__':main()
