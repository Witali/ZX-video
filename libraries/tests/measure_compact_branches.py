"""Smaller LZSA2 conditional policy: only the measured Case11x short branch."""
import argparse,json
from pathlib import Path
from measure_long_copy import samples,sha
from measure_fast_jumps import layout,summarize
from native_block import execute as resident_execute
from measure_compact_sync import execute as coroutine_execute
from lzsa.block import build as block
from lzsa.resumable import build as coroutine


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    report=dict(date='2026-10-20',baseline_revision='bb687f71',goal_baseline_revision='f5a0362c',complete=False,release=False,goal_achieved=False,profiles={})
    cases=list(samples())+[('single-nibble-eof-A',bytes.fromhex('ef41f0e8'),b'A'),('single-nibble-eof-empty',bytes.fromhex('e7f0e8'),b'')]
    for resident in (True,False):
        configurations=[{},dict(fast_jumps=True),dict(fast_jumps=True,nibble_prefill=True),dict(fast_jumps=True,nibble_prefill=True,long_copy=True,near_literals=True)]
        if not resident:
            configurations[2]['compact_sync']=True
            configurations[3].update(compact_sync=True,restore_compare=True)
        for index,options in enumerate(configurations):
            builder=block if resident else coroutine
            old=builder(core=0x8000,core_limit=0x8400,**options)
            new=builder(core=0x8000,core_limit=0x8400,compact_branches=True,**options)
            moved=builder(core=0x9103,core_limit=0x9500,compact_branches=True,**options)
            assert new[2]['code_bytes']==old[2]['code_bytes']-1
            assert len(new[2]['branch_changes'])==1 and new[2]['branch_changes'][0]['target']=='Case11x'
            rows=[]
            for case,payload,raw in cases:
                def run(profile,irq=False):
                    return resident_execute(profile,payload,raw,interrupts=irq) if resident else coroutine_execute(profile,payload,raw,interrupts=irq)
                before,after,irq,relocated=run(old),run(new),run(new,True),run(moved)
                assert after['tstates']==relocated['tstates']
                row=dict(case=case,raw_bytes=len(raw),raw_sha256=sha(raw),payload_sha256=sha(payload),baseline_tstates=before['tstates'],
                    candidate_tstates=after['tstates'],delta_tstates=after['tstates']-before['tstates'],exact=True,relocated_exact=True,injected_interrupts=irq['injected_interrupts'])
                if resident:
                    assert before['stack_bytes']==after['stack_bytes'];row.update(stack_bytes=after['stack_bytes'],irq_stack_bytes=irq['stack_bytes'])
                else:
                    assert before['output_cursors']==after['output_cursors']
                    delta=[b-a for a,b in zip(before['slices'],after['slices'])]
                    row.update(slower_slices=sum(t>0 for t in delta),largest_slice_delta=max(delta),caller_stack_bytes=after['caller_stack_bytes'],
                        private_stack_bytes=after['private_stack_bytes'],irq_caller_stack_bytes=irq['caller_stack_bytes'],irq_private_stack_bytes=irq['private_stack_bytes'])
                rows.append(row)
            name=('block' if resident else 'coroutine')+str(index)
            report['profiles'][name]=dict(options=options,baseline=layout(old),candidate=layout(new),summary=summarize(rows),blocks=rows)
            print(name,json.dumps(summarize(rows)),flush=True)
    report['complete']=True;args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
