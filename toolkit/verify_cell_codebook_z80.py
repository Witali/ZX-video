"""Guarded banked and independent full-flags checks of native CB41 output.

Caller supplies validated packets, mapped target and initial screens. No
packet copy, paging, publication, real AY/IRQ/ULA or disk scheduling claim.
"""
import argparse,json,struct
from collections import Counter
from pathlib import Path
import numpy as np
from z80 import Z80Machine
from benchmark_compact_screen import NativeCPU
from validate_fast_sparse import CPU
from build_fap3_trd import sha
from build_five_level_test_trd import save
from frame_output_pipeline import display_screen
from row_dictionary_video import reference_tables
from probe_cell_codebook import changes,encode
from test_cell_codebook import put
import cell_codebook_z80 as machine

STACK,STOP=0xbff0,0x100


def active(address,base):
    offset=address-base
    if 0<=offset<6144:
        y=((offset>>8)&7)|((offset>>2)&56)|((offset>>5)&192)
        return 24<=y<168
    return 6144+96<=offset<6144+672


class GuardedCPU(NativeCPU):
    def read8(self,address):
        address&=65535
        if self.guarding:
            assert any(lo<=address<hi for lo,hi in self.readable),('unexpected read',hex(address),hex(self.pc))
        return CPU.read8(self,address)

    def write8(self,address,value):
        address&=65535
        if self.guarding:
            allowed=(self.state[0]<=address<self.state[1] or STACK-128<=address<STACK)
            allowed |= (machine.BOOK<=address<machine.BOOK+2048) if self.loading else active(address,self.target)
            assert allowed,('unexpected write',hex(address),hex(self.pc))
        CPU.write8(self,address,value)


