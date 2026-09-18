"""Add exact intra-frame above-row prediction to a bounded-motion candidate.

Choose between its original temporal predictor and an above-row predictor
with a simple offline cost. Pixel/attribute states are preserved exactly.
The decoder must apply each correction before predicting the next row.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_hybrid_tiles import read_header
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader
from probe_motion_residual_order import field_order
from probe_spatial_contexts import profile, encode, decode


def choose(states, vectors, residual):
    order = field_order(8).reshape(192, 20)[:, :16]
    above = np.zeros_like(states[:, :3072]); above[:, 32:] = states[:, :3040]
    delta = states[:, :3072] ^ above
    pop = np.array([i.bit_count() for i in range(256)], dtype=np.uint8)
    old, new = residual[:, order], delta[:, order]
    old_cost = (8*(old != 0)+pop[old]).sum(axis=2)+8*(vectors != 0)
    new_cost = (8*(new != 0)+pop[new]).sum(axis=2)+8
    intra = new_cost < old_cost
    result_v = vectors.copy(); result_v[intra] = 82
    result_r = residual.copy()
    new_blocks = np.where(intra[:, :, None], new, old)
    result_r[:, order.ravel()] = new_blocks.reshape(len(states), 3072)
    return result_v, result_r, intra


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--baseline-fht', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--models', nargs='+', choices=('motion', 'above'), default=['motion', 'above'])
    p.add_argument('--counts', type=int, nargs='+', default=[16])
    args = p.parse_args()
    baseline = args.baseline_fht.read_bytes()
    original, count, _, _, _ = read_header(Reader(baseline))
    with np.load(args.motion_cache) as saved:
        states, old_v, old_r = (saved[k] for k in ('states', 'vectors', 'residual'))
    from probe_hybrid_tiles import decode as decode_baseline
    if count != len(states) or decode_baseline(baseline)[0] != states.tobytes():
        raise ValueError('candidate differs from baseline')
    vectors, residual, intra = choose(states, old_v, old_r)
    args.cache.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.cache/'candidate.npz', states=states, vectors=vectors, residual=residual)
    report = dict(scope=__doc__, baseline_commit='e7727cd', complete=False,
        states_sha256=sha(states.tobytes()), baseline_sha256=sha(baseline), frames=count,
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        intra_tiles=int(intra.sum()), bitmap_values_before=int(np.count_nonzero(old_r[:, :3072])),
        bitmap_values_after=int(np.count_nonzero(residual[:, :3072])), rows=[])
    for name in args.models:
        model = int(name == 'above')
        prof = profile(states, residual, model, args.counts)
        for group in prof['groups']:
            contexts = group['bitmap_contexts']
            data, detail = encode(original, states, vectors, residual, model,
                bytes(group['context_map']), [bytes(t) for t in group['tables']])
            restored, rows = decode(data)
            if restored != states.tobytes() or rows != detail['frames'] or sum(f['bits'] for f in rows) != group['bits']:
                raise AssertionError('independent restoration differs')
            stem = f'{name}_{contexts}'
            (args.cache/(stem+'.raw')).write_bytes(data)
            row = dict(name=stem, model=model, contexts=contexts, raw_bytes=len(data), sha256=sha(data),
                exact_causal_frame_decode=True, bits=group['bits'], groups=len(detail['groups']),
                max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
                prefix_layout=group['prefix_layout'], deflate_8192=measure(data, 8192))
            report['rows'].append(row)
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(json.dumps(dict(intra_tiles=report['intra_tiles'], bitmap_values_after=report['bitmap_values_after'], **row)), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
