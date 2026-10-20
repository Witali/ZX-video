"""Two-bank resident PCM8 table component with exactly uniform 28-T outputs.

The single physical bank transition is explicit and static: bank0 to bank1.
This is not a variable-bank descriptor reader, full-song player or release.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import time

import numpy as np
from z80 import Z80Machine

from table_pdm_uniform16 import model
from sdm16_uniform7 import assemble

HERE = Path(__file__).resolve().parent
TABLE = 0x4000
MAP = 0xBF00
SOURCE = 0xC000


def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def pulse(bit,immediate=False,alternate=False):
    if immediate:return ' OUT (254),A\n'
    return (' OUT (C),H\n' if alternate else ' OUT (C),B\n') if bit else ' DB 237,113\n'
def seta(bit):return ' LD A,B\n' if bit else ' XOR A\n'


def variants(words,nxt,states):
    return sorted({(int(words[v,s])&255,states.index(int(nxt[v,s]))*4)
                   for v in range(64) for s in states})


def kernel_source(first,second):
    text='''; Isolated residentPCM8 component, bank0 -> bank1 once, no disk/EOF.
; Main BC=10FE, DE=one-ahead source cursor, HL=lookup/nextFIRST pointer.
; Main IY/IX and AF' remain free/preserved. SP is a lookup pointer, no calls.
; ALT HL=10FE constant: H is the alternate EAR-high byte, L restores port C.
; ALT BC starts7FFE and becomes7FFD at the one bank switch. ALT DE is scratch.
; Main A/F are scratch; bank detection clears C and keeps it through RET C.
; Each FIRST self-patches only its own final JP operand with the SECOND word.
; Each lookup record is FIRST pointer, specialized SECOND pointer (4 bytes).
; SECOND specializes the low8 output bits and next feedback offset.
; Source mapping changes one PCM sample early, after the final old byte has
; already been prefetched into lookup state. The next FIRST then increments
; BF:FF to C0:00 and reads the new bank; no old source byte is reread.
; All instruction counts assume uncontended Pentagon CPU/I/O. Physical ROM,
; cover, loader, general descriptor iteration and clone timing are unproved.
 ORG 0x8000
'''
    for word in first:
        text+=f'first_{word}:\n'
        for slot in range(8):
            text+=f'first_{word}_pulse_{slot}:\n'+pulse((word>>(7-slot))&1,slot in (5,6,7))
            if slot==0:text+=' POP HL\n INC DE\n'
            elif slot==1:text+=f' LD (first_{word}_jump+1),HL\n'
            elif slot==2:text+=' EXX\n LD C,L\n EXX\n NOP\n'
            elif slot==3:text+=' LD L,E\n LD H,D\n NOP\n NOP\n'
            elif slot==4:text+=' LD L,(HL)\n'+seta((word>>2)&1)+' LD SP,HL\n'
            elif slot==5:text+=f' LD H,{MAP>>8}\n'+seta((word>>1)&1)+' LD SP,HL\n'
            elif slot==6:text+=' LD H,(HL)\n'+seta(word&1)+' LD SP,HL\n'
            else:text+=f' INC SP\nfirst_{word}_jump:\n JP 0\n'
    for word,feedback in second:
        name=f'{word}_{feedback}'
        text+=f'second_{name}:\n'
        for slot in range(4):
            text+=f'second_{name}_pulse_{8+slot}:\n'+pulse((word>>(7-slot))&1,alternate=slot==3)
            if slot==0:text+=f' LD L,{feedback}\n LD A,R\n'
            elif slot==1:text+=' LD SP,HL\n POP HL\n'
            elif slot==2:text+=' LD A,D\n AND E\n INC A\n EXX\n'
            else:text+=f' JP Z,bank_{name}\n LD A,{16*((word>>3)&1)}\n'
        text+=pulse((word>>3)&1,immediate=True)+' EXX\n NOP\n NOP\n NOP\n'
        text+=pulse((word>>2)&1)+' NOP\n NOP\n NOP\n NOP\n'
        text+=pulse((word>>1)&1)+' NOP\n NOP\n NOP\n NOP\n'
        text+=pulse(word&1)+' NOP\n NOP\n NOP\n JP (HL)\n'
        text+=f'''bank_{name}:
 LD A,{16*((word>>3)&1)}
 OUT (254),A
 LD BC,0x7FFD
 LD A,{16*((word>>2)&1)}
 OUT (254),A
 LD DE,0x19C0
 LD A,{16*((word>>1)&1)}
 OUT (254),A
 OUT (C),D
 EXX
'''+pulse(word&1)+''' ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
'''
    return text+'kernel_end:\n NOP\n'


def tables(labels,words,nxt,states):
    table=bytearray(16384)
    for value in range(64):
        for i,state in enumerate(states):
            word=int(words[value,state]);feedback=states.index(int(nxt[value,state]))*4
            at=value*256+i*4
            table[at:at+4]=struct.pack('<HH',labels[f'first_{word>>8}'],labels[f'second_{word&255}_{feedback}'])
    return bytes(table),bytes((TABLE>>8)+(value>>2) for value in range(256))


def run(blob,labels,lookup,mapping,words,nxt,states,source,*,initial_state=16,
        initial_address=SOURCE,details=False):
    first_capacity=0x10000-initial_address
    assert SOURCE<=initial_address<=0xFFFF
    # Do not put the guard at the second bank'sFFFF. The one-sample-ahead
    # handoff would then require a third bank even if the guard is not played.
    # EOF suppression is a separate unimplemented player obligation.
    assert 2<=len(source)<=first_capacity+16383
    samples=len(source)-1
    bank0=bytearray(16384);bank1=bytearray(16384)
    bank0[initial_address-SOURCE:]=source[:first_capacity]
    bank1[:max(0,len(source)-first_capacity)]=source[first_capacity:]
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    m.memory[TABLE:TABLE+len(lookup)]=lookup;m.memory[MAP:MAP+256]=mapping
    m.memory[SOURCE:]=bank0
    startword=int(words[source[0]>>2,initial_state]);record=TABLE+(source[0]>>2)*256+states.index(initial_state)*4
    registers=dict(bc=0x10FE,de=initial_address,hl=labels[f'first_{startword>>8}'],
        ix=0x5500,iy=0xA55A,sp=record+2,af=0x3C01,alt_bc=0x7FFE,
        alt_de=0x1234,alt_hl=0x10FE,alt_af=0xDEF0)
    for k,v in registers.items():setattr(m,k,v)
    m.i=0x36;m.iff1=m.iff2=False;m.pc=registers['hl']
    expected=[];state=initial_state
    for value in source[:-1]:
        word=int(words[value>>2,state]);expected.extend((word>>shift)&1 for shift in range(15,-1,-1))
        state=int(nxt[value>>2,state])
    nextword=int(words[source[-1]>>2,state]);stop=labels[f'first_{nextword>>8}']
    nextrecord=TABLE+(source[-1]>>2)*256+states.index(state)*4
    budget=samples*448+10000;observed=[];times=[];page_events=[];active_bank=0
    initial_fixed=bytes(m.memory[:SOURCE]);initial_guard=bytes(m.memory[SOURCE:])
    def output(port,value):
        nonlocal active_bank
        clock=budget-m.ticks_to_stop
        if port==0x7FFD:
            assert value==0x19 and active_bank==0,(port,value,active_bank)
            page_events.append(dict(tstate=clock,value=value,after_speaker_outputs=len(observed),
                source_cursor=m.alt_de,already_prefetched_old_final_PCM=source[first_capacity-1]))
            active_bank=1;m.memory[SOURCE:]=bank1
            return
        assert port in (0x00FE,0x10FE,0x7FFE) and value in (0,16),(port,value)
        observed.append(value>>4);times.append(clock)
        if len(observed)==16*samples:m.set_breakpoint(stop)
    m.set_output_callback(output);m.ticks_to_stop=budget
    while len(observed)<16*samples or m.pc!=stop:
        event=m.run();assert not event&m._TICKS_LIMIT_HIT,'Native component timeout'
    assert observed==expected,('bits',next((i for i,(a,b) in enumerate(zip(observed,expected)) if a!=b),None))
    assert all(b-a==28 for a,b in zip(times,times[1:]))
    assert budget-m.ticks_to_stop==samples*448
    # The final sample is a guard prefetched for the next lookup.
    expected_bank=int(samples>=first_capacity)
    expected_de=initial_address+samples if not expected_bank else SOURCE+samples-first_capacity
    assert active_bank==expected_bank and m.de==expected_de,(active_bank,m.de,expected_de)
    assert len(page_events)==int(samples>=first_capacity-1)
    assert m.bc==registers['bc'] and m.ix==registers['ix'] and m.iy==registers['iy']
    assert m.hl==stop and m.sp==nextrecord+2
    assert m.alt_hl==0x10FE and m.alt_af==registers['alt_af'] and m.i==0x36
    assert m.iff1==m.iff2==0
    assert m.alt_bc==0x7FFE
    # Self-modified JP operands are the only CPU-written fixed bytes.
    mutable=[]
    for name,address in labels.items():
        if name.startswith('first_') and name.endswith('_jump'):
            mutable.extend((address+1,address+2))
    fixed=bytearray(m.memory[:SOURCE])
    for address in mutable:fixed[address]=initial_fixed[address]
    assert bytes(fixed)==initial_fixed
    assert bytes(m.memory[SOURCE:])==bytes(bank1 if active_bank else initial_guard)
    result=dict(samples=samples,initial_address=initial_address,initial_state=initial_state,
        actual_source_banks=1+active_bank,page_events=page_events,
        outputs=len(observed),sample_period_tstates=448,every_speaker_hold_tstates=28,
        bits_exact=True,successor_lookup_exact=True,source_order_exact=True,
        bits_sha256=sha(bytes(observed)),times_sha256=sha(np.asarray(times,dtype='<u4').tobytes()),
        fixed_RAM_CPU_mutable_bytes=len(mutable),source_RAM_CPU_unchanged=True)
    if details:result.update(bits=observed,times=times)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use fresh output; preserve earlier attempts')
    out.mkdir(parents=True,exist_ok=True);started=time.monotonic()
    words,nxt,states,first,_=model();second=variants(words,nxt,states)
    blob,labels=assemble(out,kernel_source(first,second));assert 0x8000+len(blob)<=MAP,(len(blob),MAP-0x8000)
    lookup,mapping=tables(labels,words,nxt,states)
    (out/'lookup.bin').write_bytes(lookup);(out/'pcm-high.bin').write_bytes(mapping)
    cases=[]
    for state in states:
        for value in range(256):
            # Three old-bank bytes make all test cases cross the real map
            # switch and then continue through the next ordinary path.
            source=bytes([value,(value*73+17)&255,(value*29+state)&255,
                          (value*41+3)&255,(value*7+state)&255,0xA5])
            cases.append(run(blob,labels,lookup,mapping,words,nxt,states,source,
                             initial_state=state,initial_address=0xFFFD))
    indices=np.arange(32767,dtype=np.uint32)
    source=((indices*73+(indices>>2)*19+(indices>>8)*131) ^ (indices>>4)).astype('u1').tobytes()
    trajectory=run(blob,labels,lookup,mapping,words,nxt,states,source,details=True)
    (out/'trajectory-pcm8.bin').write_bytes(source)
    (out/'trajectory-bits.u8.gz').write_bytes(gzip.compress(bytes(trajectory.pop('bits')),mtime=0))
    (out/'trajectory-times.u32.gz').write_bytes(gzip.compress(np.asarray(trajectory.pop('times'),dtype='<u4').tobytes(),mtime=0))
    save(out/'all-cells.json',cases)
    report=dict(complete=True,date='2026-10-20',elapsed_seconds=time.monotonic()-started,
        mechanism='Resident PCM8, same64-level integral PDM table, specializedSECOND and self-patchedFIRST',
        states=states,FIRST_patterns=len(first),SECOND_variants=len(second),kernel_bytes=len(blob),
        code_end=0x8000+len(blob),map_address=MAP,table_allocated_bytes=len(lookup),
        table_used_bytes=64*len(states)*4,fixed_allocation_bytes=len(blob)+len(lookup)+256,
        all_cell_cases=len(cases),trajectory=trajectory,total_outputs=sum(r['outputs'] for r in cases)+trajectory['outputs'],
        ordinary_page_bank_source_period_tstates=448,all_actual_speaker_holds_tstates=28,
        original_ordinary_tstates=449,ordinary_delta_tstates=-1,
        original_bank_extra_tstates=243,cached_byte_previous_bank_extra_tstates=229,
        new_static_bank_extra_tstates=0,
        changed_register_contract='ALT HL=10FE constant; ALT B7F remains port high and ALT H16 emits the single alternate normal high pulse; FIRST restores ALT C fromL',
        scope='Native CPU plus a real two-bank memory-window callback; one static0->1 map per run. No general descriptor reader, full-song or actualFuse proof.',
        not_proved=['Dynamic bank sequence/descriptor lookup','PCM16 or liveIMA decoding','FinalEOF and insufficientRAM refills',
                    'Cover, progress, bootableTRD and independentcoldboot','PhysicalPentagonpaging/otherclonecontention','Audioquality'],
        decision='A complete448T residentPCM8 table loop with ordinary pages and one static bankhandoff is proven in native execution. Additional bank metadata still requires a distinct integration step.')
    save(out/'report.json',report)
    producer=Path(__file__).read_bytes();(out/'producer.py.gz').write_bytes(gzip.compress(producer,mtime=0))
    for dependency in (HERE/'table_pdm_uniform16.py',HERE/'sdm16_uniform7.py',HERE.parent.parent/'probe_feedback_packets.py'):
        target=out/'producer-source'/(dependency.name+'.gz');target.parent.mkdir(exist_ok=True)
        target.write_bytes(gzip.compress(dependency.read_bytes(),mtime=0))
    artifacts={p.relative_to(out).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
               for p in sorted(out.rglob('*')) if p.is_file()}
    save(out/'manifest.json',dict(complete=True,artifact_files=artifacts))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
