"""Measure the rejected-size full-token LZSA2 speed bound on complete inputs."""
import argparse
import gzip
import json
from pathlib import Path

from measure_long_copy import ROOT, samples, sha
from lzsa import decompress, encode
from lzsa.block import build as public_build
from native_block import execute
from full_token_dispatch import build


def directed_tokens():
    # The first match initializes repeat-offset history. Its nibble-sized
    # versus byte-sized offset sets both reservoir phases for the next token.
    # An all-A 9,000-byte seed makes every represented offset readable.
    for phase, first in (('empty', 3), ('full', 34)):
        for value in range(256):
            cls, literal, field = value>>5, (value>>3)&3, value&7
            distance = (1, 2, 33, 257, 513, 769, 8705, first)[cls]
            start = 9002+literal
            raw = b'A'*(start+field+2)
            payload = encode(raw, [(9000, 2, first), (start, field+2, distance)])
            yield f'token-{value:02x}-{phase}', payload, raw, value
    # Every possible offset nibble, including the signed-offset boundaries.
    for cls in (0, 1, 4, 5):
        for half in range(16):
            distance = (65536-(0xffe0|(half<<1)|(1-cls)) if cls<2 else
                        65536-(0xe000|(half<<9)|((1-(cls&1))<<8))+512)
            raw = b'A'*9004
            payload = encode(raw, [(9000, 2, 34), (9002, 2, distance)])
            yield f'offset-nibble-{cls}-{half}', payload, raw, cls<<5
    for n in (1, 2):
        raw = bytes(range(n))
        payload = bytes.fromhex('5f ff ef')+n.to_bytes(2, 'little')+raw+bytes.fromhex('00 e8')
        yield f'word-literal-{n}', payload, raw, 0x5f
    yield 'single-nibble-eof-empty', bytes.fromhex('e7 f0 e8'), b'', 0xe7
    yield 'single-nibble-eof-one', bytes.fromhex('ef 41 f0 e8'), b'A', 0xef


def summarize(rows):
    real = [r for r in rows if r['case'].startswith('real-')]
    before = sum(r['baseline_tstates'] for r in real)
    after = sum(r['candidate_tstates'] for r in real)
    return dict(cases=len(rows), real_blocks=len(real), real_raw_bytes=sum(r['raw_bytes'] for r in real),
        real_baseline_tstates=before, real_candidate_tstates=after,
        real_delta_tstates=after-before, real_percent_saved=100*(before-after)/before,
        all_delta_tstates=sum(r['delta_tstates'] for r in rows),
        slower_blocks=[r['case'] for r in rows if r['delta_tstates']>0],
        maximum_regression_tstates=max(r['delta_tstates'] for r in rows),
        injected_interrupts=sum(r['injected_interrupts'] for r in rows))


