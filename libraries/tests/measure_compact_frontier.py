"""Combined compact codec profiles: complete CPU, quotas and total service memory."""
import argparse
import json
from pathlib import Path

from measure_long_copy import ROOT, sha, samples as lsamples
from measure_bit_phases import samples as zsamples
from measure_fast_jumps import layout, summarize
from native_block import execute
from lzsa.native import execute as resume
from lzsa.block import build as lblock
from lzsa.resumable import build as lcoroutine
from zx0.block import build as zblock
from zx0.resumable import build as zcoroutine


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    reference=json.loads((ROOT/'libraries/evidence/ten_percent_tuned_branches.json').read_text())['profiles']
    report=dict(date='2026-10-19',complete=False,goal_achieved=False,release=False,
        baseline_revision='f5a0362c',integration_parent='ca861f97',service_memory_limit_bytes=10000,
        service_memory_scope='all emitted regions (variables included) plus required caller/private stack and internal scratch; input/output excluded',
        input_output_accounted_separately=True,profiles={})
    for codec,samples,raw_builder,coro_builder in (
            ('zx0',zsamples,zblock,zcoroutine),('lzsa2',lsamples,lblock,lcoroutine)):
        cases=list(samples())
        if codec=='lzsa2':cases += [('single-nibble-eof-A',bytes.fromhex('ef41f0e8'),b'A'),
                                    ('single-nibble-eof-empty',bytes.fromhex('e7f0e8'),b'')]
        for resident in (True,False):
            builder=raw_builder if resident else coro_builder
            baseline=dict(fast_jumps=True) if codec=='lzsa2' else {}
            selected=(dict(branch_tuned=True,literal_prefix=True,inline_tail_refill=True) if codec=='zx0' else
                      dict(fast_jumps=True,branch_tuned=True,nibble_prefill=True))
            old=builder(core=0x8000,core_limit=0x8400,**baseline)
            new=builder(core=0x8000,core_limit=0x8400,**selected)
            moved=builder(core=0x9103,core_limit=0x9500,**selected)
            name=codec+('-block' if resident else '-coroutine')
            frozen={row['case']:row for row in reference[name]['blocks']}
            rows=[]
            for case,payload,raw in cases:
                def run(profile,irq=False):
                    return (execute(profile,payload,raw,interrupts=irq) if resident else
                            resume(*profile,payload,raw,source=0x2000,interrupts=irq))
                before,after,relocated,irq=run(old),run(new),run(moved),run(new,True)
                assert after['tstates']==relocated['tstates']
                if case in frozen:
                    assert before['tstates']==frozen[case]['baseline_tstates']
                    assert sha(payload)==frozen[case]['payload_sha256']
                row=dict(case=case,payload_bytes=len(payload),raw_bytes=len(raw),payload_sha256=sha(payload),raw_sha256=sha(raw),
                    baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],
                    delta_tstates=after['tstates']-before['tstates'],exact=True,relocated_exact=True,
                    injected_interrupts=irq['injected_interrupts'],
                    caller_stack_bytes=after['stack_bytes'] if resident else after['caller_stack_bytes'],
                    private_stack_bytes=0 if resident else after['private_stack_bytes'],
                    irq_caller_stack_bytes=irq['stack_bytes'] if resident else irq['caller_stack_bytes'],
                    irq_private_stack_bytes=0 if resident else irq['private_stack_bytes'])
                if not resident:
                    assert before['output_cursors']==after['output_cursors']==relocated['output_cursors']==irq['output_cursors']
                    delta=[b-a for a,b in zip(before['slices'],after['slices'])]
                    row.update(quota_returns_exact=True,slices=len(delta),slower_slices=sum(d>0 for d in delta),
                               maximum_slice_increase=max([0]+delta))
                rows.append(row)
            summary=summarize(rows);real=[r for r in rows if r['case'].startswith('real-')]
            summary.update(real_slower_blocks=sum(r['delta_tstates']>0 for r in real),
                           real_slower_slices=sum(r.get('slower_slices',0) for r in real),
                           real_gain_percent=100*(1-summary['real_candidate_tstates']/summary['real_baseline_tstates']))
            emitted=sum(len(data) for _,data in new[0])
            mutable=0 if resident else new[1]['end']-new[1]['state']
            operand_bytes=len(set(new[2].get('patched_addresses',[])))
            caller=max(r['caller_stack_bytes'] for r in rows);private=max(r['private_stack_bytes'] for r in rows)
            irq_caller=max(r['irq_caller_stack_bytes'] for r in rows);irq_private=max(r['irq_private_stack_bytes'] for r in rows)
            # Valid code has no recursive calls: resident CALL/PUSH needs four
            # bytes including the caller return; coroutine cold CALL needs four
            # caller bytes and the deepest yield frame needs 12 ZX0/14 LZSA2.
            assert caller==4 and private==(0 if resident else (12 if codec=='zx0' else 14))
            irq_reserve=6*(1+bool(private))
            memory=dict(emitted_code_and_data_bytes=emitted,mutable_state_arrays_bytes_already_in_regions=mutable,
                self_modifying_operand_bytes_already_in_regions=operand_bytes,
                caller_stack_peak_including_return=caller,private_stack_peak=private,
                internal_scratch_bytes=0,measured_service_bytes=emitted+caller+private,
                service_with_tested_irq_stack_bytes=emitted+irq_caller+irq_private,
                test_irq_handler_code_bytes=13,
                service_with_tested_irq_handler_and_stack_bytes=emitted+irq_caller+irq_private+13,
                service_reserved_for_tested_irq_contract_bytes=emitted+caller+private+irq_reserve+13,
                within_service_cap=emitted+caller+private+irq_reserve+13<=10000,
                stack_scope='observed full corpus; IRQ handler adds two AF pushes plus hardware PC; not arbitrary application IRQ/NMI nesting',
                maximum_compressed_input_bytes=max(r['payload_bytes'] for r in rows),
                maximum_output_history_bytes=max(r['raw_bytes'] for r in rows),
                data_scope='complete resident source and output/history; output already contains history, do not count twice')
            assert memory['within_service_cap']
            report['profiles'][name]=dict(options=selected,baseline=layout(old),candidate=layout(new),
                memory=memory,summary=summary,blocks=rows)
            print(name,json.dumps(summary),'memory',json.dumps(memory),flush=True)
    report['complete']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
