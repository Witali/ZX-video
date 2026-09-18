"""Compare exact temporal prediction with above/left/second-above tiles.

Selection uses 8*changed bytes + popcount +8 for a nonzero vector.
All intra sources are already decoded at the point of use. No new pixel
loss; Z80 execution is checked separately by benchmark_spatial_tiles.py.
This storage probe does not prove playback speed.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_hybrid_tiles import read_header
from probe_motion_entropy import Reader
from probe_motion_residual_order import field_order
from probe_lossless_layouts import sha, measure
from probe_spatial_contexts import profile, encode, decode

PREDICTORS = ('above', 'left', 'above2')


def choose(states, vectors, residual, names=PREDICTORS):
    order = field_order(8).reshape(192, 20)[:, :16]
    current = states[:, :3072].reshape(-1, 96, 32)
    pop = np.array([i.bit_count() for i in range(256)], dtype=np.uint8)
    blocks = residual[:, order].copy()
    costs = (8*(blocks != 0)+pop[blocks]).sum(axis=2)+8*(vectors != 0)
    v = vectors.copy()
    for name in names:
        neighbour = np.zeros_like(current)
        if name == 'above':
            neighbour[:, 1:] = current[:, :-1]
        elif name == 'left':
            neighbour[:, :, 1:] = current[:, :, :-1]
        elif name == 'above2':
            neighbour[:, 2:] = current[:, :-2]
        else:
            raise ValueError('unknown predictor')
        delta = (current ^ neighbour).reshape(-1, 3072)[:, order]
        candidate_cost = (8*(delta != 0)+pop[delta]).sum(axis=2)+8
        better = candidate_cost < costs
        costs = np.where(better, candidate_cost, costs)
        v[better] = 82+PREDICTORS.index(name)
        blocks = np.where(better[:, :, None], delta, blocks)
    result = residual.copy()
    result[:, order.ravel()] = blocks.reshape(len(states), 3072)
    return v, result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--baseline-fht', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--predictors', nargs='+', choices=PREDICTORS, default=list(PREDICTORS))
    args = p.parse_args()
    source = args.baseline_fht.read_bytes()
    original, count, _, _, _ = read_header(Reader(source))
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    from probe_hybrid_tiles import decode as decode_baseline
    if states.shape != (count, 3840) or decode_baseline(source)[0] != states.tobytes():
        raise ValueError('baseline differs from candidate')
    v, delta = choose(states, vectors, residual, args.predictors)
    group = profile(states, delta, 0, [16])['groups'][0]
    data, detail = encode(original, states, v, delta, 0, bytes(group['context_map']), [bytes(t) for t in group['tables']])
    actual, rows = decode(data)
    if actual != states.tobytes() or rows != detail['frames'] or sum(f['bits'] for f in rows) != group['bits']:
        raise AssertionError('independent restoration differs')
    args.cache.mkdir(parents=True, exist_ok=True)
    (args.cache/'motion_16.raw').write_bytes(data)
    np.savez_compressed(args.cache/'candidate.npz', states=states, vectors=v, residual=delta)
    report = dict(scope=__doc__, baseline_commit='e7727cd', complete=True,
        baseline_sha256=sha(source), states_sha256=sha(actual), no_additional_pixel_changes=True,
        player_changed=False, integrated_player_delta_tstates=0,
        selected_predictors=args.predictors, vectors={str(i): int(np.count_nonzero(v == i)) for i in range(85)},
        frames=count, values=int(np.count_nonzero(delta)), bitmap_values=int(np.count_nonzero(delta[:, :3072])),
        raw_bytes=len(data), sha256=sha(data), exact_causal_frame_decode=True, bits=group['bits'],
        groups=len(detail['groups']), max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
        prefix_layout=group['prefix_layout'], deflate_8192=measure(data, 8192))
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
