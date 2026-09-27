"""Measure real sector/header/carry code plus resumable ZX0 over all blocks.

ROM is mocked. Instruction T-states exclude ROM execution, IRQ, ULA and
physical disk latency. Queue/frame scheduling remains a separate test.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct

import bank2_zx0
import bank_local_zx0
import direct_slot_input_z80 as previous
import inplace_slot_input_z80 as current
import pipelined_frame_z80 as video
import fap3_disk_z80 as disk
import disk_layout
from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from benchmark_direct_slot_input import ProducerCPU
from build_fap3_trd import sha
from fast_return_irq import install as fast_irq
from inplace_slot_player import decoder_patch
from test_fap3_disk import install
from validate_fast_sparse import CPU
from zx0_codec import decompress
from inplace_zx0 import trace

ROOT=Path(__file__).parent


class SlotCPU(ProducerCPU):
    decoding=False
    def read8(self,address):
        address &= 65535
        if self.decoding and address>=0xc000:
            if self.port_7ffd&7!=self.slot: raise AssertionError('wrong decoder bank')
            if address==self.input_start+self.input_reads and self.input_reads<len(self.payload):
                value=CPU.read8(self,address)
                if value!=self.payload[self.input_reads]: raise AssertionError('unread input changed')
                self.input_reads+=1; return value
            if not self.output_base<=address<self.output_base+self.produced:
                raise AssertionError('read outside input/produced history')
        return CPU.read8(self,address)

    def write8(self,address,value):
        address &= 65535
        if self.decoding:
            if self.output_base<=address<self.output_base+len(self.expected):
                if address!=self.output_base+self.produced or value!=self.expected[self.produced]:
                    raise AssertionError('wrong output byte/address')
                if self.input_reads<len(self.payload) and self.input_start+self.input_reads<=address<self.input_start+len(self.payload):
                    raise AssertionError('overwrites unread input')
                self.digest.update(self.input_reads.to_bytes(4,'little'));self.produced+=1
            elif not (bank_local_zx0.STACK_BOTTOM<=address<bank_local_zx0.STACK_TOP
                    or STACK-96<=address<STACK or self.zlabels['state']<=address<self.zlabels['end']
                    or address in self.patched):
                raise AssertionError(('write outside coroutine',hex(address)))
        return CPU.write8(self,address,value)


class Harness:
    def __init__(self,stream,first,*,inplace,elapsed_fields=0x8005):
        self.inplace=inplace; self.output=0xc000 if inplace else 0xe000
        sectors=(len(stream)+255)//256; self.positions=[first+n for n in disk_layout.positions(sectors,first%16)]
        physical=disk_layout.arrange(stream+bytes((-len(stream))%256),first%16)
        image=bytearray(655360);image[first*256:first*256+len(physical)]=physical
        c=self.cpu=SlotCPU(b'',bytes(image));c.iy=0;c.poison_rom=True;c.reads=[];c.short_once=False;c.guarding=False
        for bank in c.banks:bank[:]=b'\xa5'*16384
        c.port_7ffd=0x17
        regions,_,vrows=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),
            dict(history_page=0x8002),dict(elapsed_fields=0x8003),irq_safe_paging=True)
        for at,blob in regions:install(c,at,blob)
        c.write8(video.SHADOW,0x17)
        regions,self.z,report=bank2_zx0.build()
        for at,blob in regions:install(c,at,blob)
        if inplace:decoder_patch(c.read8,lambda at,blob:install(c,at,blob),dict(decoder_labels=self.z))
        code,self.d,drows=disk.build_disk(first,sectors,fast_disk=True,cached_seek=True,interleaved=True)
        install(c,disk.DISK,code);code,_,srows=disk.build_cached_seek(self.d);install(c,disk.CACHED_SEEK,code)
        fast_irq(c.read8,lambda at,blob:install(c,at,blob),dict(fast_disk=True,required_trdos_sha256=disk.TRDOS_503_SHA256,
            disk_labels=self.d,slot_queue_instruction_listing=drows))
        self.elapsed_fields=elapsed_fields
        word(c,elapsed_fields,0)
        if inplace:regions,self.p,prows=current.build(self.z,self.d,elapsed_fields=elapsed_fields)
        else:
            code,self.p,prows=previous.build(dict(self.z,end=previous.CODE),self.d)
            code=b'\xfe\x03'+code[2:];prows[0]['instruction']='CP 3';regions=[(previous.CODE,code)]
        for at,blob in regions:install(c,at,blob)
        self.regions=regions;self.instructions={r['address']:r for r in vrows+drows+srows+prows}
        self.histogram=Counter();self.copy_bytes=0;self.results=[]
        c.write8(0x5cf5,first//16);c.write8(0x5cf6,0);c.write8(0x5cfa,0x80)
        c.zlabels=self.z;c.patched={self.z[n] for n in ('slice_high_operand','slice_low_operand','slice_equal_branch',
            'match_high_operand','match_low_operand','match_equal_branch')}
        c.patched.update((self.z['dzx0t_last_offset']+1,self.z['dzx0t_last_offset']+2))

    def call(self,entry,interrupt=None):
        c=self.cpu;c.pc=entry;c.sp=STACK;c.push(STOP);start=c.tstates;steps=c.steps;irq=0
        while c.pc!=STOP:
            if c.pc==self.p['fatal'] or c.steps-steps>100000:raise AssertionError(('producer failed',hex(c.pc)))
            pc,before=c.pc,c.tstates;c.step();ticks=c.tstates-before;row=self.instructions[pc];wanted=row['tstates']
            if ticks not in (wanted if isinstance(wanted,list) else [wanted]):raise AssertionError(('instruction cost',hex(pc),ticks,wanted))
            self.histogram[pc,ticks]+=1
            if row['phase'] in ('direct_slot_input','inplace_slot_input') and row['instruction']=='LDI':self.copy_bytes+=1
            if interrupt and c.pc!=STOP:irq+=interrupt(c)
        if c.sp!=STACK:raise AssertionError('producer stack differs')
        return c.tstates-start-irq

    def block(self,payload,expected,index,*,short=False,interrupt=None):
        c=self.cpu;c.decoding=False;slot=(0,1,3)[index%3]
        protected={b:bytes(c.banks[b]) for b in (0,1,3,4,6,7) if b!=slot};screen=bytes(c.banks[5][:6912])
        reads=len(c.reads);copied=self.copy_bytes;c.a=index%3
        begin=self.call(self.p['begin'],interrupt);steps=[];c.short_once=short
        while True:
            before=len(c.reads);steps.append(self.call(self.p['step'],interrupt))
            if len(c.reads)-before>1:raise AssertionError('multiple successful sectors in one step')
            if c.a==1:break
            if c.a!=0 or len(steps)>75:raise AssertionError('input never completes')
        pointer=word(c,self.z['input_pointer'])
        if (word(c,self.z['block_length'])!=len(expected) or word(c,self.z['block_end'])!=(self.output+len(expected))&65535
                or word(c,self.p['compressed_length'])!=len(payload) or c.read8(self.z['block_stored'])
                or bytes(c.banks[slot][pointer-0xc000:pointer-0xc000+len(payload)])!=payload):
            raise AssertionError('input descriptor or payload differs')
        c.slot,c.payload,c.expected,c.input_start,c.output_base=slot,payload,expected,pointer,self.output
        c.produced=c.input_reads=0;c.digest=hashlib.sha256();slices=[]
        targets=list(range(256,len(expected),256))+[len(expected)]
        for i,target in enumerate(targets):
            c.decoding=False;word(c,self.z['slice_target'],(self.output+target)&65535)
            c.pc=self.z['begin' if i==0 else 'slice_until'];c.sp=STACK;c.push(STOP);c.decoding=True
            start=c.tstates;count=c.steps;irq=0
            while c.pc!=STOP:
                if c.pc==self.z['fatal'] or c.steps-count>2000000:raise AssertionError('coroutine did not return')
                c.step()
                if interrupt and c.pc!=STOP:irq+=interrupt(c)
            c.decoding=False
            if c.sp!=STACK or not target<=c.produced<=len(expected):raise AssertionError('coroutine result differs')
            slices.append(c.tstates-start-irq)
            for name in ('a','b','c','d','e','h','l','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):setattr(c,name,0x97)
            c.z=c.carry=c.alt_z=c.alt_carry=True
        _,proof=trace(payload,limit=len(expected))
        if (c.input_reads!=len(payload) or c.produced!=len(expected) or c.digest.hexdigest()!=proof['write_input_cursors_sha256']
                or bytes(c.banks[slot][self.output&16383:(self.output&16383)+len(expected)])!=expected
                or bytes(c.banks[5][:6912])!=screen or any(bytes(c.banks[b])!=v for b,v in protected.items())):
            raise AssertionError('coroutine trace/output or protected bank differs')
        row=dict(index=index,decoded_bytes=len(expected),payload_bytes=len(payload),input_pointer=pointer,
            raw_sha256=sha(expected),payload_sha256=sha(payload),begin_tstates=begin,step_tstates=steps,
            producer_tstates=begin+sum(steps),decoder_tstates=sum(slices),slice_tstates=slices,
            sectors=len(c.reads)-reads,carry_copy_bytes=self.copy_bytes-copied,exact=True)
        self.results.append(row);return row

    def finish(self):
        if [r['sector'] for r in self.cpu.reads]!=self.positions or word(self.cpu,self.d['remaining']):
            raise AssertionError('sector order/count differs')
        if any(r['count']!=1 or r['address']&255 or not (r['address']==current.CARRY and self.inplace
                or 0xc000<=r['address']<=(0xff00 if self.inplace else 0xdf00)) for r in self.cpu.reads):
            raise AssertionError('sector destination differs')
        producer=sum(r['producer_tstates'] for r in self.results);decoder=sum(r['decoder_tstates'] for r in self.results)
        if sum(t*n for (_,t),n in self.histogram.items())!=producer:raise AssertionError('producer histogram differs')
        return dict(complete=True,producer_tstates=producer,decoder_tstates=decoder,total_tstates=producer+decoder,
            sector_reads=len(self.cpu.reads),sectors_exact_once=True,carry_copy_bytes=self.copy_bytes,
            max_step_tstates=max(t for r in self.results for t in r['step_tstates']),
            instruction_histogram=[dict(address=pc,tstates=t,count=n,instruction=self.instructions[pc]['instruction'])
                for (pc,t),n in sorted(self.histogram.items())])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    a=p.parse_args();probe=json.loads((ROOT/'inplace_zx0_probe.json').read_bytes())
    build=json.loads(a.build.read_bytes())
    if not build['complete']:raise ValueError('complete integrated build required')
    report=dict(complete=False,release=False,scope=__doc__,probe_sha256=sha((ROOT/'inplace_zx0_probe.json').read_bytes()),
                build_sha256=sha(a.build.read_bytes()),idle_clock_frozen=True,variants=[])
    def save():a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        for size in (8192,15872):
            variant=dict(block_bytes=size,volumes=[]);report['variants'].append(variant)
            for source in probe['sources']:
                part=source['part'];filename=f'block{size}-part{part:02}.stream.gz'
                packed=(ROOT/'inplace_zx0_evidence'/filename).read_bytes();record=next(r for r in probe['archives'] if r['file']==filename)
                if sha(packed)!=record['sha256']:raise ValueError('stream archive changed')
                stream=gzip.decompress(packed);built=build['volumes'][part-1]
                first=source['video_start_sector'] if size==8192 else built['video_start_sector']
                if size!=8192 and sha(stream)!=built['stream_sha256']:raise ValueError('build stream differs')
                counter=built['inplace_video']['elapsed_fields']
                h=Harness(stream,first,inplace=size!=8192,elapsed_fields=counter)
                row=dict(part=part,video_start_sector=first,blocks=h.results,regions=[dict(address=at,code_hex=b.hex()) for at,b in h.regions])
                variant['volumes'].append(row);at=index=0
                while at<len(stream):
                    n,count=struct.unpack_from('<HH',stream,at);at+=4;payload=stream[at:at+count];at+=count
                    h.block(payload,decompress(payload,limit=n),index);index+=1
                    if index%20==1:save();print(f'{size}: disk {part}, {index} producer/coroutine blocks exact',flush=True)
                row['summary']=h.finish();save()
            variant['totals']={k:sum(v['summary'][k] for v in variant['volumes']) for k in
                ('producer_tstates','decoder_tstates','total_tstates','sector_reads','carry_copy_bytes')}
        report['complete']=True
    except Exception as exc:report['failure']=repr(exc);raise
    finally:
        names=('benchmark_inplace_slot.py','inplace_slot_input_z80.py','inplace_slot_player.py','test_inplace_slot.py',
            'bank2_zx0.py','bank_local_zx0.py','incremental_zx0.py','direct_slot_input_z80.py',
            'fap3_disk_z80.py','fast_return_irq.py','pipelined_frame_z80.py','benchmark_direct_slot_input.py')
        report['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names};save()
    print(json.dumps([dict(block_bytes=v['block_bytes'],**v['totals']) for v in report['variants']]),flush=True)


if __name__=='__main__':main()