class Harness:
    def __init__(self,table,rows,initial,dictionary,*,front_reuse=False,fast_masks=False,partial_rows=False,inline_cells=False):
        self.regions,self.labels,self.meta=machine.build(dictionary=dictionary,front_reuse=front_reuse,fast_masks=fast_masks,partial_rows=partial_rows,inline_cells=inline_cells)
        self.c=GuardedCPU(b'',b'');self.c.guarding=False;self.c.port_7ffd=0x17
        self.c.state=self.labels['state'],self.labels['end'];self.rows=rows;self.table=table
        for at,data in self.regions+[(machine.ROWS,rows)]:self.install(at,data)
        self.c.banks[7][:6912]=initial[:6912];self.c.banks[5][:6912]=initial[6912:]
        self.instructions={r['address']:r for r in self.meta['instruction_listing']};self.hist=Counter()
        self.base_reads=[(at,at+len(data)) for at,data in self.regions]+[(machine.ROWS,machine.ROWS+512),
            (machine.BOOK,machine.BOOK+2048),(STACK-128,STACK)]
        if front_reuse:self.base_reads += [(0x4000,0x5b00),(0xc000,0xdb00)]
        self.loader=None
        if dictionary:
            self.loader=self.run('load_book',table,0x6400,0xc0,loading=True)
            expected=bytes(table[i*8+line] for line in range(8) for i in range(256))
            assert bytes(self.c.banks[2][machine.BOOK-0x8000:machine.BOOK-0x8000+2048])==expected
            assert self.loader['tstates']==54028

    def install(self,at,data):
        for i,v in enumerate(data):self.c.write8(at+i,v)

    def run(self,entry,payload,source,target,loading=False):
        c=self.c;c.guarding=False;c.loading=loading;c.target=target<<8
        c.port_7ffd=0x17 if target==0xc0 else 0x1f
        self.install(source,payload)
        for n in ('a','b','c','d','e','h','l','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):
            setattr(c,n,0x97)
        c.ix,c.iy=0x1122,0x3344;c.a=target;c.set_hl(source);c.sp=STACK;c.push(STOP)
        c.pc=self.labels[entry];c.readable=self.base_reads+[(source,source+len(payload))]
        c.guarding=True;before=c.tstates;stages=Counter();steps=0
        while c.pc!=STOP:
            pc,t=c.pc,c.tstates;c.step();dt=c.tstates-t;steps+=1
            row=self.instructions[pc];wanted=row['tstates']
            assert dt in (wanted if isinstance(wanted,list) else [wanted]),('timing',row,dt)
            stages[row['stage']]+=dt;self.hist[pc,dt]+=1
            assert steps<150000,'kernel did not return'
        c.guarding=False
        assert c.hl()==source+len(payload),('input cursor',hex(c.hl()),hex(source+len(payload)))
        assert c.sp==STACK and (c.ix,c.iy)==(0x1122,0x3344)
        assert c.port_7ffd==(0x17 if target==0xc0 else 0x1f)
        assert bytes(c.read8(source+i) for i in range(len(payload)))==payload
        for at,data in self.regions:
            size=self.labels['state']-at if at==self.regions[0][0] else len(data)
            assert bytes(c.read8(at+i) for i in range(size))==data[:size]
        assert bytes(c.read8(machine.ROWS+i) for i in range(512))==self.rows
        if not loading and self.meta['dictionary']:
            expected=bytes(self.table[i*8+line] for line in range(8) for i in range(256))
            assert bytes(c.read8(machine.BOOK+i) for i in range(2048))==expected
        assert sum(stages.values())==c.tstates-before
        return dict(tstates=c.tstates-before,stages=dict(stages),source=source,bytes=len(payload),
            target_high=target,minimum_sp=c.min_sp)


def independent(h,payload,source,target,before,after,expected_t,interrupts=False,loading=False):
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    for at,data in h.regions:m.set_memory_block(at,data)
    m.set_memory_block(machine.ROWS,h.rows)
    if h.meta['dictionary'] and not loading:
        m.set_memory_block(machine.BOOK,bytes(h.table[i*8+line] for line in range(8) for i in range(256)))
    m.set_memory_block(0xc000,before[7]);m.set_memory_block(0x4000,before[5]);m.set_memory_block(source,payload)
    m.set_memory_block(STACK-2,STOP.to_bytes(2,'little'));m.set_breakpoint(STOP)
    for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):setattr(m,name,0x9797)
    m.ix,m.iy=0x1122,0x3344;m.a=target;m.hl=source;m.sp=STACK-2
    entry=h.labels['load_book' if loading else 'draw'];m.pc=entry
    irq=bytes.fromhex('f5 c5 d5 e5 d9 c5 d5 e5 08 f5 3e55 eeaa f1 08 e1 d1 c1 d9 e1 d1 c1 f1 fb ed4d')
    m.set_memory_block(0x38,irq)
    if interrupts:
        m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'));m.pc=0x200
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for lo,hi in h.base_reads+[(source,source+len(payload)),(0x38,0x38+len(irq)),(0x200,0x207)]:
        m.unmark_addrs(lo,hi-lo,m.READ_MARK)
    def read(address):raise AssertionError(('independent invalid read',hex(address),hex(m.pc)))
    def write(address,value):
        allowed=(h.labels['state']<=address<h.labels['end'] or STACK-128<=address<STACK)
        allowed |= (machine.BOOK<=address<machine.BOOK+2048) if loading else active(address,target<<8)
        assert allowed,('independent invalid write',hex(address),hex(m.pc))
        m.memory[address]=value
    m.set_read_callback(read);m.set_write_callback(write)
    budget=2000000;m.ticks_to_stop=budget;count=skipped=0
    while m.pc!=STOP:
        event=m.run();assert not event&m._TICKS_LIMIT_HIT
        if interrupts and m.pc!=STOP and event&m._END_OF_FRAME:
            if not m.iff1 or m.int_disabled:skipped+=1;continue
            m.on_handle_active_int();assert m.pc==0x38;count+=1
    t=budget-m.ticks_to_stop
    assert m.hl==source+len(payload) and m.sp==STACK and (m.ix,m.iy)==(0x1122,0x3344)
    for bank,address in ((7,0xc000),(5,0x4000)):
        assert bytes(m.memory[address:address+6912])==after[bank],('independent screen',bank)
    assert bytes(m.memory[source:source+len(payload)])==payload
    if loading:
        assert bytes(m.memory[machine.BOOK:machine.BOOK+2048])==bytes(h.table[i*8+line] for line in range(8) for i in range(256))
    if not interrupts:assert t==expected_t,('independent timing',t,expected_t)
    return dict(tstates=t,interrupts=count,unavailable_interrupt_events=skipped,exact=True)


def packets(data):
    count,entries=struct.unpack_from('<HH',data,4);at=8+entries*8
    result=[]
    for _ in range(count):
        n=struct.unpack_from('<H',data,at)[0];at+=2;result.append(data[at:at+n]);at+=n
    assert at==len(data)
    return result,data[8:8+entries*8],bool(entries)


