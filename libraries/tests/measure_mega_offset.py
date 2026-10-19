"""Complete native audit of test-only Mega dead-offset shifts and reuse exits."""
import argparse
from collections import Counter
import json
from pathlib import Path

from measure_long_copy import ROOT, sha
from measure_bit_phases import samples
from measure_fast_jumps import layout, summarize
from native_block import execute
from profile_branch_mix import instructions, condition
from mega_offset_profile import build
from zx0.block import build as public
from test_libraries import profiles


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    baseline=public('mega',fast_jumps=True)
    assert baseline[:2]==build(dead_offset_shifts=False)[:2]
    configurations={
        'dead-offset-shifts':dict(dead_offset_shifts=True,reuse_tail_jp=False),
        'reuse-tail-jp':dict(dead_offset_shifts=False,reuse_tail_jp=True),
        'combined':dict(dead_offset_shifts=True,reuse_tail_jp=True)}
    candidates={name:build(**options) for name,options in configurations.items()}
    moved={name:build(origin=0x9103,**options) for name,options in configurations.items()}
    rows={name:[] for name in configurations}
    frozen=json.loads((ROOT/'libraries/evidence/fast_jumps.json').read_text())['profiles']['zx0-mega']
    golden={row['case']:row['candidate_tstates'] for row in frozen['blocks']}
    for case,payload,raw in samples():
        hits=Counter(); watched={}
        for name,address in baseline[1].items():
            if name.startswith('dzx0m_elias_offset'):
                def observe(machine, label=name):hits[label]+=1
                watched[address]=observe
        for origin,blob in baseline[0]:
            for address,code in instructions(blob,origin):
                if code[0] != 0x30:continue
                target=address+2+int.from_bytes(code[1:],'little',signed=True)
                if target not in [baseline[1][f'dzx0m_literals{i}'] for i in (0,2,4,6)]:continue
                def observe(machine, pc=address):hits['exit_taken' if condition(machine.f,2) else 'exit_not_taken']+=1
                watched[address]=observe
        old=execute(baseline,payload,raw,watch=watched)
        assert old['tstates']==golden[case]
        dead=sum(value for key,value in hits.items() if key.startswith('dzx0m_elias_offset'))
        for name,candidate in candidates.items():
            result=execute(candidate,payload,raw)
            irq=execute(candidate,payload,raw,interrupts=True)
            relocated=execute(moved[name],payload,raw)
            assert relocated['tstates']==result['tstates']
            options=configurations[name]
            predicted=(-8*dead if options['dead_offset_shifts'] else 0)
            if options['reuse_tail_jp']:predicted+=-2*hits['exit_taken']+3*hits['exit_not_taken']
            delta=result['tstates']-old['tstates']
            assert delta==predicted
            assert result['stack_bytes']==old['stack_bytes']
            rows[name].append(dict(case=case,payload_sha256=sha(payload),raw_sha256=sha(raw),
                raw_bytes=len(raw),payload_bytes=len(payload),baseline_tstates=old['tstates'],
                candidate_tstates=result['tstates'],delta_tstates=delta,predicted_delta_tstates=predicted,
                offset_gamma_iterations=dead,reuse_exit_taken=hits['exit_taken'],
                reuse_exit_not_taken=hits['exit_not_taken'],stack_bytes=result['stack_bytes'],
                injected_interrupts=irq['injected_interrupts'],exact=True,relocated_exact=True))
    report=dict(date='2026-10-19',source_baseline='6db73511',goal_baseline='f5a0362c',
        complete=True,release=False,goal_achieved=False,test_only=True,coroutine_supported=False,
        default_profiles_exact=31,payload_delta_bytes=0,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        original_mega_673_bytes=True,baseline=layout(baseline),profiles={})
    for name,candidate in candidates.items():
        report['profiles'][name]=dict(candidate=layout(candidate),summary=summarize(rows[name]),blocks=rows[name])
        print(name,json.dumps(summarize(rows[name])),flush=True)
    report['goal_fast_real_tstates']=156012520
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
