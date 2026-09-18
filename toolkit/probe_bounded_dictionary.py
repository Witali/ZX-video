"""Screen full-movie bitmap codebooks with explicitly bounded pixel changes.

Offline experiment, not a playable Z80 format. Attributes are exact; there is
no resampling, frame dropping or temporal hold. The dictionary is searched
on the PC. A cell may change <=--max-changed-pixels (default 2) logical pixels
by <=1 quarter coverage;
its 2x2-average RGB RMSE must also fit --limits. Zero is a lossless control.

Groups contain <frames:u16, dictionary_entries:u16>, then 4 bytes/entry.
Each frame has 768 cells in raster order: top two token bits mean skip n-2,
dictionary, literal, or invalid; bottom six encode count-1. Dictionary indices
use one byte for <=256 entries; larger tables use 0..254 or FF plus u16.
Then a 96-byte attribute change mask and changed attributes follow (n-2).
Both prediction banks reset at each group. Outer DEFLATE only screens layouts.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np

import build_long_video_trd as video
from build_zxv_trd import SCREEN_PALETTE
from probe_exact_dictionary import STATES_SHA256
from probe_lossless_layouts import measure

COVERAGE = np.array([0, 1, 2, 4], dtype=np.int16)
TOP = np.frombuffer(video.PLAYER_DITHER_TOP, dtype=np.uint8)
BOTTOM = np.frombuffer(video.PLAYER_DITHER_BOTTOM, dtype=np.uint8)
POPCOUNT = np.array([i.bit_count() for i in range(256)], dtype=np.uint8)


def bitmap_cells(states):
    return states[:, :3072].reshape(-1, 24, 4, 32).transpose(0, 1, 3, 2).reshape(-1, 768, 4).copy()


def compact_states(cells, attrs):
    pixels = cells.reshape(-1, 24, 32, 4).transpose(0, 1, 3, 2).reshape(-1, 3072)
    return np.concatenate((pixels, attrs), axis=1)


def features(patterns):
    return COVERAGE[((patterns[..., None] >> np.array([6, 4, 2, 0])) & 3).reshape(-1, 16)]


def closest_patterns(patterns, table):
    samples = features(patterns).astype(np.float32)
    centres = features(table).astype(np.float32)
    norms = (centres * centres).sum(axis=1)
    result = np.empty(len(samples), dtype=np.int32)
    for first in range(0, len(samples), 512):
        chunk = samples[first:first + 512]
        distances = (chunk * chunk).sum(axis=1)[:, None] + norms[None, :] - 2 * chunk @ centres.T
        result[first:first + len(chunk)] = distances.argmin(axis=1)
    return result


def contrast_squared(attrs):
    bright = (attrs >> 3) & 8
    ink = SCREEN_PALETTE[(attrs & 7) | bright].astype(np.float64)
    paper = SCREEN_PALETTE[((attrs >> 3) & 7) | bright].astype(np.float64)
    return ((ink - paper) ** 2).mean(axis=-1)


def accept_pattern(original, candidate, attrs, rmse_limit, maximum_changed=2):
    delta = features(original.reshape(-1, 4)) - features(candidate.reshape(-1, 4))
    changed = np.count_nonzero(delta, axis=1).reshape(attrs.shape)
    max_delta = np.abs(delta).max(axis=1).reshape(attrs.shape)
    squared = (delta * delta).sum(axis=1).reshape(attrs.shape)
    mse = squared * contrast_squared(attrs) / 256
    if rmse_limit == 0:
        return changed == 0
    return (changed <= maximum_changed) & (max_delta <= 1) & (mse <= rmse_limit ** 2)


def encode_group(cells, attrs, table):
    count = len(cells)
    output = bytearray(struct.pack('<HH', count, len(table)) + table.tobytes())
    lookup = {bytes(pattern): i for i, pattern in enumerate(table)}
    previous = [[bytes(4)] * 768 for _ in range(2)]
    previous_attrs = np.zeros((2, 768), dtype=np.uint8)
    for frame in range(count):
        current = [bytes(pattern) for pattern in cells[frame]]
        bank = frame & 1
        kinds = [0 if value == old else 1 if value in lookup else 2
                 for value, old in zip(current, previous[bank])]
        cursor = 0
        while cursor < 768:
            kind = kinds[cursor]
            end = cursor + 1
            while end < min(768, cursor + 64) and kinds[end] == kind:
                end += 1
            output.append((kind << 6) | (end - cursor - 1))
            if kind == 1:
                for value in current[cursor:end]:
                    index = lookup[value]
                    if len(table) <= 256 or index < 255:
                        output.append(index)
                    else:
                        output += b'\xff' + struct.pack('<H', index)
            elif kind == 2:
                output += b''.join(current[cursor:end])
            cursor = end
        mask = attrs[frame] != previous_attrs[bank]
        output += np.packbits(mask).tobytes() + attrs[frame, mask].tobytes()
        previous[bank] = current
        previous_attrs[bank] = attrs[frame]
    return bytes(output)


def decode(data):
    """Parse the serialized stream independently of quantizer/encoder choices."""
    offset = 0
    frames = []

    def read(count):
        nonlocal offset
        if offset + count > len(data):
            raise ValueError('truncated bounded dictionary stream')
        value = data[offset:offset + count]
        offset += count
        return value

    while offset < len(data):
        frame_count, table_count = struct.unpack('<HH', read(4))
        if frame_count == 0 or table_count == 0:
            raise ValueError('empty group/table')
        table = [read(4) for _ in range(table_count)]
        screens = [bytearray(3072), bytearray(3072)]
        attributes = [bytearray(768), bytearray(768)]
        for frame in range(frame_count):
            screen = screens[frame & 1]
            attrs = attributes[frame & 1]
            position = 0
            while position < 768:
                token = read(1)[0]
                kind, length = token >> 6, (token & 63) + 1
                if kind == 3 or position + length > 768:
                    raise ValueError('invalid bitmap run')
                for cell in range(position, position + length):
                    if kind == 0:
                        continue
                    if kind == 1:
                        index = read(1)[0]
                        if table_count > 256 and index == 255:
                            index = int.from_bytes(read(2), 'little')
                        if index >= table_count:
                            raise ValueError('invalid bitmap index')
                        pattern = table[index]
                    else:
                        pattern = read(4)
                    y, x = divmod(cell, 32)
                    for row in range(4):
                        screen[y * 128 + row * 32 + x] = pattern[row]
                position += length
            mask = read(96)
            for cell in range(768):
                if mask[cell // 8] & (128 >> (cell & 7)):
                    attrs[cell] = read(1)[0]
            frames.append(bytes(screen + attrs))
    return np.frombuffer(b''.join(frames), dtype=np.uint8).reshape(-1, 3840)


def quality(original, filtered):
    if not np.array_equal(original[:, 3072:], filtered[:, 3072:]):
        raise AssertionError('attributes changed')
    # Exclude the 24-pixel top/bottom letterbox: cells 3..20, 576 per frame.
    first, last = 3 * 32, 21 * 32
    old = bitmap_cells(original)[:, first:last]
    new = bitmap_cells(filtered)[:, first:last]
    contrast = contrast_squared(original[:, 3072 + first:3072 + last])
    delta = features(old.reshape(-1, 4)) - features(new.reshape(-1, 4))
    logical_mse = (delta * delta).sum(axis=1).reshape(contrast.shape) * contrast / 256
    bit_changes = (POPCOUNT[TOP[old] ^ TOP[new]] + POPCOUNT[BOTTOM[old] ^ BOTTOM[new]]).sum(axis=2)
    # Pattern changes between identical ink/paper have no displayed effect.
    native_mse = bit_changes * contrast / 64
    frame_logical = logical_mse.mean(axis=1)
    frame_native = native_mse.mean(axis=1)

    def psnr(mse):
        return None if mse == 0 else float(10 * math.log10(255 ** 2 / mse))

    changes = np.count_nonzero(delta, axis=1)
    return dict(reference='accepted Spectrum release, active 256x144 area; no original-source quality claim',
                attributes_exact=True, frames=len(original),
                altered_cells=int(np.count_nonzero(changes)),
                max_changed_logical_pixels_per_cell=int(changes.max()),
                max_quarter_coverage_delta=int(np.abs(delta).max()),
                average_rgb_psnr_db=psnr(float(frame_logical.mean())),
                worst_frame_average_rgb_psnr_db=psnr(float(frame_logical.max())),
                native_rgb_psnr_db=psnr(float(frame_native.mean())),
                worst_frame_native_rgb_psnr_db=psnr(float(frame_native.max())),
                max_cell_average_rgb_rmse=float(np.sqrt(logical_mse.max())),
                native_changed_fraction=float(np.mean(bit_changes * (contrast > 0)) / 64),
                worst_frame_native_changed_fraction=float((bit_changes * (contrast > 0)).mean(axis=1).max() / 64),
                worst_frames=np.argsort(frame_logical)[-12:][::-1].tolist(),
                repeated_frames_added=int(np.count_nonzero(np.all(filtered[1:] == filtered[:-1], axis=1) &
                                                          ~np.all(original[1:] == original[:-1], axis=1))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--group-frames', type=int, default=512)
    parser.add_argument('--entries', type=int, nargs='+', default=[256, 1024])
    parser.add_argument('--limits', type=float, nargs='+', default=[0, 4, 8, 12])
    parser.add_argument('--max-changed-pixels', type=int, choices=range(1, 17), default=2)
    args = parser.parse_args()
    if not 1 <= args.group_frames <= 65535 or any(not 1 <= n <= 65535 for n in args.entries) or any(n < 0 for n in args.limits):
        parser.error('invalid group, dictionary size or error bound')
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    digest = hashlib.sha256(states.tobytes()).hexdigest()
    if states.shape != (4971, 3840) or digest != STATES_SHA256 or np.any(states[:, 3072:] & 128):
        raise ValueError('unexpected full-movie states')
    cells = bitmap_cells(states)
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='24a819a', states_sha256=digest,
                  resolution=[256, 192], logical_resolution=[128, 96], fps='25/3', frames=len(states),
                  audio='unchanged; omitted from storage probe', group_frames=args.group_frames,
                  max_changed_pixels_per_cell=args.max_changed_pixels,
                  complete=False, player_changed=False, hot_path_delta_tstates=0, rows=[])

    def save():
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    for entries in args.entries:
        streams = {limit: [] for limit in args.limits}
        converted = {limit: [] for limit in args.limits}
        max_entries = 0
        for start in range(0, len(states), args.group_frames):
            group = cells[start:start + args.group_frames]
            attrs = states[start:start + len(group), 3072:]
            patterns, inverse, counts = np.unique(group.reshape(-1, 4), axis=0, return_inverse=True, return_counts=True)
            order = np.argsort(-counts, kind='stable')[:entries]
            table = patterns[order]
            max_entries = max(max_entries, len(table))
            nearest = table[closest_patterns(patterns, table)][inverse].reshape(group.shape)
            for limit in args.limits:
                accepted = accept_pattern(group, nearest, attrs, limit, args.max_changed_pixels)
                selected = np.where(accepted[:, :, None], nearest, group)
                streams[limit].append(encode_group(selected, attrs, table))
                converted[limit].append(compact_states(selected, attrs))
            print(f'Dictionary {entries}: {start + len(group)}/{len(states)} frames', flush=True)
        for limit in args.limits:
            name = f'bitmap{entries}_rmse{limit:g}_group{args.group_frames}'
            if args.max_changed_pixels != 2:
                name += f'_changes{args.max_changed_pixels}'
            data = b''.join(streams[limit])
            filtered = np.concatenate(converted[limit])
            if not np.array_equal(decode(data), filtered):
                raise AssertionError('encoded frames do not round trip')
            if limit == 0 and not np.array_equal(filtered, states):
                raise AssertionError('lossless control changed states')
            (args.cache / (name + '.raw')).write_bytes(data)
            np.savez_compressed(args.cache / (name + '.npz'), states=filtered)
            row = dict(name=name, entries=entries, rmse_limit=limit, raw_bytes=len(data),
                       stream_sha256=hashlib.sha256(data).hexdigest(),
                       filtered_sha256=hashlib.sha256(filtered.tobytes()).hexdigest(),
                       compact_dictionary_ram_bytes=4 * max_entries,
                       expanded_dictionary_ram_bytes=8 * max_entries,
                       decoded_frames_exact_to_filtered=True, quality=quality(states, filtered),
                       deflate={str(size): measure(data, size) for size in (6144, len(data))})
            report['rows'].append(row)
            save()
            print(json.dumps(row), flush=True)
    report['complete'] = True
    save()


if __name__ == '__main__':
    main()
