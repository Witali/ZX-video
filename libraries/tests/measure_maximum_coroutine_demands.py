"""Repeated/zero/final quotas with forced IRQs that temporarily clobber IX."""
import argparse,json
from pathlib import Path
from measure_bit_phases import samples
from measure_long_copy import sha
from zx0.resumable import build as fast
from zx0.maximum_coroutine import build
from maximum_coroutine_native import execute
from zx0 import trace


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    baseline=fast(core=0x8000,core_limit=0x8400);candidate=build(irq_code_bytes=21,irq_stack_bytes=8)
    rows=[];hits=set();inplace=[];profiles={cap:build(prefix_cap=cap)for cap in (31,63,127)}
    for name,payload,raw in samples():
        targets=[0,0]+[n for n in range(256,len(raw),256) for _ in range(2)]+[len(raw),len(raw)]
        before=execute(baseline,payload,raw,targets=targets)
        after=execute(candidate,payload,raw,targets=targets,interrupts=True,force_irq=True,irq_clobber_ix=True)
        assert before['output_cursors']==after['output_cursors'] and before['finished_states']==after['finished_states'],name
        assert after['output_cursors'][:2]==[0,0] and after['finished_states'][-2:]==[True,True]
        assert after['caller_stack_bytes']<=12 and after['private_stack_bytes']<=20
        hits.update(after['forced_irq_addresses'])
        rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),targets=targets,
            output_cursors=after['output_cursors'],eof_states=after['finished_states'],every_fast_return_exact=True,
            injected_interrupts=after['injected_interrupts'],forced_interrupts=after['forced_interrupts'],periodic_interrupts=after['periodic_interrupts'],
            caller_stack_bytes=after['caller_stack_bytes'],private_stack_bytes=after['private_stack_bytes']))
        _,proof=trace(payload,limit=len(raw));source=0xc000+proof['minimum_input_start']
        assert proof['minimum_footprint']<=16384
        before_inplace=execute(baseline,payload,raw,source=source)
        variants={}
        for cap,profile in profiles.items():
            after_inplace=execute(profile,payload,raw,source=source,interrupts=True)
            assert after_inplace['output_cursors']==before_inplace['output_cursors'] and after_inplace['finished_states']==before_inplace['finished_states']
            variants[str(cap)]=dict(exact=True,every_fast_return_exact=True,unread_input_never_overwritten=True,injected_interrupts=after_inplace['injected_interrupts'])
        inplace.append(dict(case=name,source=source,input_start=proof['minimum_input_start'],minimum_footprint=proof['minimum_footprint'],profiles=variants))
    sites={site['name']:candidate[1][site['name']+'_check']+2 for site in candidate[2]['quota_sites']}
    assert all(at in hits for at in sites.values())
    report=dict(date='2026-10-20',complete=True,release=False,cases=len(rows),profiles='cap127 selected IX-quota coroutine',
        forced_all_phase_comparisons=sites,forced_irq_addresses=sorted(hits),
        irq_stub_bytes=21,irq_extra_stack_bytes=8,service_bytes_with_this_irq=candidate[2]['service_memory_bytes'],
        all_caller_ix_iy_alternate_pairs_preserved=True,all_caller_registers_clobbered_between_demands=True,blocks=rows,inplace_minimum_start_cases=inplace)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,cases=len(rows),requests=sum(len(r['targets']) for r in rows),
        forced_phase_sites=len(sites),injected_interrupts=sum(r['injected_interrupts'] for r in rows),
        forced_interrupts=sum(r['forced_interrupts']for r in rows),periodic_interrupts=sum(r['periodic_interrupts']for r in rows),
        inplace_profiles=len(inplace)*3)),flush=True)


if __name__=='__main__':main()
