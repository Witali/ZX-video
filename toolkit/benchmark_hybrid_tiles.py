"""Causal Z80 FHT1 decode, including motion, masks, literals and attributes.

Same CPU-only scope/map as benchmark_causal_tiles. Host expands group
metadata and supplies pointers/cache flag, never reconstructed predictors.
Excludes ZX0, metadata decoder, input refill, native drawing, caller setup,
IRQ/ULA, TR-DOS ROM and physical disk. Not a frame-delivery measurement.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine
from probe_hybrid_tiles import read_header, read_group
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
import probe_motion_alphabet as alphabet


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fht', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--states-sha256', default=alphabet.INPUT_STATES_SHA)
    p.add_argument('--baseline-commit', default='608e57b')
    args = p.parse_args()
    data = args.fht.read_bytes(); r = Reader(data)
    _, expected, offsets, mapping, tables = read_header(r)
    with np.load(args.motion_cache) as saved:
        states = saved['states']
    if expected != 4971 or states.shape != (expected, 3840) or sha(states.tobytes()) != args.states_sha256:
        raise ValueError('unexpected source')
    h = Harness(tables, mapping, offsets, skip_empty=True, hybrid=True)
    report = dict(scope=__doc__, baseline_commit=args.baseline_commit, input_sha256=sha(data),
        states_sha256=sha(states.tobytes()), frames_expected=expected, complete=False,
        code_bytes=h.labels['state']-machine.CODE, state_bytes=h.labels['end']-h.labels['state'],
        code_hex=h.code.hex(), labels=h.labels, instruction_listing=h.listing,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        tables=[dict(base=base, bytes=len(blob), sha256=sha(blob)) for base, blob in h.regions],
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        groups=[], frames=[])
    start = 0
    while start < expected:
        n, flags, bits, vectors, bm, at, encoded = read_group(r, expected-start)
        h.begin(encoded, vectors, bm, at)
        for i in range(n):
            result = h.run(i, states[start+i].tobytes())
            wanted = sum(b.bit_count() for b in bm[384*i:384*(i+1)]+at[96*i:96*(i+1)])
            if result['values'] != wanted or result['literals'] != vectors[192*i:192*(i+1)].count(82):
                raise AssertionError('value/literal coverage differs')
            if result['cache'] != bool(flags & (128 >> i)):
                raise AssertionError('cache flag differs')
            report['frames'].append(dict(index=start+i, **result))
        if h.position() != bits:
            raise AssertionError('group bit coverage differs')
        report['groups'].append(dict(start=start, frames=n, bits=bits, encoded_bytes=len(encoded)))
        start += n
        if len(report['groups']) % 25 == 1:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'FHT1 Z80: verified {start}/{expected} frames', flush=True)
    r.end()
    stages = Counter()
    for row in report['frames']:
        stages.update(row['stages'])
    totals = [row['total_tstates'] for row in report['frames']]
    report['summary'] = dict(frames=start, groups=len(report['groups']), total_tstates=sum(totals),
        mean_frame_tstates=sum(totals)/start, max_frame_tstates=max(totals), worst_frame=totals.index(max(totals)),
        frames_over_nominal_425448=sum(t > 425448 for t in totals), stages=dict(stages),
        bits=sum(f['bits'] for f in report['frames']), values=sum(f['values'] for f in report['frames']),
        literals=sum(f['literals'] for f in report['frames']), cache_frames=sum(f['cache'] for f in report['frames']),
        max_contiguous_input_bytes=max(g['encoded_bytes'] for g in report['groups']))
    report['instruction_histogram'] = [dict(address=pc, tstates=t, count=n) for (pc, t), n in sorted(h.histogram.items())]
    if sum(t*n for (_, t), n in h.histogram.items()) != sum(totals):
        raise AssertionError('histogram differs')
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
