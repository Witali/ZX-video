"""Exact half-logical-pixel prediction using four-level blending tables.

HMR1 header: magic, rounding u8 (0 lower/1 upper on ties), tile u8 (8),
offset count u8, total frames u32, signed (hx,hy) pairs in half-pixel units.
Group: frame count u16, 192 vector indices per frame, 480 mask bytes per
frame, then nonzero XOR bytes. Residual fields use 8x8 logical tile order:
16 packed bitmap bytes then 4 attribute bytes. Index == offset count means
zero bitmap; attributes always predict the same position in frame n-1.

Interpolation averages coverage [0,1,2,4], rounding horizontal first, then
vertical. Out-of-screen samples are zero BEFORE interpolation. All residual
corrections are retained. This storage prototype does not establish Z80 speed.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_exact_dictionary import STATES_SHA256
from probe_lossless_layouts import measure, sha
import probe_fine_motion as motion
from probe_motion_residual_order import field_order

COVERAGE = np.array([0, 1, 2, 4], dtype=np.int16)
ORDER = field_order(8)


def blend_table(upper=False):
    sums = COVERAGE[:, None] + COVERAGE[None, :]
    error = np.abs(2 * COVERAGE[None, None, :] - sums[:, :, None])
    return (3 - error[:, :, ::-1].argmin(axis=2) if upper else error.argmin(axis=2)).astype(np.uint8)


def offsets_for(half):
    integer = [(0, 0)] + [(x, y) for y in range(-8, 9, 2) for x in range(-8, 9, 2) if x or y]
    fractional = [(x, y) for y in range(-6, 7) for x in range(-6, 7) if (x & 1) or (y & 1)]
    return integer + fractional if half else integer


def shifted_candidates(previous, offsets, table):
    pixels = ((previous[:, None] >> np.array([6, 4, 2, 0])) & 3).reshape(96, 128)
    padding = 6
    padded = np.pad(pixels, padding)
    horizontal = table[padded[:, :-1], padded[:, 1:]]
    vertical = table[padded[:-1], padded[1:]]
    both = table[horizontal[:-1], horizontal[1:]]
    phases = [padded, horizontal, vertical, both]
    shifted = np.zeros((len(offsets) + 1, 96, 128), dtype=np.uint8)
    for index, (hx, hy) in enumerate(offsets):
        phase = (hx & 1) + 2 * (hy & 1)
        x, y = padding + (-hx // 2), padding + (-hy // 2)
        shifted[index] = phases[phase][y:y + 96, x:x + 128]
    packed = ((shifted[:, :, 0::4] << 6) | (shifted[:, :, 1::4] << 4)
              | (shifted[:, :, 2::4] << 2) | shifted[:, :, 3::4])
    return packed.reshape(len(shifted), 3072)


def predict(states, offsets, upper=False):
    table = blend_table(upper)
    target = motion.tile_bytes(states[:, :3072], 8)
    vectors = np.empty((len(states), 192), dtype=np.uint8)
    residual = np.empty_like(states)
    previous = np.zeros(3840, dtype=np.uint8)
    for frame, current in enumerate(states):
        candidates = motion.tile_bytes(shifted_candidates(previous[:3072], offsets, table), 8)
        delta = candidates ^ target[frame]
        cost = 8 * np.count_nonzero(delta, axis=2) + motion.POPCOUNT[delta].sum(axis=2)
        cost[1:] += 8
        chosen = cost.argmin(axis=0)
        vectors[frame] = chosen
        residual[frame, :3072] = motion.raster_bytes(delta[chosen, np.arange(192)][None], 8)[0]
        residual[frame, 3072:] = current[3072:] ^ previous[3072:]
        previous = current
        if frame % 500 == 0:
            print(f'Half-pixel search ({len(offsets)} offsets, upper={upper}): {frame}/{len(states)}', flush=True)
    return vectors, residual


def encode(vectors, residual, offsets, upper=False, group_frames=8):
    output = bytearray(b'HMR1' + struct.pack('<BBBI', int(upper), 8, len(offsets), len(residual)))
    for hx, hy in offsets:
        output += struct.pack('<bb', hx, hy)
    for start in range(0, len(residual), group_frames):
        group = residual[start:start + group_frames, ORDER]
        output += struct.pack('<H', len(group)) + vectors[start:start + len(group)].tobytes()
        output += np.packbits(group != 0, axis=1).tobytes() + group[group != 0].tobytes()
    return bytes(output)


def decode(data):
    """Independent coordinate sampler, scalar rounding and residual addresses."""
    cursor = 0

    def read(count):
        nonlocal cursor
        if count < 0 or cursor + count > len(data):
            raise ValueError('truncated half-pixel stream')
        chunk = data[cursor:cursor + count]
        cursor += count
        return chunk

    if read(4) != b'HMR1':
        raise ValueError('unknown stream')
    upper, tile, count, total = struct.unpack('<BBBI', read(7))
    if upper not in (0, 1) or tile != 8 or not 1 <= count <= 254 or total > len(data) // 480:
        raise ValueError('invalid half-pixel header')
    offsets = [struct.unpack('<bb', read(2)) for _ in range(count)]
    if any(abs(hx) > 8 or abs(hy) > 8 for hx, hy in offsets):
        raise ValueError('offset out of supported range')
    coverage = (0, 1, 2, 4)
    scalar_blends = [[min(range(4), key=lambda level: (abs(2 * coverage[level] - coverage[a] - coverage[b]),
                                                     -level if upper else level))
                      for b in range(4)] for a in range(4)]
    previous = bytes(3840)
    frames = []
    while len(frames) < total:
        length = int.from_bytes(read(2), 'little')
        if not 1 <= length <= total - len(frames):
            raise ValueError('invalid group length')
        vectors = read(length * 192)
        masks = read(length * 480)
        for row in range(length):
            screen = bytearray(3072) + bytearray(previous[3072:])

            def pixel(x, y):
                return ((previous[y * 32 + x // 4] >> (6 - 2 * (x & 3))) & 3
                        if 0 <= x < 128 and 0 <= y < 96 else 0)

            for block in range(192):
                index = vectors[row * 192 + block]
                if index > count:
                    raise ValueError('invalid vector')
                if index == count:
                    continue
                hx, hy = offsets[index]
                tile_y, tile_x = divmod(block, 16)
                for y in range(tile_y * 8, tile_y * 8 + 8):
                    sy = (2 * y - hy) // 2
                    for x in range(tile_x * 8, tile_x * 8 + 8):
                        sx = (2 * x - hx) // 2
                        value = pixel(sx, sy)
                        if hx & 1:
                            value = scalar_blends[value][pixel(sx + 1, sy)]
                        if hy & 1:
                            bottom = pixel(sx, sy + 1)
                            if hx & 1:
                                bottom = scalar_blends[bottom][pixel(sx + 1, sy + 1)]
                            value = scalar_blends[value][bottom]
                        screen[y * 32 + x // 4] |= value << (6 - 2 * (x & 3))
            for byte, flags in enumerate(masks[row * 480:(row + 1) * 480]):
                for bit in range(8):
                    if not flags & (128 >> bit):
                        continue
                    block, within = divmod(byte * 8 + bit, 20)
                    tile_y, tile_x = divmod(block, 16)
                    if within < 16:
                        y, x = divmod(within, 2)
                        address = (tile_y * 8 + y) * 32 + tile_x * 2 + x
                    else:
                        y, x = divmod(within - 16, 2)
                        address = 3072 + (tile_y * 2 + y) * 32 + tile_x * 2 + x
                    screen[address] ^= read(1)[0]
            previous = bytes(screen)
            frames.append(previous)
    if cursor != len(data):
        raise ValueError('trailing bytes')
    return np.frombuffer(b''.join(frames), dtype=np.uint8).reshape(-1, 3840)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--expected-sha256', default=STATES_SHA256)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variants', nargs='+', choices=['integer', 'half_lower', 'half_upper'],
                        default=['integer', 'half_lower', 'half_upper'])
    parser.add_argument('--group-frames', type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.group_frames <= 65535:
        parser.error('invalid group size')
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    if states.shape != (4971, 3840) or sha(states.tobytes()) != args.expected_sha256:
        raise ValueError('unexpected full-movie states')
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='8dd09de', frames=len(states),
                  input_states_sha256=args.expected_sha256, accepted_reference_sha256=STATES_SHA256,
                  exact_to_accepted_reference=args.expected_sha256 == STATES_SHA256,
                  group_frames=args.group_frames, vector_mask_ram_bytes=672 * args.group_frames,
                  resolution=[256, 192], logical_resolution=[128, 96], fps='25/3',
                  audio='unchanged, excluded from size', player_changed=False, hot_path_delta_tstates=0,
                  complete=False, rows=[])
    for variant in args.variants:
        offsets = offsets_for(variant != 'integer')
        upper = variant == 'half_upper'
        vectors, residual = predict(states, offsets, upper)
        data = encode(vectors, residual, offsets, upper, args.group_frames)
        name = f'{variant}_g{args.group_frames}_{args.expected_sha256[:8]}'
        (args.cache / (name + '.raw')).write_bytes(data)
        np.savez_compressed(args.cache / (name + '.npz'), vectors=vectors, residual=residual)
        if not np.array_equal(decode(data), states):
            raise AssertionError('independent half-pixel decoder changed input states')
        fractional = np.array([(x & 1) or (y & 1) for x, y in offsets] + [False])
        row = dict(name=name, variant=variant, offsets=offsets, blend_table=blend_table(upper).tolist(),
                   raw_bytes=len(data), stream_sha256=sha(data), exact_round_trip=True,
                   nonzero_bitmap_bytes=int(np.count_nonzero(residual[:, :3072])),
                   nonzero_attribute_bytes=int(np.count_nonzero(residual[:, 3072:])),
                   fractional_tiles=int(np.count_nonzero(fractional[vectors])),
                   total_tiles=vectors.size,
                   deflate={str(n): measure(data, n) for n in (8192, len(data))})
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in row.items() if k not in ('offsets', 'blend_table')}), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
