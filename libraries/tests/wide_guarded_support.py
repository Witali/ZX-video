"""Wide guarded verification with full native flags and the real sector producer.

The native machine protects every unread input/history byte. The separate
banked producer model executes original sector/header/carry code; ROM service,
physical latency and ULA timing remain outside both instruction counts.
"""
import hashlib
import sys

from measure_long_copy import ROOT
sys.path.insert(0,str(ROOT/'toolkit'))
from z80 import Z80Machine
from lzsa import trace
from lzsa.native import put_word
from lzsa.wide_coroutine import build
from zx0.inplace import layout as inplace_layout
import test_streaming_lzsa2 as guard
import benchmark_inplace_slot as base
from inplace_streaming_core import input_prefix
from test_fap3_disk import install
from collections import Counter


def wide_profile(*,shared=False,direct=False,core=0xa000):
    return build(streaming=True,direct_header=direct,shared_literals=shared,
                 prefix=0x7000,prefix_limit=0x7400,core=core,core_limit=0xbc00)


def native(profile,payload,expected,*,offset=0,interrupts=False):
    regions,z,report=profile
    _,proof=trace(payload,limit=len(expected))
    place=inplace_layout(len(payload),len(expected),proof['minimum_input_start'],offset)
    assert place['sector_aligned_fits']
    start=0xc000+place['input_start'];end=start+len(payload)
    output,stack,stop=0xc000,0x9df0,0x100
    private=report.get('private_stack',0x7be0)
    private_limit=report.get('private_stack_bytes',24)+(6 if interrupts else 0)
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    for at,data in regions:
        assert at+len(data)<=start or at>=end
        assert at+len(data)<=output or at>=output+len(expected)
        m.set_memory_block(at,data)
    high=output;loaded=start&0xff00;input_at=start
    low_private=private;low_caller=stack-2
    put_word(m,z['input_pointer'],start);put_word(m,z['block_end'],output+len(expected))
    put_word(m,z['block_length'],len(expected));m.set_breakpoint(stop);m.set_breakpoint(z['fatal'])
    irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
    m.set_memory_block(0x38,irq)
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for at,data in regions:m.unmark_addrs(at,len(data),m.READ_MARK)
    for lo,hi in ((stack-96,stack),(private-96,private),(0x38,0x38+len(irq)),(0x200,0x207)):
        m.unmark_addrs(lo,hi-lo,m.READ_MARK)
    m.unmark_addrs(z['state'],z['end']-z['state'],m.WRITE_MARK)
    for at in report['patched_addresses']:m.unmark_addr(at,m.WRITE_MARK)
    def read(at):
        nonlocal input_at
        if start<=at<end and not output<=at<high:
            assert at<loaded,('unloaded input',hex(at),hex(loaded),hex(m.pc))
            assert m.memory[at]==payload[at-start]
            input_at=max(input_at,at+1)
        else:assert output<=at<high,('uninitialized history',hex(at),hex(m.pc))
        return m.memory[at]
    def write(at,value):
        nonlocal high,low_private,low_caller
        if output<=at<output+len(expected):
            assert at==high and value==expected[at-output],('output',hex(at),hex(m.pc))
            assert not input_at<=at<end,('overwritten unread input',hex(at),hex(input_at))
            high+=1
        elif private-96<=at<private:low_private=min(low_private,at)
        else:
            assert stack-96<=at<stack,('invalid write',hex(at),hex(m.pc))
            low_caller=min(low_caller,at)
        m.memory[at]=value
    m.set_read_callback(read);m.set_write_callback(write)
    helper_cost=[]
    def supply():
        nonlocal loaded
        assert loaded<65536
        previous=bytes(m.memory[output:high]);lo=max(start,loaded);loaded+=256
        hi=min(end,loaded)
        if hi>lo:m.set_memory_block(lo,payload[lo-start:hi-start])
        assert bytes(m.memory[output:high])==previous
        full=loaded==65536
        for name in ('input_high','header_frontier','literal_frontier'):
            m.memory[z[name]]=(loaded>>8)&255
        m.memory[z['all_loaded']]=int(full)
        if 'update_guards' in z:
            # Execute the shipped patcher, whose bytes and stack are included
            # in service RAM. The producer comparison also retains its original
            # inline patcher for identical producer-instruction accounting.
            m.af=int(full)<<8;m.pc=z['update_guards'];m.sp=stack-2;put_word(m,stack-2,stop)
            m.ticks_to_stop=20_000_000
            while m.pc!=stop:
                event=m.run();assert not event&m._TICKS_LIMIT_HIT
            helper_cost.append(20_000_000-m.ticks_to_stop)
            assert m.sp==stack
        else:
            for name in ('header_patch','guard_literals'):
                if name in z:m.memory[z[name]]=0xc9 if full else 0xf5
            for target,partial,complete in (
                ('token_high_target',z['token_guard'],z['token_body']),
                ('token_low_target',z['token_guard'],z['token_body']),
                ('token_end_target',z['token_guard'],z['token_body']),
                ('long8_target',z['guard_long8'],z.get('long8_complete',z['CopyMoreLiterals'])),
                ('long16_target',z['guard_long16'],z.get('long16_complete',z['NextUseBC']))):
                put_word(m,z[target],complete if full else partial)
    supply();first=True;cost=[];waits=[];published=[];irqs=0
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
            published.append(high-output)
            for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):setattr(m,name,0x9797)
            if not m.memory[z['input_needed']]:
                assert high>=output+target;break
            waits.append(dict(produced=high-output,loaded=loaded-start))
            supply()
    assert m.memory[z['finished']] and bytes(m.memory[output:high])==expected and high==output+len(expected)
    assert loaded==65536 and input_at==end
    assert private-low_private<=private_limit,(private-low_private,private_limit)
    assert stack-low_caller<=4+(6 if interrupts else 0)
    return dict(exact=True,tstates=sum(cost),slices=cost,input_waits=waits,
        output_cursors=published,injected_interrupts=irqs,input_start=start,
        private_stack_bytes=private-low_private,caller_stack_bytes=stack-low_caller,
        guard_update_tstates=sum(helper_cost),guard_update_calls=len(helper_cost))


class WideCPU(guard.StreamingCPU):
    def write8(self,address,value):
        if hasattr(self,'stack_lows'):
            for top in self.stack_lows:
                if top-96<=address<top:self.stack_lows[top]=min(self.stack_lows[top],address)
        return super().write8(address,value)

    def instruction(self):
        # The reference application CPU had no indirect JP. Its documented
        # Z80 timing is4 T, independently checked against the full native run.
        if self.read8(self.pc)==0xe9:
            self.pc=self.hl();return 4
        return super().instruction()


class Harness(guard.Harness):
    def __init__(self,stream,first,*,shared=False,direct=False):
        base.Harness.__init__(self,stream,first,inplace=True)
        c=self.cpu;c.__class__=WideCPU;c.decoder_histogram=Counter()
        c.stack_lows={0x7be0:0x7be0,0x9df0:0x9df0,0x9c00:0x9c00}
        profile=wide_profile(shared=shared,direct=direct)
        regions,self.z,self.layout=profile
        for at,data in regions:install(c,at,data)
        c.zlabels=self.z;c.patched=set(self.layout['patched_addresses'])
        c.token_rereads={at+i+1 for at,data in regions for i,op in enumerate(data) if op==0x7e}
        regions,self.p,rows=input_prefix(self.z,self.d,elapsed_fields=self.elapsed_fields,
                                       origin=self.layout['prefix_end'],patch_guards=True)
        for at,data in regions:install(c,at,data)
        self.regions=regions;self.instructions.update({r['address']:r for r in rows})
