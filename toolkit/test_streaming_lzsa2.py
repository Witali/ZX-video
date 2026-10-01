"""Guarded LZSA2: real sector producer, input boundaries and full-flags replay.

ROM and physical latency are excluded. The independent core also verifies
in-place decoding with one-sector supplies and register-clobbering callers.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
from unittest.mock import patch

from z80 import Z80Machine
from benchmark_lzma_z80 import put_word
import benchmark_inplace_slot as base
import benchmark_inplace_streaming as streaming
from benchmark_row_lzsa import LzsaCPU,fixture as old_fixture
from build_fap3_trd import sha
from convert_video import write_json
from inplace_streaming_core import input_prefix
from inplace_zx0 import layout as inplace_layout
from lzsa2_oracle import encode
import lzsa2_stream
import resumable_lzsa2
from test_fap3_disk import install


class StreamingCPU(LzsaCPU):
    def read8(self,address):
        at=address&65535
        if self.decoding and self.input_start<=at<self.input_start+len(self.payload):
            assert at<self.loaded_until,('unloaded LZSA2 byte',hex(at),hex(self.loaded_until))
        return super().read8(address)


class Harness(streaming.Harness):
    def __init__(self,stream,first,*,direct_header=False):
        base.Harness.__init__(self,stream,first,inplace=True)
        c=self.cpu;c.__class__=StreamingCPU;c.decoder_histogram=Counter()
        regions,self.z,self.layout=resumable_lzsa2.build(core=0x8d74,core_limit=0x8e80,streaming=True,direct_header=direct_header)
        for at,data in regions:install(c,at,data)
        c.zlabels=self.z;c.patched=set(self.layout['patched_addresses'])
        c.token_rereads={r['address']+1 for r in self.layout['instruction_listing']
            if r['instruction'] in ('LD A,(HL)','LD B,(HL)','OR (HL)')}
        regions,self.p,rows=input_prefix(self.z,self.d,elapsed_fields=self.elapsed_fields,origin=self.layout['prefix_end'],patch_guards=True)
        for at,data in regions:install(c,at,data)
        self.regions=regions;self.instructions.update({r['address']:r for r in rows})


def independent(payload,expected,*,offset=0,interrupts=False,direct_header=False):
    regions,z,report=resumable_lzsa2.build(core=0x8d74,core_limit=0x8e80,streaming=True,direct_header=direct_header)
    _,proof=lzsa2_stream.trace(payload,limit=len(expected))
    place=inplace_layout(len(payload),len(expected),proof['minimum_input_start'],offset)
    assert place['sector_aligned_fits']
    start=0xc000+place['input_start'];end=start+len(payload)
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    for at,data in regions:m.set_memory_block(at,data)
    output,stack,stop=0xc000,0x9df0,0x100
    high=output;loaded=start&0xff00;input_at=start
    put_word(m,z['input_pointer'],start);put_word(m,z['block_end'],output+len(expected))
    put_word(m,z['block_length'],len(expected));m.set_breakpoint(stop);m.set_breakpoint(z['fatal'])
    irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
    m.set_memory_block(0x38,irq)
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for at,data in regions:m.unmark_addrs(at,len(data),m.READ_MARK)
    for lo,hi in ((stack-128,stack),(resumable_lzsa2.STACK-128,resumable_lzsa2.STACK),
                  (0x38,0x38+len(irq)),(0x200,0x207)):
        m.unmark_addrs(lo,hi-lo,m.READ_MARK)
    m.unmark_addrs(z['state'],z['end']-z['state'],m.WRITE_MARK)
    for at in report['patched_addresses']:m.unmark_addr(at,m.WRITE_MARK)
    def read(at):
        nonlocal input_at
        if start<=at<end and not output<=at<high:
            assert at<loaded,('unloaded independent input',hex(at),hex(loaded),hex(m.pc))
            assert m.memory[at]==payload[at-start]
            input_at=max(input_at,at+1)
        else:assert output<=at<high,('uninitialized history',hex(at),hex(m.pc))
        return m.memory[at]
    def write(at,value):
        nonlocal high
        if output<=at<output+len(expected):
            assert at==high and value==expected[at-output],('output',hex(at),hex(m.pc))
            assert not input_at<=at<end,('overwritten unread input',hex(at),hex(input_at))
            high+=1
        else:assert stack-128<=at<stack or resumable_lzsa2.STACK-128<=at<resumable_lzsa2.STACK
        m.memory[at]=value
    m.set_read_callback(read);m.set_write_callback(write)
    def supply():
        nonlocal loaded
        assert loaded<0x10000
        previous=bytes(m.memory[output:high]);lo=max(start,loaded);loaded+=256
        hi=min(end,loaded)
        if hi>lo:m.set_memory_block(lo,payload[lo-start:hi-start])
        assert bytes(m.memory[output:high])==previous
        m.memory[z['input_high']]=(loaded>>8)&255;m.memory[z['all_loaded']]=int(loaded==0x10000)
        for name in ('header_frontier','literal_frontier'):m.memory[z[name]]=(loaded>>8)&255
        for name in ('header_patch','guard_literals'):
            if name in z:m.memory[z[name]]=0xc9 if loaded==0x10000 else 0xf5
        for target,partial,full in (
                ('token_high_target',z['token_guard'],z['token_body']),('token_low_target',z['token_guard'],z['token_body']),
                ('token_end_target',z['token_guard'],z['token_body']),('long8_target',z['guard_long8'],z['CopyMoreLiterals']),
                ('long16_target',z['guard_long16'],z['NextUseBC'])):
            put_word(m,z[target],full if loaded==0x10000 else partial)
    supply();first=True;cost=[];waits=[];irqs=0
    for target in list(range(256,len(expected),256))+[len(expected)]:
        while True:
            put_word(m,z['slice_target'],output+target);put_word(m,stack-2,stop)
            entry=z['begin' if first else 'slice_until'];first=False
            m.pc,m.sp=entry,stack-2
            if interrupts:
                m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'));m.pc=0x200
            budget=20_000_000;m.ticks_to_stop=budget
            while m.pc!=stop:
                event=m.run()
                assert not event&m._TICKS_LIMIT_HIT and m.pc!=z['fatal']
                if interrupts and m.pc!=stop and event&m._END_OF_FRAME and m.iff1 and not m.int_disabled:
                    m.on_handle_active_int();assert m.pc==0x38;irqs+=1
            assert m.sp==stack
            cost.append(budget-m.ticks_to_stop)
            for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):setattr(m,name,0x9797)
            if not m.memory[z['input_needed']]:
                assert high>=output+target;break
            waits.append(dict(produced=high-output,loaded=loaded-start))
            supply()
    assert m.memory[z['finished']] and bytes(m.memory[output:high])==expected and high==output+len(expected)
    assert loaded==65536
    return dict(exact=True,tstates=sum(cost),input_waits=waits,injected_interrupts=irqs,input_start=start)


def cases():
    for n in (1,2,3,17,18,237,238,239,255,256,257,511,800,4096,15872):
        raw=bytes(i%251 for i in range(n));yield f'literal-{n}',encode(raw,[]),raw
    for distance in (1,2,32,33,511,512,513,8704,8705):
        raw=bytes(i%251 for i in range(distance));raw+= (raw* (15872//distance+1))[:15872-distance]
        yield f'match-{distance}',encode(raw,[(distance,15872-distance,distance)]),raw


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stream',type=Path);p.add_argument('--raw',type=Path)
    p.add_argument('--direct-header',action='store_true');a=p.parse_args()
    samples=list(cases())
    if a.stream:
        data=a.stream.read_bytes();raw=a.raw.read_bytes();at=out=0;index=0
        while at<len(data):
            n,size=struct.unpack_from('<HH',data,at);at+=4
            samples.append((f'real-{index}',data[at:at+size],raw[out:out+n]));at+=size;out+=n;index+=1
        assert out==len(raw)
    stream=b''.join(struct.pack('<HH',len(raw),len(payload))+payload for _,payload,raw in samples)
    new=Harness(stream,57,direct_header=a.direct_header);old,oldlayout=old_fixture(stream,57,0x8d74,0x8e80)
    replay=[]
    with patch.object(streaming,'trace',lzsa2_stream.trace),patch.object(base,'trace',lzsa2_stream.trace):
        for i,(name,payload,raw) in enumerate(samples):
            assert lzsa2_stream.trace(payload,limit=len(raw))[0]==raw
            old.block(payload,raw,i);new.block(payload,raw,i,short=i==1)
            row=dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                full_flags=[independent(payload,raw,offset=offset,interrupts=offset==253,direct_header=a.direct_header) for offset in (0,1,252,253,254,255)])
            replay.append(row);print(name,'exact',flush=True)
    for h,layout in ((old,oldlayout),(new,new.layout)):
        rows={r['address']:r for r in layout['instruction_listing']}
        for (pc,t),count in h.cpu.decoder_histogram.items():
            wanted=rows[pc]['tstates']
            allowed=wanted if isinstance(wanted,list) else [wanted]
            if pc in (h.z.get('guard_header'),h.z.get('guard_literals')):allowed=allowed+[10]
            assert t in allowed,(rows[pc],t)
        assert sum(t*n for (_,t),n in h.cpu.decoder_histogram.items())==sum(r['decoder_tstates'] for r in h.results)
    baseline=old.finish();candidate=new.finish()
    report=dict(complete=True,release=False,scope=__doc__,cases=len(samples),baseline=baseline,candidate=candidate,
        total_tstates_delta=candidate['total_tstates']-baseline['total_tstates'],baseline_blocks=old.results,blocks=new.results,
        independent=replay,layout=new.layout,stream_sha256=sha(stream),regions=[dict(address=at,code_hex=data.hex()) for at,data in new.regions])
    write_json(a.output,report)
    print(json.dumps(dict(complete=True,cases=len(samples),baseline_T=baseline['total_tstates'],candidate_T=candidate['total_tstates'])))


if __name__=='__main__':main()
