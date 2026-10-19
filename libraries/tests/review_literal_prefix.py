"""Independent literal-prefix review: repeated zero demand and an IRQ at deferred EX AF."""
import argparse,hashlib,json
from pathlib import Path
from measure_long_copy import ROOT
from z80 import Z80Machine
from zx0 import Token,encode
from zx0.resumable import build
from zx0.block import build as block
from lzsa.native import execute as native

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()


def put(m,at,value):m.set_memory_block(at,value.to_bytes(2,'little'))


def run(profile,payload,raw,*,force_irq=False):
    regions,z,meta=profile;m=Z80Machine();m.memory[:]=b'\xa5'*65536
    for at,data in regions:m.set_memory_block(at,data)
    src,out,stack,private,stop=0x2000,0xc000,0xbff0,0x7be0,0x100
    m.set_memory_block(src,payload)
    put(m,z['input_pointer'],src);put(m,z['block_end'],out+len(raw));put(m,z['block_length'],len(raw))
    irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed4d');m.set_memory_block(0x38,irq)
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for at,data in regions:m.unmark_addrs(at,len(data),m.READ_MARK)
    for at,length in ((stack-128,128),(private-128,128),(0x38,len(irq)),(0x200,7)):
        m.unmark_addrs(at,length,m.READ_MARK)
    m.unmark_addrs(z['state'],z['end']-z['state'],m.WRITE_MARK)
    for at in meta['patched_addresses']:m.unmark_addr(at,m.WRITE_MARK)
    high=out;cursor=src
    def read(at):
        nonlocal cursor
        if src<=at<src+len(payload):
            assert at in (cursor,cursor-1),(hex(at),hex(cursor),hex(m.pc))
            cursor=max(cursor,at+1)
        else:assert out<=at<high,('uninitialized read',hex(at),hex(m.pc))
        return m.memory[at]
    def write(at,value):
        nonlocal high
        if out<=at<out+len(raw):
            assert at==high and value==raw[at-out],('output mismatch',hex(at),hex(m.pc))
            high+=1
        else:assert stack-128<=at<stack or private-128<=at<private
        m.memory[at]=value
    m.set_read_callback(read);m.set_write_callback(write);m.set_breakpoint(stop)
    irq_done=False;cursors=[]
    point=z.get('slice_fast')
    if force_irq:m.set_breakpoint(point)
    targets=[0,0,1,1]+list(range(2,len(raw)+1))
    for index,target in enumerate(targets):
        put(m,z['slice_target'],out+target);put(m,stack-2,stop)
        entry=z['begin' if index==0 else 'slice_until'];m.pc,m.sp=entry,stack-2
        m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'));m.pc=0x200
        m.ticks_to_stop=20_000_000
        while m.pc!=stop:
            event=m.run();assert not event&m._TICKS_LIMIT_HIT and m.pc!=z['fatal']
            if force_irq and not irq_done and m.pc==point:
                # This address is EX AF,AF'; long success has just executed LDI
                # with scratch AF and still keeps the live reservoir in AF'.
                saved=tuple(getattr(m,n) for n in ('af','alt_af','bc','de','hl','sp'))
                assert m.iff1 and not m.int_disabled
                m.on_handle_active_int();assert m.pc==0x38
                while m.pc!=point:assert not m.run()&m._TICKS_LIMIT_HIT
                assert saved==tuple(getattr(m,n) for n in ('af','alt_af','bc','de','hl','sp'))
                m.clear_breakpoint(point);irq_done=True
        assert m.sp==stack and high>=out+target
        if index<2:assert high==out,('wrote before demand',index)
        cursors.append(high-out)
        for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):
            setattr(m,name,0x9797)
    assert high==out+len(raw) and cursor==src+len(payload)
    assert not force_irq or irq_done
    return dict(exact=True,cursors=cursors,forced_deferred_irq=irq_done)


cases=[]
for n in (1,2,3,15,16,255,256,257):
    raw=bytes(i%251 for i in range(n));cases.append((f'literal-{n}',encode(raw,[Token(0,n)]),raw))
for first in (1,2,3,255,256,257):
    raw=bytearray(bytes(i%251 for i in range(first)));tokens=[Token(0,first)]
    for length in (1,2,3,4,1):
        tokens.append(Token(len(raw),2,1));raw+=raw[-1:]*2
        tokens.append(Token(len(raw),length));raw+=bytes(range(length))
    raw=bytes(raw);cases.append((f'mixed-{first}',encode(raw,tokens),raw))
rows=[]
for tuned in (False,True):
    old=build(core=0x9103,core_limit=0x9500,branch_tuned=tuned)
    new=build(core=0x9103,core_limit=0x9500,branch_tuned=tuned,literal_prefix=True)
    for name,payload,raw in cases:
        before=run(old,payload,raw);after=run(new,payload,raw,force_irq=True)
        assert before['cursors']==after['cursors']
        # Also vary ordinary demand size; exact source/output checking above
        # is independent from the existing native helper.
        for demand in (2,3,17,None):
            a=native(*old,payload,raw,source=0x2000,slice_bytes=demand)
            b=native(*new,payload,raw,source=0x2000,slice_bytes=demand)
            assert a['output_cursors']==b['output_cursors']
        rows.append(dict(case=name,branch_tuned=tuned,requests=len(after['cursors']),exact=True,forced_irq=True))
result=dict(complete=True,scope=__doc__,cases=rows,source_sha256_lf={
    str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    for p in [ROOT/'libraries/zx0/src/zx0/block.py',ROOT/'libraries/zx0/src/zx0/resumable.py']})
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(complete=True,case_profiles=len(rows),deferred_irqs=len(rows),request_policy='0,0,1,1,then each byte; plus2,3,17,whole-block')))
