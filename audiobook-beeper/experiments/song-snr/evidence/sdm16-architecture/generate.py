"""Bounded source-independent precision architecture audit; no player edits.

Run from this worktree with its normal pyz80/z80/NumPy dependencies. Assembly
and results are written only to --output. No audio corpus or Fuse run occurs.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from z80 import Z80Machine

from direct_player import HOLDS
from probe_feedback_packets import integral_table

HERE=Path(__file__).resolve().parent
PLAYER=HERE.parents[3]


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def assemble(out,name,source):
    folder=out/name;folder.mkdir(parents=True,exist_ok=True)
    (folder/'kernel.asm').write_text(source,encoding='utf-8',newline='\n')
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=kernel.bin',
        '--lstfile=kernel.lst','-s','.*','kernel.asm'],cwd=folder,capture_output=True,text=True)
    (folder/'assembler.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(line) for line in run.stdout.splitlines() if line.startswith('{'))
    return (folder/'kernel.bin').read_bytes(),labels


def decoder(high=False):
    # Actual table-decoder instructions, with fresh direct-modulation register
    # ownership: mainHL accumulator, mainDE sample, mainC16. AlternateHL row,
    # alternateDE source cursor, alternateBC IMA delta, IX exact predictor.
    # EXX protects mainC16, so it needs only one setup outside the sample loop.
    nibble=('AND 240\n RRCA\n RRCA\n INC DE' if high else 'AND 15\n RLCA\n RLCA')
    return f'''EXX
 LD A,(DE)
 {nibble}
 OR L
 LD L,A
 LD SP,HL
 POP BC
 POP HL
 ADD IX,BC
 EXX
 LD D,IXH
 LD E,IXL
'''


def first_order_source(mask_c=False,pulses=16,padded=False):
    body=' ADD HL,DE\n SBC A,A\n '+('AND C' if mask_c else 'AND 16')+'\n OUT (254),A\n'
    text='''; Standalone counted precision feasibility kernel, not a release player.
; Unclipped IMA predictor IX is copied to mainDE after each table decode.
; mainHL is a16-bit modulo accumulator, mainC16 is preserved by EXX.
; ADD carry becomes only EAR bit4; MIC and border stay0. AF is scratch.
; DEC/INC source paging, IRQ, UI and real disk delays are not implemented.
 ORG 0x8000
'''
    pairs=2 if padded else 1
    for pair in range(pairs):
        text+=f'low_{pair}:\n'+decoder(False)
        if padded:text+=' LD A,R\n NOP\n' #13T, A/F die in first ADD/SBC.
        text+=body*pulses+f'low_complete_{pair}:\n'
        text+=decoder(True)
        if padded:text+=' LD A,R\n NOP\n NOP\n' #17T, same dead A/F.
        text+=body*pulses
        text+=f' JP '+(f'low_{pair+1}' if pair+1<pairs else 'complete')+'\n'
    return text+'complete:\n NOP\n'


def snapshot(m):
    return {name:getattr(m,name) for name in ('af','bc','de','hl','ix','iy','sp',
        'alt_af','alt_bc','alt_de','alt_hl')}


def kernel_audit(out,mask_c=False,pulses=16,padded=False):
    name=('mask-c' if mask_c else 'mask-immediate')+f'-{pulses}'+('-padded' if padded else '')
    blob,labels=assemble(out,name,first_order_source(mask_c,pulses,padded))
    reports=[];budget=100000
    targets=(0,1,32767,32768,32769,65534,65535)
    for target in targets:
        m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
        # IMA index0/code0 has exact integer delta0 and returns the same row.
        # It isolates arbitrary full-range16-bit input from source changes.
        m.memory[0x9000:0x9004]=bytes.fromhex('00000090')
        m.memory[0xC000:0xC004]=bytes(4)
        for key,value in dict(ix=target,hl=32767,de=0xABCD,bc=0x3310,
            alt_hl=0x9000,alt_de=0xC000,alt_bc=0xFEDC,alt_af=0xA5A5,
            iy=0x1234,sp=0x7777).items():setattr(m,key,value)
        m.iff1=m.iff2=False;m.r=255
        observed=[]
        def output(port,value):observed.append((budget-m.ticks_to_stop,port,value))
        m.set_output_callback(output);m.pc=labels['low_0'];m.set_breakpoint(labels['complete'])
        m.ticks_to_stop=budget;event=m.run();assert m.pc==labels['complete'],(name,event,m.pc)
        elapsed=budget-m.ticks_to_stop
        accumulator=32767;bits=[]
        for _ in observed:
            accumulator+=target;bits.append(int(accumulator>=65536));accumulator%=65536
        assert [x[2] for x in observed]==[bit*16 for bit in bits]
        assert all(x[1]&255==254 and x[2] in (0,16) for x in observed)
        assert m.hl==accumulator and m.ix==target and m.de==target
        assert m.bc==0x3310 and m.alt_af==0xA5A5 and m.iy==0x1234
        assert m.sp==0x9004 and m.alt_hl==0x9000
        expected=(1792 if padded else 1166 if mask_c else 1262)
        assert elapsed==expected,(name,elapsed,expected)
        starts=[observed[i][0] for i in range(0,len(observed),pulses)]
        if padded:assert np.diff(starts).tolist()==[448,448,448]
        reports.append(dict(input_unsigned16=target,elapsed_tstates=elapsed,
            source_packet_first_OUT_tstates=starts,events=observed,final_registers=snapshot(m),
            exact_unsigned16_accumulator=True,main_C16_and_alternate_AF_preserved=True))
    step=30 if mask_c else 33
    return dict(name=name,pulses_per_sample=pulses,kernel_tstates_per_pulse=step,
        kernel_instructions=([['ADD HL,DE',11],['SBC A,A',4],['AND C',4],['OUT (254),A',11]] if mask_c else
            [['ADD HL,DE',11],['SBC A,A',4],['AND16',7],['OUT (254),A',11]]),
        decoder_tstates_low=95,decoder_tstates_high=101,final_high_JP_tstates=10,
        setup_main_C16_once_tstates=7 if mask_c else 0,
        ordinary_low_tstates=(438 if padded else 95+pulses*step),
        ordinary_high_tstates=(458 if padded else 111+pulses*step),
        actual_448_packet_OUT_clock=padded,
        padded_holds_tstates=[30]*10+[148] if padded else None,
        paging_UI_contention_and_quality_verified=False,vectors=reports)


def residual_source():
    return '''; Fractional q-input correction only; this is not an integrated modulator.
; IX unsigned16 predictor, fraction is a9-bit accumulator in two fixed bytes.
; Add low10 predictor bits to fraction; return A=carry0/1/2 in q*8 units.
; Preserve IX/IY/BC/DE, alternate registers and AF'. Main HL/A/F are scratch.
; Processing high partial first preserves the carry from the low-byte add.
 ORG 0x8000
fraction: EQU 0xAF00
start:
 LD HL,fraction+1
 LD A,IXH
 AND 3
 ADD A,(HL)
 LD (HL),A
 DEC HL
 LD A,IXL
 ADD A,(HL)
 LD (HL),A
 INC HL
 LD A,(HL)
 ADC A,0
 RRA
 LD (HL),0
 RL (HL)
fraction_complete:
 ; Three256-aligned maps translate old compact offset to an injected offset.
 ADD A,0xA0
 LD H,A
 LD L,E
 LD E,(HL)
complete:
 NOP
'''


def residual_audit(out):
    blob,labels=assemble(out,'fractional-q-injection',residual_source())
    holds=HOLDS.copy();holds[7]+=26
    words,nxt,_=integral_table(64,2,holds=holds,beta=.5,extent=.5,pcm_origin=0)
    reached={16};layers=[]
    while True:
        injected={min(15,state//2+carry)*2+state%2 for state in reached for carry in (0,1,2)}
        after=reached|injected|set(map(int,nxt[:,sorted(injected)].ravel()))
        layers.append(dict(before=sorted(reached),injected=sorted(injected),after=sorted(after)))
        if after==reached:break
        reached=after
    states=sorted(reached);assert len(states)==24
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    for carry in (0,1,2):
        for offset,state in enumerate(states):
            injected=min(15,state//2+carry)*2+state%2
            m.memory[0xA000+256*carry+6*offset]=states.index(injected)*6
    budget=10000;native=0;observed_carries=set()
    for low in range(1024):
        for fraction in (0,1,255,256,511):
            target=0x8000|low;initial=states.index(16)*6
            for key,value in dict(ix=target,iy=0x1234,bc=0x5678,de=0x1000|initial,
                alt_hl=0x2222,alt_de=0x3333,alt_bc=0x4444,alt_af=0xA5A5,sp=0x7777).items():setattr(m,key,value)
            m.memory[0xAF00]=fraction&255;m.memory[0xAF01]=fraction>>8
            m.pc=labels['start'];m.set_breakpoint(labels['complete']);m.ticks_to_stop=budget
            while m.pc!=labels['complete']:
                event=m.run();assert not event&m._TICKS_LIMIT_HIT,'Residual probe timeout'
            elapsed=budget-m.ticks_to_stop;carry,remainder=divmod(low+fraction,512)
            assert elapsed==138,(low,fraction,elapsed)
            assert int(m.memory[0xAF00])+256*int(m.memory[0xAF01])==remainder
            expected_state=min(15,16//2+carry)*2+16%2
            assert m.e==states.index(expected_state)*6
            assert m.d==16 and m.ix==target and m.iy==0x1234 and m.bc==0x5678
            assert (m.alt_hl,m.alt_de,m.alt_bc,m.alt_af,m.sp)==(0x2222,0x3333,0x4444,0xA5A5,0x7777)
            native+=1;observed_carries.add(carry)
    # Exhaust the actual9-bit residual/low10-bit domain with independent
    # integer byte arithmetic, not the primary table generator or audio.
    for low in range(1024):
        for fraction in range(512):
            lower=(low&255)+(fraction&255)
            upper=(low>>8)+(fraction>>8)+(lower>>8)
            assert ((upper>>1),((upper&1)<<8)|(lower&255))==divmod(low+fraction,512)
    return dict(fraction_lattice='q has unit1/8; low10 input contributes low10/512 q-units per16-pulse packet',
        full_input16_fraction_is_9_bits=True,implementation_position='Hypothesis: inject carried q at a packet boundary; not equal to full-input decisions inside that packet',
        fractional_native_tstates=116,map_native_tstates=22,total_added_native_tstates=138,
        native_cases=native,all_524288_fraction_low10_pairs_integer_verified=True,
        observed_carries=sorted(observed_carries),all_input_bins=64,layers=layers,
        reached_states=states,state_count=24,record_bytes=6,row_bytes=144,
        decoder_rows_begin_at_page_offset=128,overlap_bytes_per_packet_page=16,
        six_byte_rows_24_vs_18=True,map_alignment_reserved_bytes=768,
        map_useful_offsets_per_page=139,fraction_RAM_bytes=2,
        physical_timing_if_added_without_other_changes={'128':561,'scorpion':561,'pentagon448':586,'pentagon449':587},
        existing_pacing_slack_maximum26_insufficient=True,
        native_register_guards=True,quality_or_integrated_player_verified=False)


def hierarchical_dimensions(out):
    # Enumerate the actual new C counterfactual B, rather than substituting a
    # related Python recurrence. This is a model-B memory catalogue, not a
    # formal exact-arithmetic certificate or a player quality proof.
    import sdm16_precision as precision
    binary=precision.build_executable();started=time.perf_counter()
    cells=np.empty(65536*32,dtype=np.dtype([('pcm','<i2'),('seed','u1')],align=False))
    cells['pcm']=np.repeat(np.arange(-32768,32768,dtype=np.int16),32)
    cells['seed']=np.tile(np.arange(32,dtype=np.uint8),65536)
    assert cells.dtype.itemsize==3
    with tempfile.TemporaryDirectory(dir=out,prefix='cells-scratch-') as scratch:
        scratch=Path(scratch).resolve();assert scratch.is_relative_to(out)
        cells.tofile(scratch/'cells.bin')
        words,nxt,statistics=precision.execute(binary,'cells','b',scratch/'cells.bin',
            scratch/'words.bin',scratch/'states.bin')
    elapsed=time.perf_counter()-started
    words=words.reshape(65536,32);nxt=nxt.reshape(65536,32)
    np.savez_compressed(out/'model-b-all-pcm16-cells.npz',words=words,successors=nxt,
        signed_pcm16=np.arange(-32768,32768,dtype=np.int16),seeds=np.arange(32,dtype=np.uint8))
    shutil.copyfile(precision.SOURCE,out/'sources/sdm16_precision.c')
    shutil.copyfile(Path(precision.__file__),out/'sources/sdm16_precision.py')
    reached={16};previous=None
    while reached!=previous:
        previous=reached.copy();reached|=set(map(int,nxt[:,sorted(reached)].ravel()))
    active=sorted(reached);pairs=(words[:,active].astype(np.uint32)<<8)|nxt[:,active]
    runs=np.count_nonzero(pairs[1:]!=pairs[:-1],axis=0)+1
    leaves={pairs[i:i+256,j].astype('<u4').tobytes() for j in range(len(active)) for i in range(0,65536,256)}
    first=len(np.unique(words[:,active]>>8));second=len(np.unique(words[:,active]&255))
    pointers=(0x8340+42*first+64*second+255)&~255
    return dict(scope='Actual source-independent C modelB65536-input catalogue; not formal arithmetic or quality proof',
        c_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        c_source_sha256=hashlib.sha256(precision.SOURCE.read_bytes()).hexdigest(),
        c_cells_statistics=statistics,cell_enumeration_elapsed_seconds=elapsed,
        all_cells=65536*32,input_records_bytes=cells.nbytes,
        input_records_sha256=hashlib.sha256(cells.tobytes()).hexdigest(),
        input_levels=65536,feedback_states=active,state_count=len(active),
        raw_current_six_byte_records=65536*len(active)*6,
        unique_word_successor_records=len(np.unique(pairs)),
        runs_per_state=runs.tolist(),total_interval_runs=int(runs.sum()),
        interval_bound16_plus_pointer16_bytes=int(runs.sum())*4,
        compact_three_byte_word_successor_records=len(np.unique(pairs))*3,
        current_six_byte_dispatch_records=len(np.unique(pairs))*6,
        two_level_8plus8_bit_unique_leaves=len(leaves),four_byte_leaf_bytes=1024,
        two_level_total_bytes=len(leaves)*1024+256*len(active)*2,
        first_patterns=first,second_patterns=second,
        current_dictionary_code_bytes=42*first+64*second,
        current_pcm_high_address=pointers,current_resident_end=pointers+256+1024+1088,
        fixed_bank2_limit=0xC000,current_direct_layout_overflow_before_worker=max(0,pointers+2368-0xC000))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    sources=out/'sources';sources.mkdir(exist_ok=True)
    for name in ('direct_player.py','stream-player.asm','stream-worker.asm','probe_feedback_packets.py','ima_codec.py'):
        shutil.copyfile(PLAYER/name,sources/name)
    kernels=[kernel_audit(out,False),kernel_audit(out,True),kernel_audit(out,True,11,True)]
    report=dict(date='2026-10-19',purpose='Read-only architecture feasibility audit for retaining useful16-bit predictor precision',
        source_PCM_precision=16,current_PDM_input_levels=64,current_discarded_low_bits=10,
        current_source_storage_unchanged=True,player_core_or_C_Python_encoder_modified=False,
        first_order_kernels=kernels,fractional_q=residual_audit(out),hierarchical=hierarchical_dimensions(out),
        primary_timing_reference='https://www.zilog.com/docs/z80/um0080.pdf',
        full_second_order_measured_native_kernel=False,
        second_order_note='No stable full16-bit two-state arithmetic kernel is implemented here; extra arithmetic/register pressure must be counted on a concrete candidate, not inferred as a measured lower bound',
        complete=True,full_corpus_Fuse_or_quality_claim=False)
    save(out/'report.json',report)
    manifest=[dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
    save(out/'manifest.json',dict(artifacts=manifest,files=len(manifest)))
    print(json.dumps(dict(complete=True,artifacts=len(manifest),kernel_totals=[r['vectors'][0]['elapsed_tstates'] for r in kernels],fractional_q_tstates=138)))


if __name__=='__main__':main()
