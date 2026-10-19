"""Native conditional-branch frequencies on every frozen real block; no IRQ/disk."""
import argparse
from collections import Counter
import json
from pathlib import Path

from measure_long_copy import ROOT, sha, samples as lzsa_samples
from measure_bit_phases import samples as zx0_samples
from native_block import execute
from lzsa.block import build as lblock
from zx0.block import build as zblock


def instructions(blob, origin):
    # Linear disassembly of this pinned emitter subset. Immediate words are
    # skipped, so self-modified offset data cannot become a watched opcode.
    at = 0
    while at < len(blob):
        op = blob[at]
        if op == 0xed:
            size = 4 if blob[at+1] in (0x43,0x4b,0x53,0x5b,0x63,0x6b,0x73,0x7b) else 2
        elif op == 0xcb:
            size = 2
        elif op in (0xdd, 0xfd):
            raise AssertionError('unsupported index-prefix opcode')
        elif op in (0x01,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a,0xc3,0xcd) or op & 0xc7 in (0xc2,0xc4):
            size = 3
        elif op in (0x10,0x18,0x20,0x28,0x30,0x38,0xc6,0xce,0xd6,0xde,0xe6,0xee,0xf6,0xfe) or (op < 0x40 and op & 7 == 6):
            size = 2
        else:
            size = 1
        yield origin+at, bytes(blob[at:at+size])
        at += size
    assert at == len(blob)


def condition(flags, index):
    return (not flags & 0x40, bool(flags & 0x40), not flags & 1, bool(flags & 1),
            not flags & 4, bool(flags & 4), not flags & 0x80, bool(flags & 0x80))[index]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = dict(date='2026-10-19', baseline_revision='f5a0362c', complete=False,
                  release=False, scope=__doc__, profiles={})
    frozen = json.loads((ROOT/'libraries/evidence/fast_jumps.json').read_text())['profiles']
    for name, samples, profile in (
            ('lzsa2-fast', lzsa_samples, lblock(fast_jumps=True)),
            ('zx0-fast', zx0_samples, zblock()),
            ('zx0-mega', zx0_samples, zblock('mega', fast_jumps=True))):
        watched = {}; branches = {}; hits = Counter(); blocks = []
        for origin, blob in profile[0]:
            for at, code in instructions(blob, origin):
                op = code[0]
                if op & 0xc7 == 0xc2:
                    kind = 'jp'; index = (op >> 3) & 7
                    target = int.from_bytes(code[1:], 'little')
                elif op in (0x20,0x28,0x30,0x38):
                    kind = 'jr'; index = (op-0x20)//8
                    target = at+2+int.from_bytes(code[1:], 'little', signed=True)
                else:
                    continue
                branches[at] = dict(address=at, kind=kind, condition=index, target=target,
                    labels=[key for key, value in profile[1].items() if value == target])
                def observe(machine, pc=at, test=index):
                    hits[pc, condition(machine.f, test)] += 1
                watched[at] = observe
        golden = None
        if name == 'lzsa2-fast':
            golden = {row['case']:row['candidate_tstates'] for row in frozen['lzsa-block']['blocks']}
        elif name == 'zx0-mega':
            golden = {row['case']:row['candidate_tstates'] for row in frozen['zx0-mega']['blocks']}
        else:
            old = json.loads((ROOT/'libraries/evidence/trick_28.json').read_text())['codecs']['zx0']['blocks']
            golden = {row['case']:row['candidate_tstates'] for row in old}
        for case, payload, raw in samples():
            if not case.startswith('real-'):
                continue
            result = execute(profile, payload, raw, watch=watched)
            assert result['tstates'] == golden[case]
            blocks.append(dict(case=case, payload_sha256=sha(payload), raw_sha256=sha(raw),
                               tstates=result['tstates'], exact=True))
        rows = []
        for at, branch in branches.items():
            yes, no = hits[at, True], hits[at, False]
            old = (12*yes+7*no) if branch['kind'] == 'jr' else 10*(yes+no)
            other = 10*(yes+no) if branch['kind'] == 'jr' else 12*yes+7*no
            relative_fits = -128 <= branch['target']-(at+2) <= 127
            rows.append(dict(branch, taken=yes, not_taken=no, total_tstates=old,
                alternative_delta=other-old, relative_fits_current_layout=relative_fits,
                hardware_has_both_forms=branch['condition'] < 4))
        rows.sort(key=lambda row:row['alternative_delta'])
        report['profiles'][name] = dict(code_bytes=len(profile[0][0][1]), blocks=blocks, branches=rows,
            summary=dict(blocks=len(blocks), tstates=sum(row['tstates'] for row in blocks),
                promising_sites=sum(row['alternative_delta'] < 0 and row['hardware_has_both_forms']
                                     and (row['kind'] == 'jr' or row['relative_fits_current_layout']) for row in rows)))
        print(name, json.dumps(report['profiles'][name]['summary']), flush=True)
        for row in rows[:5]:
            print(' ', hex(row['address']), row['kind'], row['condition'], row['labels'], row['alternative_delta'], flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
