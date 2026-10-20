"""Compare twelve patched quota sites with caller-preserving alternate-DE quota."""
import argparse,json
from pathlib import Path
from measure_bit_phases import samples
from measure_long_copy import sha
from zx0.resumable import build as fast
from zx0.maximum_coroutine import build
from maximum_coroutine_native import execute


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--modes',nargs='+',choices=('patched','alternate','index'),default=['patched','alternate','index']);a=p.parse_args()
    baseline=fast(core=0x8000,core_limit=0x8400)
    candidates={mode:build(_quota_mode=mode) for mode in a.modes}
    rows={mode:[] for mode in candidates}
    for name,payload,raw in samples():
        before=execute(baseline,payload,raw)
        for mode,profile in candidates.items():
            after=execute(profile,payload,raw)
            assert after['output_cursors']==before['output_cursors'] and after['finished_states']==before['finished_states'],name
            delta=[b-a for a,b in zip(before['slices'],after['slices'])]
            rows[mode].append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),raw_bytes=len(raw),
                baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],delta_tstates=sum(delta),
                slower_slices=sum(t>0 for t in delta),largest_slice_delta=max(delta),
                output_cursors_exact=True,eof_states_exact=True,exact=True))
        if name in ('real-2-0','real-3-0'):print(name,'complete',flush=True)
    report=dict(date='2026-10-20',complete=True,release=False,goal_baseline='f5a0362c',profiles={})
    for mode,items in rows.items():
        real=[r for r in items if r['case'].startswith('real-')]
        summary=dict(cases=len(items),real_blocks=len(real),baseline_tstates=sum(r['baseline_tstates'] for r in items),candidate_tstates=sum(r['candidate_tstates'] for r in items),
            real_baseline_tstates=sum(r['baseline_tstates'] for r in real),real_candidate_tstates=sum(r['candidate_tstates'] for r in real),
            slower_blocks=sum(r['delta_tstates']>0 for r in items),slower_real_blocks=sum(r['delta_tstates']>0 for r in real),
            slower_slices=sum(r['slower_slices'] for r in items),maximum_slice_delta=max(r['largest_slice_delta'] for r in items))
        report['profiles'][mode]=dict(service_memory_bytes=candidates[mode][2]['service_memory_bytes'],summary=summary,blocks=items)
        print(mode,json.dumps(summary),flush=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
