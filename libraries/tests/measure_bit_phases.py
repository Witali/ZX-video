"""Item23: pinned Mega versus adapted Fast, same one-shot contract and streams."""
import argparse
import gzip
import json
from pathlib import Path
import random
import struct
import sys
from measure_long_copy import ROOT,sha
from native_block import execute
from test_libraries import profiles
from zx0._z80 import MiniAssembler
from zx0.codec import emit_decoder,decompress
from zx0.resumable import emit_fast
sys.path.insert(0,str(ROOT/'toolkit'))
from zx0_speed import Token,encode


def build(variant,origin=0x8000):
    a=MiniAssembler(origin)
    if variant=='fast':
        emit_fast(a,lambda a,site:None);entry='DecompressZX0';offset='PrevOffset+1'
    else:
        entry=emit_decoder(a,variant);offset=f'dzx0{variant[0]}_last_offset+1'
    patches=[] if variant=='standard' else [a.labels[offset],a.labels[offset]+1]
    return [(origin,a.resolve())],a.labels,dict(entry=entry,patched_addresses=patches,variant=variant)


def samples():
    probe=json.loads((ROOT/'toolkit/inplace_zx0_probe.json').read_text())
    variant=next(v for v in probe['variants'] if v['block_bytes']==8192)
    for volume in variant['volumes']:
        name=f'block8192-part{volume["part"]:02}.stream.gz'
        ref=next(d for d in probe['archives'] if d['file']==name)
        archive=(ROOT/'toolkit/inplace_zx0_evidence'/name).read_bytes();stream=gzip.decompress(archive)
        assert sha(archive)==ref['sha256'] and sha(stream)==ref['decoded_sha256']
        at=0
        for old in volume['blocks']:
            n,size=struct.unpack_from('<HH',stream,at);at+=4
            payload=stream[at:at+size];at+=size;raw=decompress(payload,limit=n)
            assert sha(payload)==old['payload_sha256'] and sha(raw)==old['raw_sha256']
            yield f'real-{volume["part"]}-{old["index"]}',payload,raw
        assert at==len(stream)
    for n in (1,2,3,7,8,15,16,127,128,255,256,257,8192,15872):
        raw=bytes(i%251 for i in range(n));yield f'literal-{n}',encode(raw,[Token(0,n)]),raw
    for offset in (1,2,127,128,255,256,8192):
        raw=bytes(i%251 for i in range(offset));raw+=(raw*16000)[:15872-offset]
        yield f'match-{offset}',encode(raw,[Token(0,offset),Token(offset,15872-offset,offset)]),raw
    rng=random.Random(20261014)
    for i in range(32):
        raw=bytearray(rng.randbytes(rng.randint(1,260)));tokens=[Token(0,len(raw))]
        for _ in range(24):
            length=rng.choice((2,3,8,9,127,128,255,256,257));offset=rng.randint(1,len(raw))
            tokens.append(Token(len(raw),length,offset))
            for _ in range(length):raw.append(raw[-offset])
            length=rng.randint(1,25);tokens.append(Token(len(raw),length));raw.extend(rng.randbytes(length))
        yield f'random-{i}',encode(bytes(raw),tokens),bytes(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();built={v:build(v) for v in ('standard','turbo','fast','mega')};rows=[]
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    for name,payload,raw in samples():
        costs={v:execute(p,payload,raw) for v,p in built.items()}
        irq=execute(built['mega'],payload,raw,interrupts=True)
        relocated=execute(build('mega',0x9103),payload,raw)
        assert relocated['tstates']==costs['mega']['tstates']
        rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),payload_bytes=len(payload),
                         raw_bytes=len(raw),profiles=costs,mega_irq=irq['injected_interrupts']))
    summary={v:dict(tstates=sum(r['profiles'][v]['tstates'] for r in rows),
                  real_tstates=sum(r['profiles'][v]['tstates'] for r in rows if r['case'].startswith('real-')),
                  stack_bytes=max(r['profiles'][v]['stack_bytes'] for r in rows)) for v in built}
    report=dict(date='2026-10-14',baseline_revision='bfdc9258',complete=True,release=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',defaults_exact=31,
        contract='HL source, DE output; complete resident valid stream/history, nonwrapping output; caller stack; exact EOF',
        cases=len(rows),decoded_bytes=sum(r['raw_bytes'] for r in rows),summary=summary,
        mega_slower_than_fast=sum(r['profiles']['mega']['tstates']>r['profiles']['fast']['tstates'] for r in rows),
        injected_interrupts=sum(r['mega_irq'] for r in rows),
        profiles={v:dict(metadata=p[2],code_bytes=len(p[0][0][1]),code_sha256=sha(p[0][0][1])) for v,p in built.items()},blocks=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('profiles','blocks')}))

if __name__=='__main__':main()
