"""Lossless tile motion experiment; storage evidence, not a Z80 player.

Vectors predict both packed pixels and attributes from the preceding frame.
Every residual byte is retained and the full sequence is decoded to verify it.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_lossless_layouts import deflate, measure, sha


def tiles(states, size):
    n = len(states)
    bitmap = states[:, :3072].reshape(n, 96 // size, size, 128 // size, size // 4)
    bitmap = bitmap.transpose(0, 1, 3, 2, 4).reshape(n, -1, size * size // 4)
    attrs = states[:, 3072:].reshape(n, 96 // size, size // 4, 128 // size, size // 4)
    attrs = attrs.transpose(0, 1, 3, 2, 4).reshape(n, -1, size * size // 16)
    return np.concatenate([bitmap, attrs], axis=2)


def untile(array, size):
    n = len(array)
    bitmap = array[:, :, :size * size // 4].reshape(n, 96 // size, 128 // size, size, size // 4)
    attrs = array[:, :, size * size // 4:].reshape(n, 96 // size, 128 // size, size // 4, size // 4)
    return np.concatenate([bitmap.transpose(0, 1, 3, 2, 4).reshape(n, 3072),
                           attrs.transpose(0, 1, 3, 2, 4).reshape(n, 768)], axis=1)


def shift(state, dx, dy):
    out = np.zeros_like(state)
    for begin, end, height, divisor in ((0, 3072, 96, 1), (3072, 3840, 24, 4)):
        source = state[begin:end].reshape(height, 32)
        dest = out[begin:end].reshape(height, 32)
        x, y = dx // 4, dy // divisor
        dest[max(0, y):min(height, height + y), max(0, x):min(32, 32 + x)] = source[max(0, -y):min(height, height - y), max(0, -x):min(32, 32 - x)]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--tile', type=int, choices=(4, 8, 16), default=8)
    p.add_argument('--radius', type=int, choices=(4, 8, 12), default=8)
    args = p.parse_args()
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    assert sha(states.tobytes()) == '9cc006a31408e2c3c3f96f96901b003756c2a480497e12d6b124baedafaeb35d'
    target = tiles(states, args.tile)
    assert np.array_equal(untile(target, args.tile), states)
    offsets = [(0, 0)] + [(x, y) for y in range(-args.radius, args.radius + 1, 4) for x in range(-args.radius, args.radius + 1, 4) if x or y]
    bitcount = np.array([i.bit_count() for i in range(256)], dtype=np.uint8)
    residuals = np.empty_like(target)
    vectors = np.zeros(target.shape[:2], dtype=np.uint8)
    previous = np.zeros(3840, dtype=np.uint8)
    for index, state in enumerate(states):
        candidates = tiles(np.array([shift(previous, dx, dy) for dx, dy in offsets]), args.tile)
        delta = candidates ^ target[index]
        # A non-default predictor needs a vector: require at least 8 bits saved.
        cost = bitcount[delta].sum(axis=2, dtype=np.int16)
        cost[1:] += 8
        vector = cost.argmin(axis=0)
        vectors[index] = vector
        residuals[index] = delta[vector, np.arange(len(vector))]
        decoded = untile((candidates[vector, np.arange(len(vector))] ^ residuals[index])[None], args.tile)[0]
        assert np.array_equal(decoded, state)
        previous = decoded
        if index % 500 == 0:
            print(f'Verified {index}/{len(states)} motion frames', flush=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    streams = {
        'tile_interleaved': np.concatenate([vectors[:, :, None], residuals], axis=2).tobytes(),
        'separate_vectors': vectors.tobytes() + residuals.tobytes(),
        'frame_separate_vectors': b''.join(v.tobytes() + r.tobytes() for v, r in zip(vectors, residuals)),
    }
    report = dict(scope=__doc__, tile=args.tile, offsets=offsets, frames=len(states),
                  states_sha256=sha(states.tobytes()), exact_round_trip=True,
                  motion_tiles=int(np.count_nonzero(vectors)), total_tiles=vectors.size, layouts=[])
    for name, data in streams.items():
        path = args.cache / (name + '.raw')
        path.write_bytes(data)
        row = dict(name=name, sha256=sha(data), raw_bytes=len(data),
                   deflate={str(size): measure(data, size) for size in (8192, 32768, len(data))})
        report['layouts'].append(row)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
