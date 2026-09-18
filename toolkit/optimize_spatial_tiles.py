"""Choose temporal/intra tiles by coded bits, then retrain 16 contexts.

Deterministic offline rate optimization; all candidate pixels remain exact.
Costs include canonical value lengths, nonempty mask bytes and an 8-bit
nonzero-vector penalty. They estimate pre-ZX0 cost, not final disk size or
Z80 time. Every iteration is serialized and independently decoded in full.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_lossless_layouts import sha, measure
from probe_motion_entropy import Reader
from probe_motion_residual_order import field_order
from probe_spatial_contexts import read_header, profile, encode, decode
from probe_spatial_predictors import PREDICTORS


def choose_coded(states, vectors, residual, mapping, tables, names=('above',)):
    order = field_order(8).reshape(192, 20)[:, :16]
    current = states[:, order]
    temporal = (states ^ residual)[:, order]
    lengths = np.asarray([list(t) for t in tables], dtype=np.uint8)
    lengths = np.where(lengths, lengths, 24)
    lookup = np.frombuffer(bytes(mapping), dtype=np.uint8)

    def cost(prediction):
        active = prediction != current
        values = (lengths[lookup[prediction], current]*active).sum(axis=2)
        mask_bytes = active.reshape(len(states), 192, 2, 8).any(axis=3).sum(axis=2)
        return values+8*mask_bytes

    best_cost = cost(temporal)+8*(vectors != 0)
    result_v, predicted = vectors.copy(), temporal.copy()
    raster = states[:, :3072].reshape(-1, 96, 32)
    for name in names:
        neighbour = np.zeros_like(raster)
        if name == 'above':
            neighbour[:, 1:] = raster[:, :-1]
        elif name == 'left':
            neighbour[:, :, 1:] = raster[:, :, :-1]
        elif name == 'above2':
            neighbour[:, 2:] = raster[:, :-2]
        else:
            raise ValueError('unknown predictor')
        spatial = neighbour.reshape(-1, 3072)[:, order]
        new_cost = cost(spatial)+8
        selected = new_cost < best_cost
        result_v[selected] = 82+PREDICTORS.index(name)
        best_cost = np.where(selected, new_cost, best_cost)
        predicted = np.where(selected[:, :, None], spatial, predicted)
    result_r = residual.copy()
    result_r[:, order.ravel()] = (current ^ predicted).reshape(len(states), 3072)
    return result_v, result_r, result_v >= 82


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--initial-fhs', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--iterations', type=int, default=2)
    p.add_argument('--predictors', nargs='+', choices=PREDICTORS, default=['above'])
    args = p.parse_args()
    initial = args.initial_fhs.read_bytes()
    model, original, count, mapping, tables = read_header(Reader(initial))
    if model != 0 or args.iterations < 1:
        raise ValueError('expected motion context/positive iterations')
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if states.shape != (count, 3840) or decode(initial)[0] != states.tobytes():
        raise ValueError('initial stream differs from candidate')
    report = dict(scope=__doc__, baseline_commit='e7727cd', complete=False,
        initial_sha256=sha(initial), states_sha256=sha(states.tobytes()),
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        cost='sum active canonical lengths (unseen=24) +8 per nonzero mask byte +8 per nonzero vector', rows=[])
    args.cache.mkdir(parents=True, exist_ok=True)
    for iteration in range(1, args.iterations+1):
        v, delta, intra = choose_coded(states, vectors, residual, mapping, tables, args.predictors)
        prof = profile(states, delta, 0, [16])['groups'][0]
        mapping, tables = bytes(prof['context_map']), [bytes(t) for t in prof['tables']]
        data, detail = encode(original, states, v, delta, 0, mapping, tables)
        restored, rows = decode(data)
        if restored != states.tobytes() or rows != detail['frames'] or sum(f['bits'] for f in rows) != prof['bits']:
            raise AssertionError('independent restoration differs')
        stem = f'iteration_{iteration}'
        (args.cache/(stem+'.raw')).write_bytes(data)
        np.savez_compressed(args.cache/(stem+'.npz'), states=states, vectors=v, residual=delta)
        row = dict(name=stem, iteration=iteration, intra_tiles=int(intra.sum()), bitmap_values=int(np.count_nonzero(delta[:, :3072])),
            predictors=args.predictors, intra_vectors={str(i): int(np.count_nonzero(v == i)) for i in (82, 83, 84)},
            raw_bytes=len(data), sha256=sha(data), exact_causal_frame_decode=True, bits=prof['bits'],
            groups=len(detail['groups']), max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
            prefix_layout=prof['prefix_layout'], deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
