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


def execute(regions, labels, layout, payload, expected, interrupts=False):
    m = Z80Machine()
    m.memory[:] = b'\xa5'*65536
    for address,data in regions:
        m.set_memory_block(address,data)
    source,output,stack,stop = 0x4000,0xc000,0xbff0,0x100
    m.set_memory_block(source,payload)
    put_word(m,labels['input_pointer'],source)
    put_word(m,labels['block_end'],output+len(expected))
    put_word(m,labels['block_length'],len(expected))
    m.set_breakpoint(stop)
    # Register-preserving IM1 handler also alters AF' temporarily.
    irq = bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
    m.set_memory_block(0x38,irq)
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for address,data in regions:
        m.unmark_addrs(address,len(data),m.READ_MARK)
    for lo,hi in ((source,source+len(payload)),(stack-128,stack),
                  (resumable_lzsa2.STACK-128,resumable_lzsa2.STACK),(0x38,0x38+len(irq)),(0x200,0x207)):
        m.unmark_addrs(lo,hi-lo,m.READ_MARK)
    m.unmark_addrs(labels['state'],labels['end']-labels['state'],m.WRITE_MARK)
    for address in layout['patched_addresses']:
        m.unmark_addr(address,m.WRITE_MARK)
    high=output
    def read(address):
        assert output<=address<high,('invalid read',hex(address),hex(m.pc))
        return m.memory[address]
    def write(address,value):
        nonlocal high
        if output<=address<output+len(expected):
            assert address==high,('nonsequential output',hex(address))
            high+=1
        else:
            assert (stack-128<=address<stack or
                    resumable_lzsa2.STACK-128<=address<resumable_lzsa2.STACK),('invalid write',hex(address),hex(m.pc))
        m.memory[address]=value
    m.set_read_callback(read);m.set_write_callback(write)
    slices=[];irqs=0
    for index,target in enumerate(list(range(256,len(expected),256))+[len(expected)]):
        put_word(m,labels['slice_target'],output+target)
        put_word(m,stack-2,stop)
        entry=labels['begin' if index==0 else 'slice_until']
        m.pc,m.sp=entry,stack-2
        if interrupts:
            m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'))
            m.pc=0x200
        budget=20_000_000;m.ticks_to_stop=budget
        while m.pc!=stop:
            event=m.run()
            assert not event&m._TICKS_LIMIT_HIT and m.pc!=labels['fatal']
            if interrupts and m.pc!=stop and event&m._END_OF_FRAME:
                m.on_handle_active_int()
                assert m.pc==0x38
                irqs+=1
        assert m.sp==stack and high>=output+target
        slices.append(budget-m.ticks_to_stop)
        # The caller may overwrite every working register between demands.
        for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):
            setattr(m,name,0x9797)
    assert bytes(m.memory[output:high])==expected and high==output+len(expected)
    return dict(tstates=sum(slices),slices=slices,exact=True,injected_interrupts=irqs)


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
