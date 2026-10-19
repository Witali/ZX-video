"""Count a concrete full16-bit residual quantizer; reject its runtime budget.

The persistent residual is a10-bit sample-domain error accumulator, separate
from the current packet-PDM state. This is not the old138-T q-state injection.
Only standalone assembly/evidence is emitted; no player/source/model changes.
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


HERE=Path(__file__).resolve().parent


def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def assemble(out):
    source='''; Full-input residual quantizer, standalone feasibility proof only.
; IX=u: exact biased signed IMA predictor in0..65535; it must remain unchanged.
; The self-modified immediate stores R in0..1023. HL,IY,A/F and SP are dead
; on entry after a hypothetical selector dispatch; no stack operations follow.
; BC port,D16,IX,alternate registers and AF' are preserved. Return IYL=q0..64,
; HL=Rnew,SP=IX, with only the two residual-immediate bytes changed in RAM.
; q=floor((u+R)/1024),Rnew=(u+R)mod1024. The17th carry is significant at
; positive fullscale: q64 is real and needs a65th level or an explicit clip.
; This PDM-prequantizer model differs from current modelA/B. No audio is scored.
 ORG 0x8000
residual: LD HL,0
 LD SP,IX
 ADD HL,SP
 ; Extract sum bits16..10 before AND destroys the addition's carry. RRCA's
 ; unwanted wrapped bit9 is removed by AND127; all paths take identical time.
 LD A,H
 RRA
 RRCA
 AND 127
 LD IYL,A
 ; Store the exact remainder for the next sample. This is self-modified data,
 ; not an ordinary stack or an input-dependent branch/paging operation.
 LD A,H
 AND 3
 LD H,A
 LD (residual+1),HL
complete: NOP
'''
    (out/'kernel.asm').write_text(source,encoding='utf-8',newline='\n')
    result=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=kernel.bin',
        '--lstfile=kernel.lst','-s','.*','kernel.asm'],cwd=out,capture_output=True,text=True)
    (out/'assembler.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    labels=next(ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith('{'))
    return (out/'kernel.bin').read_bytes(),labels


def execute(blob,labels,out):
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    m.set_breakpoint(labels['complete']);state=labels['residual']+1
    guards=dict(bc=0x10FE,de=0x1030,ix=0,alt_af=0xA5FD,alt_bc=0x1234,alt_de=0xC0FF,alt_hl=0x7200)
    cases=0;endpoint64=0;lowbit_witness=None
    def call(value,residual,flags,*,initialize=True):
        nonlocal cases,endpoint64
        for name,wanted in guards.items():setattr(m,name,value if name=='ix' else wanted)
        m.iy=0xABCD;m.hl=0x5555;m.sp=0x7777;m.af=0x5A00|flags
        m.iff1=False;m.iff2=bool(flags&1)
        if initialize:
            m.memory[state]=residual&255;m.memory[state+1]=residual>>8
        before=bytes(m.memory);m.pc=labels['residual'];m.ticks_to_stop=1000
        while m.pc!=labels['complete']:
            event=m.run();assert not event&m._TICKS_LIMIT_HIT,'residual timeout'
        assert 1000-m.ticks_to_stop==89,('native residual count',1000-m.ticks_to_stop)
        q,new=divmod(value+residual,1024)
        assert m.iy==(0xAB00|q) and m.hl==new and m.sp==value
        assert int(m.memory[state])+256*int(m.memory[state+1])==new
        for name,wanted in guards.items():assert getattr(m,name)==(value if name=='ix' else wanted),(name,value,residual)
        assert m.iff1 is False and m.iff2==bool(flags&1)
        changed=np.flatnonzero(np.frombuffer(before,'u1')!=np.frombuffer(m.memory,'u1'))
        assert set(map(int,changed)).issubset({state,state+1})
        cases+=1;endpoint64+=int(q==64)
        return q,new
    endpoints=(0,1,255,256,511,512,1023,1024,32767,32768,64511,64512,64513,65534,65535)
    for residual in range(1024):
        for value in endpoints:
            for flags in (0,1,0xFE,0xFF):call(value,residual,flags)
    # A one-LSB input change is carried through every remainder bit, even when
    # the first output bin remains equal. There is no packet-boundary rounding.
    observed=[]
    for value in (32768,32769):
        residual=0;bins=[]
        for sample in range(1025):
            q,residual=call(value,residual,sample&1,initialize=sample==0)
            bins.append(q)
        observed.append(bins)
    assert observed[0]==[32]*1025
    assert observed[1][1023]==33 and observed[1][:1023]==[32]*1023
    lowbit_witness=dict(constant_unsigned16=[32768,32769],seed_residual=0,
        first_changed_bin_sample_zero_based=1023,base_bin=32,one_LSB_bin=33,
        own_residual_carried_for1025_native_samples=True)
    # Exact modulo addition on all low10 pairs; the upper6 input bits simply
    # add to q. Test every upper6 value too, in bounded1024x1024 arrays.
    lower=np.arange(1024,dtype=np.int64)[None,:]
    residue=np.arange(1024,dtype=np.int64)[:,None]
    total=lower+residue
    for high in range(64):
        whole=total+1024*high
        assert np.array_equal(whole%1024,total&1023)
        assert np.array_equal(whole//1024,high+(total>>10))
    result=dict(native_cases=cases,native_q64_endpoint_cases=endpoint64,absolute_tstates=89,
        all1024_residuals=True,all15_unsigned_input_boundaries=True,initial_flag_bytes=[0,1,254,255],
        BC_D_IX_altregs_AFprime_IFF_preserved=True,only_two_residual_bytes_written=True,
        lowbit_witness=lowbit_witness,integer_all67108864_input_residual_pairs_verified=True)
    save(out/'native.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'evidence/sdm16-residual')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    blob,labels=assemble(out);native=execute(blob,labels,out)
    rows=[['LD HL,R immediate',10],['LD SP,IX',10],['ADD HL,SP',11],['LD A,H',4],
          ['RRA',4],['RRCA',4],['AND127',7],['LD IYL,A',8],['LD A,H',4],
          ['AND3',7],['LD H,A',4],['LD(nn),HL',16]]
    assert sum(row[1] for row in rows)==89
    report=dict(complete=True,date='2026-10-19',native=native,instruction_table=rows,
        formula='q=floor((u+R)/1024); Rnext=(u+R)%1024',residual_bits=10,
        source_model='Hypothetical sample-domain residual quantizer feeding packet PDM; not exact frozenB or second-order SDM',
        old_lookup_and_dispatch_tstates=70,available_Pentagon_padding_tstates=26,total_budget=96,
        quantizer_only_tstates=89,existing_bin_lookup_and_POPs_still_required_tstates=70,
        concrete_unoptimized_combination_tstates=159,over_budget_tstates=63,
        extra_native_sample_cost_vs_original_lookup=89,
        timing_assumptions='89T is only the exact residual-prequantizer. The existing70T selector/POPs are still needed; q64 additionally requires an endpoint policy. No variable-time saturation or hidden paging is counted as free.',
        endpoint_policy='The exact residual quantizer can return65 levels0..64. The current64-bin zero-origin packet model has no level64; clipping it changes this model and its bounded-error identity.',
        register_findings=dict(IX='Exact IMA predictor must remain16-bit',IY='NextSECOND pointer live until dispatch, then dead',
            AFprime='Source phase and prefetched nibble live',alternateHL='IMA row live',alternateDE='Compressed cursor live',
            alternateBC='Overwritten by next decoder POP, not stable persistent residual storage',
            BC='Port-preserving10-bit residual encoding8002h+4R is theoretically possible, but current bank tail overwritesBC and its release OUT usesB as data; packing/update/restore costs are not free'),
        decision='Reject this concrete runtime residual mechanism for the96T budget. It preserves all16-bit input influence causally but does not fit the current constant449/448 clock.',
        no_source_stream_player_or_encoder_changed=True,no_audio_quality_sweep=True,
        physical_hardware_tested=False,release_accepted=False)
    save(out/'report.json',report)
    (out/'generator.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    files=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts:
            raw=path.read_bytes();files.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    save(out/'manifest.json',dict(files=len(files),artifacts=files))
    print(json.dumps(dict(complete=True,native_cases=native['native_cases'],quantizer89=True,
        combined159=True,budget96=True,decision='rejected_runtime_budget')))


if __name__=='__main__':main()
