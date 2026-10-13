"""Cross-check LZSA2 dispatch on an independent full-flags native Z80 core.

Same archived payloads and 256-byte demands as the banked component test.
Flat memory only; synthetic IM1 probes do not replace the full Fuse run.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

from z80 import Z80Machine
from benchmark_lzma_z80 import put_word, word
import resumable_lzsa2

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'toolkit/row_lzsa_evidence'


def archived(name):
    return gzip.decompress((EVIDENCE/(name+'.gz')).read_bytes())


from lzsa.native import execute


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cpu',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    baseline=json.loads(archived('lzsa2-metadata.json'))
    oldcpu=json.loads(archived('lzsa2-cpu.json'));newcpu=json.loads(a.cpu.read_text())
    stream=archived('video.stream');raw=archived('video.raw')
    assert hashlib.sha256(stream).hexdigest()==newcpu['stream_sha256']==oldcpu['stream_sha256']
    assert hashlib.sha256(raw).hexdigest()==newcpu['raw_sha256']==oldcpu['raw_sha256']
    oldregions=[(r['address'],bytes.fromhex(r['code_hex'])) for r in baseline['lzsa2']['regions']]
    newregions,newlabels,newlayout=resumable_lzsa2.build()
    variants=[('baseline',oldregions,baseline['decoder_labels'],baseline['lzsa2']['layout'],oldcpu),
              ('candidate',newregions,newlabels,newlayout,newcpu)]
    # Exhaustive flag truth table in the independent emulator, including S.
    for token in range(256):
        m=Z80Machine();m.set_memory_block(0x200,bytes([0x3e,token,0xe6,24,0]))
        m.pc=0x200;m.set_breakpoint(0x204);m.run()
        assert bool(m.f&4)==((token&24) in (0,24))
        m=Z80Machine();m.set_memory_block(0x200,bytes([0x3e,token,0xb7,0]))
        m.pc=0x200;m.set_breakpoint(0x203);m.run()
        assert bool(m.f&128)==(token>=128)
    results={};at=offset=0;blocks=[]
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        blocks.append((stream[at:at+size],raw[offset:offset+n]));at+=size;offset+=n
    for name,regions,labels,layout,reference in variants:
        rows=[]
        for index,(payload,expected) in enumerate(blocks):
            row=execute(regions,labels,layout,payload,expected)
            assert row['slices']==reference['blocks'][index]['slice_tstates'],(name,index,row['tstates'])
            irq=execute(regions,labels,layout,payload,expected,interrupts=True)
            rows.append(dict(block=index,**row,interrupt_run=irq))
        results[name]=dict(blocks=rows,total_tstates=sum(r['tstates'] for r in rows),
            injected_interrupts=sum(r['interrupt_run']['injected_interrupts'] for r in rows))
        print(name,results[name]['total_tstates'],'T; all slices exact',flush=True)
    report=dict(complete=True,release=False,scope=__doc__,variants=results,
                exhaustive_flag_inputs=256,source_sha256_lf=hashlib.sha256(Path(resumable_lzsa2.__file__).read_text().encode()).hexdigest())
    a.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
