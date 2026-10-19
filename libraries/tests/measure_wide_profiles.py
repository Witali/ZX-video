"""Recheck public wide LZSA2 raw profiles against the frozen independent proof."""
import argparse
import json
from pathlib import Path

from measure_long_copy import ROOT, samples, sha
from measure_full_token_dispatch import directed_tokens, repeat_micro_paths, layout
from native_block import execute
from lzsa.block import build
from lzsa import decompress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    frozen = json.loads((ROOT/'libraries/evidence/ten_percent_full_token_dispatch.json').read_text())
    cases = list(samples())
    directed = list(directed_tokens())
    report = dict(date='2026-10-19', complete=False, release=False,
        baseline_revision='f5a0362c', independent_revision='042989fc',
        scope='Public resident wide/wide-shared; no coroutine/guarded producer or player claim.',
        storage_budget_bytes=10000, profiles={})
    for variant, name in (('wide', 'expanded'), ('wide-shared', 'shared-literal-bodies')):
        profile = build(variant, core=0x8000, core_limit=0xb000)
        moved = build(variant, core=0x9103, core_limit=0xb000)
        reference = frozen['profiles'][name]
        assert layout(profile) == reference['candidate']
        assert layout(moved) == reference['relocated']
        old = {r['case']:r for r in reference['blocks']}
        rows = []
        for name_, payload, raw in cases:
            assert sha(payload)==old[name_]['payload_sha256'] and sha(raw)==old[name_]['raw_sha256']
            plain = execute(profile, payload, raw)
            irq = execute(profile, payload, raw, interrupts=True)
            relocated = execute(moved, payload, raw)
            assert plain['tstates'] == relocated['tstates'] == old[name_]['candidate_tstates']
            assert plain['stack_bytes'] <= profile[2]['caller_stack_bytes']
            rows.append(dict(case=name_, tstates=plain['tstates'], exact=True,
                compressed_input_bytes=len(payload), output_including_history_bytes=len(raw),
                separate_service_and_buffers_bytes=profile[2]['service_memory_bytes']+len(payload)+len(raw),
                injected_interrupts=irq['injected_interrupts'], stack_bytes=plain['stack_bytes']))
        seen = set()
        def watch(value):return lambda machine:seen.add(value)
        watches = {profile[1]['token_'+str(v)]:watch(v) for v in range(256)}
        irqs = 0
        for name_, payload, raw, value in directed:
            assert decompress(payload, limit=len(raw)) == raw
            seen.clear()
            plain = execute(profile, payload, raw, watch=watches)
            assert value in seen
            irq = execute(profile, payload, raw, interrupts=True)
            relocated = execute(moved, payload, raw)
            assert relocated['tstates'] == plain['tstates']
            irqs += irq['injected_interrupts']
        micro = repeat_micro_paths(profile, prototype=True, shared=variant=='wide-shared')
        report['profiles'][variant] = dict(candidate=layout(profile), relocated=layout(moved),
            total_storage_bytes=profile[2]['total_storage_bytes'],
            service_memory=profile[2]['service_memory'],
            verified_irq_headroom_bytes=6,
            maximum_real_input_bytes=max(len(p) for n,p,r in cases if n.startswith('real-')),
            maximum_real_output_history_bytes=max(len(r) for n,p,r in cases if n.startswith('real-')),
            relocated_total_storage_bytes=moved[2]['total_storage_bytes'],
            corpus_cases=len(rows), directed_cases=len(directed), blocks=rows,
            directed_injected_interrupts=irqs, micro_paths=micro,
            frozen_summary=reference['summary'], exact=True, relocated_exact=True)
        print(variant, reference['summary']['real_candidate_tstates'], profile[2]['code_bytes'], flush=True)
    report['source_sha256_lf'] = {str(p.relative_to(ROOT)).replace('\\', '/'):sha(p.read_bytes().replace(b'\r\n', b'\n'))
        for p in (ROOT/'libraries/lzsa/src/lzsa/wide.py', ROOT/'libraries/lzsa/src/lzsa/block.py',
                  ROOT/'libraries/lzsa/src/lzsa/__main__.py', ROOT/'libraries/lzsa/src/lzsa/export.py', Path(__file__))}
    report['complete'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':main()
