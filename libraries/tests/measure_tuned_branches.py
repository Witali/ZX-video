"""Complete field-equivalent Fast branch candidates; real and directed regressions."""
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
from tuned_branch_profile import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = dict(date='2026-10-19', baseline_revision='f5a0362c', complete=False,
                  release=False, scope=__doc__, goal_achieved=False, profiles={})
    for codec, samples, raw_builder, coroutine_builder in (
            ('lzsa2', lsamples, lblock, lcoroutine), ('zx0', zsamples, zblock, zcoroutine)):
        cases = list(samples())
        options = dict(fast_jumps=True) if codec == 'lzsa2' else {}
        for resident in (True, False):
            builder = raw_builder if resident else coroutine_builder
            old = builder(core=0x8000, core_limit=0x8400, **options)
            new = build(codec, resident=resident, **options)
            relocated = build(codec, resident=resident, core=0x9103, **options)
            rows = []
            for case, payload, raw in cases:
                def run(profile, irq=False):
                    return (execute(profile, payload, raw, interrupts=irq) if resident else
                            resume(*profile, payload, raw, source=0x2000, interrupts=irq))
                before, after = run(old), run(new)
                irq, moved = run(new, True), run(relocated)
                assert moved['tstates'] == after['tstates']
                row = dict(case=case, raw_bytes=len(raw), raw_sha256=sha(raw),
                           payload_sha256=sha(payload), baseline_tstates=before['tstates'],
                           candidate_tstates=after['tstates'],
                           delta_tstates=after['tstates']-before['tstates'],
                           injected_interrupts=irq['injected_interrupts'], exact=True)
                if not resident:
                    assert len(before['slices']) == len(after['slices'])
                    delta = [b-a for a,b in zip(before['slices'], after['slices'])]
                    row['slower_slices'] = sum(t > 0 for t in delta)
                rows.append(row)
            name = codec+('-block' if resident else '-coroutine')
            summary = summarize(rows)
            report['profiles'][name] = dict(baseline=layout(old), candidate=layout(new),
                branch_changes=new[2]['branch_changes'],
                relative_overflow_fallbacks=new[2]['relative_overflow_fallbacks'], summary=summary, blocks=rows)
            print(name, json.dumps(summary), 'code', layout(old)['code_bytes'], '->', layout(new)['code_bytes'], flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
