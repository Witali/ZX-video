"""Complete ZX0 repeat-gamma tail refill comparison, identical bytes and ABI."""
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
from test_libraries import profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert profiles() == json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    resources = json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources = resources['original_resources'] + resources['added_pinned_resources']
    for item in resources:
        path = ROOT/'libraries'/item['package']/'src'/item['package']/'asm'/item['file']
        assert sha(path.read_bytes()) == item['sha256']
    report = dict(date='2026-10-19', baseline_revision='674a1fc8', goal_baseline='f5a0362c',
                  complete=False, release=False, goal_achieved=False, default_profiles_exact=31,
                  upstream_resources_exact=len(resources), payload_delta_bytes=0,
                  timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
                  scope=__doc__, profiles={})
    cases = list(samples())
    for tuned in (False, True):
        for resident in (True, False):
            builder = block if resident else coroutine
            options = dict(core=0x8000, core_limit=0x8400, branch_tuned=tuned)
            old = builder(**options)
            new = builder(**options, inline_tail_refill=True)
            moved = builder(**dict(options, core=0x9103, core_limit=0x9500), inline_tail_refill=True)
            rows = []
            for name, payload, raw in cases:
                counts = [0, 0]
                def refill(machine):
                    assert machine.a == 0
                    counts[machine.memory[machine.hl] >> 7] += 1
                def run(profile, irq=False, observe=False):
                    return (execute(profile, payload, raw, interrupts=irq,
                                    watch={profile[1]['TailRefill']: refill} if observe else None)
                            if resident else resume(*profile, payload, raw, source=0x2000, interrupts=irq))
                before, after = run(old), run(new, observe=resident)
                irq, relocated = run(new, True), run(moved)
                assert relocated['tstates'] == after['tstates']
                assert after['tstates'] <= before['tstates']
                row = dict(case=name, payload_sha256=sha(payload), raw_sha256=sha(raw),
                           raw_bytes=len(raw), payload_bytes=len(payload),
                           baseline_tstates=before['tstates'], candidate_tstates=after['tstates'],
                           delta_tstates=after['tstates']-before['tstates'],
                           injected_interrupts=irq['injected_interrupts'], exact=True, relocated_exact=True)
                if resident:
                    assert row['delta_tstates'] == -5*counts[0]-18*counts[1]
                    row.update(refill_stop_0=counts[0], refill_stop_1=counts[1],
                               baseline_stack_bytes=before['stack_bytes'], candidate_stack_bytes=after['stack_bytes'])
                    assert after['stack_bytes'] <= before['stack_bytes']
                else:
                    assert len(before['slices']) == len(after['slices'])
                    deltas = [b-a for a,b in zip(before['slices'], after['slices'])]
                    assert not any(delta > 0 for delta in deltas)
                    row.update(slices=len(deltas), slower_slices=0)
                rows.append(row)
            key = ('block' if resident else 'coroutine') + ('-branch-tuned' if tuned else '')
            report['profiles'][key] = dict(baseline=layout(old), candidate=layout(new),
                summary=summarize(rows), blocks=rows,
                branch_fallbacks=new[2].get('relative_overflow_fallbacks', []))
            print(key, json.dumps(summarize(rows)), flush=True)
    frozen = json.loads((ROOT/'libraries/evidence/trick_23.json').read_text())
    report['strongest_existing_mega_real_tstates'] = frozen['summary']['mega']['real_tstates']
    report['complete'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
