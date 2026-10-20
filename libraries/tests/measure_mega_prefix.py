"""Wide Mega frontier: full native CPU and all service memory, identical blocks."""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path

from measure_long_copy import ROOT,sha
from measure_bit_phases import samples
from measure_fast_jumps import layout,summarize
from profile_branch_mix import instructions,condition
from native_block import execute
from mega_prefix_profile import build
from zx0.block import build as public
from test_libraries import profiles


def high_word_samples():
    """Exercise both sides of the length-word high bit in a disjoint layout."""
    from zx0.tokens import Token,encode
    for offset in (1,2,127,128,255,256,257):
        for length in (127,128,255,256,257,32767,32768,49151):
            seed=bytes(index%251 for index in range(offset))
            raw=seed+(seed*((length+offset-1)//offset))[:length]
            yield f'high-word-offset-{offset}-length-{length}',encode(raw,[Token(0,offset),Token(offset,length,offset)]),raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--public',action='store_true',help='replay the independently packaged maximum generator')
    parser.add_argument('--high-word',action='store_true',help='separate disjoint high-word gamma correctness supplement')
    args=parser.parse_args()
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    origin,relocation=(0x0800,0x0903) if args.high_word else (0x8000,0x9103)
    options=dict(source=0x0400,output=0x3000,caller_stack=0x2ff0) if args.high_word else {}
    base=public('mega',core=origin,core_limit=origin+0x400,fast_jumps=True,mega_tuned=True)
    candidates={cap:build(origin=origin,prefix_cap=cap) for cap in (31,63,127)}
    moved={cap:build(origin=relocation,prefix_cap=cap) for cap in candidates}
    if args.public:
        from zx0.maximum import build as maximum
        for cap in candidates:
            candidate=maximum(core=origin,prefix_cap=cap)
            relocated=maximum(core=relocation,prefix_cap=cap)
            assert candidate[:2]==candidates[cap][:2] and relocated[:2]==moved[cap][:2]
            candidates[cap],moved[cap]=candidate,relocated
    rows={cap:[] for cap in candidates}
    for name,payload,raw in (high_word_samples() if args.high_word else samples()):
        branch=Counter();watch={}
        for origin,blob in base[0]:
            for at,code in instructions(blob,origin):
                if code[0]!=0x38:continue
                def observe(machine):branch['taken' if condition(machine.f,3) else 'not_taken']+=1
                watch[at]=observe
        before=execute(base,payload,raw,watch=watch,**options)
        for cap,candidate in candidates.items():
            hits=Counter();watch={}
            for label in candidate[2]['removed_word_shift_stages']:
                def observe(machine):hits['removed_word_shifts']+=1
                watch[candidate[1][label]]=observe
            for label,info in candidate[2]['prefixes'].items():
                def observe(machine,item=info):
                    assert machine.bc>=item['minimum_count'] and machine.bc>item['prefix_bytes']
                    hits['prefix_entries']+=1;hits['prefix_bytes']+=item['prefix_bytes']
                    if item['extra_offset_load_tstates']:hits['phase7_indirect_loads']+=1
                watch[candidate[1][label]]=observe
            for label in candidate[2]['word_copy_joins']:
                def observe(machine):hits['word_joins']+=1
                watch[candidate[1][label]]=observe
            after=execute(candidate,payload,raw,watch=watch,**options)
            irq=execute(candidate,payload,raw,interrupts=True,**options)
            relocated=execute(moved[cap],payload,raw,**options)
            assert relocated['tstates']==after['tstates']
            expected=(-8*hits['removed_word_shifts']-5*hits['prefix_bytes']+10*hits['prefix_entries']
                      +6*hits['phase7_indirect_loads']+10*hits['word_joins']
                      -2*branch['taken']+3*branch['not_taken'])
            delta=after['tstates']-before['tstates']
            assert delta==expected,(name,cap,delta,expected,hits,branch)
            assert after['stack_bytes']==before['stack_bytes'] and after['stack_bytes']<=4
            assert irq['stack_bytes']<=10
            rows[cap].append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                payload_bytes=len(payload),raw_bytes=len(raw),baseline_tstates=before['tstates'],
                candidate_tstates=after['tstates'],delta_tstates=delta,predicted_delta_tstates=expected,
                dynamic_counts=dict(hits,extra_jr_taken=branch['taken'],extra_jr_not_taken=branch['not_taken']),
                injected_interrupts=irq['injected_interrupts'],stack_bytes=after['stack_bytes'],
                irq_stack_bytes=irq['stack_bytes'],exact=True,relocated_exact=True))
        if name=='real-3-0':
            print('real progress',name,flush=True)
    report=dict(date=date.today().isoformat(),source_baseline='1784e45a',goal_baseline='f5a0362c',
        complete=True,release=False,test_only=not args.public,coroutine_supported=False,
        default_profiles_exact=31,payload_delta_bytes=0,scope=__doc__,
        baseline=layout(base),goal_fast_real_tstates=None if args.high_word else 156012520,
        high_word_supplement=args.high_word,placement=dict(core=origin,relocated_core=relocation,**options),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',profiles={})
    for cap,candidate in candidates.items():
        summary=summarize(rows[cap])
        if not args.high_word:
            summary['gain_vs_goal_fast_percent']=(156012520-summary['real_candidate_tstates'])/156012520*100
        report['profiles'][str(cap)]=dict(candidate=layout(candidate),summary=summary,blocks=rows[cap],
            workspace_bytes=candidate[2]['workspace_bytes'],max_decoder_stack_bytes=4,
            max_observed_irq_stack_bytes=max(row['irq_stack_bytes'] for row in rows[cap]),
            service_memory=candidate[2].get('service_memory'),
            service_with_probe_irq_bytes=candidate[2]['workspace_bytes']+13+6)
        print(cap,'code',candidate[2]['code_bytes'],'service',candidate[2]['workspace_bytes'],json.dumps(summary),flush=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
