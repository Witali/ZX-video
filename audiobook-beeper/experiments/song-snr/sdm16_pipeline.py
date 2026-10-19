"""Bounded CPU/liveness probes for precision-player scheduling opportunities.

These fragments retain the current SECOND logic and legacy bank tail. They
do not implement a full16 modulator or complete player. The cached-byte probe
removes a duplicate IMA read and regular-page tail; the bank229-T extra is
still explicitly present. Changed intra-packet holds need a matched model.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from z80 import Z80Machine


HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]
MODES=('baseline','cache_b','cache_altc','inline_altbc','prefetch_uniform')


def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def pulse(bit):return ' OUT (C),D\n' if bit else ' DB 0xED,0x71\n'


def assembly(patterns):
    text='''; Standalone uncontended Pentagon CPU probe, not a release player.
; At FIRST suffix, mainHL/AF are dead, BC supplies the ULA port, D=16,
; E feedback is replaced by SECOND, IX exact predictor, IY current SECOND.
; ALT HL row and DE source remain live. ALT BC delta dies after ADD IX,BC.
; MainB is only a port-high byte until a bank tail explicitly saves its bit;
; this probe's B scratch interpretation is Pentagon-only, with no ULA waits.
; SP points at the three-word next-packet record and is not a call stack.
 ORG 0x8000
entry_baseline:
 JP delay_baseline
entry_cache_b:
 JP delay_cache_b
entry_cache_altc:
 JP delay_cache_altc
; Inline20T copy plus6T padding replaces the entire26T shared pacing delta.
; A=IXH on entry. ALT BC keeps the next exact16-bit sample through SECOND,
; but is overwritten by the following FIRST decoder POP BC.
entry_inline_altbc:
 EXX
 LD B,A
 LD C,IXL
 EXX
 INC HL
 JP (IY)
entry_prefetch_uniform:
 JP delay_baseline
delay_baseline:
 NOP
 NOP
 NOP
 NOP
 JP (IY)
delay_cache_b:
 LD B,IXL
 NOP
 NOP
 JP (IY)
delay_cache_altc:
 EXX
 LD C,IXL
 EXX
 JP (IY)
'''
    for p in patterns:
        for pipelined in (False,True):
            suffix=f'{p}_{int(pipelined)}'
            text+=f'second_{suffix}:\n'+pulse(p>>7&1)+' POP HL\n'+pulse(p>>6&1)+' POP IY\n'+pulse(p>>5&1)+' POP DE\n'+pulse(p>>4&1)
            text+=f" EX AF,AF'\n CCF\n JP C,high_{suffix}\n"+pulse(p>>3&1)+" EX AF,AF'\n EXX\n LD A,(DE)\n EXX\n"
            if pipelined:text+=' LD B,A\n'
            text+=pulse(p>>2&1)+' AND 15\n RLCA\n RLCA\n'+pulse(p>>1&1)
            if pipelined:
                # AND15 then two left rotates always leave carry0. RET C is
                # therefore a five-T no-op; it never reads the lookup SP.
                # Removing one NOP pays the early LD B,A. Replacing JP10 by
                # RET C5+NOP4 removes one more T, balancing the high path.
                text+=' RET C\n NOP\n NOP\n NOP\n'
            else:text+=' JP $+3\n NOP\n NOP\n NOP\n'
            text+=pulse(p&1)+' JP (HL)\n'+f'high_{suffix}:\n'+pulse(p>>3&1)+" EX AF,AF'\n"
            text+=(' LD A,B\n' if pipelined else ' EXX\n LD A,(DE)\n EXX\n')
            text+=pulse(p>>2&1)+' AND 240\n RRCA\n RRCA\n'+pulse(p>>1&1)+' EXX\n'
            if pipelined:
                # INC DE updates both address bytes uniformly. INC D/DEC D
                # tests the restored high byte without touching prefetched A.
                # All live source addresses are C000..FFFF, so D0 identifies
                # the FFFF-to0000 wrap exactly; the handler replaces DE.
                text+=f' INC DE\n INC D\n DEC D\n JP Z,bank_{p&1}\n'
            else:text+=f' INC E\n JP Z,page_{p&1}\n'
            text+=' EXX\n'+pulse(p&1)+' JP (HL)\n'
    for bit in (0,1):
        text+=f'page_{bit}:\n INC D\n JP Z,bank_{bit}\n EXX\n'+pulse(bit)+' JP (HL)\n'
        text+=f"bank_{bit}:\n EX AF,AF'\n EXX\n LD B,{16*bit}\n EXX\n JP bank_jump\n"
    text+='''bank_jump:
 JP bank_tail
; Unchanged legacy descriptor critical path. ALT HL must be preserved; AF'
; protects the already-prefetched high nibble while paging changes A.
bank_tail:
 LD (saved_row),HL
 LD HL,(next_record)
 LD A,(HL)
 OR A
 JP Z,exhausted
 LD (paging),A
 INC HL
 LD D,(HL)
 LD E,0
 INC HL
 LD A,(HL)
 INC HL
 LD (next_record),HL
 LD HL,(saved_row)
 JP high_done
 LD BC,0x1FFD
 OUT (C),A
high_done:
 LD BC,0x7FFD
 LD A,(paging)
 OUT (C),A
 EXX
 SCF
 EX AF,AF'
 OUT (C),B
 JP (HL)
exhausted:
 HALT
complete:
 NOP
saved_row: EQU 0x6A10
next_record: EQU 0x6A12
paging: EQU 0x6A14
'''
    return text


def build(output,patterns):
    source=assembly(patterns)
    (output/'probe.asm').write_text(source,encoding='utf-8',newline='\n')
    result=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=probe.bin','--lstfile=probe.lst','-s','.*','probe.asm'],
        cwd=output,capture_output=True,text=True)
    (output/'assembler.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    labels=next(ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith('{'))
    return (output/'probe.bin').read_bytes(),labels


def machine(blob,labels,p,phase,cursor,source_byte,mode,ix=0x8125):
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    m.memory[0x6000:0x6006]=bytes([labels['complete']&255,labels['complete']>>8,0x34,0x12,0x42,0x10])
    m.memory[cursor]=source_byte
    m.memory[0x6A00:0x6A03]=bytes([0x58,0xC0,0])
    m.memory[0x6A12:0x6A14]=bytes([0,0x6A])
    # A FIRST completed its lookup. A still holds IXH, HL=SP the packet
    # record; the alternate decoder row and source must survive SECOND.
    for key,value in dict(af=(ix>>8)*256+0xA5,bc=((source_byte if mode=='prefetch_uniform' and phase=='high' else 0)<<8)|0xFE,
        de=0x1042,hl=0x6000,ix=ix,iy=labels[f'second_{p}_{int(mode=="prefetch_uniform")}'],sp=0x6000,
        alt_af=0x4201 if phase=='low' else 0x4200,alt_bc=0xABCD,alt_de=cursor,alt_hl=0x6400).items():
        setattr(m,key,value)
    m.iff1=m.iff2=False;m.pc=labels['entry_'+mode];m.set_breakpoint(labels['complete'])
    return m


def execute(m,budget=5000):
    events=[]
    m.set_output_callback(lambda port,value:events.append((budget-m.ticks_to_stop,port,value)))
    m.ticks_to_stop=budget
    # A single fragment is shorter than one emulated video frame; the only
    # expected stop is the explicit complete breakpoint.
    event=m.run()
    assert not event&m._TICKS_LIMIT_HIT
    return budget-m.ticks_to_stop,events


def run(output):
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('Use a fresh output; preserve prior attempts')
    output.mkdir(parents=True,exist_ok=True)
    table=HERE/'evidence/sdm16-architecture/model-b-all-pcm16-cells.npz'
    with np.load(table) as oracle:
        reached={16}
        while True:
            after=reached|set(map(int,oracle['successors'][:,sorted(reached)].ravel()))
            if after==reached:break
            reached=after
        patterns=sorted(map(int,np.unique(oracle['words'][:,sorted(reached)]&255)))
    blob,labels=build(output,patterns)
    assert 0x8000+len(blob)<0xC000,'Keep this standalone probe code fixed'
    cases=0;timings={};examples=[]
    for p in patterns:
        for phase in ('low','high'):
            for scenario,cursor in (('ordinary',0xD034),('page',0xD0FF),('bank',0xFFFF)):
                for source_byte in (0,0xAB,255):
                    observations={}
                    for mode in MODES:
                        m=machine(blob,labels,p,phase,cursor,source_byte,mode)
                        elapsed,events=execute(m)
                        assert m.pc==labels['complete']
                        pulses=[(time,value) for time,port,value in events if port&255==254]
                        assert [value for _,value in pulses]==[16*((p>>(7-k))&1) for k in range(8)]
                        expected_code=(source_byte&15)*4 if phase=='low' else (source_byte&240)//4
                        assert m.a==expected_code
                        bank=phase=='high' and scenario=='bank'
                        expected_cursor=cursor if phase=='low' else 0xC000 if bank else cursor+1
                        assert m.alt_de==expected_cursor and m.alt_hl==0x6400
                        assert m.ix==0x8125 and m.hl==labels['complete'] and m.iy==0x1234 and m.sp==0x6006 and m.de==0x1042
                        assert m.alt_af&1==(phase=='high')
                        expected_b=16*(p&1) if bank else (0x25 if mode=='cache_b' else source_byte if mode=='prefetch_uniform' else 0)
                        assert m.bc==(expected_b<<8)|254
                        expected_altbc=0x7FFD if bank else (0xAB25 if mode=='cache_altc' else 0x8125 if mode=='inline_altbc' else 0xABCD)
                        assert m.alt_bc==expected_altbc
                        if bank:assert int(m.memory[0x6A12])+256*int(m.memory[0x6A13])==0x6A03
                        observations[mode]=(elapsed,pulses)
                        cases+=1
                    for mode in ('cache_b','cache_altc','inline_altbc'):
                        assert observations[mode]==observations['baseline']
                    wanted_delta=-1 if phase=='low' or scenario=='ordinary' else -15
                    assert observations['prefetch_uniform'][0]-observations['baseline'][0]==wanted_delta
                    key=phase+'-'+scenario
                    timings.setdefault(key,{mode:elapsed for mode,(elapsed,_) in observations.items()})
                    assert timings[key]=={mode:elapsed for mode,(elapsed,_) in observations.items()}
                    if p in (patterns[0],patterns[-1]) and source_byte==0xAB:
                        examples.append(dict(pattern=p,phase=phase,scenario=scenario,outputs={mode:value for mode,value in observations.items()}))
    assert timings['high-page']['baseline']-timings['high-ordinary']['baseline']==14
    assert timings['high-bank']['baseline']-timings['high-ordinary']['baseline']==243
    assert timings['high-page']['prefetch_uniform']==timings['high-ordinary']['prefetch_uniform']
    assert timings['high-bank']['prefetch_uniform']-timings['high-ordinary']['prefetch_uniform']==229
    # Demonstrate a genuine early-paging window: after LOW cached the whole
    # byte, change its backing memory. HIGH still extracts its original half.
    p=patterns[0];m=machine(blob,labels,p,'low',0xFFFF,0xAB,'prefetch_uniform')
    execute(m);assert m.b==0xAB
    m.memory[0xFFFF]=0xDC
    m.pc=labels['entry_prefetch_uniform'];m.sp=0x6000;m.iy=labels[f'second_{p}_1'];m.hl=0x6000;m.a=0x81
    execute(m);assert m.a==40 and m.alt_de==0xC000
    report=dict(complete=True,scope='Standalone CPU fragments only; no integrated full16 selector, renderer, disk or physical emulator proof',
        native_cases=cases,second_patterns=len(patterns),timings=timings,examples=examples,
        liveness=dict(main_HL_AF_dead_at_first_suffix=True,alt_BC_dead_after_ADD_IX_until_next_POP=True,
            main_B_scratch_pentagon_only=True,main_B_not_legacy_ULA_wait_safe=True,
            lookup_SP_not_call_stack=True,low_RET_C_proven_untaken=True),
        equal_time_padding_bodies=dict(baseline_shared=16,cache_B_from_IXL=16,cache_ALTC_from_IXL=16,
            inline_full_predictor_copy=26,inline_dictionary_growth_per_first_pattern=5),
        cached_source_memory_changed_after_low_high_nibble_still_original=True,
        complete_source_clock_claim=False,
        derived_packet_totals=dict(previous_ordinary449=449,prospective_ordinary_and_page=448,
            prospective_bank=677,remaining_bank_extra=229),
        source_pulse_holds_changed=True,matched_new_modulator_model_required=True,
        descriptor_prefetch_microsequencer_implemented=False,
        physical_paging_ULA_NMI_UI_and_full_RAM_not_verified=True,
        decision='Useful lower-byte scratch and duplicate-read/page-tail removal are proven in bounded CPU fragments. Bank critical path remains229T; no gap-free full16 player or extra RAM is established.',
        original_sources={name:sha((AUDIO/name).read_bytes()) for name in ('stream-player.asm','stream-worker.asm','stream-playback-progress.asm')},
        producer_sha256=sha(Path(__file__).read_bytes()))
    save(output/'report.json',report)
    files={path.name:dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for path in sorted(output.iterdir()) if path.is_file()}
    save(output/'manifest.json',dict(complete=True,artifact_files=files))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=run(args.output)
    print(json.dumps(dict(complete=True,native_cases=report['native_cases'],timings=report['timings'])))
