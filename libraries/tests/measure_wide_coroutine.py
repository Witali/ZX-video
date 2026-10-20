"""Complete native wide coroutine comparison, including publication cursors."""
import argparse
import json
from pathlib import Path

from measure_long_copy import ROOT,samples,sha
from measure_full_token_dispatch import directed_tokens
from lzsa.wide_coroutine import build
from lzsa.resumable import build as old
from lzsa.native import execute


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    cases=list(samples())
    baseline=old(core=0x8000,core_limit=0x8400,fast_jumps=True)
    before={n:execute(*baseline,p,r,source=0x2000) for n,p,r in cases}
    assert sum(before[n]['tstates'] for n,p,r in cases if n.startswith('real-'))==19407004
    report=dict(date='2026-10-20',complete=False,release=False,goal_achieved=False,
        baseline_revision='f5a0362c',scope='Ordinary output-demand coroutine; complete resident input, no input guards.',
        slice_bytes=256,storage_budget_bytes=10000,profiles={})
    for shared in (False,True):
        profile=build(shared_literals=shared)
        moved=build(core=0x9103,shared_literals=shared)
        rows=[]
        for name,payload,raw in cases:
            new=execute(*profile,payload,raw,source=0x2000)
            irq=execute(*profile,payload,raw,source=0x2000,interrupts=True)
            relocated=execute(*moved,payload,raw,source=0x2000)
            previous=before[name]
            assert new['publication_offsets']==previous['publication_offsets']==relocated['publication_offsets']==irq['publication_offsets']
            assert new['tstates']==relocated['tstates']
            assert new['caller_stack_bytes']<=4 and new['private_stack_bytes']<=16
            assert irq['caller_stack_bytes']<=10 and irq['private_stack_bytes']<=22
            deltas=[b-a for a,b in zip(previous['slices'],new['slices'])]
            rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                compressed_input_bytes=len(payload),output_history_bytes=len(raw),
                baseline_tstates=previous['tstates'],candidate_tstates=new['tstates'],
                delta_tstates=new['tstates']-previous['tstates'],slices=len(deltas),
                slower_slices=sum(d>0 for d in deltas),maximum_slice_delta=max(deltas),
                caller_stack_bytes=new['caller_stack_bytes'],private_stack_bytes=new['private_stack_bytes'],
                publication_offsets=new['publication_offsets'],publication_exact=True,
                injected_interrupts=irq['injected_interrupts'],exact=True))
        extra=list(directed_tokens())
        extra_irqs=0;directed_rows=[]
        for name,payload,raw,value in extra:
            prior=execute(*baseline,payload,raw,source=0x2000)
            new=execute(*profile,payload,raw,source=0x2000)
            irq=execute(*moved,payload,raw,source=0x2000,interrupts=True)
            relocated=execute(*moved,payload,raw,source=0x2000)
            assert new['publication_offsets']==prior['publication_offsets']==irq['publication_offsets']
            assert new['publication_offsets']==relocated['publication_offsets']
            assert new['tstates']==relocated['tstates']
            assert new['caller_stack_bytes']<=4 and new['private_stack_bytes']<=16
            assert irq['caller_stack_bytes']<=10 and irq['private_stack_bytes']<=22
            deltas=[b-a for a,b in zip(prior['slices'],new['slices'])]
            directed_rows.append(dict(case=name,token_value=value,payload_sha256=sha(payload),raw_sha256=sha(raw),
                compressed_input_bytes=len(payload),output_history_bytes=len(raw),
                baseline_tstates=prior['tstates'],candidate_tstates=new['tstates'],
                delta_tstates=new['tstates']-prior['tstates'],slices=len(deltas),
                slower_slices=sum(d>0 for d in deltas),maximum_slice_delta=max(deltas),
                caller_stack_bytes=new['caller_stack_bytes'],private_stack_bytes=new['private_stack_bytes'],
                publication_offsets=new['publication_offsets'],publication_exact=True,
                injected_interrupts=irq['injected_interrupts'],exact=True,relocated_exact=True))
            extra_irqs+=irq['injected_interrupts']
        real=[r for r in rows if r['case'].startswith('real-')]
        baseline_t=sum(r['baseline_tstates'] for r in real)
        candidate_t=sum(r['candidate_tstates'] for r in real)
        key='wide-shared-coroutine' if shared else 'wide-coroutine'
        report['profiles'][key]=dict(metadata=profile[2],relocated_metadata=moved[2],blocks=rows,
            directed_blocks=directed_rows,
            regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]],
            summary=dict(cases=len(rows),directed_cases=len(extra),real_blocks=len(real),
                baseline_tstates=baseline_t,candidate_tstates=candidate_t,delta_tstates=candidate_t-baseline_t,
                percent_saved=100*(baseline_t-candidate_t)/baseline_t,
                slower_blocks=[r['case'] for r in rows if r['delta_tstates']>0],
                slower_slices=sum(r['slower_slices'] for r in rows),
                real_slower_slices=sum(r['slower_slices'] for r in real),
                maximum_slice_delta=max(r['maximum_slice_delta'] for r in rows),
                actual_caller_stack_bytes=max(r['caller_stack_bytes'] for r in rows),
                actual_private_stack_bytes=max(r['private_stack_bytes'] for r in rows),
                directed_injected_interrupts=extra_irqs,publication_offsets_exact=True,
                directed_slower_blocks=[r['case'] for r in directed_rows if r['delta_tstates']>0],
                directed_slower_slices=sum(r['slower_slices'] for r in directed_rows),
                directed_maximum_slice_delta=max(r['maximum_slice_delta'] for r in directed_rows)))
        print(key,json.dumps(report['profiles'][key]['summary']),flush=True)
    report['source_sha256_lf']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes().replace(b'\r\n',b'\n'))
        for p in (ROOT/'libraries/lzsa/src/lzsa/wide.py',ROOT/'libraries/lzsa/src/lzsa/wide_coroutine.py',
                  ROOT/'libraries/lzsa/src/lzsa/native.py',Path(__file__))}
    report['complete']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
