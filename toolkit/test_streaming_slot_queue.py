"""Execute streaming slots with guarded input/history and mocked TR-DOS."""
from collections import Counter
import unittest

from benchmark_bank_local_zx0 import STACK,STOP
from benchmark_context_huffman import word
from benchmark_direct_slot_input import ProducerCPU
from test_direct_slot_input import fixture,literal
from test_fap3_disk import install
from zx0_speed import Token,encode
import streaming_slot_input as producer
import streaming_slot_queue as queue
import streaming_zx0_layout as decoder
import pipelined_frame_z80 as video


BANKS=(0,1,3,4)


class StreamingCPU(ProducerCPU):
    def read8(self,address):
        if getattr(self,'decoder_active',False) and address>=0xc000:
            if self.port_7ffd&7!=BANKS[super().read8(self.producer_labels['write_region'])]:
                raise AssertionError('decoder input/history in wrong slot')
            if address<0xe000:
                end=word(self,self.producer_labels['compressed_end'])
                loaded=super().read8(self.decoder_labels['input_high'])*256
                if address!=self.input_cursor or address>=min(loaded,end):
                    raise AssertionError(('unloaded/out-of-order input',hex(address),hex(loaded),hex(end)))
                self.input_cursor+=1
            elif address>=self.output_cursor:
                raise AssertionError('decoder reads unproduced history')
        return super().read8(address)

    def write8(self,address,value):
        if getattr(self,'decoder_active',False) and address>=0xc000:
            if (self.port_7ffd&7!=BANKS[super().read8(self.producer_labels['write_region'])] or
                address!=self.output_cursor or address>=0xe000+word(self,self.decoder_labels['block_length'])):
                raise AssertionError('decoder writes outside current output')
            self.output_cursor+=1
        return super().write8(address,value)


class StreamingQueueHarness:
    def __init__(self,h,blocks):
        self.h=h;self.cpu=c=h.cpu;c.__class__=StreamingCPU;c.decoder_active=False
        zregions,z,self.layout=decoder.build();h.decoder.labels=z
        pregions,p,prows=producer.build(z,h.d,self.layout['helper_end']);h.p=p
        self.regions,self.q,qrows=queue.build(z,p,blocks,demand_decode=True)
        for address,data in zregions+pregions+self.regions:install(c,address,data)
        c.decoder_labels=z;c.producer_labels=dict(p,write_region=h.d['write_region'])
        self.decoder_ranges=[(at,at+len(blob)) for at,blob in zregions]
        self.instructions={pc:r for pc,r in h.instructions.items() if r['phase']!='direct_slot_input'}
        self.instructions.update({r['address']:r for r in prows+qrows})
        self.histogram=Counter();self.calls=[];self.copied=0;self.active_copied=0;self.phase3_copied=0
        self.pending_eof_returns=0;self.pending_eof_finishes=0
        self.copy_pcs={pc for pc,r in self.instructions.items() if r['phase']=='slot_bridge' and r['instruction']=='LDI'}

    def state(self,key):return self.cpu.banks[7][self.q[key]-0xc000]

    def call(self,entry):
        c=self.cpu;c.pc=entry;c.sp=STACK;c.push(STOP)
        start,steps,reads=c.tstates,c.steps,len(c.reads)
        while c.pc!=STOP:
            pc=c.pc
            if pc in (self.q['fatal'],self.h.p['fatal'],self.h.decoder.labels['fatal']):
                raise AssertionError(('streaming fatal',hex(pc)))
            if c.steps-steps>4000000:raise AssertionError('queue did not return')
            if pc==self.h.decoder.labels['begin']:
                c.input_cursor=word(c,self.h.decoder.labels['input_pointer']);c.output_cursor=0xe000
            if pc==self.q['finish_consumed'] and self.state('phase')==3:
                self.pending_eof_finishes+=1
            if pc in self.copy_pcs:
                slot=self.state('read_slot')
                if c.port_7ffd&7!=BANKS[slot]:raise AssertionError('consumer copied from wrong bank')
                if self.state('count'):
                    at=self.q['lengths']-0xc000+2*slot
                    available=int.from_bytes(c.banks[7][at:at+2],'little')
                else:
                    phase=self.state('phase')
                    if phase not in (2,3) or slot!=self.state('write_slot'):raise AssertionError('no active prefix')
                    available=(word(c,self.h.decoder.labels['slice_output'])-0xe000)&65535
                    self.active_copied+=1;self.phase3_copied+=phase==3
                if not 0xe000<=c.hl()<0xe000+available:
                    raise AssertionError(('consumer read unproduced byte',hex(c.hl()),available,
                        self.state('count'),self.state('phase'),word(c,self.q['position'])))
                self.copied+=1
            c.decoder_active=any(lo<=pc<hi for lo,hi in self.decoder_ranges)
            t=c.tstates;c.step();ticks=c.tstates-t;c.decoder_active=False
            if pc in self.instructions:
                row=self.instructions[pc];expected=row['tstates']
                if ticks not in (expected if isinstance(expected,list) else [expected]):
                    raise AssertionError(('wrong instruction cost',hex(pc),ticks,row))
            elif not any(lo<=pc<hi for lo,hi in self.decoder_ranges):
                raise AssertionError(('unknown instruction',hex(pc)))
            self.histogram[pc,ticks]+=1
        if c.sp!=STACK or c.port_7ffd&7!=7:raise AssertionError('queue stack/page differs')
        if entry==self.q['step'] and len(c.reads)-reads>1:raise AssertionError('step read more than one sector')
        z=self.h.decoder.labels
        if (self.state('phase')==3 and word(c,z['slice_output'])==word(c,z['block_end']) and
            word(c,self.q['position'])==word(c,z['block_length']) and not c.read8(z['finished'])):
            self.pending_eof_returns+=1
        self.calls.append((entry,c.tstates-start));return c.tstates-start

    def take(self,count):
        c=self.cpu;c.set_bc(count);c.set_de(0xa6a0);self.call(self.q['take'])
        if c.de()!=0xa6a0+count:raise AssertionError('bad copy destination')
        return bytes(c.read8(0xa6a0+i) for i in range(count))

    def finish(self,expected):
        c=self.cpu
        if self.copied!=len(expected) or self.state('count') or word(c,self.q['blocks_left']):
            raise AssertionError('incomplete consumer')
        if [r['sector'] for r in c.reads]!=self.h.positions:raise AssertionError('sector order/count differs')


