"""Execute every FHS1/FHF1 motion-context frame with causal prediction.

CPU fixture only: includes causal cache/motion/intra/masks/values/attributes;
excludes ZX0/metadata, input refill/paging, native output, IRQ/ULA/ROM/disk.
The contiguous bit input overlaps the screen/TR-DOS workspace.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine
from probe_spatial_contexts import read_header, read_group, OFFSETS
from probe_motion_entropy import Reader
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--states-sha256', required=True)
    p.add_argument('--extended', action='store_true', help='enable all three spatial predictors')
    p.add_argument('--fast-fragments', action='store_true', help='FHF1 complete fragment payloads; requires --extended')
    p.add_argument('--unrolled-motion', action='store_true')
    p.add_argument('--baseline-commit', default='7dea054')
    args = p.parse_args()
    if args.fast_fragments and not args.extended:
        p.error('--fast-fragments requires --extended')
    data = args.fhs.read_bytes(); r = Reader(data)
    model, _, count, mapping, tables = read_header(r, magic=b'FHF1' if args.fast_fragments else b'FHS1')
    with np.load(args.motion_cache) as saved:
        states = saved['states']
    if model != 0 or states.shape != (4971, 3840) or count != len(states) or sha(states.tobytes()) != args.states_sha256:
        raise ValueError('model/source mismatch')
    h = Harness(tables, mapping, OFFSETS, skip_empty=True, hybrid=True, intra_above=True, intra_extended=args.extended, fast_fragments=args.fast_fragments, unrolled_motion=args.unrolled_motion)
    report = dict(scope=__doc__, baseline_commit=args.baseline_commit, input_sha256=sha(data),
        intra_extended=args.extended, fast_fragments=args.fast_fragments, unrolled_motion=args.unrolled_motion,
        states_sha256=sha(states.tobytes()), frames_expected=count, complete=False,
        code_bytes=h.labels['state']-machine.CODE, state_bytes=h.labels['end']-h.labels['state'],
        code_hex=h.code.hex(), labels=h.labels, instruction_listing=h.listing,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        tables=[dict(base=base, bytes=len(blob), sha256=sha(blob)) for base, blob in h.regions],
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        groups=[], frames=[])
    start = 0
    while start < count:
        n, flags, bits, vectors, bm, at, encoded = read_group(r, count-start, fast_fragments=args.fast_fragments)
        if any(v > (88 if args.fast_fragments else (84 if args.extended else 82)) for v in vectors):
            raise ValueError('unsupported vector in this Z80 configuration')
        h.begin(encoded, vectors, bm, at)
        for i in range(n):
            got = h.run(i, states[start+i].tobytes())
            expected = intra = 0
            modes = Counter()
            for tile, v in enumerate(vectors[i*192:(i+1)*192]):
                if 82 <= v <= 84:
                    values = sum(b.bit_count() for b in bm[i*384+tile*2:i*384+tile*2+2])
                    expected += machine.intra_tstates(v, tile, values, extended=args.extended)
                    intra += 1
                    modes[v] += 1
            values = sum(b.bit_count() for b in bm[i*384:(i+1)*384]+at[i*96:(i+1)*96])
            if (got['stages'].get('intra', 0) != expected or got['values'] != values
                    or got['cache'] != bool(flags & (128 >> i)) or got['literals']):
                raise AssertionError('formula/coverage/cache mismatch')
            report['frames'].append(dict(index=start+i, intra_tiles=intra, intra_modes=dict(modes), **got))
        if h.position() != bits:
            raise AssertionError('group bit coverage')
        report['groups'].append(dict(start=start, frames=n, bits=bits, encoded_bytes=len(encoded)))
        start += n
        if len(report['groups']) % 25 == 1:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'{data[:4].decode()} Z80: verified {start}/{count}', flush=True)
    r.end()
    stages = Counter()
    for row in report['frames']:
        stages.update(row['stages'])
    totals = [f['total_tstates'] for f in report['frames']]
    report['summary'] = dict(frames=count, groups=len(report['groups']), total_tstates=sum(totals),
        mean_frame_tstates=sum(totals)/count, max_frame_tstates=max(totals), worst_frame=totals.index(max(totals)),
        frames_over_nominal_425448=sum(t > 425448 for t in totals), stages=dict(stages),
        values=sum(f['values'] for f in report['frames']), intra_tiles=sum(f['intra_tiles'] for f in report['frames']))
    report['summary']['intra_modes'] = dict(sum((Counter(row['intra_modes']) for row in report['frames']), Counter()))
    if args.fast_fragments:
        report['summary']['fast_kinds'] = dict(sum((Counter(row['fast_kinds']) for row in report['frames']), Counter()))
        report['summary']['fast_tiles'] = sum(row['fast_tiles'] for row in report['frames'])
        report['summary']['fast_unaligned'] = sum(row['fast_unaligned'] for row in report['frames'])
    report['instruction_histogram'] = [dict(address=pc, tstates=t, count=n) for (pc, t), n in sorted(h.histogram.items())]
    if sum(t*n for (_, t), n in h.histogram.items()) != sum(totals):
        raise AssertionError('histogram differs')
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
