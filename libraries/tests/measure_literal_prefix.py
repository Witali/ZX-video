"""Full native ZX0 literal-prefix comparison, including per-return quota cursors."""
import argparse
import json
from pathlib import Path

from measure_long_copy import ROOT, sha
from measure_bit_phases import samples
from measure_fast_jumps import layout, summarize
from native_block import execute
from lzsa.native import execute as resume
from zx0.block import build as block
from zx0.resumable import build as coroutine
from zx0.codec import decompress
from test_libraries import profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert profiles() == json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    cases = list(samples())
    frozen = json.loads((ROOT/'libraries/evidence/ten_percent_tuned_branches.json').read_text())['profiles']
    report = dict(date='2026-10-19', baseline_revision='674a1fc8', goal_baseline='f5a0362c',
                  complete=False, release=False, goal_achieved=False, payload_delta_bytes=0,
                  timing_reference='libraries/Z80_TIMINGS.md', profiles={})
    for tuned in (False, True):
        for resident in (True, False):
            builder = block if resident else coroutine
            options = dict(branch_tuned=tuned)
            old = builder(core=0x8000, core_limit=0x8400, **options)
            new = builder(core=0x8000, core_limit=0x8400, literal_prefix=True, **options)
            moved = builder(core=0x9103, core_limit=0x9500, literal_prefix=True, **options)
            name = 'zx0-'+('block' if resident else 'coroutine')+('-tuned' if tuned else '')
            base_name = 'zx0-'+('block' if resident else 'coroutine')
            base_key = 'candidate' if tuned else 'baseline'
            assert layout(old) == frozen[base_name][base_key]
            reference = {row['case']: row for row in frozen[base_name]['blocks']}
            rows = []
            for case, payload, raw in cases:
                def run(profile, irq=False):
                    return (execute(profile, payload, raw, interrupts=irq) if resident else
                            resume(*profile, payload, raw, source=0x2000, interrupts=irq))
                before, after = run(old), run(new)
                irq, relocated = run(new, True), run(moved)
                assert relocated['tstates'] == after['tstates']
                long_literals = []
                assert decompress(payload, limit=len(raw), on_literals=lambda at,n:long_literals.append(n>=2)) == raw
                count = sum(long_literals)
                expected_delta = -5*count+(0 if resident else 26*len(after['slices']))
                assert after['tstates']-before['tstates'] == expected_delta
                assert before['tstates'] == reference[case][base_key+'_tstates']
                assert sha(payload) == reference[case]['payload_sha256']
                row = dict(case=case, raw_bytes=len(raw), raw_sha256=sha(raw),
                           payload_sha256=sha(payload), baseline_tstates=before['tstates'],
                           candidate_tstates=after['tstates'],
                           delta_tstates=after['tstates']-before['tstates'],
                           goal_baseline_tstates=reference[case]['baseline_tstates'],
                           injected_interrupts=irq['injected_interrupts'], long_literal_runs=count,
                           expected_delta_tstates=expected_delta, exact=True, relocated_exact=True)
                if resident:
                    assert before['stack_bytes'] == after['stack_bytes']
                    row['stack_bytes'] = after['stack_bytes']
                else:
                    assert before['output_cursors'] == after['output_cursors'] == irq['output_cursors'] == relocated['output_cursors']
                    delta = [b-a for a,b in zip(before['slices'], after['slices'])]
                    row.update(slices=len(delta), output_cursors=after['output_cursors'],
                               slower_slices=sum(t>0 for t in delta), maximum_slice_increase=max([0]+delta),
                               quota_returns_exact=True)
                rows.append(row)
            summary = summarize(rows)
            real = [row for row in rows if row['case'].startswith('real-')]
            summary.update(real_slower_blocks=sum(row['delta_tstates']>0 for row in real),
                           real_slower_slices=sum(row.get('slower_slices',0) for row in real),
                           real_goal_baseline_tstates=sum(row['goal_baseline_tstates'] for row in real))
            report['profiles'][name] = dict(baseline=layout(old), candidate=layout(new),
                relative_overflow_fallbacks=new[2].get('relative_overflow_fallbacks', []),
                summary=summary, blocks=rows)
            print(name, json.dumps(summary), 'code', layout(old)['code_bytes'], '->', layout(new)['code_bytes'], flush=True)
    report['complete'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