class StreamingQueueTests(unittest.TestCase):
    def test_headers_shared_sectors_independent_starts_and_retry(self):
        candidates={}
        for n in range(1,520):
            payload,raw=literal(n);candidates.setdefault((len(payload)+4)%256,(payload,raw))
        for first in (32,47,53,63):
            for offset in (0,1,252,253,254,255):
                with self.subTest(first=first,offset=offset):
                    blocks=[candidates[offset],literal(1700),literal(11),literal(280),literal(1)]
                    q=StreamingQueueHarness(fixture(blocks,first),len(blocks));c=q.cpu
                    c.short_once=True;c.write8(video.SHADOW,0x1f)
                    raw=b''.join(r for _,r in blocks)
                    out=bytearray();i=0
                    while len(out)<len(raw):
                        q.call(q.q['step']);n=min((1,255,301,19)[i%4],len(raw)-len(out));i+=1
                        out+=q.take(n)
                    self.assertEqual(bytes(out),raw);q.finish(raw);self.assertEqual(c.port_7ffd&8,8)

    def test_full_queue_and_zero_consumption(self):
        blocks=[literal(n) for n in (17,1,1700,4096,2,7900,11,256)]
        q=StreamingQueueHarness(fixture(blocks),len(blocks));q.call(q.q['prefill'])
        self.assertEqual(q.state('count'),4);reads=len(q.cpu.reads)
        q.call(q.q['step']);self.assertEqual(q.cpu.a,0);self.assertEqual(len(q.cpu.reads),reads)
        self.assertEqual(q.take(0),b'')
        raw=b''.join(r for _,r in blocks);out=bytearray()
        while len(out)<len(raw):out+=q.take(min(1977,len(raw)-len(out)))
        self.assertEqual(bytes(out),raw);q.finish(raw)

    def test_output_end_with_pending_eof_never_copies_zero_length(self):
        raw=bytes(range(256))*32;payload=encode(raw,[Token(0,600),Token(600,len(raw)-600,256)])
        candidates={}
        for n in range(1,520):
            p,r=literal(n);candidates.setdefault((len(p)+4)%256,(p,r))
        # Visit all source alignments, requesting the next block immediately
        # after consuming the full output of a still input-suspended block.
        pending_eof=0
        for offset in range(256):
            blocks=[candidates[offset],(payload,raw),literal(1)]
            q=StreamingQueueHarness(fixture(blocks),len(blocks));wanted=b''.join(r for _,r in blocks)
            out=bytearray()
            for _,r in blocks:
                for lo in range(0,len(r),3000):out+=q.take(min(3000,len(r)-lo))
            self.assertEqual(bytes(out),wanted);q.finish(wanted)
            pending_eof+=q.pending_eof_finishes
            self.assertEqual(q.pending_eof_returns,0)
        self.assertGreater(pending_eof,0)


if __name__=='__main__':unittest.main()
