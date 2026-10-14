"""Item24 test-only distance-one prefix; never a public decoder option."""
import argparse
import inspect
import json
from pathlib import Path
from measure_long_copy import samples,sha
from lzsa import resumable
from lzsa.native import execute
from test_libraries import profiles,ROOT


def candidate():
    # Alter our trusted generator, not a downloaded program. Require a unique
    # exact site; if the generator changes, explicitly re-audit this experiment.
    source=inspect.getsource(resumable.build)
    anchor="""        ld('LD HL,(offset)',0x2a,'offset',16);emit('ADD HL,DE',(0x19,),11)
        for _ in range(16):ldi()
        ldir();jp(0xc3,'AfterLongMatch')"""
    replacement="""        ld('LD HL,(offset)',0x2a,'offset',16)
        # AF is dead; AF' retains the nibble. Only offset FFFF is distance1.
        # Structurally byte-form count >=24, B=0. Save/restore HL as before.
        emit('LD A,H',(0x7c,),4);emit('AND L',(0xa5,),4);emit('INC A',(0x3c,),4)
        jr(0x20,'RepeatFallback');emit('ADD HL,DE',(0x19,),11)
        emit('LD A,(HL)',(0x7e,),7);emit('EX DE,HL',(0xeb,),4)
        # Write24 copies of the seed, then resume forward overlap for residue.
        for _ in range(24):
            emit('LD (HL),A',(0x77,),7);inc()
        emit('LD D,H',(0x54,),4);emit('LD E,L',(0x5d,),4)
        emit('LD A,C',(0x79,),4);emit('SUB 24',(0xd6,24),7);emit('LD C,A',(0x4f,),4)
        jr(0x28,'RepeatDone');emit('DEC HL',(0x2b,),6);ldir()
        a.label('RepeatDone');jp(0xc3,'AfterLongMatch')
        a.label('RepeatFallback');emit('ADD HL,DE',(0x19,),11)
        for _ in range(16):ldi()
        ldir();jp(0xc3,'AfterLongMatch')"""
    assert source.count(anchor)==1
    scope=dict(vars(resumable));exec(source.replace(anchor,replacement),scope)
    return scope['build'](long_copy=True,core_limit=0x9000)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();old=resumable.build(long_copy=True,core_limit=0x9000);new=candidate();rows=[]
    assert profiles()==json.loads((ROOT/'tests/decoder_baseline.json').read_text())['profiles']
    for name,payload,raw in samples():
        before=execute(*old,payload,raw,source=0x2000);after=execute(*new,payload,raw,source=0x2000)
        irq=execute(*new,payload,raw,source=0x2000,interrupts=True)
        delta=[b-a for a,b in zip(before['slices'],after['slices'])]
        rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),raw_bytes=len(raw),
            baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],delta_tstates=sum(delta),
            slower_slices=sum(t>0 for t in delta),exact=True,interrupts=irq['injected_interrupts']))
    report=dict(date='2026-10-14',item=24,baseline_revision='1e8cb030',complete=True,release=False,
        generator_sha256=sha(inspect.getsource(resumable.build).encode()),defaults_exact=31,
        code_bytes_before=old[2]['code_bytes'],code_bytes_after=new[2]['code_bytes'],state_stack_payload_delta=0,
        summary=dict(cases=len(rows),baseline_tstates=sum(r['baseline_tstates'] for r in rows),
            candidate_tstates=sum(r['candidate_tstates'] for r in rows),delta_tstates=sum(r['delta_tstates'] for r in rows),
            real_delta_tstates=sum(r['delta_tstates'] for r in rows if r['case'].startswith('real-')),
            slower_blocks=sum(r['delta_tstates']>0 for r in rows),slower_slices=sum(r['slower_slices'] for r in rows),
            injected_interrupts=sum(r['interrupts'] for r in rows)),
        candidate=dict(regions=[[at,data.hex()] for at,data in new[0]],labels=new[1],metadata=new[2]),blocks=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(report['summary']))

if __name__=='__main__':main()
