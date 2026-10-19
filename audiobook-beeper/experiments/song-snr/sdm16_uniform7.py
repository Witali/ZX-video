"""Counted full-precision first-order kernels; no released-player mutation.

The accepted mechanism of this bounded CPU study is uniform7x64 timing,
not an audio-quality or banked-release claim. A separate exact area kernel
quantifies why multiplying the old long hold is not a free correction.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

import numpy as np
from z80 import Z80Machine

from ima_codec import STEPS, INDEX, decode, encode, require_unclipped

HERE=Path(__file__).resolve().parent


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def assemble(folder,source):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'kernel.asm').write_text(source,encoding='utf-8',newline='\n')
    result=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=kernel.bin',
        '--lstfile=kernel.lst','-s','.*','kernel.asm'],cwd=folder,capture_output=True,text=True)
    (folder/'assembler.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    labels=next(ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith('{'))
    return (folder/'kernel.bin').read_bytes(),labels


def uniform_source():
    text='''; Standalone full16-bit first-order modulator with seven uniform64-T holds.
; A sample lasts448 T; IMA stays compressed and is decoded one sample ahead.
; MainHL=modulo16 accumulator, DE=current full16-bit biased sample, C=16.
; IX=next predictor, alternateHL=IMA row, alternateDE=source cursor,
; alternateBC=delta. AF' holds a prepared nibble only between gaps1 and2.
; MainB/IY are free; OUT(FE),A emits only EAR0/16, with MIC/border0.
; SP is dead after gap3 POPs, and reset before every future POP. No CALL/PUSH.
; Enter high_packet after priming the first LOW nibble; source cursor then
; points at that same byte. Page/bank handling and EOF are not implemented.
; IRQs must remain disabled, including while SP is a dead scratch pointer.
 ORG 0x8000
'''
    for phase in ('low','high'):
        high=phase=='high';text+=phase+'_packet:\n'
        for slot in range(7):
            text+=f'{phase}_pulse_{slot}:\n ADD HL,DE\n SBC A,A\n AND C\n OUT (254),A\n'
            text+=f'{phase}_gap_{slot}:\n'
            if slot==0:
                text+='''; Gap1,34 T: fetch/prepare the next code, then preserve it in AF'.
 EXX
 LD A,(DE)
'''+(' AND 240\n RRCA\n RRCA\n' if high else ' AND 15\n RLCA\n RLCA\n')+''' EX AF,AF'
 EXX
'''
            elif slot==1:
                text+='''; Gap2,26 useful+8 pad: restore code and select its four-byte IMA row.
 EXX
 EX AF,AF'
 OR L
 LD L,A
 LD SP,HL
 EXX
 NOP
 NOP
'''
            elif slot==2:
                text+='''; Gap3,28 useful+6 pad: load delta/next row, then discard lookup SP.
 EXX
 POP BC
 POP HL
 EXX
 LD SP,HL
'''
            elif slot==3:
                text+='''; Gap4,23 useful+11 pad: update next predictor, preserving current DE.
 EXX
 ADD IX,BC
 EXX
 LD A,0
 NOP
'''
            elif slot==4:
                if high:text+='''; Gap5,14 useful+20 pad: both nibbles are consumed; advance source.
 EXX
 INC DE
 EXX
 NOP
 NOP
 NOP
 NOP
 NOP
'''
                else:text+='''; Gap5,34 pad: source still points at its unconsumed high nibble.
 LD A,R
 LD A,R
 NOP
 NOP
 NOP
 NOP
'''
            elif slot==5:
                text+='''; Gap6 is34 T available for future resident-descriptor/paging work.
 LD A,R
 LD A,R
 NOP
 NOP
 NOP
 NOP
'''
            else:
                text+='''; Gap7: current output is finished; latch next predictor into DE.
 LD D,IXH
 LD E,IXL
'''
                if high:text+=''' NOP
 NOP
 JP low_packet
'''
                else:text+=''' LD A,R
 LD A,R
'''
    text+='kernel_end:\n NOP\n'
    return text


def decoder_table():
    result=bytearray()
    for index,step in enumerate(STEPS):
        for code in range(16):
            delta=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
            if code&8:delta=-delta
            next_index=max(0,min(88,index+INDEX[code&7]))
            result+=struct.pack('<HH',delta&65535,0x9000+64*next_index)
    return bytes(result)


def run_uniform(blob,labels,packed,pcm,indices,*,samples,accumulator=32767,details=False):
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    table=decoder_table();m.memory[0x9000:0x9000+len(table)]=table
    m.memory[0xC000:0xC000+len(packed)]=packed
    initial=int(pcm[0])+32768
    for key,value in dict(ix=initial,de=initial,hl=accumulator,bc=0x3310,iy=0x1234,
        alt_hl=0x9000+64*int(indices[0]),alt_de=0xC000,alt_bc=0xABCD,
        alt_af=0x5A5A,sp=0x7777).items():setattr(m,key,value)
    m.iff1=m.iff2=False;m.r=255;budget=max(100000,samples*448+1000)
    observed=[];times=[];predictions=0
    stop=labels['high_packet' if samples%2==0 else 'low_packet']
    before=bytes(m.memory)
    def output(port,value):
        nonlocal predictions
        sample,slot=divmod(len(observed),7)
        assert port in (254,4350) and value in (0,16)
        assert m.de==int(pcm[sample])+32768,('held input',sample,slot,m.de,int(pcm[sample]))
        if slot==4:
            assert m.ix==int(pcm[sample+1])+32768
            assert m.alt_hl==0x9000+64*int(indices[sample+1]);predictions+=1
        observed.append(value>>4);times.append(budget-m.ticks_to_stop)
        if len(observed)==samples*7:m.set_breakpoint(stop)
    m.set_output_callback(output);m.pc=labels['high_packet'];m.ticks_to_stop=budget
    while len(observed)<samples*7 or m.pc!=stop:
        event=m.run();assert not event&m._TICKS_LIMIT_HIT,'Uniform kernel timeout'
    expected=[];state=accumulator
    for sample in range(samples):
        value=int(pcm[sample])+32768
        for _ in range(7):
            state+=value;expected.append(int(state>=65536));state&=65535
    assert observed==expected
    assert np.diff(times).tolist()==[64]*(len(times)-1)
    assert budget-m.ticks_to_stop==samples*448
    assert m.hl==state and m.de==int(pcm[samples])+32768
    assert m.ix==int(pcm[samples])+32768 and m.iy==0x1234 and m.bc==0x3310
    assert bytes(m.memory)==before
    result=dict(samples=samples,bits=len(observed),native_tstates=samples*448,
        all_actual_OUT_holds_tstates=64,pcm_period_tstates=448,decision_rate_hz=56000,
        every_source_bit_exact=True,every_predictor_index_exact=True,full_input_held_until_gap7=True,
        no_RAM_writes_or_CALL_PUSH=True,final_accumulator=state,predictor_checks=predictions)
    if details:result.update(bits_values=observed,OUT_tstates=times)
    return result


def uniform_audit(out):
    blob,labels=assemble(out/'uniform7',uniform_source())
    # Reference-encoded arbitrary mixed source exercises decoder rows, signs,
    # allnibble values, source pages and full predictor precision. It stays in
    # one physical16-KiB source bank: bank handoff is not part of this proof.
    clock=np.arange(8192)
    source=np.clip(np.rint(128+80*np.sin(clock*.173)+27*np.sin(clock*.713)),0,255).astype('u1')
    packed=encode(source);guard=require_unclipped(packed);pcm,indices=decode(packed)
    trajectory=run_uniform(blob,labels,packed,pcm,indices,samples=len(pcm)-2,details=True)
    bit_bytes=bytes(trajectory.pop('bits_values'))
    time_bytes=np.asarray(trajectory.pop('OUT_tstates'),dtype='<u4').tobytes()
    (out/'uniform7/trajectory-bits.u8.gz').write_bytes(gzip.compress(bit_bytes,mtime=0))
    (out/'uniform7/trajectory-times.u32.gz').write_bytes(gzip.compress(time_bytes,mtime=0))
    trajectory.update(bits_sha256=hashlib.sha256(bit_bytes).hexdigest(),
                      times_sha256=hashlib.sha256(time_bytes).hexdigest())
    (out/'uniform7/trajectory.ima').write_bytes(packed)
    cases=[]
    for unsigned in (0,1,32767,32768,32769,65534,65535):
        values=np.full(10,unsigned-32768,dtype=np.int16);idx=np.zeros(10,dtype=np.uint8)
        cases.append(dict(unsigned_pcm16=unsigned,report=run_uniform(blob,labels,bytes(8),values,idx,samples=8,details=True)))
    # A common initial accumulator lets one input LSB flip a real output bit.
    witnesses=[]
    for unsigned in (32768+37,32768+38):
        values=np.full(6,unsigned-32768,dtype=np.int16)
        witnesses.append(dict(signed_pcm16=unsigned-32768,
            report=run_uniform(blob,labels,bytes(4),values,np.zeros(6,dtype=np.uint8),
                samples=4,accumulator=65536-(32768+38),details=True)))
    assert witnesses[0]['report']['bits_values'][0]!=witnesses[1]['report']['bits_values'][0]
    gaps=[dict(gap=1,total=34,low_useful=34,high_useful=34,low_free=0,high_free=0),
        dict(gap=2,total=34,low_useful=26,high_useful=26,low_free=8,high_free=8),
        dict(gap=3,total=34,low_useful=28,high_useful=28,low_free=6,high_free=6),
        dict(gap=4,total=34,low_useful=23,high_useful=23,low_free=11,high_free=11),
        dict(gap=5,total=34,low_useful=0,high_useful=14,low_free=34,high_free=20),
        dict(gap=6,total=34,low_useful=0,high_useful=0,low_free=34,high_free=34),
        dict(gap=7,total=34,low_useful=16,high_useful=26,low_free=18,high_free=8)]
    return dict(complete=True,kernel_bytes=len(blob),labels=labels,reference_trajectory=trajectory,
        reference_saturation_guard=guard,extreme_vectors=cases,one_LSB_output_witness=witnesses,
        pulse_kernel_tstates=30,uniform_hold_tstates=64,gaps=gaps,
        low_useful_total=127,high_useful_total=151,low_free_total=111,high_free_total=87,
        physical_scope='Flat native CPU, one source bank; no banked mapping, boot, EOF or Fuse proof',
        arithmetic='Unsigned16 first-order modulo carry; equal64-T holds make decision-index error exactly proportional to physical area error',
        quality_claim=False)


def area_source(hold):
    return f'''; Exact area-error inner pulse for h={hold}; product supplied externally.
; A:HL is signed24-bit q. C:DE is signed24-bit h*(U-32768).
; q stayswithin +/-74*65536; trueintermediate fits25 signed bits. The ADC
; overflow flag disambiguates the sign when its24-bit representation wraps.
; BC high is scratch/restored q high; IX/IY/alternate state/SP are unchanged.
; All four sign/overflow paths cost78 T and emit only EAR0/16.
 ORG 0x8000
start:
 ADD HL,DE
 ADC A,C
 JP PE,overflow
 JP M,normal_negative
 SUB {hold//2}
 LD B,A
 LD A,16
 JP emit
normal_negative:
 ADD A,{hold//2}
 LD B,A
 LD A,0
 JP emit
overflow:
 JP P,overflow_negative
 SUB {hold//2}
 LD B,A
 LD A,16
 JP emit
overflow_negative:
 ADD A,{hold//2}
 LD B,A
 LD A,0
 JP emit
emit:
 OUT (254),A
 LD A,B
complete:
 NOP
'''


def weighted_audit(out):
    count=0;overflow_count=0;subreports=[];half=74*65536
    for hold in (30,148):
        blob,labels=assemble(out/f'weighted-{hold}',area_source(hold));m=Z80Machine()
        m.memory[0x8000:0x8000+len(blob)]=blob;m.set_breakpoint(labels['complete'])
        bit=[];m.set_output_callback(lambda port,value:bit.append((port,value)))
        for q in (-half,-15*65536,-1,0,1,15*65536-1,half-1):
            for unsigned in range(65536):
                product=hold*(unsigned-32768);stored_product=product&0xFFFFFF;stored_q=q&0xFFFFFF
                m.hl=stored_q&65535;m.a=stored_q>>16;m.de=stored_product&65535
                m.c=stored_product>>16;m.ix=unsigned;m.iy=0x1234;m.sp=0x7777
                m.alt_af=0xA5A5;m.alt_bc=0x2468;m.alt_de=0xC123;m.alt_hl=0xABCD
                m.pc=labels['start'];m.ticks_to_stop=1000;bit.clear()
                while m.pc!=labels['complete']:
                    event=m.run();assert not event&m._TICKS_LIMIT_HIT
                true_intermediate=q+product;wanted=int(true_intermediate>=0)
                wanted_q=q+hold*(unsigned-65536*wanted)
                raw=(m.a<<16)|m.hl;actual_q=raw-(1<<24) if raw&(1<<23) else raw
                assert actual_q==wanted_q and bit==[(254|(wanted*16)<<8,wanted*16)]
                assert 1000-m.ticks_to_stop==78
                assert -half<=wanted_q<half
                assert (m.ix,m.iy,m.sp,m.alt_af,m.alt_bc,m.alt_de,m.alt_hl)==(unsigned,0x1234,0x7777,0xA5A5,0x2468,0xC123,0xABCD)
                count+=1;overflow_count+=int(not -(1<<23)<=true_intermediate<(1<<23))
        subreports.append(dict(hold=hold,native_tstates_per_pulse=78,all_unsigned16_inputs=65536,
            state_vectors=7,external_product_formation_and_loads_not_counted=True))
    return dict(complete=True,native_cases=count,true25bit_intermediate_cases=overflow_count,
        q_signed_bits=24,intermediate_signed_bits=25,interval_holds=[30]*10+[148],
        invariant_absolute_q_maximum=half,
        update='q_next=q+h*(U-65536*y), y=sign(q+h*(U-32768))>=0',
        inner_native_tstates_per_pulse=78,eleven_inner_pulses_tstates=858,
        sample_decoder_and_product_load_formation_excluded=True,variants=subreports,
        decision='Reject this concrete weighted24-bit kernel for448-T11-pulse playback; the counted inner pulses alone exceed the period, not an impossibility bound for all algorithms')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    report=dict(date='2026-10-19',uniform7=uniform_audit(out),weighted_old_schedule=weighted_audit(out),
        complete=True,host_elapsed_seconds=time.perf_counter()-started,
        original_player_and_encoders_changed=False,corpus_Fuse_or_release_claim=False)
    save(out/'report.json',report)
    (out/'sdm16_uniform7.py').write_bytes(Path(__file__).read_bytes())
    manifest=[dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
    save(out/'manifest.json',dict(files=len(manifest),artifacts=manifest))
    print(json.dumps(dict(complete=True,uniform_samples=report['uniform7']['reference_trajectory']['samples'],
        weighted_native_cases=report['weighted_old_schedule']['native_cases'],elapsed=report['host_elapsed_seconds'])))


if __name__=='__main__':main()
