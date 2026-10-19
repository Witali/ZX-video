"""Measure the complete frozen real-input token mix before choosing CPU kernels."""
import argparse
from collections import Counter
import json
from pathlib import Path

from measure_long_copy import ROOT, sha, samples as lzsa_samples
from measure_bit_phases import samples as zx0_samples
import lzsa
from zx0.codec import decompress as zx0_decode


def lzsa_mix(data, raw, counts):
    # This is a control-field profiler, not a correctness oracle. The independent
    # production host decoder authenticates its complete output first.
    assert lzsa.decompress(data, limit=len(raw)) == raw
    at = produced = 0
    cached = None

    def byte():
        nonlocal at
        result = data[at]; at += 1
        return result

    def nibble():
        nonlocal cached
        if cached is not None:
            result = cached; cached = None
            return result
        result = byte(); cached = result & 15
        return result >> 4

    def length(value, base):
        if value != base:
            return value, 'token'
        value += nibble()
        if value != base+15:
            return value, 'nibble'
        value += byte()
        if value < 256:
            return value, 'byte'
        if value == 256:
            assert base == 9
            return 0, 'eof'
        assert value == 257
        return byte()+256*byte(), 'word'

    while True:
        token = byte()
        literals, form = length((token >> 3) & 3, 3)
        counts['literal_lengths'][literals] += 1
        counts['literal_forms'][form] += 1
        at += literals; produced += literals
        mode = token >> 5
        counts['offset_modes'][mode] += 1
        if mode < 2:
            nibble()
        elif mode < 4:
            byte()
        elif mode < 6:
            nibble(); byte()
        elif mode == 6:
            byte(); byte()
        match, form = length((token & 7)+2, 9)
        counts['match_forms'][form] += 1
        if not match:
            assert at == len(data) and produced == len(raw)
            return
        counts['match_lengths'][match] += 1
        produced += match


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = dict(date='2026-10-19', baseline_revision='f5a0362c', complete=False,
                  release=False, scope=__doc__, codecs={})
    prior = json.loads((ROOT/'libraries/evidence/fast_jumps_verification.json').read_text())
    for name, expected in prior['source_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) == expected
    report['baseline_source_hashes_exact'] = True
    for codec, samples in (('lzsa2', lzsa_samples), ('zx0', zx0_samples)):
        counters = {key:Counter() for key in
                    ('literal_lengths', 'match_lengths', 'literal_forms', 'match_forms', 'offset_modes')}
        blocks = []
        for name, payload, raw in samples():
            if not name.startswith('real-'):
                continue
            if codec == 'lzsa2':
                lzsa_mix(payload, raw, counters)
            else:
                def literal(start, length):
                    counters['literal_lengths'][length] += 1
                def match(start, offset, length):
                    counters['match_lengths'][length] += 1
                    counters['offset_modes'][offset] += 1
                assert zx0_decode(payload, limit=len(raw), on_match=match, on_literals=literal) == raw
            blocks.append(dict(case=name, payload_sha256=sha(payload), raw_sha256=sha(raw),
                               payload_bytes=len(payload), raw_bytes=len(raw)))
        result = dict(blocks=blocks, counts={key:dict(sorted(value.items())) for key, value in counters.items()})
        result['summary'] = dict(blocks=len(blocks), raw_bytes=sum(row['raw_bytes'] for row in blocks),
            literal_runs=sum(counters['literal_lengths'].values()),
            matches=sum(counters['match_lengths'].values()),
            literal_bytes=sum(n*count for n, count in counters['literal_lengths'].items()),
            match_bytes=sum(n*count for n, count in counters['match_lengths'].items()),
            common_literal_lengths=counters['literal_lengths'].most_common(12),
            common_match_lengths=counters['match_lengths'].most_common(16))
        assert result['summary']['literal_bytes'] + result['summary']['match_bytes'] == result['summary']['raw_bytes']
        report['codecs'][codec] = result
        print(codec, json.dumps(result['summary']), flush=True)
    report['complete'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
