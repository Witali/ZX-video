"""Full causal Z80 FHR1 run with opcode timing and mask/value coverage checks.

Includes frame traversal/cache/motion/masks/raw or Huffman values/attributes.
Excludes metadata and ZX0 decoding, caller pointer/cache-flag setup, window
refill/paging, screen expansion, IRQ/ULA/ROM/disk. Contiguous input overlaps
screen/TR-DOS: CPU fixture only, not a release memory map or cadence proof.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine
from probe_raw_patches import read_header, read_group, OFFSETS
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
import probe_motion_alphabet as alphabet


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhr', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.fhr.read_bytes(); r = Reader(data)
    kind, _, expected, mapping, tables, _ = read_header(r)
    if kind not in (0, 1):
        raise ValueError('Z80 reader currently supports direct/XOR only')
    with np.load(args.motion_cache) as saved:
        states = saved['states']
    if expected != 4971 or states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected source')
    h = Harness(tables, mapping, OFFSETS, skip_empty=True, hybrid=True, raw_kind=kind)
    report = dict(scope=__doc__, baseline_commit='2de2203', input_sha256=sha(data),
        states_sha256=sha(states.tobytes()), frames_expected=expected, kind=kind, complete=False,
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
            raw_values = raw_tiles = raw_base = 0
            for tile, v in enumerate(vectors[i*192:(i+1)*192]):
                if v & 128:
                    a, b = bm[i*384+tile*2:i*384+tile*2+2]
                    raw_tiles += 1; raw_values += a.bit_count()+b.bit_count()
                    raw_base += 649 if a and b else 444 if a else 434
            total_values = sum(b.bit_count() for b in bm[i*384:(i+1)*384]+at[i*96:(i+1)*96])
            wanted = raw_base+(20 if kind == 0 else 27)*raw_values+10*result['unaligned_raw_tiles']
            if (result['raw_values'] != raw_values or result['raw_tiles'] != raw_tiles
                    or result['values'] != total_values-raw_values or result['stages'].get('raw_patch', 0) != wanted
                    or result['cache'] != bool(flags & (128 >> i))):
                raise AssertionError('formula/value/mask/cache coverage differs')
            report['frames'].append(dict(index=start+i, **result))
        if h.position() != bits:
            raise AssertionError('group bit coverage differs')
        report['groups'].append(dict(start=start, frames=n, bits=bits, encoded_bytes=len(encoded)))
        start += n
        if len(report['groups']) % 25 == 1:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'FHR1 Z80: verified {start}/{expected} frames', flush=True)
    r.end()
    stages = Counter()
    for frame in report['frames']:
        stages.update(frame['stages'])
    totals = [f['total_tstates'] for f in report['frames']]
    report['summary'] = dict(frames=start, groups=len(report['groups']), total_tstates=sum(totals),
        mean_frame_tstates=sum(totals)/start, max_frame_tstates=max(totals), worst_frame=totals.index(max(totals)),
        frames_over_nominal_425448=sum(t > 425448 for t in totals), stages=dict(stages),
        **{k: sum(f[k] for f in report['frames']) for k in ('bits', 'values', 'raw_values', 'raw_tiles', 'unaligned_raw_tiles')},
        max_contiguous_input_bytes=max(g['encoded_bytes'] for g in report['groups']))
    report['instruction_histogram'] = [dict(address=pc, tstates=t, count=n) for (pc, t), n in sorted(h.histogram.items())]
    if sum(t*n for (_, t), n in h.histogram.items()) != sum(totals):
        raise AssertionError('histogram differs')
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
