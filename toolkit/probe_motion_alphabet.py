"""Exact correction alphabets conditioned on each predicted 2-bit level.

FPR1: magic, 16 decoder-table bytes (prediction*4+code), then an FMO1 stream.
Code zero always reproduces the predicted value; masks therefore do not
change. Attribute corrections remain XOR. This transforms an existing movie
exactly, without another motion search or another image quantization.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_bounded_dictionary import COVERAGE
import probe_fine_motion as motion
import probe_motion_residual_order as ordering
from probe_lossless_layouts import measure, sha

INPUT_STATES_SHA = 'cab64f41c1046d8b9a59c4adbe009029ee6b37d52d22ccd9877644fd376dffa2'
INPUT_FMR_SHA = '504114fff444c5a0fda51e5ccfeb0443384e5e6b3495f86d68af7f493efeaca5'


def counts_for(states, residual):
    predicted = states[:, :3072] ^ residual[:, :3072]
    counts = np.zeros((4, 4), dtype=np.int64)
    for shift in (6, 4, 2, 0):
        labels = (((predicted >> shift) & 3) << 2) | ((states[:, :3072] >> shift) & 3)
        counts += np.bincount(labels.ravel(), minlength=16).reshape(4, 4)
    return counts


def alphabets(counts):
    yield 'xor', np.array([[p ^ c for c in range(4)] for p in range(4)], dtype=np.uint8)
    yield 'frequency', np.array([[p] + sorted([q for q in range(4) if q != p],
        key=lambda q: (-counts[p, q], q)) for p in range(4)], dtype=np.uint8)
    yield 'nearest', np.array([[p] + sorted([q for q in range(4) if q != p],
        key=lambda q: (abs(int(COVERAGE[p]) - int(COVERAGE[q])), q)) for p in range(4)], dtype=np.uint8)
    yield 'cyclic', np.array([[(p + c) & 3 for c in range(4)] for p in range(4)], dtype=np.uint8)


def remap(states, residual, symbols):
    inverse = np.argsort(symbols, axis=1).astype(np.uint8)
    predicted = states[:, :3072] ^ residual[:, :3072]
    converted = residual.copy()
    converted[:, :3072] = 0
    for shift in (6, 4, 2, 0):
        converted[:, :3072] |= inverse[(predicted >> shift) & 3, (states[:, :3072] >> shift) & 3] << shift
    if not np.array_equal(converted != 0, residual != 0):
        raise AssertionError('change masks differ')
    return converted


def decode(data):
    if data[:4] != b'FPR1' or len(data) < 20:
        raise ValueError('not FPR1')
    table = [list(data[4 + p * 4:8 + p * 4]) for p in range(4)]
    return motion.decode(ordering.decode(data[20:]), symbols=table)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion-cache', type=Path, required=True,
                        help='NPZ containing states, vectors and residual from bounded motion p2/b128/a1/e24')
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[key] for key in ('states', 'vectors', 'residual'))
    offsets = [(0, 0)] + [(x, y) for y in range(-4, 5) for x in range(-4, 5) if x or y]
    baseline = motion.encode(vectors, residual, 8, offsets, 8)
    if states.shape != (4971, 3840) or sha(states.tobytes()) != INPUT_STATES_SHA or sha(baseline) != INPUT_FMR_SHA:
        raise ValueError('unexpected checked movie/cache')
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts = counts_for(states, residual)
    report = dict(scope=__doc__, baseline_commit='8dd09de', frames=len(states),
                  input_states_sha256=INPUT_STATES_SHA, input_fmr1_sha256=INPUT_FMR_SHA,
                  predicted_to_actual_counts=counts.tolist(), no_additional_pixel_changes=True,
                  player_changed=False, hot_path_delta_tstates=0, complete=False, rows=[])
    for name, symbols in alphabets(counts):
        converted = remap(states, residual, symbols)
        data = b'FPR1' + symbols.tobytes() + ordering.encode(motion.encode(vectors, converted, 8, offsets, 8), 8)
        if not np.array_equal(decode(data), states):
            raise AssertionError('alphabet decoder changed movie')
        (args.cache / (name + '.raw')).write_bytes(data)
        row = dict(name=name, symbols=symbols.tolist(), raw_bytes=len(data), stream_sha256=sha(data),
                   exact_round_trip=True, mask_unchanged=True,
                   deflate={str(n): measure(data, n) for n in (8192, len(data))})
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