def verify(data,states,start,meta,*,full_interrupts=True):
    payloads,table,dictionary=packets(data);count=len(payloads)
    with reference_tables(meta):
        expected={7:display_screen(states[start-2].tobytes(),black_borders=True),
                  5:display_screen(states[start-1].tobytes(),black_borders=True)}
        initial=expected[7]+expected[5];h=Harness(table,bytes.fromhex(meta['tables_hex']),initial,dictionary)
        if dictionary:
            independent(h,table,0x6400,0xc0,expected,expected,h.loader['tstates'],loading=True)
        frames=[]
        for i,payload in enumerate(payloads):
            target=7 if i%2==0 else 5;high=0xc0 if target==7 else 0x40
            source=0x6400+(i*13%61);before=expected.copy()
            row=h.run('draw',payload,source,high)
            expected[target]=display_screen(states[start+i].tobytes(),black_borders=True)
            assert all(bytes(h.c.banks[b][:6912])==s for b,s in expected.items()),('banked screens',start+i)
            check=independent(h,payload,source,high,before,expected,row['tstates'])
            irq=independent(h,payload,source,high,before,expected,row['tstates'],True) if full_interrupts else None
            frames.append(dict(frame=start+i,**row,independent=check,interrupt_run=irq))
        assert sum(t*n for (_,t),n in h.hist.items())==sum(r['tstates'] for r in frames)+(h.loader['tstates'] if h.loader else 0)
        return dict(complete=True,release=False,frames=frames,loader=h.loader,native=h.meta,
            regions=[dict(address=at,hex=data.hex()) for at,data in h.regions],labels=h.labels,
            frame_tstates=sum(r['tstates'] for r in frames),
            histogram=[dict(pc=pc,tstates=t,count=n) for (pc,t),n in sorted(h.hist.items())],
            all_screens_exact=True,all_instruction_timings_exact=True,
            injected_interrupts=sum(r['interrupt_run']['interrupts'] for r in frames if r['interrupt_run']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','states','metadata','baseline-frames','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();probe=json.loads((a.work/'probe.json').read_bytes());metadata=json.loads(a.metadata.read_bytes());meta=metadata['row_dictionary']
    with np.load(a.states,allow_pickle=False) as f:states=f['states']
    assert sha(states.tobytes())==probe['states_sha256']==metadata['states_sha256']
    result=dict(complete=False,release=False,scope=__doc__,variants={},edges=[])
    for name in ('direct_rows','codebook'):
        data=(a.work/(name+'.raw')).read_bytes();assert sha(data)==probe['variants'][name]['raw_sha256']
        result['variants'][name]=verify(data,states,probe['start'],meta)
        print(name,result['variants'][name]['frame_tstates'],'native renderer T',flush=True)
    book=[bytes(r) for r in probe['dictionary_row_keys']];words=meta['words'];base=states[probe['start']].copy()
    fallback=next(bytes([i,j,i,j]) for i in range(len(words)) for j in range(len(words))
        if i!=j and bytes([i,j,i,j]) not in book)
    cases=[('unchanged',[],False),('attributes_only',[],True),('all_indices',book,False),
        ('full_literal_and_attributes',[fallback]*576,True)]
    cases += [('mode_boundary_'+str(n),[book[i] if i%2 else fallback for i in range(n)],False) for n in (1,7,8,9,15,16,17)]
    for name,updates,attrs in cases:
        sample=np.stack([base.copy() for _ in range(3)])
        for cell,key in enumerate(updates):
            old=bytes([0])*4 if key!=bytes([0])*4 else bytes([1])*4
            put(sample[0],cell,old);put(sample[1],cell,old);put(sample[2],cell,key)
        if attrs:sample[2,3168:3744]^=64
        for mode in ([],book):
            raw,_,_=encode(changes(sample,2,1),mode,words)
            result['edges'].append(dict(case=name,dictionary=bool(mode),**verify(raw,sample,2,meta)))
    old=json.loads(a.baseline_frames.read_bytes());assert old['complete']
    assert old['raw_sha256']==metadata['raw_sha256'] and old['video_sha256']==probe['source_video_sha256']
    selected=old['frames'][probe['start']:probe['start']+probe['count']]
    result.update(complete=True,baseline_frame_tstates=sum(r['tstates'] for r in selected),
        states_sha256=probe['states_sha256'],source_raw_sha256=probe['variants']['codebook']['raw_sha256'],
        native_rendering_only=True,real_cadence_verified=False,
        baseline_frames_sha256=sha(a.baseline_frames.read_bytes()),
        source_sha256_lf={name:sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n',b'\n')) for name in (
            'cell_codebook_z80.py','verify_cell_codebook_z80.py','probe_cell_codebook.py','test_cell_codebook.py',
            'benchmark_compact_screen.py','validate_fast_sparse.py','row_dictionary_video.py')})
    save(a.output,result)
    print(json.dumps(dict(complete=True,baseline_frame_tstates=result['baseline_frame_tstates'],
        variants={k:dict(tstates=v['frame_tstates'],interrupts=v['injected_interrupts']) for k,v in result['variants'].items()},
        edges=len(result['edges']))),flush=True)


if __name__=='__main__':main()
