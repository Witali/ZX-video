"""Verify continuation-cloned ZX0 shared suffixes against same-cap Maximum."""
import argparse
from datetime import date
import gzip
import json
from pathlib import Path

from measure_bit_phases import samples
from measure_mega_prefix import high_word_samples
from measure_long_copy import ROOT,sha
from native_block import execute
from shared_zero_prefix_profile import build
from zx0.maximum import build as public


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--caps',type=int,nargs='+',default=[31,63,127,227,228])
    p.add_argument('--high-word',action='store_true')
    args=p.parse_args()
    origin,relocation=(0x0800,0x0703) if args.high_word else (0x8000,0x9103)
    placement=dict(source=0x0400,output=0x3000,caller_stack=0x2ff0) if args.high_word else {}
    cases=list(high_word_samples() if args.high_word else samples())
    report=dict(date=date.today().isoformat(),complete=False,release=False,
        source_baseline='bbe9e202',scope='resident only; no quota/streaming/player qualification',
        high_word=args.high_word,profiles={},input_output_history_counted_separately=True,
        timing_formula='-10 * baseline literal4 direct entries -10 * eliminated baseline word joins')
    for cap in args.caps:
        before=public(core=origin,prefix_cap=cap)
        after=build(origin=origin,prefix_cap=cap)
        moved=build(origin=relocation,prefix_cap=cap)
        audit=after[2]['shared_zero_audit'];rows=[]
        for name,payload,raw in cases:
            hits=dict(literal4=0,word=0)
            def lit(m):hits['literal4']+=1
            def word(m):hits['word']+=1
            watch={before[1][label]:lit for label in audit['literal_direct_aliases']}
            watch.update({before[1][label]:word for label in audit['eliminated_word_join_labels']})
            old=execute(before,payload,raw,watch=watch,**placement)
            new=execute(after,payload,raw,**placement)
            irq=execute(after,payload,raw,interrupts=True,**placement)
            relocated=execute(moved,payload,raw,**placement)
            delta=new['tstates']-old['tstates'];predicted=-10*sum(hits.values())
            assert delta==predicted,(cap,name,delta,predicted,hits)
            assert relocated['tstates']==new['tstates']
            assert new['stack_bytes']<=4 and irq['stack_bytes']<=10
            rows.append(dict(case=name,input_sha256=sha(payload),output_sha256=sha(raw),
                input_bytes=len(payload),output_history_bytes=len(raw),
                baseline_tstates=old['tstates'],candidate_tstates=new['tstates'],delta_tstates=delta,
                baseline_literal4_entries=hits['literal4'],baseline_word_joins=hits['word'],
                stack_bytes=new['stack_bytes'],irq_injections=irq['injected_interrupts'],relocated_exact=True))
        real=[r for r in rows if r['case'].startswith('real-')]
        summary=dict(code_bytes=after[2]['code_bytes'],service_bytes=after[2]['service_memory_bytes'],
            baseline_service_bytes=before[2]['service_memory_bytes'],
            real_baseline_tstates=sum(r['baseline_tstates'] for r in real),
            real_candidate_tstates=sum(r['candidate_tstates'] for r in real),
            real_delta_tstates=sum(r['delta_tstates'] for r in real),
            all_delta_tstates=sum(r['delta_tstates'] for r in rows),cases=len(rows),real_cases=len(real),
            slower_cases=[r['case'] for r in rows if r['delta_tstates']>0],
            maximum_regression_tstates=max(r['delta_tstates'] for r in rows),
            irq_injections=sum(r['irq_injections'] for r in rows))
        assert not summary['slower_cases']
        report['profiles'][str(cap)]=dict(summary=summary,
            regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in after[0]],
            relocated_regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in moved[0]],
            service_memory=after[2]['service_memory'],audit=audit,blocks=rows)
        print(cap,json.dumps(summary),flush=True)
    report['source_sha256_lf']={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n'))
        for path in (Path(__file__),Path(__file__).with_name('shared_zero_prefix_profile.py'),ROOT/'libraries/zx0/src/zx0/maximum.py')}
    report['complete']=True
    blob=(json.dumps(report,indent=2)+'\n').encode()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(gzip.compress(blob,mtime=0) if args.output.suffix=='.gz' else blob)


if __name__=='__main__':main()
