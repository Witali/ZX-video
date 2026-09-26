"""Execute input-page-suspending ZX0 against exact TRD blocks.

Standalone CPU cost only. Host page supply is NOT disk execution, paging,
the packet queue, or an elapsed playback forecast. Baseline has all input
loaded and the same output requests. Both must consume exactly the same
compressed bytes and reproduce every output byte with protected RAM intact.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from benchmark_bank_local_zx0 import Harness as Baseline,GuardCPU,STACK,STOP,disk_blocks,sha
from benchmark_context_huffman import word
import streaming_local_zx0 as machine


class InputGuardCPU(GuardCPU):
    def read8(self,address):
        if self.guarding and machine.INPUT<=address<machine.OUTPUT and address>=self.loaded_until:
            raise AssertionError(('unloaded input read',hex(address),hex(self.loaded_until)))
        return super().read8(address)


class CountingCPU(GuardCPU):
    def step(self):
        pc,t=self.pc,self.tstates
        super().step()
        self.histogram[pc,self.tstates-t]+=1


class Harness(Baseline):
    def __init__(self):
        super().__init__(dynamic_input=True)
        self.code,self.labels=machine.build()
        c=self.cpu;c.__class__=InputGuardCPU;c.labels=self.labels
        c.patched={self.labels[n] for n in ('slice_high_operand','slice_low_operand',
            'slice_equal_branch','match_high_operand','match_low_operand','match_equal_branch')}
        c.patched.update((self.labels['dzx0t_last_offset']+1,self.labels['dzx0t_last_offset']+2))
        for i,value in enumerate(self.code):c.write8(machine.CODE+i,value)

    def begin(self,payload,expected,*,input_offset=0,slot=1,screen_bit=0,preload=False):
        super().begin(payload,expected,input_offset=input_offset,slot=slot,screen_bit=screen_bit)
        c=self.cpu
        c.banks[slot][input_offset:input_offset+len(payload)]=b'\xa5'*len(payload)
        c.loaded_until=c.input_start&0xff00
        self.input_waits=0;self.supplied_pages=0;self.histogram=Counter()
        self.input_wait_output=[];self.first_output_loaded_bytes=None
        c.write8(self.labels['input_needed'],0);c.write8(self.labels['finished'],0)
        self.supply()
        if preload:
            while c.loaded_until<c.input_start+len(payload):self.supply()

    def supply(self):
        c=self.cpu
        if c.loaded_until>=c.input_start+len(c.payload):raise AssertionError('unnecessary input request after EOF')
        end=min(c.loaded_until+256,c.input_start+len(c.payload))
        first=max(c.loaded_until,c.input_start)
        c.banks[c.slot][first-machine.INPUT:end-machine.INPUT]=c.payload[first-c.input_start:end-c.input_start]
        c.loaded_until=(end+255)&0xff00
        c.write8(self.labels['input_high'],c.loaded_until>>8)
        c.write8(self.labels['all_loaded'],int(end==c.input_start+len(c.payload)))
        self.supplied_pages+=1

    def run(self,target,interrupt=None):
        if not self.last_target<=target<=len(self.expected):raise ValueError('nonmonotonic target')
        c=self.cpu;c.guarding=False
        word(c,self.labels['slice_target'],(machine.OUTPUT+target)&65535)
        c.pc=self.labels['begin' if self.first else 'resume']
        c.sp=STACK;c.push(STOP);c.guarding=True
        before,steps,irq=c.tstates,c.steps,0
        produced_before=c.produced
        while c.pc!=STOP:
            if c.pc==self.labels['fatal'] or c.steps-steps>2_000_000:raise AssertionError('decoder did not return')
            pc,t=c.pc,c.tstates;c.step();self.histogram[pc,c.tstates-t]+=1
            if interrupt and c.pc!=STOP:irq+=interrupt(c)
        c.guarding=False
        needed=c.read8(self.labels['input_needed']);finished=c.read8(self.labels['finished'])
        if (c.sp!=STACK or c.port_7ffd!=self.page or not 0<=c.produced<=len(self.expected)
                or bytes(c.banks[c.slot][8192:8192+c.produced])!=self.expected[:c.produced]
                or (not needed and c.produced<target)):
            raise AssertionError('output, stack, page or suspend contract differs')
        if finished and (needed or c.produced!=len(self.expected) or c.input_reads!=len(c.payload)):
            raise AssertionError('premature EOF')
        if needed:
            if c.loaded_until>=c.input_start+len(c.payload):raise AssertionError('waiting for absent page')
            self.input_waits+=1;self.input_wait_output.append(c.produced)
        if self.first_output_loaded_bytes is None and c.produced>produced_before:
            self.first_output_loaded_bytes=min(c.loaded_until-c.input_start,len(c.payload))
        elapsed=c.tstates-before-irq;self.total+=elapsed;self.first=False;self.last_target=target
        self.slices.append(dict(target=target,produced=c.produced,input_read=c.input_reads,
            loaded_bytes=min(c.loaded_until-c.input_start,len(c.payload)),input_needed=bool(needed),
            finished=bool(finished),tstates=elapsed,irq_tstates=irq))
        for name in ('a','b','c','d','e','h','l','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):
            setattr(c,name,0x97)
        c.z=c.carry=c.alt_z=c.alt_carry=True
        return elapsed

    def finish(self):
        if not self.cpu.read8(self.labels['finished']):raise AssertionError('EOF was not consumed')
        result=super().finish()
        if sum(t*n for (_,t),n in self.histogram.items())!=self.total:raise AssertionError('CPU histogram differs')
        return dict(result,input_waits=self.input_waits,supplied_pages=self.supplied_pages,
            input_wait_output=self.input_wait_output,first_output_loaded_bytes=self.first_output_loaded_bytes)

    def decode(self,quantum=256,interrupt=None):
        c=self.cpu
        for target in list(range(quantum,len(self.expected),quantum))+[len(self.expected)]:
            self.run(target,interrupt)
            while c.read8(self.labels['input_needed']):
                self.supply();self.run(target,interrupt)
        return self.finish()


def histogram_rows(counts):
    return [dict(pc=pc,tstates=t,count=count) for (pc,t),count in sorted(counts.items())]


def first_stall_probe(blocks,prior):
    """Same packet boundary, with no claim that the new schedule reaches it."""
    entry=prior['packet_entry'];call=prior['queue_call']
    if entry['phase']!=2 or entry['count']!=0:raise ValueError('unsupported reference frontier')
    active=len(blocks)-entry['blocks_left'];remaining=len(blocks[active][1])-entry['position']
    if call['copied_bytes']<=remaining:
        if call['sectors']:raise ValueError('unexpected disk within fully loaded old input')
        return dict(crosses_block=False,reference_sectors=0)
    next_block=active+1;target=call['copied_bytes']-remaining
    payload,raw=blocks[next_block]
    if not 0<target<=len(raw):raise ValueError('probe crosses more than one new block')
    start=sum(4+len(p) for p,_ in blocks[:next_block]);header_offset=start%256
    offset=header_offset+4;carried_page=int(header_offset!=0)
    full_reads=(offset+len(payload)+255)//256-carried_page
    if full_reads!=call['sectors']:raise ValueError('reference whole-input read count differs')
    h=Harness();h.begin(payload,raw,input_offset=offset)
    h.run(target)
    while h.cpu.read8(h.labels['input_needed']):h.supply();h.run(target)
    reads=(h.cpu.loaded_until-machine.INPUT)//256-carried_page
    return dict(crosses_block=True,local_frame=call['local_frame'],old_block=active,
        next_block=next_block,bytes_from_old=remaining,requested_new_output=target,
        produced_new_output=h.cpu.produced,compressed_bytes=len(payload),input_offset=offset,
        compressed_bytes_read=h.cpu.input_reads,loaded_prefix_bytes=min(h.cpu.loaded_until-h.cpu.input_start,len(payload)),
        reference_sectors=full_reads,prototype_prefix_sectors=reads,
        prefix_decoder_cpu_tstates=h.total,physical_io_or_full_schedule_simulated=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True,type=Path)
    p.add_argument('--output',default=Path('toolkit/streaming_zx0_input_cpu.json'),type=Path)
    a=p.parse_args();base=Baseline(dynamic_input=True,inline_literals=True);new=Harness()
    base.cpu.__class__=CountingCPU
    prior_path=Path(__file__).with_name('zero_mask_history_profile.json')
    prior=json.loads(prior_path.read_bytes())
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='d4f31df',
        integrated=False,new_fuse_execution=False,extra_stream_bytes=0,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        starvation_profile_sha256=sha(prior_path.read_bytes()),
        sources={n:sha((Path(__file__).parent/n).read_bytes()) for n in
            ('benchmark_streaming_zx0_input.py','streaming_local_zx0.py','incremental_zx0.py','zx0_codec.py',
             'bank_local_zx0.py','benchmark_bank_local_zx0.py','validate_fast_sparse.py',
             'benchmark_compact_screen.py','benchmark_context_huffman.py','third_party/zx0/dzx0_turbo.asm')},
        baseline_code_bytes=len(base.code),prototype_code_bytes=len(new.code),
        baseline_code_sha256=sha(base.code),prototype_code_sha256=sha(new.code),
        baseline_code_hex=base.code.hex(),prototype_code_hex=new.code.hex(),
        baseline_labels=base.labels,prototype_labels=new.labels,volumes=[])
    def save():a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    for part in (1,2,3):
        m,stream,blocks=disk_blocks(a.directory,part);rows=[];position=0
        old_hist=Counter();new_hist=Counter()
        for i,(payload,raw) in enumerate(blocks):
            offset=position%256+4;position+=4+len(payload)
            # Supply a single compressed input page initially, with all later
            # pages physically poisoned. The page guard checks every read.
            new.begin(payload,raw,input_offset=offset,slot=(0,1,3,4)[i%4])
            result=new.decode()
            base.begin(payload,raw,input_offset=offset,slot=(0,1,3,4)[i%4])
            base.cpu.histogram=Counter()
            for target in range(256,len(raw),256):base.run(target)
            base.run(len(raw));old=base.finish()
            if sum(t*n for (_,t),n in base.cpu.histogram.items())!=old['tstates']:
                raise AssertionError('baseline histogram differs')
            old_hist.update(base.cpu.histogram);new_hist.update(new.histogram)
            row=dict(block=i,decoded_bytes=len(raw),compressed_bytes=len(payload),input_offset=offset,
                raw_sha256=sha(raw),compressed_sha256=sha(payload),baseline_tstates=old['tstates'],
                prototype_tstates=result['tstates'],delta_tstates=result['tstates']-old['tstates'],
                input_waits=result['input_waits'],input_wait_output=result['input_wait_output'],
                first_output_loaded_bytes=result['first_output_loaded_bytes'],supplied_pages=result['supplied_pages'],
                private_stack_bytes=result['private_stack_bytes'],slices=result['slices'])
            rows.append(row)
            if (i+1)%16==0:print(f'part {part}: {i+1}/{len(blocks)} blocks exact',flush=True)
        v=dict(part=part,frames=m['frames'],trd_sha256=m['trd_sha256'],stream_sha256=sha(stream),
            blocks=rows,all_bytes_exact=True,input_reads_guarded=True,
            totals={key:sum(r[key] for r in rows) for key in
                ('decoded_bytes','compressed_bytes','baseline_tstates','prototype_tstates','delta_tstates','input_waits')},
            blocks_produce_before_whole_input=sum(r['first_output_loaded_bytes']<r['compressed_bytes'] for r in rows),
            max_private_stack_bytes=max(r['private_stack_bytes'] for r in rows),
            baseline_instruction_histogram=histogram_rows(old_hist),
            prototype_instruction_histogram=histogram_rows(new_hist),
            first_starvation_prefix=first_stall_probe(blocks,prior['volumes'][part-1]['first_starvation']))
        report['volumes'].append(v);save();print(json.dumps({k:v[k] for k in ('part','totals','blocks_produce_before_whole_input')}),flush=True)
    report.update(complete=True,blocks=sum(len(v['blocks']) for v in report['volumes']))
    save()


if __name__=='__main__':main()
