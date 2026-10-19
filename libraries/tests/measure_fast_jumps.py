"""Full-block JR-to-JP comparison: flat CPU only, same bytes and caller ABI."""
import argparse
import json
from pathlib import Path

from measure_long_copy import ROOT, samples as lzsa_samples, sha
from measure_bit_phases import samples as zx0_samples
from native_block import execute
from lzsa.native import execute as resume
from lzsa.block import build as lblock
from lzsa.resumable import build as coroutine
from zx0.block import build as zblock
from test_libraries import profiles


def layout(profile):
    regions, labels, metadata = profile
    return dict(code_bytes=sum(len(blob) for _, blob in regions), labels=labels,
                raw_region_sectors=sum((len(blob)+255)//256 for _, blob in regions),
                patched_addresses=metadata.get('patched_addresses', []),
                regions=[dict(address=at, bytes=len(blob), sha256=sha(blob), code_hex=blob.hex())
                         for at, blob in regions])


def summarize(rows):
    real = [row for row in rows if row['case'].startswith('real-')]
    return dict(cases=len(rows), real_blocks=len(real), raw_bytes=sum(r['raw_bytes'] for r in rows),
                baseline_tstates=sum(r['baseline_tstates'] for r in rows),
                candidate_tstates=sum(r['candidate_tstates'] for r in rows),
                delta_tstates=sum(r['delta_tstates'] for r in rows),
                real_baseline_tstates=sum(r['baseline_tstates'] for r in real),
                real_candidate_tstates=sum(r['candidate_tstates'] for r in real),
                real_delta_tstates=sum(r['delta_tstates'] for r in real),
                slower_blocks=sum(r['delta_tstates'] > 0 for r in rows),
                slower_slices=sum(r.get('slower_slices', 0) for r in rows),
                injected_interrupts=sum(r['injected_interrupts'] for r in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert profiles() == json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    frozen = json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources = frozen['original_resources'] + frozen['added_pinned_resources']
    for resource in resources:
        path = ROOT/'libraries'/resource['package']/'src'/resource['package']/'asm'/resource['file']
        assert sha(path.read_bytes()) == resource['sha256']
    blocks = dict(lzsa=list(lzsa_samples()), zx0=list(zx0_samples()))
    configurations = []
    for variant in ('standard', 'turbo', 'mega'):
        configurations.append(('zx0-'+variant, 'zx0', execute,
            lambda fast, core, v=variant: zblock(v, core=core, core_limit=core+0x400, fast_jumps=fast)))
    for extended in (False, True):
        configurations.append(('lzsa-block' + ('-combined' if extended else ''), 'lzsa', execute,
            lambda fast, core, ext=extended: lblock(core=core, core_limit=core+0x400,
                long_copy=ext, near_literals=ext, fast_jumps=fast)))
        configurations.append(('lzsa-coroutine' + ('-combined' if extended else ''), 'lzsa', resume,
            lambda fast, core, ext=extended: coroutine(core=core, core_limit=core+0x400,
                long_copy=ext, near_literals=ext, restore_compare=ext, fast_jumps=fast)))
    report = dict(date='2026-10-19', baseline_revision='dbde780c', complete=False, release=False,
                  scope=__doc__, timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
                  branch='codex/codec-speed-pass3', default_profiles_exact=31,
                  upstream_resources_exact=len(resources), payload_delta_bytes=0,
                  instruction_policy=dict(before='JR e', before_tstates=12, after='JP nn',
                                          after_tstates=10, code_delta_per_site=1,
                                          conditional_branches_unchanged=True), profiles={})
    reference_zx0 = json.loads((ROOT/'libraries/evidence/trick_23.json').read_text())['profiles']
    for name, codec, runner, build in configurations:
        before, after, relocated = build(False, 0x8000), build(True, 0x8000), build(True, 0x9103)
        if codec == 'zx0':
            variant = name.removeprefix('zx0-')
            assert sha(before[0][0][1]) == reference_zx0[variant]['code_sha256']
        rows = []
        for case, payload, raw in blocks[codec]:
            def run(profile, interrupts=False):
                return (runner(*profile, payload, raw, source=0x2000, interrupts=interrupts)
                        if runner is resume else runner(profile, payload, raw, interrupts=interrupts))
            old, new = run(before), run(after)
            irq, moved = run(after, True), run(relocated)
            assert new['tstates'] <= old['tstates'] and moved['tstates'] == new['tstates']
            assert (new['tstates']-old['tstates']) % 2 == 0
            if name in ('zx0-turbo', 'zx0-mega'):
                assert new['tstates']-old['tstates'] == -2
            row = dict(case=case, payload_sha256=sha(payload), raw_sha256=sha(raw),
                       payload_bytes=len(payload), raw_bytes=len(raw),
                       baseline_tstates=old['tstates'], candidate_tstates=new['tstates'],
                       delta_tstates=new['tstates']-old['tstates'],
                       injected_interrupts=irq['injected_interrupts'], exact=True, relocated_exact=True)
            if 'slices' in new:
                assert len(old['slices']) == len(new['slices'])
                delta = [b-a for a, b in zip(old['slices'], new['slices'])]
                assert not any(t > 0 for t in delta)
                row.update(slices=len(delta), slower_slices=0)
            else:
                assert new['stack_bytes'] == old['stack_bytes']
                row.update(stack_bytes=new['stack_bytes'])
            rows.append(row)
        summary = summarize(rows)
        report['profiles'][name] = dict(baseline=layout(before), candidate=layout(after),
                                        summary=summary, blocks=rows)
        print(name, json.dumps(summary), flush=True)
    report['complete'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
