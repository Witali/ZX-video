"""Exact compact q-successor arithmetic for the admitted full-input B cells.

This is a standalone metadata/native proof. It does not alter the player,
selector, source stream, modulation model, gain, filter or physical clock.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from z80 import Z80Machine


HERE = Path(__file__).resolve().parent
HOLDS = np.array([36,28,28,31,24,26,22,46,22,26,22,30,31,27,34,16],dtype=np.int64)
REGISTERS = ('bc','de','hl','ix','iy','sp','alt_af','alt_bc','alt_de','alt_hl')
CORE = ' LD A,IXL\n SUB L\n LD A,IXH\n SBC A,H\n SRA A\n ADD A,E\n'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def assemble(output):
    text = '''; Exact q-successor component for a previously selected valid model-B word.
; Entry IX=unsigned biased IMA predictor, HL=C(word) modulo65536.
; E=old qcode0..15,D16; BC,IX,IY,SP,alternate registers and AF' are live.
; Return A=new qcode. Only A/F change in CORE36. No stack or paging operation.
; The admitted-cell certificate bounds the true subtraction within signed16
; and proves qcode already0..15. This routine must not be used with an arbitrary
; unrelated word or an unvalidated model; otherwise clipping/sign rules differ.
 ORG 0x8000
core36:
''' + CORE + '''core36_complete: NOP
; Original raw seed=2*qcode+recent can be consumed after word selection.
rawseed44:
 SRL E
''' + CORE + '''rawseed44_complete: NOP
; Current selector prototype's root-page byte is40h+2*rawseed.
; Extract its qcode without changing BC,D,IX,alternates or AF'. E is consumed.
rootpage59:
 LD A,E
 RRCA
 RRCA
 AND 15
 LD E,A
''' + CORE + '''rootpage59_complete: NOP
; Batch driver for exhaustive real-cell execution. Six-byte fixture records
; contain C16,u16,qseed8,D16. These POPs/OUT/loop instructions are harness work,
; not part of the36-T component or a claimed integrated player schedule.
batch:
 LD SP,0xC000
 LD IY,2048
batch_loop:
 POP HL
 POP IX
 POP DE
''' + CORE + ''' OUT (0xFD),A
 DEC IY
 LD A,IYH
 OR IYL
 JP NZ,batch_loop
batch_complete: NOP
'''
    (output/'kernel.asm').write_text(text,encoding='utf-8',newline='\n')
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=kernel.bin','--lstfile=kernel.lst',
                        '-s','.*','kernel.asm'],cwd=output,capture_output=True,text=True)
    (output/'assembler.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(line) for line in run.stdout.splitlines() if line.startswith('{'))
    return (output/'kernel.bin').read_bytes(),labels


def component_cases(blob, labels, C, expected, output):
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    controls={}
    values=[0,1,255,256,511,512,1023,32767,32768,32769,65534,65535]
    for mode, total in (('core36',36),('rawseed44',44),('rootpage59',59)):
        count=0
        for value in values:
            for seed in range(32):
                for flags in (0,1,0xFE,0xFF):
                    qseed=seed//2
                    e={'core36':qseed,'rawseed44':seed,'rootpage59':0x40+2*seed}[mode]
                    before=dict(bc=0x10FE,de=0x1000+e,hl=int(C[value,seed])&65535,
                                ix=value,iy=0xABCD,sp=0x7030,alt_af=0xA500|flags,
                                alt_bc=0x1234,alt_de=0xC0FF,alt_hl=0x7200)
                    for name,register in before.items():setattr(m,name,register)
                    m.af=0x5A00|flags;m.iff1=False;m.iff2=bool(flags&1)
                    m.pc=labels[mode];m.set_breakpoint(labels[mode+'_complete']);m.ticks_to_stop=1000
                    while m.pc!=labels[mode+'_complete']:
                        event=m.run();assert not event&m._TICKS_LIMIT_HIT,'q component timeout'
                    assert 1000-m.ticks_to_stop==total,(mode,1000-m.ticks_to_stop)
                    assert m.a==int(expected[value,seed]),(mode,value,seed,m.a,int(expected[value,seed]))
                    for name in REGISTERS:
                        wanted=before[name] if name!='de' else 0x1000+qseed
                        assert getattr(m,name)==wanted,(mode,name,getattr(m,name),wanted)
                    assert m.iff1 is False and m.iff2==bool(flags&1)
                    m.clear_breakpoint(labels[mode+'_complete']);count+=1
        controls[mode]=dict(native_cases=count,absolute_tstates=total,
            BC_D_IX_IY_SP_alternates_AFprime_IFF_preserved=True,E_consumed_to_qseed=mode!='core36',
            A_returns_exact_qcode=True)
    save(output/'component-tests.json',controls)
    return controls


def all_native(blob, labels, C, expected, output):
    # Canonical order is unsigned biased predictor ascending, rawseed0..31.
    # Exactly2^21 real selected cells, divisible into1024 complete2048-cell batches.
    count=expected.size;batch=2048
    dtype=np.dtype([('C','<u2'),('u','<u2'),('qseed','u1'),('D','u1')],align=False)
    assert dtype.itemsize==6 and count%batch==0
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    m.set_breakpoint(labels['batch_complete']);got=bytearray();metadata_digest=hashlib.sha256()
    guards=dict(bc=0x10FE,alt_af=0xA5FD,alt_bc=0x1234,alt_de=0xC0FF,alt_hl=0x7200)
    position=0;record=None;batch_first=0
    def observe(port,value):
        nonlocal position
        assert port&255==0xFD
        local=position-batch_first
        assert m.ix==int(record['u'][local]) and m.hl==int(record['C'][local])
        assert m.de==0x1000+int(record['qseed'][local])
        assert m.sp==0xC000+6*(local+1) and m.iy==batch-local
        for name,wanted in guards.items():assert getattr(m,name)==wanted,('batch register',name)
        got.append(value);position+=1
    m.set_output_callback(observe)
    flatC=(C&65535).astype('<u2').ravel()
    for first in range(0,count,batch):
        batch_first=first
        ids=np.arange(first,first+batch,dtype=np.int64)
        record=np.empty(batch,dtype=dtype);record['C']=flatC[first:first+batch]
        record['u']=ids//32;record['qseed']=(ids%32)//2;record['D']=16
        raw=record.tobytes();metadata_digest.update(raw)
        m.memory[0xC000:0xC000+len(raw)]=raw
        for name,wanted in guards.items():setattr(m,name,wanted)
        m.pc=labels['batch'];m.ticks_to_stop=1_000_000
        while m.pc!=labels['batch_complete']:
            event=m.run();assert not event&m._TICKS_LIMIT_HIT,'native exhaustive batch timeout'
        assert position==first+batch
    actual=np.frombuffer(got,'u1').reshape(expected.shape)
    assert np.array_equal(actual,expected),'native successor mismatch'
    (output/'native-qcodes.u8.gz').write_bytes(gzip.compress(got,mtime=0))
    return dict(cells_executed=count,batches=count//batch,each_native_qcode_matches_real_B=True,
        each_cell_BC_D_IX_HL_SP_IY_altregs_AFprime_guarded=True,
        input_records_sha256=metadata_digest.hexdigest(),output_qcodes_sha256=sha(got),
        component_tstates=36,fixture_record_bytes=6,
        scope='Every real B cell, all65536 input levels andall32 original states; batch POP/OUT/loop overhead is excluded from component36T')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'evidence/sdm16-qphase')
    parser.add_argument('--catalogue',type=Path,default=HERE/'evidence/sdm16-architecture/model-b-all-pcm16-cells.npz')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    archive=np.load(args.catalogue);words=archive['words'];successors=archive['successors']
    areas=np.array([sum(int(h) for i,h in enumerate(HOLDS) if word&(1<<(15-i)))
                    for word in range(65536)],dtype=np.int64)
    active_areas=np.unique(areas[words]);a=areas[words]
    # Exact integer ceil: no float truncation, half-LSB centering or fitted gain.
    C=(65536*a-256*449+448)//449
    u=np.arange(65536,dtype=np.int64)[:,None];seed=np.arange(32,dtype=np.int64)[None,:]
    difference=u-C;raw=seed//2+difference//512
    assert np.array_equal(raw,successors//2)
    assert int(raw.min())>=0 and int(raw.max())<=15
    assert int(difference.min())>=-32768 and int(difference.max())<32768
    expected=raw.astype('u1')
    blob,labels=assemble(out)
    components=component_cases(blob,labels,C,expected,out)
    save(out/'metadata-partial.json',dict(complete=False,all_real_cells=words.size,
        raw_qcode_range=[int(raw.min()),int(raw.max())],true_difference_range=[int(difference.min()),int(difference.max())],
        clipping_needed=False,negative_C_marker_needed=False,components=components))
    native=all_native(blob,labels,C,expected,out)
    params=[]
    for area in active_areas:
        value=(65536*int(area)-256*449+448)//449
        params.append(dict(area=int(area),C_signed=value,C_u16=value&65535))
    (out/'all450-C.u16le.bin').write_bytes(np.array([
        ((65536*area-256*449+448)//449)&65535 for area in range(450)],dtype='<u2').tobytes())
    report=dict(complete=True,date='2026-10-19',catalogue_sha256=sha(args.catalogue.read_bytes()),
        exact_formula='qcode=old_rawseed//2+floor((u-ceil(65536*area(word)/449-256))/512)',
        input_unsigned16='u=signed_IMA_predictor+32768; existing player IX already has this bias',
        all_real_cells=words.size,raw_qcode_range=[int(raw.min()),int(raw.max())],
        true_difference_range=[int(difference.min()),int(difference.max())],
        clipping_needed_on_real_B_cells=False,negative_C_marker_needed_on_real_B_cells=False,
        positive_and_negative_C_handled_modulo65536=True,metadata_bytes_per_area=2,
        area_parameters=params,components=components,exhaustive_native=native,
        core_instruction_table=[['LD A,IXL',8],['SUB L',4],['LD A,IXH',8],['SBC A,H',4],['SRA A',8],['ADD A,E',4]],
        core36_only_A_F_clobbered=True,metadata_loading_SP_POP_HL_extra_tstates=10,
        rootpage_encoded_E_extraction_extra_tstates=23,
        combined_q_budget_if_C_already_loaded=36,combined_q_budget_with_POP_C_and_root_E_extract=69,
        full_lookup_budget_including_old_Pentagon_pacing=96,
        budget_remaining_for_word_selection_dispatch_if_qseed_ready_and_C_already_loaded=60,
        budget_remaining_if_POP_C_and_root_E_extract_needed=27,
        whole_lookup_fits_budget=False,
        decision='The36T arithmetic component is exact, but a complete word-selector/metadata/phase/dispatch integration is not proven tofit96T. Do not claim a running8kHz player from this component.',
        scope='All actual Bcells only, chosen by the authenticated fullinput word generator. Arbitrary unrelated (u,word,seed) triples are not admitted and can overflow or need clipping.',
        source_modulation_encoder_or_player_changed=False,audio_quality_measured=False,
        physical_hardware_tested=False,release_accepted=False)
    save(out/'report.json',report)
    (out/'generator.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    files=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts:
            rawdata=path.read_bytes();files.append(dict(path=path.relative_to(out).as_posix(),bytes=len(rawdata),sha256=sha(rawdata)))
    save(out/'manifest.json',dict(files=len(files),artifacts=files))
    print(json.dumps(dict(complete=True,native_cells=words.size,core_tstates=36,
        raw_qcode_range=report['raw_qcode_range'],difference_range=report['true_difference_range'],whole_lookup_fits=False)))


if __name__=='__main__':main()
