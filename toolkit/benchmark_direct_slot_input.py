"""Execute direct-sector input and resumable ZX0 over every current TRD block.

Disk services are mocked; their CALL/JP instruction costs are counted, ROM,
IRQ/ULA and physical latency are excluded. Host releases a slot and requests
decoder quotas, but Z80 parses headers, advances sectors and carries the
shared sector. All reads/copies use one shared CPU/RAM instance. This is a
producer/core experiment, not the frame scheduler or a release measurement.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import bank_local_zx0 as local
import direct_slot_input_z80 as producer
import fap3_disk_z80 as disk
import pipelined_frame_z80 as video
from benchmark_bank_local_zx0 import Harness as Decoder,GuardCPU,disk_blocks,sha,STACK,STOP
from benchmark_context_huffman import word
from benchmark_fap3_disk import ShortReadCPU
from test_fap3_disk import install
import disk_layout

BANKS=(0,1,3,4)


class ProducerCPU(ShortReadCPU):
    def mock_trdos(self):
        if self.c==5:
            self.reads.append(dict(sector=self.d*16+self.e,bank=self.port_7ffd&7,address=self.hl(),count=self.b))
        super().mock_trdos()


class Harness:
    def __init__(self,image,first,sectors,*,inline_literals=False):
        self.decoder=Decoder(dynamic_input=True,inline_literals=inline_literals)
        old=self.decoder.cpu
        cpu=self.cpu=ProducerCPU(b'',image);cpu.__dict__.update(old.__dict__)
        cpu.trd=image;cpu.iy=0;cpu.poison_rom=True;cpu.reads=[];cpu.short_once=False
        cpu.guarding=False;cpu.port_7ffd=0x17
        self.decoder.cpu=cpu
        regions,_,vrows=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),
            dict(history_page=0x8002),dict(elapsed_fields=0x8003),irq_safe_paging=True)
        for address,blob in regions:install(cpu,address,blob)
        cpu.write8(video.SHADOW,0x17)
        code,self.d,drows=disk.build_disk(first,sectors,fast_disk=True,cached_seek=True,interleaved=True)
        install(cpu,disk.DISK,code)
        code,_,seekrows=disk.build_cached_seek(self.d);install(cpu,disk.CACHED_SEEK,code)
        self.code,self.p,prows=producer.build(self.decoder.labels,self.d);install(cpu,producer.CODE,self.code)
        self.instructions={r['address']:r for r in vrows+drows+seekrows+prows}
        self.histogram=Counter();self.copy_bytes=0;self.results=[]
        cpu.write8(0x5cf5,first//16);cpu.write8(0x5cf6,0);cpu.write8(0x5cfa,0x80)
        self.positions=[first+p for p in disk_layout.positions(sectors,first%16)]

    def call(self,entry):
        cpu=self.cpu;cpu.pc=entry;cpu.sp=STACK;cpu.push(STOP)
        start,steps=cpu.tstates,cpu.steps
        while cpu.pc!=STOP:
            if cpu.pc in (self.p['fatal'],self.decoder.labels['fatal']) or cpu.steps-steps>100000:
                raise AssertionError(('producer failed',hex(cpu.pc)))
            pc,before=cpu.pc,cpu.tstates;cpu.step();ticks=cpu.tstates-before
            row=self.instructions[pc];wanted=row['tstates']
            if ticks not in (wanted if isinstance(wanted,list) else [wanted]):
                raise AssertionError(('instruction timing',pc,ticks,wanted))
            self.histogram[pc,ticks]+=1
            if row['phase']=='direct_slot_input' and row['instruction']=='LDI':self.copy_bytes+=1
        if cpu.sp!=STACK:raise AssertionError('producer stack changed')
        return cpu.tstates-start

    def block(self,payload,expected,index,*,short=False):
        cpu=self.cpu;cpu.__class__=ProducerCPU;cpu.guarding=False
        slot=BANKS[index%4];other={b:bytes(cpu.banks[b]) for b in range(8) if b not in (slot,2,5)}
        screen=bytes(cpu.banks[5][:6912]);prior_output=bytes(cpu.banks[slot][8192:])
        reads=len(cpu.reads);copied=self.copy_bytes
        cpu.a=index%4;start=self.call(self.p['begin']);steps=[]
        cpu.short_once=short
        while True:
            before=len(cpu.reads);t=self.call(self.p['step']);steps.append(t)
            if len(cpu.reads)-before>1:raise AssertionError('more than one successful sector per step')
            if cpu.a==1:break
            if cpu.a!=0 or len(steps)>35:raise AssertionError('input did not complete')
        z=self.decoder.labels
        pointer=word(cpu,z['input_pointer']);length=word(cpu,self.p['compressed_length'])
        if (length!=len(payload) or word(cpu,z['block_length'])!=len(expected)
                or word(cpu,z['block_end'])!=(0xe000+len(expected))&65535
                or cpu.read8(z['block_stored']) or not 0xc000<=pointer<=0xe000-len(payload)):
            raise AssertionError('Z80 block descriptor differs')
        if (bytes(cpu.banks[slot][8192:])!=prior_output or bytes(cpu.banks[5][:6912])!=screen
                or any(bytes(cpu.banks[b])!=blob for b,blob in other.items())):
            raise AssertionError('producer damaged decoded slots or screens')
        cpu.__class__=GuardCPU
        self.decoder.begin(payload,expected,slot=slot,screen_bit=cpu.port_7ffd&8,
            input_offset=pointer-0xc000,preloaded=True)
        for target in list(range(256,len(expected),256))+[len(expected)]:self.decoder.run(target)
        result=self.decoder.finish()
        row=dict(index=index,slot=slot,raw_bytes=len(expected),compressed_bytes=len(payload),input_offset=pointer-0xc000,
            producer_tstates=start+sum(steps),begin_tstates=start,step_tstates=steps,
            sector_reads=len(cpu.reads)-reads,carry_copy_bytes=self.copy_bytes-copied,
            decoder_tstates=result['tstates'],decoder_slices=result['slices'],
            raw_sha256=sha(expected),compressed_sha256=sha(payload))
        self.results.append(row)
        return row

    def finish(self):
        actual=[r['sector'] for r in self.cpu.reads]
        if (actual!=self.positions or len(set(actual))!=len(actual)
                or word(self.cpu,self.d['remaining'])
                or any(r['count']!=1 or r['address']&255 or not 0xc000<=r['address']<0xe000 for r in self.cpu.reads)):
            raise AssertionError('sector order, count, destination or EOF differs')
        stages=Counter()
        for (pc,t),n in self.histogram.items():stages[self.instructions[pc]['phase']]+=t*n
        if sum(stages.values())!=sum(r['producer_tstates'] for r in self.results):raise AssertionError('histogram differs')
        return dict(producer_stages=dict(stages),sector_reads=len(actual),unique_sectors=len(set(actual)),
            sectors_exact_once_in_original_order=True,carry_copy_bytes=self.copy_bytes,
            producer_tstates=sum(stages.values()),decoder_tstates=sum(r['decoder_tstates'] for r in self.results),
            max_step_cpu_tstates=max(t for r in self.results for t in r['step_tstates']),
            input_end_max=max(r['input_offset']+r['compressed_bytes'] for r in self.results))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('directory','baseline','output'):p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();baseline=json.loads(args.baseline.read_bytes())
    if not baseline['complete']:raise ValueError('partial baseline')
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='03013e3',
        baseline_report_sha256=sha(args.baseline.read_bytes()),player_changed=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',rom_execution_verified=False,
        actual_publication_verified=False,volumes=[])
    def save():args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    for part in (1,2,3):
        meta,stream,blocks=disk_blocks(args.directory,part)
        image=(args.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        before=baseline['volumes'][part-1]
        if before['stream_sha256']!=sha(stream) or before['trd_sha256']!=sha(image):raise ValueError('different baseline stream')
        h=Harness(image,meta['video_start_sector'],meta['video_sectors'])
        row=dict(part=part,trd_sha256=sha(image),stream_sha256=sha(stream),stream_bytes=len(stream),
            decoder_code_bytes=len(h.decoder.code),producer_code_bytes=len(h.code),producer_labels=h.p,blocks=h.results)
        report['volumes'].append(row)
        for i,(payload,raw) in enumerate(blocks):
            r=h.block(payload,raw,i)
            if r['decoder_tstates']!=before['blocks'][i]['tstates']+6:
                raise AssertionError('dynamic input pointer must add exactly 6 T per block')
            if i%25==0:save();print(f'Direct sectors and exact ZX0: disk {part}, block {i+1}/{len(blocks)}',flush=True)
        row['summary']=h.finish();row['read_log']=h.cpu.reads
        row['instruction_histogram']=[dict(address=pc,tstates=t,count=n) for (pc,t),n in sorted(h.histogram.items())]
        print(json.dumps(dict(part=part,**row['summary'])),flush=True)
    report['complete']=True;save()


if __name__=='__main__':main()
