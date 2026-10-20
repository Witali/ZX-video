"""Screen/test shared ZX0 LDI suffixes against unchanged public Maximum.

LDI is 16 T and JP is 10 T. A shared entry adds one JP; literal >=4
entries already reached by a JP are redirected directly and add no cost.
The largest suffix and its existing word join remain byte-for-byte in form.
All remaining execution is unchanged, so delta must equal 10*shared_hits.
"""
import argparse
from datetime import date
import json
from pathlib import Path

from measure_bit_phases import samples
from measure_mega_prefix import high_word_samples
from measure_long_copy import ROOT,sha
from native_block import execute
from mega_prefix_profile import build
from zx0.maximum import build as public


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--caps',type=int,nargs='+',default=[127,228])
    p.add_argument('--thresholds',type=int,nargs='+',default=[3,15,31,63])
    p.add_argument('--verify',action='store_true',help='IRQ and relocation on every case')
    p.add_argument('--high-word',action='store_true')
    args=p.parse_args()
    origin,moved=(0x0800,0x0703) if args.high_word else (0x8000,0x9103)
    opts=dict(source=0x0400,output=0x3000,caller_stack=0x2ff0) if args.high_word else {}
    cases=list(high_word_samples() if args.high_word else samples())
    bases={cap:public(core=origin,prefix_cap=cap) for cap in args.caps}
    baseline={cap:{} for cap in args.caps}
    for cap,profile in bases.items():
        for name,payload,raw in cases:baseline[cap][name]=execute(profile,payload,raw,**opts)['tstates']
    report=dict(date=date.today().isoformat(),complete=False,release=False,test_only=True,
        baseline_revision='b99dd123',scope='resident Maximum suffix-sharing; high-word' if args.high_word else 'resident Maximum suffix-sharing; full main corpus',
        irq_and_relocation=args.verify,profiles={},input_output_history_counted_separately=True,
        timing_formula='candidate - same-cap Maximum = 10 * shared_entry_jumps; literal4 alias adds zero')
    for cap in args.caps:
        for threshold in args.thresholds:
            profile=build(origin=origin,prefix_cap=cap,share_minimum=threshold)
            relocated=build(origin=moved,prefix_cap=cap,share_minimum=threshold)
            rows=[]
            for name,payload,raw in cases:
                hits=[0]
                def count(m):hits[0]+=1
                watched={profile[1][label]:count for label in profile[2]['shared_entry_jumps']}
                result=execute(profile,payload,raw,watch=watched,**opts)
                before=baseline[cap][name]
                assert result['tstates']-before==10*hits[0],(cap,threshold,name,result,before,hits)
                row=dict(case=name,input_sha256=sha(payload),output_sha256=sha(raw),
                    input_bytes=len(payload),output_history_bytes=len(raw),baseline_tstates=before,
                    candidate_tstates=result['tstates'],delta_tstates=result['tstates']-before,
                    shared_jumps=hits[0],stack_bytes=result['stack_bytes'])
                assert row['stack_bytes']<=4
                if args.verify:
                    irq=execute(profile,payload,raw,interrupts=True,**opts)
                    move=execute(relocated,payload,raw,**opts)
                    assert move['tstates']==result['tstates'] and irq['stack_bytes']<=10
                    row.update(irq_injections=irq['injected_interrupts'],relocated_exact=True)
                rows.append(row)
            real=[r for r in rows if r['case'].startswith('real-')]
            total=sum(r['candidate_tstates'] for r in real)
            before=sum(r['baseline_tstates'] for r in real)
            summary=dict(service_bytes=profile[2]['workspace_bytes'],code_bytes=profile[2]['code_bytes'],
                caller_stack_including_return_bytes=4,extra_state_tables_padding_scratch_bytes=0,
                cases=len(rows),real_cases=len(real),real_candidate_tstates=total,real_baseline_tstates=before,
                real_delta_tstates=total-before,all_delta_tstates=sum(r['delta_tstates'] for r in rows),
                slower_real_blocks=sum(r['delta_tstates']>0 for r in real),
                slower_cases=sum(r['delta_tstates']>0 for r in rows),
                maximum_regression_tstates=max(r['delta_tstates'] for r in rows))
            report['profiles'][f'{cap}-share-{threshold}']=dict(summary=summary,
                regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]],blocks=rows)
            print(cap,threshold,json.dumps(summary),flush=True)
    report['source_sha256_lf']={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n'))
        for path in (Path(__file__),Path(__file__).with_name('mega_prefix_profile.py'),ROOT/'libraries/zx0/src/zx0/maximum.py')}
    report['complete']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
