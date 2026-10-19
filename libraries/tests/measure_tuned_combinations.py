"""Public LZSA2 branch option with old copy/restore/unconditional-jump profiles."""
import argparse
import json
from pathlib import Path

from measure_long_copy import samples, sha
from measure_fast_jumps import layout, summarize
from lzsa.block import build as block
from lzsa.resumable import build as coroutine
from lzsa.native import execute as resume
from native_block import execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cases = list(samples())
    report = dict(date='2026-10-19', baseline_revision='f5a0362c', complete=False,
                  release=False, goal_achieved=False, scope=__doc__, profiles={})
    for resident in (True, False):
        for fast, extended in ((False, False), (False, True), (True, True)):
            options = dict(fast_jumps=fast, long_copy=extended, near_literals=extended)
            if not resident:
                options['restore_compare'] = extended
            builder = block if resident else coroutine
            before = builder(core=0x8000, core_limit=0x8400, **options)
            after = builder(core=0x8000, core_limit=0x8400, branch_tuned=True, **options)
            relocated = builder(core=0x9103, core_limit=0x9500, branch_tuned=True, **options)
            rows = []
            for case, payload, raw in cases:
                def run(profile, irq=False):
                    return (execute(profile, payload, raw, interrupts=irq) if resident else
                            resume(*profile, payload, raw, source=0x2000, interrupts=irq))
                old, new = run(before), run(after)
                irq, moved = run(after, True), run(relocated)
                assert moved['tstates'] == new['tstates']
                row = dict(case=case, raw_bytes=len(raw), raw_sha256=sha(raw), payload_sha256=sha(payload),
                    baseline_tstates=old['tstates'], candidate_tstates=new['tstates'],
                    delta_tstates=new['tstates']-old['tstates'],
                    injected_interrupts=irq['injected_interrupts'], exact=True)
                if not resident:
                    assert len(old['slices']) == len(new['slices'])
                    row['slower_slices'] = sum(b>a for a,b in zip(old['slices'], new['slices']))
                rows.append(row)
            name = ('block' if resident else 'coroutine')+f'-fast{fast}-extended{extended}'
            report['profiles'][name] = dict(options=options, baseline=layout(before), candidate=layout(after),
                                            summary=summarize(rows), blocks=rows)
            print(name, json.dumps(summarize(rows)), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
