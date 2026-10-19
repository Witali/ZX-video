"""Full LZSA2 cold-sync comparisons, protected pointers and observed stack peaks."""
import argparse,json
from measure_long_copy import samples,sha
from measure_fast_jumps import layout,summarize
from lzsa.resumable import build
from z80 import Z80Machine
from pathlib import Path


def word(m,at,value):m.set_memory_block(at,value.to_bytes(2,'little'))


def execute(profile,payload,expected,*,interrupts=False,slice_bytes=256,targets=None):
    regions,z,meta=profile;m=Z80Machine();m.memory[:]=b'\xa5'*65536
    source,output,stack,private,stop=0x2000,0xc000,0xbff0,meta['private_stack'],0x100
    for at,data in regions:m.set_memory_block(at,data)
    m.set_memory_block(source,payload);word(m,z['input_pointer'],source)
    word(m,z['block_end'],output+len(expected));word(m,z['block_length'],len(expected))
    irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed4d');m.set_memory_block(0x38,irq)
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for at,data in regions:m.unmark_addrs(at,len(data),m.READ_MARK)
    for at,n in ((stack-128,128),(private-128,128),(0x38,len(irq)),(0x200,7)):
        m.unmark_addrs(at,n,m.READ_MARK)
    m.unmark_addrs(z['state'],z['end']-z['state'],m.WRITE_MARK)
    for at in meta['patched_addresses']:m.unmark_addr(at,m.WRITE_MARK)
    high=output;cursor=source;lowest_caller=stack;lowest_private=private
    def read(at):
        nonlocal cursor
        if source<=at<source+len(payload):
            assert at in (cursor,cursor-1),('nonsequential source',hex(at),hex(cursor),hex(m.pc))
            cursor=max(cursor,at+1)
        else:assert output<=at<high,('read outside payload/history',hex(at),hex(m.pc))
        return m.memory[at]
    def write(at,value):
        nonlocal high,lowest_caller,lowest_private
        if output<=at<output+len(expected):
            assert at==high and value==expected[at-output],('output differs',hex(at),hex(m.pc))
            high+=1
        elif stack-128<=at<stack:lowest_caller=min(lowest_caller,at)
        elif private-128<=at<private:lowest_private=min(lowest_private,at)
        else:raise AssertionError(('write outside stack/output',hex(at),hex(m.pc)))
        m.memory[at]=value
    m.set_read_callback(read);m.set_write_callback(write);m.set_breakpoint(stop);m.set_breakpoint(z['fatal'])
    if targets is None:targets=([len(expected)] if slice_bytes is None else list(range(slice_bytes,len(expected),slice_bytes))+[len(expected)])
    costs=[];cursors=[];irqs=0
    for index,target in enumerate(targets):
        word(m,z['slice_target'],output+target);word(m,stack-2,stop)
        entry=z['begin' if index==0 else 'slice_until'];m.pc,m.sp=entry,stack-2
        if interrupts:
            m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'));m.pc=0x200
        m.ticks_to_stop=20_000_000
        while m.pc!=stop:
            event=m.run();assert not event&m._TICKS_LIMIT_HIT and m.pc!=z['fatal']
            if interrupts and m.pc!=stop and event&m._END_OF_FRAME and m.iff1 and not m.int_disabled:
                m.on_handle_active_int();assert m.pc==0x38;irqs+=1
        assert m.sp==stack and high>=output+target
        costs.append(20_000_000-m.ticks_to_stop);cursors.append(high-output)
        for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):setattr(m,name,0x9797)
    assert cursor==source+len(payload) and high==output+len(expected)
    return dict(tstates=sum(costs),slices=costs,output_cursors=cursors,exact=True,
        injected_interrupts=irqs,caller_stack_bytes=stack-lowest_caller,private_stack_bytes=private-lowest_private)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    configs=dict(default={},restored={'restore_compare':True},
        tuned=dict(fast_jumps=True,branch_tuned=True,nibble_prefill=True),
        combined=dict(fast_jumps=True,branch_tuned=True,nibble_prefill=True,long_copy=True,near_literals=True,restore_compare=True))
    cases=list(samples())+[
        ('single-nibble-eof-A',bytes.fromhex('ef41f0e8'),b'A'),('single-nibble-eof-empty',bytes.fromhex('e7f0e8'),b'')]
    report=dict(date='2026-10-19',baseline_revision='841bf955',complete=False,release=False,goal_achieved=False,profiles={})
    for name,options in configs.items():
        old=build(core=0x8000,core_limit=0x8400,**options)
        new=build(core=0x8000,core_limit=0x8400,compact_sync=True,**options)
        moved=build(core=0x9103,core_limit=0x9500,compact_sync=True,**options)
        assert new[2]['code_bytes']-old[2]['code_bytes']==(-3 if options.get('restore_compare') else -5)
        rows=[]
        for case,payload,raw in cases:
            before,after,irq,relocated=execute(old,payload,raw),execute(new,payload,raw),execute(new,payload,raw,interrupts=True),execute(moved,payload,raw)
            assert before['output_cursors']==after['output_cursors']==relocated['output_cursors']
            assert after['tstates']==relocated['tstates']
            assert before['caller_stack_bytes']==after['caller_stack_bytes'] and before['private_stack_bytes']==after['private_stack_bytes']
            delta=[b-a for a,b in zip(before['slices'],after['slices'])]
            assert delta==([-3]+[-23]*(len(delta)-1) if options.get('restore_compare') else [-8]+[-28]*(len(delta)-1))
            rows.append(dict(case=case,raw_bytes=len(raw),payload_sha256=sha(payload),raw_sha256=sha(raw),
                baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],delta_tstates=sum(delta),
                slower_slices=sum(t>0 for t in delta),largest_slice_delta=max(delta),slices=len(delta),
                caller_stack_bytes=after['caller_stack_bytes'],private_stack_bytes=after['private_stack_bytes'],
                irq_caller_stack_bytes=irq['caller_stack_bytes'],irq_private_stack_bytes=irq['private_stack_bytes'],
                injected_interrupts=irq['injected_interrupts'],exact=True,relocated_exact=True))
        report['profiles'][name]=dict(options=options,baseline=layout(old),candidate=layout(new),summary=summarize(rows),blocks=rows)
        print(name,json.dumps(summarize(rows)),flush=True)
    report['complete']=True;args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
