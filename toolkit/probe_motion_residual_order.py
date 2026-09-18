"""Reorder exact FMR1 residual fields into spatial tiles before ZX0.

FMO1 stores a one-byte tile size, then the original FMR1 header and groups.
Only each frame's mask/values are reordered; vectors and prediction are
unchanged. Restoring the entire serialized FMR1 input byte-for-byte checks
the transform independently of any image-quality assumptions.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_motion_layout import tiles
from probe_lossless_layouts import measure, sha


def field_order(size):
    return tiles(np.arange(3840, dtype=np.int32)[None], size).ravel()


def rearrange(data, order):
    if data[:4] != b'FMR1' or len(data) < 10:
        raise ValueError('not FMR1')
    tile, offsets, total = struct.unpack_from('<BBI', data, 4)
    if tile not in (4, 8, 16) or not 1 <= offsets <= 254:
        raise ValueError('invalid FMR1 header')
    position = 10 + 2 * offsets
    output = bytearray(data[:position])
    frames = 0
    while frames < total:
        if position + 2 > len(data):
            raise ValueError('truncated group header')
        count = int.from_bytes(data[position:position + 2], 'little')
        if not 1 <= count <= total - frames:
            raise ValueError('invalid group size')
        end = position + 2 + count * (12288 // tile**2)
        output += data[position:end]
        mask_end = end + count * 480
        if mask_end > len(data):
            raise ValueError('truncated masks')
        masks = np.unpackbits(np.frombuffer(data[end:mask_end], dtype=np.uint8)).reshape(count, 3840).astype(bool)
        value_end = mask_end + int(masks.sum())
        if value_end > len(data):
            raise ValueError('truncated values')
        residual = np.zeros((count, 3840), dtype=np.uint8)
        residual[masks] = np.frombuffer(data[mask_end:value_end], dtype=np.uint8)
        changed = residual[:, order]
        output += np.packbits(changed != 0, axis=1).tobytes()
        output += changed[changed != 0].tobytes()
        frames += count
        position = value_end
    if position != len(data):
        raise ValueError('trailing data')
    return bytes(output)


def encode(data, size):
    return b'FMO1' + bytes([size]) + rearrange(data, field_order(size))


def decode(data):
    if data[:4] != b'FMO1' or len(data) < 5 or data[4] not in (4, 8, 16):
        raise ValueError('not supported FMO1')
    return rearrange(data[5:], np.argsort(field_order(data[4])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.raw.read_bytes()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, input_file=args.raw.name, input_sha256=sha(data),
                  frame_count=struct.unpack_from('<I', data, 6)[0], player_changed=False,
                  hot_path_delta_tstates=0, complete=False, rows=[])
    for size in (4, 8, 16):
        transformed = encode(data, size)
        if decode(transformed) != data:
            raise AssertionError('serialized FMR1 changed after inverse transform')
        name = f'{args.raw.stem}_order{size}'
        (args.cache / (name + '.raw')).write_bytes(transformed)
        row = dict(name=name, residual_tile=size, raw_bytes=len(transformed),
                   stream_sha256=sha(transformed), exact_serialized_round_trip=True,
                   deflate={str(n): measure(transformed, n) for n in (8192, len(transformed))})
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
