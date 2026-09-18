"""Exact pixel-aligned motion prediction with sparse residuals.

Search runs on the PC. FMR1 decoder only shifts/copies a selected tile and
applies XOR corrections. This offline prototype does not establish Z80 speed.
Header: magic, tile size u8, offset count u8, frames u32, signed (dx,dy) pairs.
An index equal to offset count selects zero instead of the preceding frame.
Group: frame count u16, raster tile indices for each frame, 480 mask bytes per
frame, then nonzero residual bytes in frame/raster order. Attributes predict
the same position of the preceding frame, regardless of the bitmap vector.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_exact_dictionary import STATES_SHA256
from probe_lossless_layouts import measure, sha

POPCOUNT = np.array([x.bit_count() for x in range(256)], dtype=np.uint8)


def tile_bytes(bitmap, size):
    return bitmap.reshape(-1, 96 // size, size, 128 // size, size // 4).transpose(0, 1, 3, 2, 4).reshape(-1, 12288 // size**2, size**2 // 4)


def raster_bytes(tiles, size):
    return tiles.reshape(-1, 96 // size, 128 // size, size, size // 4).transpose(0, 1, 3, 2, 4).reshape(-1, 3072)


def shifted_candidates(previous, offsets):
    pixels = ((previous[:, None] >> np.array([6, 4, 2, 0])) & 3).reshape(96, 128)
    shifted = np.zeros((len(offsets) + 1, 96, 128), dtype=np.uint8)
    for index, (dx, dy) in enumerate(offsets):
        shifted[index, max(0, dy):min(96, 96 + dy), max(0, dx):min(128, 128 + dx)] = pixels[
            max(0, -dy):min(96, 96 - dy), max(0, -dx):min(128, 128 - dx)]
    packed = (shifted[:, :, 0::4] << 6) | (shifted[:, :, 1::4] << 4) | (shifted[:, :, 2::4] << 2) | shifted[:, :, 3::4]
    return packed.reshape(len(shifted), 3072)


def predict(states, size, offsets, vector_penalty):
    target = tile_bytes(states[:, :3072], size)
    vectors = np.empty(target.shape[:2], dtype=np.uint8)
    residual = np.empty_like(states)
    previous = np.zeros(3840, dtype=np.uint8)
    for frame, current in enumerate(states):
        candidates = tile_bytes(shifted_candidates(previous[:3072], offsets), size)
        delta = candidates ^ target[frame]
        # Values and masks both have a cost. Prefer the default on ties.
        cost = 8 * np.count_nonzero(delta, axis=2) + POPCOUNT[delta].sum(axis=2)
        cost[1:] += vector_penalty
        chosen = cost.argmin(axis=0)
        vectors[frame] = chosen
        residual[frame, :3072] = raster_bytes(delta[chosen, np.arange(len(chosen))][None], size)[0]
        residual[frame, 3072:] = current[3072:] ^ previous[3072:]
        previous = current
        if frame % 500 == 0:
            print(f'Motion tile {size}: {frame}/{len(states)}', flush=True)
    return vectors, residual


def encode(vectors, residual, size, offsets, group_frames):
    output = bytearray(b'FMR1' + struct.pack('<BBI', size, len(offsets), len(residual)))
    for dx, dy in offsets:
        output += struct.pack('<bb', dx, dy)
    for start in range(0, len(residual), group_frames):
        group = residual[start:start + group_frames]
        output += struct.pack('<H', len(group))
        output += vectors[start:start + len(group)].tobytes()
        output += np.packbits(group != 0, axis=1).tobytes()
        output += group[group != 0].tobytes()
    return bytes(output)


def decode(data, symbols=None):
    # Optional per-predicted-level correction alphabet; default remains XOR.
    if symbols is not None:
        if len(symbols) != 4 or any(len(row) != 4 or sorted(row) != list(range(4)) or row[0] != p
                                     for p, row in enumerate(symbols)):
            raise ValueError('invalid correction alphabet')
    offset = 0

    def read(count):
        nonlocal offset
        if offset + count > len(data):
            raise ValueError('truncated motion stream')
        chunk = data[offset:offset + count]
        offset += count
        return chunk

    if read(4) != b'FMR1':
        raise ValueError('unknown stream')
    size, count, total = struct.unpack('<BBI', read(6))
    if size not in (4, 8, 16) or not 1 <= count <= 254 or total > len(data) // 480:
        raise ValueError('invalid motion header')
    offsets = [struct.unpack('<bb', read(2)) for _ in range(count)]
    tiles = 12288 // size**2
    previous = bytes(3840)
    frames = []
    while len(frames) < total:
        length = int.from_bytes(read(2), 'little')
        if not 1 <= length <= total - len(frames):
            raise ValueError('invalid group length')
        vectors = read(tiles * length)
        masks = read(480 * length)
        for row in range(length):
            # Decode packed source pixels directly; do not reuse the search,
            # candidate generation or tile reshape functions.
            screen = bytearray(3072) + bytearray(previous[3072:])
            for tile in range(tiles):
                index = vectors[row * tiles + tile]
                if index > count:
                    raise ValueError('invalid vector')
                if index == count:
                    continue
                dx, dy = offsets[index]
                tile_y, tile_x = divmod(tile, 128 // size)
                for y in range(tile_y * size, (tile_y + 1) * size):
                    source_y = y - dy
                    if not 0 <= source_y < 96:
                        continue
                    for x in range(tile_x * size, (tile_x + 1) * size):
                        source_x = x - dx
                        if 0 <= source_x < 128:
                            value = (previous[source_y * 32 + source_x // 4] >> (6 - 2 * (source_x & 3))) & 3
                            screen[y * 32 + x // 4] |= value << (6 - 2 * (x & 3))
            for byte, flags in enumerate(masks[row * 480:(row + 1) * 480]):
                for bit in range(8):
                    if flags & (128 >> bit):
                        address = byte * 8 + bit
                        value = read(1)[0]
                        if symbols is None or address >= 3072:
                            screen[address] ^= value
                        else:
                            previous_value = screen[address]
                            screen[address] = sum(symbols[(previous_value >> shift) & 3][(value >> shift) & 3] << shift
                                                  for shift in (6, 4, 2, 0))
            previous = bytes(screen)
            frames.append(previous)
    if offset != len(data):
        raise ValueError('trailing data')
    return np.frombuffer(b''.join(frames), dtype=np.uint8).reshape(-1, 3840)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--tiles', type=int, nargs='+', choices=[4, 8, 16], default=[8, 16])
    parser.add_argument('--radius', type=int, choices=range(1, 8), default=4)
    parser.add_argument('--group-frames', type=int, default=16)
    parser.add_argument('--vector-penalty', type=int, default=8)
    parser.add_argument('--baseline-commit', default='a13c3fe',
                        help='experiment input/code baseline recorded in the report')
    args = parser.parse_args()
    if not 1 <= args.group_frames <= 65535 or args.vector_penalty < 0:
        parser.error('invalid group/penalty')
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    if states.shape != (4971, 3840) or sha(states.tobytes()) != STATES_SHA256:
        raise ValueError('unexpected reference')
    offsets = [(0, 0)] + [(x, y) for y in range(-args.radius, args.radius + 1)
                         for x in range(-args.radius, args.radius + 1) if x or y]
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit=args.baseline_commit, frames=len(states),
                  states_sha256=STATES_SHA256, radius=args.radius, offsets=offsets,
                  vector_penalty=args.vector_penalty, group_frames=args.group_frames,
                  resolution=[256, 192], logical_resolution=[128, 96], fps='25/3',
                  audio='unchanged, excluded from sizes', player_changed=False,
                  hot_path_delta_tstates=0, complete=False, rows=[])
    for size in args.tiles:
        vectors, residual = predict(states, size, offsets, args.vector_penalty)
        data = encode(vectors, residual, size, offsets, args.group_frames)
        name = f'fine_motion_t{size}_r{args.radius}_p{args.vector_penalty}_g{args.group_frames}'
        (args.cache / (name + '.raw')).write_bytes(data)
        if not np.array_equal(decode(data), states):
            raise AssertionError('motion does not round trip')
        row = dict(name=name, tile=size, raw_bytes=len(data), stream_sha256=sha(data),
                   nonzero_bitmap_bytes=int(np.count_nonzero(residual[:, :3072])),
                   nonzero_attribute_bytes=int(np.count_nonzero(residual[:, 3072:])),
                   motion_tiles=int(np.count_nonzero((vectors > 0) & (vectors < len(offsets)))),
                   zero_tiles=int(np.count_nonzero(vectors == len(offsets))), total_tiles=vectors.size,
                   vector_mask_ram_bytes=args.group_frames * (vectors.shape[1] + 480),
                   exact_round_trip=True,
                   deflate={str(n): measure(data, n) for n in (8192, len(data))})
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
