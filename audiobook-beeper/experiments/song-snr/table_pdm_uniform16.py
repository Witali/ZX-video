"""Native resident-PCM8 table component: sixteen equally spaced PDM decisions.

This mechanism retains the integral table algorithm, uses a fixed six-byte
record and removes indexed POP/ADD instructions from the output path. It does
not decode IMA, page source banks, terminate playback or constitute a release.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from z80 import Z80Machine

from probe_feedback_packets import integral_table
from sdm16_uniform7 import assemble

HERE=Path(__file__).resolve().parent
TABLE=0x4000
MAP=0xB000
SOURCE=0xC000


def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def model():
    words,nxt,_=integral_table(64,2,holds=[28]*16,beta=.5,extent=.5,pcm_origin=0)
    states={16}
    while True:
        expanded=states|set(map(int,nxt[:,sorted(states)].ravel()))
        if expanded==states:break
        states=expanded
    states=sorted(states)
    first=sorted(set(map(int,(words[:,states]>>8).ravel())))
    second=sorted(set(map(int,(words[:,states]&255).ravel())))
    assert len(states)*6<=256
    return words,nxt,states,first,second


def pulse(bit,immediate=False):
    if immediate:return ' OUT (254),A\n'
    return ' OUT (C),B\n' if bit else ' DB 237,113\n'


def set_a(bit):return ' LD A,B\n' if bit else ' XOR A\n'


def kernel_source(first,second):
    text='''; Native residentPCM8 component, sixteen PDM outputs every28 T.
; Pentagon nominal3.584MHz gives128k decisions/s and8k PCM samples/s.
; MainBC=10FE (B is the constant EAR-high value); DE=source byte cursor.
; HL=lookup scratch / next FIRST target, IY=current SECOND target,
; IXL=successor feedback offset. Alternate registers and IXH stay untouched.
; SP is a six-byte lookup cursor and later dead scratch: never CALL/PUSH.
; Record: FIRST word, SECOND word, flag byte0, successorOffset byte.
; Enter FIRST with SP=record+2, DE=current PCM address, HL=FIRST address.
; One input sample is prefetched; current/next PCM bytes must both be valid.
; This flat one-bank proof has no IMA decoding, bank handoff, EOF or IRQ.
; Timing ledger is between effective OUT writes: ED OUT12 leaves16 T;
; immediate OUT11 leaves17 T. The latter gaps use7+4+6, neverindexedPOP14.
; Copy H/L into IY through A: direct prefixed H/L copies change semantics.
 ORG 32768
'''
    for word in first:
        text+=f'first_{word}:\n'
        for slot in range(8):
            text+=f'first_{word}_pulse_{slot}:\n'+pulse((word>>(7-slot))&1,slot==7)
            if slot==0:text+=' POP HL\n INC DE\n'
            elif slot==1:text+=' LD A,H\n LD IYH,A\n NOP\n'
            elif slot==2:text+=' LD A,L\n LD IYL,A\n NOP\n'
            elif slot==3:text+=' POP AF\n LD SP,HL\n'
            elif slot==4:text+=' LD IXL,A\n NOP\n NOP\n'
            elif slot==5:text+=' LD L,E\n LD H,D\n NOP\n NOP\n'
            elif slot==6:text+=' LD L,(HL)\n'+set_a(word&1)+' LD SP,HL\n'
            else:text+=' NOP\n NOP\n JP (IY)\n'
    for word in second:
        text+=f'second_{word}:\n'
        for slot in range(8):
            text+=f'second_{word}_pulse_{slot}:\n'+pulse((word>>(7-slot))&1,slot in (1,2))
            if slot==0:text+=f' LD H,{MAP>>8}\n'+set_a((word>>6)&1)+' LD SP,HL\n'
            elif slot==1:text+=' LD H,(HL)\n'+set_a((word>>5)&1)+' LD SP,HL\n'
            elif slot==2:text+=' LD A,IXL\n LD L,A\n NOP\n'
            elif slot==3:text+=' LD SP,HL\n POP HL\n'
            elif slot==7:text+=' NOP\n NOP\n NOP\n JP (HL)\n'
            else:text+=' NOP\n NOP\n NOP\n NOP\n'
    text+='kernel_end:\n NOP\n'
    return text


def tables(labels,words,nxt,states):
    result=bytearray(16384)
    for value in range(64):
        for index,state in enumerate(states):
            word=int(words[value,state]);offset=value*256+index*6
            result[offset:offset+6]=struct.pack('<HHBB',labels[f'first_{word>>8}'],
                labels[f'second_{word&255}'],0,states.index(int(nxt[value,state]))*6)
    return bytes(result),bytes((TABLE>>8)+(value>>2) for value in range(256))


def run(blob,labels,lookup,mapping,words,nxt,states,source,*,initial_state=16,details=False):
    assert 2<=len(source)<=16384
    samples=len(source)-1;m=Z80Machine()
    m.memory[0x8000:0x8000+len(blob)]=blob
    m.memory[TABLE:TABLE+len(lookup)]=lookup;m.memory[MAP:MAP+256]=mapping
    m.memory[SOURCE:SOURCE+len(source)]=source
    start_word=int(words[source[0]>>2,initial_state])
    record=TABLE+(source[0]>>2)*256+states.index(initial_state)*6
    for key,value in dict(bc=0x10FE,de=SOURCE,hl=labels[f'first_{start_word>>8}'],
        ix=0x5500,iy=0xA55A,sp=record+2,af=0x3C01,alt_bc=0x1234,
        alt_de=0x5678,alt_hl=0x9ABC,alt_af=0xDEF0).items():setattr(m,key,value)
    m.iff1=m.iff2=False;m.pc=labels[f'first_{start_word>>8}']
    expected=[];state=initial_state
    for value in source[:-1]:
        word=int(words[value>>2,state]);expected.extend((word>>shift)&1 for shift in range(15,-1,-1))
        state=int(nxt[value>>2,state])
    next_word=int(words[source[-1]>>2,state]);stop=labels[f'first_{next_word>>8}']
    next_record=TABLE+(source[-1]>>2)*256+states.index(state)*6
    budget=samples*448+10000;observed=[];times=[];before=bytes(m.memory)
    def output(port,value):
        assert port in (254,4350) and value in (0,16),(port,value)
        observed.append(value>>4);times.append(budget-m.ticks_to_stop)
        if len(observed)==16*samples:m.set_breakpoint(stop)
    m.set_output_callback(output);m.ticks_to_stop=budget
    while len(observed)<16*samples or m.pc!=stop:
        event=m.run();assert not event&m._TICKS_LIMIT_HIT,'Native component timeout'
    assert observed==expected,('output mismatch',next((i for i,(a,b) in enumerate(zip(observed,expected)) if a!=b),None))
    assert np.diff(times).tolist()==[28]*(len(times)-1)
    assert budget-m.ticks_to_stop==samples*448
    assert m.de==SOURCE+samples and m.ix==0x5500+states.index(state)*6
    assert m.bc==0x10FE
    assert m.hl==stop and m.sp==next_record+2
    assert (m.alt_bc,m.alt_de,m.alt_hl,m.alt_af)==(0x1234,0x5678,0x9ABC,0xDEF0)
    assert bytes(m.memory)==before
    result=dict(samples=samples,outputs=len(observed),period_tstates=448,
        every_hold_tstates=28,bits_exact=True,successor_and_next_pointer_exact=True,
        source_cursor_exact=True,alternate_registers_unchanged=True,no_RAM_writes=True,
        bits_sha256=sha(bytes(observed)),OUT_times_sha256=sha(np.asarray(times,dtype='<u4').tobytes()))
    if details:result.update(bits=observed,times=times)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,
        default=HERE/'evidence/table-pdm-uniform16-component');args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    words,nxt,states,first,second=model()
    blob,labels=assemble(out,kernel_source(first,second));assert 0x8000+len(blob)<MAP
    lookup,mapping=tables(labels,words,nxt,states)
    (out/'lookup.bin').write_bytes(lookup);(out/'pcm-high.bin').write_bytes(mapping)
    cases=[]
    for state in states:
        for value in range(256):
            result=run(blob,labels,lookup,mapping,words,nxt,states,
                bytes([value,(value*73+17)&255]),initial_state=state)
            cases.append(dict(initial_state=state,pcm8=value,**result))
    indices=np.arange(16384,dtype=np.uint32)
    source=((indices*73+(indices>>2)*19+(indices>>8)*131) ^ (indices>>4)).astype('u1').tobytes()
    trajectory=run(blob,labels,lookup,mapping,words,nxt,states,source,details=True)
    (out/'trajectory-pcm8.bin').write_bytes(source)
    (out/'trajectory-bits.u8.gz').write_bytes(gzip.compress(bytes(trajectory.pop('bits')),mtime=0))
    (out/'trajectory-times.u32.gz').write_bytes(gzip.compress(np.asarray(trajectory.pop('times'),dtype='<u4').tobytes(),mtime=0))
    save(out/'all-cells.json',cases)
    report=dict(complete=True,states=states,FIRST_patterns=len(first),SECOND_patterns=len(second),
        kernel_bytes=len(blob),table_allocated_bytes=len(lookup),table_used_bytes=64*len(states)*6,
        pcm_high_bytes=len(mapping),component_fixed_bytes=len(blob)+len(lookup)+len(mapping),
        all_cell_cases=len(cases),all_cell_outputs=16*len(cases),trajectory=trajectory,
        total_native_outputs=16*len(cases)+trajectory['outputs'],
        previous_Pentagon_ordinary_tstates=449,new_ordinary_tstates=448,delta_tstates=-1,
        previous_pulse_holds_tstates=[36,28,28,31,24,26,22,46,22,26,22,30,31,27,34,16],
        new_pulse_holds_tstates=[28]*16,
        rate_scope='3.584MHz Pentagon:128k equally spaced decisions/s; physical clone contention not measured',
        input_scope='Resident PCM8, quantized by same64-level map; no IMA decoding or16-bit-precision claim',
        gaps=[dict(after_output=i,following_OUT='immediate11T' if i in (6,8,9) else 'ED12T',
            useful_plus_padding=17 if i in (6,8,9) else 16) for i in range(16)],
        physical_scope='Flat native CPU through63 ordinary source-page crossings within one16KiB source bank; no bank handoff, EOF, boot, installedFuse or hardware proof',
        no_quality_or_release_claim=True)
    save(out/'report.json',report)
    producer=Path(__file__).read_bytes();(out/'producer.py.gz').write_bytes(gzip.compress(producer,mtime=0))
    dependencies=[]
    for dependency in (HERE/'sdm16_uniform7.py',HERE.parent.parent/'probe_feedback_packets.py'):
        content=dependency.read_bytes();target=out/'producer-source'/(dependency.name+'.gz')
        target.parent.mkdir(exist_ok=True);target.write_bytes(gzip.compress(content,mtime=0))
        dependencies.append(dict(path=dependency.as_posix(),sha256=sha(content)))
    save(out/'producer-dependencies.json',dependencies)
    files=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            content=path.read_bytes();files.append(dict(path=path.relative_to(out).as_posix(),bytes=len(content),sha256=sha(content)))
    save(out/'manifest.json',dict(complete=True,producer_sha256=sha(producer),files=files))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
