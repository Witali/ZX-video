"""Item29: exact-EOF Small versus resident Fast; code saving and CPU penalty."""
import argparse
import inspect
import json
from pathlib import Path
from measure_long_copy import samples,sha
from native_block import execute
from lzsa.block import build
from lzsa import compact
from test_libraries import profiles,ROOT


def legacy():
    # Reconstruct only the author algorithm's historical overread in our own
    # emitter; downloaded source is retained for attribution, not executed.
    source=inspect.getsource(compact.build)
    old="""    jr(0x20,'WordLength');emit('POP BC',(0xc1,),10);ret()
    a.label('WordLength');emit('LD A,(HL)',(0x7e,),7);inc();emit('LD B,(HL)',(0x46,),7);inc();ret()"""
    new="""    emit('LD A,(HL)',(0x7e,),7);inc();emit('LD B,(HL)',(0x46,),7);inc();ret(0xc0)
    emit('POP BC',(0xc1,),10)"""
    assert source.count(old)==1
    scope=dict(vars(compact));exec(source.replace(old,new),scope)
    return scope['build']()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();old=build();new=build('small');rows=[];legacy_failures=0
    assert profiles()==json.loads((ROOT/'tests/decoder_baseline.json').read_text())['profiles']
    for name,payload,raw in samples():
        before=execute(old,payload,raw);after=execute(new,payload,raw)
        irq=execute(new,payload,raw,interrupts=True)
        relocated=execute(build('small',core=0x9103,core_limit=0x9400),payload,raw)
        assert relocated['tstates']==after['tstates']
        if name.startswith('literal-'):
            try:execute(legacy(),payload,raw)
            except AssertionError:legacy_failures+=1
            else:raise AssertionError('legacy EOF should fail protected source')
        rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),raw_bytes=len(raw),
            baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],delta_tstates=after['tstates']-before['tstates'],
            stack_bytes=after['stack_bytes'],exact=True,interrupts=irq['injected_interrupts']))
    report=dict(date='2026-10-14',baseline_revision='5e070860',complete=True,release=False,
        baseline_bytes=old[2]['code_bytes'],candidate_bytes=new[2]['code_bytes'],legacy_bytes=legacy()[2]['code_bytes'],
        legacy_exact_eof_failures=legacy_failures,default_profiles_exact=31,candidate_metadata=new[2],
        summary=dict(cases=len(rows),baseline_tstates=sum(r['baseline_tstates'] for r in rows),
            candidate_tstates=sum(r['candidate_tstates'] for r in rows),delta_tstates=sum(r['delta_tstates'] for r in rows),
            real_baseline_tstates=sum(r['baseline_tstates'] for r in rows if r['case'].startswith('real-')),
            real_candidate_tstates=sum(r['candidate_tstates'] for r in rows if r['case'].startswith('real-')),
            slower_blocks=sum(r['delta_tstates']>0 for r in rows),interrupts=sum(r['interrupts'] for r in rows),
            stack_bytes=max(r['stack_bytes'] for r in rows)),blocks=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(report['summary']))

if __name__=='__main__':main()