def layout(profile):
    regions, labels, metadata = profile
    return dict(code_bytes=metadata['code_bytes'], table_bytes=metadata.get('table_bytes', 0),
        alignment_padding=metadata.get('alignment_padding', 0), core_end=metadata['core_end'],
        state_bytes=metadata['state_bytes'], patched_addresses=metadata['patched_addresses'],
        raw_region_sectors=sum((len(blob)+255)//256 for _, blob in regions),
        regions=[dict(address=at, bytes=len(blob), sha256=sha(blob)) for at, blob in regions])


def repeat_micro_paths(profile, *, prototype=False, shared=False):
    rows = []
    for literals, expected_old, expected_new in ((0, 116, 75), (1, 145, 98), (2, 166, 114)):
        token = 0xe0|(literals<<3)
        _, payload, raw, _ = next(row for row in directed_tokens() if row[0]==f'token-{token:02x}-empty')
        start = None
        observed = []
        def begin(machine):
            nonlocal start
            if machine.memory[machine.hl] == token: start = machine.ticks_to_stop
        def copy(machine):
            nonlocal start
            if start is not None:
                observed.append(start-machine.ticks_to_stop);start=None
        execute(profile, payload, raw, watch={profile[1]['ReadToken']:begin, profile[1]['MatchUseC']:copy})
        expected = expected_new+(10 if shared and literals else 0) if prototype else expected_old
        assert observed == [expected], (literals, expected, observed)
        rows.append(dict(literals=literals, match_bytes=2, token=token,
            endpoint='ReadToken fetch through before MatchUseC/PUSH HL', tstates=expected))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cases = list(samples())
    baseline = public_build(fast_jumps=True)
    previous = public_build(fast_jumps=True, branch_tuned=True)
    old = {name:execute(baseline, payload, raw) for name, payload, raw in cases}
    prior = {name:execute(previous, payload, raw) for name, payload, raw in cases}
    assert sum(old[n]['tstates'] for n, _, _ in cases if n.startswith('real-')) == 17765094
    assert sum(prior[n]['tstates'] for n, _, _ in cases if n.startswith('real-')) == 17714484
    report = dict(date='2026-10-19', baseline_revision='f5a0362c', previous_revision='674a1fc8',
        complete=False, release=False, goal_achieved=False,
        scope='Raw-only full-token speed bound; oversized test-only prototypes, no public/player adoption.',
        baseline=layout(baseline), previous=layout(previous),
        baseline_micro_paths=repeat_micro_paths(baseline), profiles={})
    for shared in (False, True):
        profile = build(shared_literals=shared)
        moved = build(core=0x9103, shared_literals=shared)
        rows = []
        for name, payload, raw in cases:
            assert decompress(payload, limit=len(raw)) == raw
            new = execute(profile, payload, raw)
            irq = execute(profile, payload, raw, interrupts=True)
            relocated = execute(moved, payload, raw)
            assert relocated['tstates'] == new['tstates']
            rows.append(dict(case=name, payload_bytes=len(payload), raw_bytes=len(raw),
                payload_sha256=sha(payload), raw_sha256=sha(raw),
                baseline_tstates=old[name]['tstates'], previous_tstates=prior[name]['tstates'],
                candidate_tstates=new['tstates'], delta_tstates=new['tstates']-old[name]['tstates'],
                stack_bytes=new['stack_bytes'], exact=True, injected_interrupts=irq['injected_interrupts']))
        directed = list(directed_tokens())
        seen = set()
        def watch(value):
            return lambda machine:seen.add(value)
        watches = {profile[1]['token_'+str(v)]:watch(v) for v in range(256)}
        irqs = 0
        digest = bytearray()
        for name, payload, raw, value in directed:
            assert decompress(payload, limit=len(raw)) == raw
            seen.clear()
            exact = execute(profile, payload, raw, watch=watches)
            assert value in seen, (name, value, seen)
            irq = execute(profile, payload, raw, interrupts=True)
            relocated = execute(moved, payload, raw)
            assert relocated['tstates'] == exact['tstates']
            irqs += irq['injected_interrupts']
            digest.extend((name+':'+sha(payload)+':'+sha(raw)+'\n').encode('ascii'))
        name = 'shared-literal-bodies' if shared else 'expanded'
        summary = summarize(rows)
        report['profiles'][name] = dict(candidate=layout(profile), relocated=layout(moved),
            summary=summary, blocks=rows,
            micro_paths=repeat_micro_paths(profile, prototype=True, shared=shared),
            directed=dict(cases=len(directed),
                all_256_token_values_both_cache_phases=True, all_64_offset_nibble_forms=True,
                single_nibble_eof=True, word_literal_1_and_2=True,
                inputs_sha256=sha(digest), injected_interrupts=irqs,
                relocated_exact=True, exact=True))
        print(name, json.dumps(summary), flush=True)
    report['limitations'] = [
        'Code and rounded code-region sectors grow far beyond the approximately 10% free-growth preference.',
        '21 expanded / 22 shared directed corpus blocks are slower; every real block improves.',
        'Only fully resident raw blocks are implemented; no coroutine, guarded input or player timing claim.',
        'CPU totals exclude injected IRQs, ULA contention, ROM and physical disk latency.',
        'Compressed payloads and public decoder sources/defaults are unchanged.']
    report['source_sha256_lf'] = {str(p.relative_to(ROOT)).replace('\\', '/'):sha(p.read_bytes().replace(b'\r\n', b'\n'))
        for p in (Path(__file__), Path(__file__).with_name('full_token_dispatch.py'))}
    report['complete'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
