"""Execute the complete separately compiled decoder; no Spectrum-player claims."""
from collections import Counter
import hashlib
from pathlib import Path
import re
import numpy as np
from z80 import Z80Machine
from benchmark_z80_c_compilers import hex_image,timing
from benchmark_lzma_z80 import put_word,word
from g726.codec import pack

CPU=3546900


class Decoder:
    def __init__(self,folder):
        self.folder=Path(folder)
        mapping=(self.folder/'decoder.map').read_text()
        self.symbols={name:int(addr,16) for addr,name in re.findall(r'([0-9A-F]{8})\s+([_\w]+)',mapping)}
        self.image=hex_image(self.folder/'decoder.ihx')
        self.entry=self.symbols['_entry'];self.decode=self.symbols['_g726_decode_one']
        assert self.symbols['s__DATA']==0x8000 and self.symbols['l__DATA']==100
        self.m=Z80Machine();self.m.memory[:]=bytes([0xa5])*65536
        for addr,b in self.image.items():self.m.memory[addr]=b
        self.calls=[];self.returns=[];self.low_stack=0xff00
        self.total=0;self.budget=500_000_000
        target=bytes([0xcd,self.decode&255,self.decode>>8])
        caller=bytes(self.m.memory[self.entry:self.entry+1024])
        at=caller.find(target);assert at>=0
        self.call_pc=self.entry+at;self.return_pc=self.call_pc+3
        self.m.mark_addrs(0,65536,self.m.READ_MARK|self.m.WRITE_MARK)
        for addr in self.image:self.m.unmark_addr(addr,self.m.READ_MARK)
        for lo,hi in ((0x8000,0x8064),(0x8f00,0x8f84),(0xf700,0xff00)):
            self.m.unmark_addrs(lo,hi-lo,self.m.READ_MARK)
        self.m.unmark_addrs(0x8000,100,self.m.WRITE_MARK)
        self.m.mark_addr(self.call_pc,self.m.READ_MARK)
        self.m.mark_addr(self.return_pc,self.m.READ_MARK)
        self.m.set_read_callback(self.read);self.m.set_write_callback(self.write)
        self.m.set_breakpoint(0x100)

    def read(self,addr):
        now=self.total+self.budget-self.m.ticks_to_stop
        if addr==self.call_pc:self.calls.append(now)
        elif addr==self.return_pc:self.returns.append(now)
        elif not (0xa000<=addr<self.output_end):
            raise AssertionError(('unexpected read',hex(addr),hex(self.m.pc)))
        return self.m.memory[addr]

    def write(self,addr,value):
        if 0xf700<=addr<0xff00:self.low_stack=min(self.low_stack,addr)
        elif not (0xa000<=addr<self.output_end or 0x8f00<=addr<0x8f84):
            raise AssertionError(('unexpected write',hex(addr),hex(self.m.pc)))
        self.m.memory[addr]=value

    def block(self,codes,reset=False,audit=False):
        assert 0<len(codes)<=4096 and len(codes)%4==0
        m=self.m;self.output_end=0xa000+len(codes)*2
        data=pack(codes);m.set_memory_block(0x9000,data)
        m.mark_addrs(0x9000,0x1000,m.READ_MARK)
        m.unmark_addrs(0x9000,len(data),m.READ_MARK)
        for i,value in enumerate((0x9000,len(codes),0xa000,int(reset),0xffff,0xffff,0)):
            put_word(m,0x8f00+i*2,value)
        put_word(m,0xfefe,0x100);m.pc=self.entry;m.sp=0xfefe
        m.ix=0x1234;m.iy=0x5678;m.ticks_to_stop=self.budget
        audited=0;hist=Counter()
        while m.pc!=0x100:
            if audit:
                pc=m.pc;expected=timing(m);before=m.frame_tick
                m.ticks_to_stop=5 if m.memory[pc] in (0xdd,0xfd) else 1
            events=m.run()
            if audit:
                actual=(m.frame_tick-before)%100000
                if m.memory[pc] in (0xdd,0xfd) and actual==4 and m.pc==pc+1:
                    before=m.frame_tick;m.ticks_to_stop=1;m.run();actual+=(m.frame_tick-before)%100000
                assert actual==expected,('instruction timing',hex(pc),actual,expected)
                audited+=actual;hist[expected]+=1
            elif events&m._TICKS_LIMIT_HIT:raise AssertionError(('timeout',hex(m.pc)))
        elapsed=audited if audit else self.budget-m.ticks_to_stop
        self.total+=elapsed
        # SDCC preserves IX/SP here, but is allowed to use IY as scratch.
        # A future Spectrum caller must save any live IY value itself.
        assert m.sp==0xff00 and m.ix==0x1234
        assert word(m,0x8f08)==len(codes) and word(m,0x8f0a)==0 and word(m,0x8f0c)==100
        pcm=np.frombuffer(bytes(m.memory[0xa000:self.output_end]),'<i2')
        state=bytes(m.memory[0x8f20:0x8f84])
        return pcm,state,dict(tstates=elapsed,instructions=sum(hist.values()),
            instruction_tstate_histogram=dict(sorted(hist.items())),every_instruction_audited=audit,
            iy_clobbered=m.iy!=0x5678)


def verify(folder,codes,codec,chunk=4096,audit_count=32):
    """All output samples and state after every chunk, plus an instruction audit."""
    m=Decoder(folder);state=codec.state();parts=[]
    for start in range(0,len(codes),chunk):
        block=codes[start:start+chunk]
        expected,state=codec.decode(block,state)
        actual,raw,counts=m.block(block,reset=start==0)
        np.testing.assert_array_equal(actual,expected,err_msg=f'Z80 output at sample {start}')
        assert raw==state.raw,('state differs',start,raw.hex(),state.raw.hex())
        parts.append(counts['tstates'])
    cost=np.asarray(m.returns,dtype=np.int64)-np.asarray(m.calls,dtype=np.int64)-17
    assert len(cost)==len(codes) and np.all(cost>0)
    audit_machine=Decoder(folder)
    _,_,audit=audit_machine.block(codes[:audit_count],reset=True,audit=True)
    plain=Decoder(folder);_,_,counter=plain.block(codes[:audit_count],reset=True)
    assert audit['tstates']==counter['tstates']
    return dict(complete=True,pcm_samples_verified=len(codes),state_checkpoints=len(parts),
        all_output_samples_exact=True,all_checkpoint_states_exact=True,memory_guards_passed=True,
        code_and_constants_bytes=len(m.image),state_bytes=100,stack_bytes=0xff00-m.low_stack,
        decode_core_tstates=dict(minimum=int(cost.min()),mean=float(cost.mean()),maximum=int(cost.max()),
            includes_return=True,excludes_call=True),
        total_tstates=m.total,block_tstates=parts,total_seconds_at_spectrum128=m.total/CPU,
        average_tstates_per_sample=m.total/len(codes),maximum_sustainable_pcm_hz=CPU/(m.total/len(codes)),
        live_8000_hz_budget_tstates=CPU/8000,live_pdm_qualified=False,
        instruction_audit=dict(samples=audit_count,**audit),
        binary_sha256=hashlib.sha256(bytes(m.image[a] for a in sorted(m.image))).hexdigest(),
        scope='Complete flat Z80 decoder benchmark. Excludes ULA, paging, ROM, disk and PDM; no TRD/player is built.')
