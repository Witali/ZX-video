"""Execute real one-sector production interleaved with guarded in-place ZX0.

Compare complete input with page-suspended input for identical 15872-byte
blocks and sector positions. ROM is mocked; no frame queue, AY service,
ULA or physical disk latency is simulated. No cadence pass is inferred.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct

from benchmark_inplace_slot import Harness as CompleteInput, SlotCPU
from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from build_fap3_trd import sha
from inplace_zx0 import trace
from test_fap3_disk import install
from zx0_codec import decompress
from verify_streaming_zx0_input import validate_histogram
import inplace_streaming_core as machine

ROOT=Path(__file__).parent


class CountedCPU(SlotCPU):
    def step(self):
        decoding=self.decoding;pc=self.pc;before=self.tstates
        result=super().step()
        if decoding:self.decoder_histogram[pc,self.tstates-before]+=1
        return result


class StreamingCPU(CountedCPU):
    def read8(self,address):
        if (self.decoding and address==self.input_start+self.input_reads
                and self.input_reads<len(self.payload) and address>=self.loaded_until):
            raise AssertionError('decoder reads an unloaded input page')
        return super().read8(address)


class Harness(CompleteInput):
    def __init__(self,stream,first):
        super().__init__(stream,first,inplace=True)
        c=self.cpu;c.__class__=StreamingCPU;c.decoder_histogram=Counter()
        regions,self.z,self.layout=machine.decoder()
        for at,data in regions:install(c,at,data)
        regions,self.p,rows=machine.input_prefix(self.z,self.d,elapsed_fields=self.elapsed_fields,origin=self.layout['helper_end'])
        for at,data in regions:install(c,at,data)
        self.regions=regions;self.instructions.update({r['address']:r for r in rows})
        c.zlabels=self.z;c.patched={self.z[n] for n in ('slice_high_operand','slice_low_operand','slice_equal_branch',
            'match_high_operand','match_low_operand','match_equal_branch')}
        c.patched.update((self.z['dzx0t_last_offset']+1,self.z['dzx0t_last_offset']+2))

    def block(self,payload,expected,index,*,short=False,interrupt=None):
        c=self.cpu;c.decoding=False;slot=(0,1,3)[index%3]
        protected={b:bytes(c.banks[b]) for b in (0,1,3,4,6,7) if b!=slot};screen=bytes(c.banks[5][:6912])
        reads=len(c.reads);copied=self.copy_bytes;c.a=index%3
        begin=self.call(self.p['begin'],interrupt);steps=[];c.short_once=short
        c.slot,c.payload,c.expected,c.output_base=slot,payload,expected,0xc000
        c.produced=c.input_reads=0;c.digest=hashlib.sha256();slices=[];waits=[];first_loaded=None
        def supply():
            before=len(c.reads)
            old_output=bytes(c.banks[slot][:c.produced])
            steps.append(self.call(self.p['step'],interrupt))
            if len(c.reads)-before>1:raise AssertionError('multiple sectors per prefix step')
            if bytes(c.banks[slot][:c.produced])!=old_output:raise AssertionError('sector supply overwrites produced output')
            if c.a not in (0,1) or len(steps)>80:raise AssertionError('prefix input never completes')
            if c.a:
                high=c.read8(self.z['input_high']);c.loaded_until=high*256 if high else 65536
                if (word(c,self.z['block_length'])!=len(expected) or word(c,self.z['block_end'])!=0xc000+len(expected)
                        or word(c,self.p['compressed_length'])!=len(payload)):raise AssertionError('descriptor differs')
                return True
            return False
        while not supply():pass
        c.input_start=word(c,self.z['input_pointer'])
        targets=list(range(256,len(expected),256))+[len(expected)];first=True
        for target in targets:
            while True:
                c.decoding=False;word(c,self.z['slice_target'],0xc000+target)
                c.pc=self.z['begin' if first else 'slice_until'];first=False
                c.sp=STACK;c.push(STOP);c.decoding=True;start=c.tstates;count=c.steps;irq=0
                while c.pc!=STOP:
                    if c.pc==self.z['fatal'] or c.steps-count>2000000:raise AssertionError('streaming coroutine did not return')
                    c.step()
                    if interrupt and c.pc!=STOP:irq+=interrupt(c)
                c.decoding=False
                needed=c.read8(self.z['input_needed']);finished=c.read8(self.z['finished'])
                if c.sp!=STACK or not 0<=c.produced<=len(expected) or (not needed and c.produced<target):
                    raise AssertionError('coroutine suspension differs')
                if first_loaded is None and c.produced:
                    first_loaded=min(c.loaded_until-c.input_start,len(payload))
                slices.append(c.tstates-start-irq)
                for name in ('a','b','c','d','e','h','l','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):
                    setattr(c,name,0x97)
                c.z=c.carry=c.alt_z=c.alt_carry=True
                if not needed:break
                if c.read8(self.z['all_loaded']):raise AssertionError('wait after all input loaded')
                waits.append(dict(produced=c.produced,input_read=c.input_reads,target=target,sectors_so_far=len(c.reads)-reads))
                if not supply():raise AssertionError('lost established prefix')
        _,proof=trace(payload,limit=len(expected))
        if (not finished or c.read8(self.p['phase'])!=2 or c.input_reads!=len(payload) or c.produced!=len(expected)
                or c.digest.hexdigest()!=proof['write_input_cursors_sha256'] or bytes(c.banks[slot][:len(expected)])!=expected
                or bytes(c.banks[5][:6912])!=screen or any(bytes(c.banks[b])!=v for b,v in protected.items())):
            raise AssertionError('final output, trace, carry or protected banks differ')
        row=dict(index=index,decoded_bytes=len(expected),payload_bytes=len(payload),input_pointer=c.input_start,
            raw_sha256=sha(expected),payload_sha256=sha(payload),begin_tstates=begin,step_tstates=steps,
            producer_tstates=begin+sum(steps),decoder_tstates=sum(slices),slice_tstates=slices,
            sectors=len(c.reads)-reads,carry_copy_bytes=self.copy_bytes-copied,exact=True,
            input_waits=waits,first_output_loaded_bytes=first_loaded)
        self.results.append(row);return row


def finish(h):
    result=h.finish();c=h.cpu;rows=[];total=0
    for (pc,t),count in sorted(c.decoder_histogram.items()):
        # Only the opcode and optional ED/CB prefix affect this timing table.
        code=bytes((c.read8(pc),c.read8(pc+1)))
        row=dict(pc=pc,tstates=t,count=count,opcode_hex=code.hex())
        total+=validate_histogram(code,pc,[row]);rows.append(row)
    if total!=result['decoder_tstates']:raise AssertionError('decoder instruction table sum differs')
    result.update(decoder_instruction_histogram=rows,decoder_instruction_table_checked=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    build_path=ROOT/'inplace_keepalive_build.json';build=json.loads(build_path.read_bytes())
    streaming_path=ROOT/'inplace_streaming_build.json';streaming=json.loads(streaming_path.read_bytes())
    if not build['complete'] or not streaming['complete']:raise ValueError('complete builds required')
    probe_path=ROOT/'inplace_zx0_probe.json';probe=json.loads(probe_path.read_bytes())
    report=dict(complete=False,release=False,scope=__doc__,build_sha256=sha(build_path.read_bytes()),
        streaming_build_sha256=sha(streaming_path.read_bytes()),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',idle_clock_frozen=True,
        probe_sha256=sha(probe_path.read_bytes()),volumes=[])
    def save():a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        for v in build['volumes']:
            part=v['part'];name=f'block15872-part{part:02}.stream.gz'
            packed=(ROOT/'inplace_zx0_evidence'/name).read_bytes();entry=next(x for x in probe['archives'] if x['file']==name)
            if sha(packed)!=entry['sha256']:raise ValueError('source archive changed')
            stream=gzip.decompress(packed)
            if sha(stream)!=v['stream_sha256']:raise ValueError('different stream')
            built=streaming['volumes'][part-1]
            if built['stream_sha256']!=sha(stream):raise ValueError('different streaming build input')
            old=CompleteInput(stream,v['video_start_sector'],inplace=True)
            old.cpu.__class__=CountedCPU;old.cpu.decoder_histogram=Counter()
            new=Harness(stream,built['video_start_sector'])
            row=dict(part=part,baseline=old.results,streaming=new.results,stream_sha256=sha(stream),
                video_start_sector=v['video_start_sector'],decoder_layout=new.layout,
                streaming_video_start_sector=built['video_start_sector'],
                producer_regions=[dict(address=at,code_hex=data.hex()) for at,data in new.regions])
            report['volumes'].append(row);at=index=0
            while at<len(stream):
                n,count=struct.unpack_from('<HH',stream,at);at+=4;payload=stream[at:at+count];at+=count
                raw=decompress(payload,limit=n);old.block(payload,raw,index);new.block(payload,raw,index);index+=1
                if index%16==1:save();print(f'disk {part}: {index} complete/streamed blocks exact',flush=True)
            row['baseline_summary']=finish(old);row['streaming_summary']=finish(new);save()
        keys=('producer_tstates','decoder_tstates','total_tstates','sector_reads','carry_copy_bytes')
        report['totals']={name:{k:sum(v[name+'_summary'][k] for v in report['volumes']) for k in keys} for name in ('baseline','streaming')}
        report['complete']=True
    except Exception as exc:report['failure']=repr(exc);raise
    finally:
        names=('benchmark_inplace_streaming.py','inplace_streaming_core.py','test_inplace_streaming.py',
            'benchmark_inplace_slot.py','inplace_slot_input_z80.py','streaming_zx0_layout.py','streaming_inline_zx0.py',
            'incremental_zx0.py','fap3_disk_z80.py','validate_fast_sparse.py','verify_streaming_zx0_input.py')
        report['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names};save()
    print(json.dumps(report['totals']),flush=True)


if __name__=='__main__':main()
