"""Inspect FMR1 nonzero values before choosing a cheap entropy precode.

Entropy is the zero-order empirical entropy of value bytes only, not a lower
bound for the movie and not a prediction of ZX0 output. Nibble savings are a
raw estimate: 15 direct values cost 4 bits, escape plus a literal costs 12.
Dictionary/header/alignment costs and interactions with ZX0 are excluded.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct

from probe_lossless_layouts import sha


def analyze(data):
    if data[:4] != b'FMR1' or len(data) < 10:
        raise ValueError('not FMR1')
    size, offsets, frames = struct.unpack_from('<BBI', data, 4)
    if size not in (4, 8, 16) or not 1 <= offsets <= 254:
        raise ValueError('invalid header')
    cursor = 10 + 2 * offsets
    frame = 0
    histogram = Counter()
    while frame < frames:
        if cursor + 2 > len(data):
            raise ValueError('truncated group header')
        count = struct.unpack_from('<H', data, cursor)[0]
        if not 1 <= count <= frames - frame:
            raise ValueError('invalid group length')
        cursor += 2 + count * (12288 // size**2)
        mask = data[cursor:cursor + 480 * count]
        if len(mask) != 480 * count:
            raise ValueError('truncated masks')
        cursor += len(mask)
        length = sum(value.bit_count() for value in mask)
        values = data[cursor:cursor + length]
        if len(values) != length:
            raise ValueError('truncated values')
        histogram.update(values)
        cursor += length
        frame += count
    if cursor != len(data):
        raise ValueError('trailing bytes')
    total = sum(histogram.values())
    direct = sum(count for _, count in histogram.most_common(15))
    entropy = -sum((count / total) * math.log2(count / total) for count in histogram.values()) if total else 0
    return dict(scope=__doc__, stream_sha256=sha(data), frames=frames,
                nonzero_value_bytes=total, zero_order_entropy_bits=entropy,
                top15_fraction=direct / total if total else 0,
                raw_nibble_saving_estimate_bytes=(direct - (total - direct)) / 2,
                top15=histogram.most_common(15), histogram=[histogram[x] for x in range(256)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.raw.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'histogram'}))


if __name__ == '__main__':
    main()
