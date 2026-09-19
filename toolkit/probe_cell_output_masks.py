"""Exact native-cell update flags for alternating screens, 80 bytes/frame.

Each bit covers one native 8x8 cell: four compact bytes in rows 8..87.
If a four-row band has at least --dense cells, mark its whole band dirty
for the faster linear output path. All attributes still copy each frame.
No omitted bitmap byte may be nonzero. No CPU speed claim is made here.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_lossless_layouts import sha, measure


def masks(states, dense=18):
    if (states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840
            or not 1 <= dense <= 32 or np.any(states[:, :256]) or np.any(states[:, 2816:3072])):
        raise ValueError('invalid screens, density or nonzero omitted rows')
    bitmap = states[:, 256:2816].reshape(-1, 20, 4, 32)
    previous = np.zeros_like(bitmap)
    previous[2:] = bitmap[:-2]
    changed = (bitmap != previous).any(axis=2)
    whole = changed.sum(axis=2) >= dense
    changed[whole] = True
    packed = np.packbits(changed, axis=2)
    restored = previous.copy()
    np.copyto(restored, bitmap, where=changed[:, :, None, :])
    if not np.array_equal(restored, bitmap):
        raise AssertionError('cell map omits output changes')
    return packed, whole, changed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--dense', type=int, default=18)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    packed, whole, changed = masks(states, args.dense)
    data = packed.tobytes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    report = dict(scope=__doc__, complete=True, states_sha256=sha(states.tobytes()),
        stream_sha256=sha(data), frames=len(states), dense_threshold=args.dense,
        raw_bytes=len(data), deflate_8192_bytes=measure(data, 8192),
        exact_alternating_screen_replay=True, mean_cells=float(changed.sum((1, 2)).mean()),
        mean_dense_bands=float(whole.sum(1).mean()),
        mean_partial_cells=float((changed & ~whole[:, :, None]).sum((1, 2)).mean()),
        maximum_cells=int(changed.sum((1, 2)).max()),
        full_frame_delivery_measured=False, player_changed=False, integrated_player_delta_tstates=0)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
