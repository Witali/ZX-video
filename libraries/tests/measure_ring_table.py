"""Item06: aligned bank lookup, full banked native ZX0 and IRQ regression."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'libraries/zx0/src'))
from zx0 import Token,encode,decompress
from zx0 import banked
from z80 import Z80Machine


def word(m,at,value):m.set_memory_block(at,value.to_bytes(2,'little'))


def execute(options,payload,expected,*,stored=False,ring_start=0xffff,interrupts=False):
    blob,z=banked.build(**options);m=Z80Machine();m.memory[:]=b'\xa5'*65536
    m.set_memory_block(banked.CODE,blob)
    banks={n:bytearray(b'\xa5'*16384) for n in (*banked.BANKS,7)}
    for i,value in enumerate(payload):
        region,offset=divmod((ring_start+i)&65535,16384);banks[banked.BANKS[region]][offset]=value
    for name,value in dict(block_length=len(expected),block_end=(banked.OUTPUT+len(expected))&65535,
            remaining=len(payload),valid=0,ring_pointer=0xc000+ring_start%16384).items():word(m,z[name],value)
    for name,value in dict(block_stored=128 if stored else 0,ring_region=ring_start//16384,
            history_page=0x1f).items():m.memory[z[name]]=value
    page=0x1f;produced=input_reads=ring_reads=irqs=0
    def output(port,value):
        nonlocal page
        assert port==0x7ffd;page=value
    def read(at):
        nonlocal input_reads,ring_reads
        if banked.INPUT<=at<banked.INPUT+256:
            valid=m.memory[z['valid']]+256*m.memory[z['valid']+1]
            assert at-banked.INPUT<valid and input_reads<len(payload)
            value=m.memory[at];assert value==payload[input_reads];input_reads+=1;return value
        assert at>=0xc000
        bank=page&7
        if bank==7:assert banked.OUTPUT<=at<banked.OUTPUT+produced
        else:
            assert bank in banked.BANKS
            position=banked.BANKS.index(bank)*16384+at-0xc000
            assert ring_reads<len(payload) and position==(ring_start+ring_reads)&65535
            ring_reads+=1
        return banks[bank][at-0xc000]
    def write(at,value):
        nonlocal produced
        if at>=0xc000:
            assert page&7==7 and at==banked.OUTPUT+produced and produced<len(expected)
            assert value==expected[produced];banks[7][at-0xc000]=value;produced+=1
        else:
            assert (banked.STACK_BOTTOM<=at<banked.STACK_TOP or 0x9d70<=at<0x9df0
                or banked.INPUT<=at<banked.INPUT+256 or z['state']<=at<z['ring_banks']
                or at in patched),('unexpected write',hex(at),hex(m.pc))
            m.memory[at]=value
    patched={z[k] for k in ('slice_high_operand','slice_low_operand')}|{z['dzx0t_last_offset']+1,z['dzx0t_last_offset']+2}
    if options['token_boundaries']:patched.add(z['slice_equal_branch'])
    if options['inline_matches']:patched.update(z[k] for k in ('match_high_operand','match_low_operand','match_equal_branch'))
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.mark_addrs(banked.INPUT,256,m.READ_MARK);m.mark_addrs(0xc000,16384,m.READ_MARK)
    m.set_read_callback(read);m.set_write_callback(write);m.set_output_callback(output)
    m.set_memory_block(0x38,bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d'))
    stop=0x100;m.set_breakpoint(stop);m.set_breakpoint(z['fatal']);slices=[]
    for index,target in enumerate(list(range(256,len(expected),256))+[len(expected)]):
        word(m,z['slice_target'],(banked.OUTPUT+target)&65535);word(m,0x9dee,stop)
        m.sp=0x9dee;m.pc=z['begin' if index==0 else 'slice_until']
        if interrupts:
            entry=m.pc;m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'));m.pc=0x200
        budget=5_000_000;m.ticks_to_stop=budget
        while m.pc!=stop:
            event=m.run();assert not event&m._TICKS_LIMIT_HIT and m.pc!=z['fatal']
            if interrupts and m.pc!=stop and event&m._END_OF_FRAME and m.iff1 and not m.int_disabled:
                m.on_handle_active_int();assert m.pc==0x38;irqs+=1
        assert m.sp==0x9df0 and page==0x1f and produced>=target
        if not options['token_boundaries']:assert produced==target
        slices.append(budget-m.ticks_to_stop)
        for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):setattr(m,name,0x9797)
    assert produced==len(expected) and input_reads==ring_reads==len(payload)
    assert bytes(banks[7][8192:8192+produced])==expected
    return dict(exact=True,tstates=sum(slices),slices=slices,interrupts=irqs,
        input_reads=input_reads,ring_reads=ring_reads)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();rows=[];layouts=[];page_checks=0
    literal=bytes(range(256))*32
    cases=[('stored',literal,literal,True),('literals',encode(literal,[Token(0,8192)]),literal,False),
        ('overlap1',encode(b'A'*8192,[Token(0,1),Token(1,8191,1)]),b'A'*8192,False),
        ('overlap256',encode(literal,[Token(0,256),Token(256,7936,256)]),literal,False)]
    for fast,refill in itertools.product((False,True),repeat=2):
        for boundary in (False,True,'decrement'):
            for inline in ((False,True) if boundary is True else (False,)):
                options=dict(fast_literal=fast,fast_refill=refill,token_boundaries=boundary,inline_matches=inline)
                before=banked.build(**options);after=banked.build(**options,aligned_ring_table=True)
                layouts.append(dict(options=options,before_bytes=len(before[0]),after_bytes=len(after[0]),
                    added_bytes=len(after[0])-len(before[0]),before_sha256=hashlib.sha256(before[0]).hexdigest(),
                    after_sha256=hashlib.sha256(after[0]).hexdigest(),table_address=after[1]['ring_banks'],
                    standalone_raw_sectors_before=(len(before[0])+255)//256,
                    standalone_raw_sectors_after=(len(after[0])+255)//256))
                for region,history in itertools.product(range(4),(0x17,0x1f)):
                    costs=[]
                    for blob,z in (before,after):
                        m=Z80Machine();m.set_memory_block(banked.CODE,blob)
                        m.memory[z['ring_region']]=region;m.memory[z['history_page']]=history
                        word(m,0x9dee,0x100);m.pc=z['ring_page'];m.sp=0x9dee
                        outputs=[];m.set_output_callback(lambda port,value:outputs.append((port,value)))
                        m.set_breakpoint(0x100);m.ticks_to_stop=10000
                        while m.pc!=0x100:assert not m.run()&m._TICKS_LIMIT_HIT
                        assert outputs==[(0x7ffd,(history&248)|banked.BANKS[region])]
                        costs.append(10000-m.ticks_to_stop)
                    assert costs==[108,87];page_checks+=1
                for index,(name,payload,raw,stored) in enumerate(cases):
                    if not stored:assert decompress(payload,limit=len(raw))==raw
                    start=(0x3fff+index*16384)&65535
                    old=execute(options,payload,raw,stored=stored,ring_start=start)
                    new=execute(dict(options,aligned_ring_table=True),payload,raw,stored=stored,ring_start=start)
                    irq=execute(dict(options,aligned_ring_table=True),payload,raw,stored=stored,ring_start=start,interrupts=True)
                    delta=[b-a for a,b in zip(old['slices'],new['slices'])];assert not any(t>0 for t in delta)
                    rows.append(dict(options=options,case=name,ring_start=start,payload_bytes=len(payload),
                        payload_sha256=hashlib.sha256(payload).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest(),
                        baseline_tstates=old['tstates'],candidate_tstates=new['tstates'],delta_tstates=sum(delta),
                        slower_slices=sum(t>0 for t in delta),exact=True,interrupts=irq['interrupts']))
    report=dict(complete=True,release=False,baseline_revision='ac346c70',scope=__doc__,
        layouts=layouts,page_checks=page_checks,blocks=rows,
        summary=dict(profiles=len(layouts),cases=len(rows),baseline_tstates=sum(r['baseline_tstates'] for r in rows),
            candidate_tstates=sum(r['candidate_tstates'] for r in rows),delta_tstates=sum(r['delta_tstates'] for r in rows),
            slower_blocks=sum(r['delta_tstates']>0 for r in rows),slower_slices=sum(r['slower_slices'] for r in rows),
            interrupts=sum(r['interrupts'] for r in rows),min_added_bytes=min(l['added_bytes'] for l in layouts),
            max_added_bytes=max(l['added_bytes'] for l in layouts)))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report['summary']))


if __name__=='__main__':main()
