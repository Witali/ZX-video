"""Bounded temporal prediction plus streamable groups of masks/values.

Offline size experiment, not a Z80 player. Each approximation is checked
against the current reference frame, never against an already filtered target.
Attributes remain byte exact. Consecutive inexact holds are optionally capped.
TRS1 format: magic, prediction distance u8, total frames u32 little-endian;
then groups: count u16, count*480 mask bytes, followed by each frame's nonzero
XOR bytes. Masks are MSB-first over 3840 compact bytes. History is zero before
the movie and continuous across groups. Grouping bounds mask storage in RAM.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_bounded_dictionary import accept_pattern, bitmap_cells, compact_states, quality
from probe_exact_dictionary import STATES_SHA256
from probe_lossless_layouts import measure, sha


def temporal_filter(states, maximum_changed, rmse_limit, max_hold):
    cells = bitmap_cells(states)
    attrs = states[:, 3072:]
    filtered = np.empty_like(cells)
    old = np.zeros((768, 4), dtype=np.uint8)
    holds = np.zeros(768, dtype=np.int32)
    peak = 0
    inexact_holds = 0
    for frame, current in enumerate(cells):
        different = np.any(old != current, axis=1)
        allowed = accept_pattern(current, old, attrs[frame], rmse_limit, maximum_changed)
        if max_hold:
            allowed &= holds < max_hold
        # Exact matches do not count as holding an incorrect image.
        holding = allowed & different
        filtered[frame] = np.where(holding[:, None], old, current)
        holds = np.where(holding, holds + 1, 0)
        peak = max(peak, int(holds.max()))
        inexact_holds += int(holding.sum())
        old = filtered[frame]
    return compact_states(filtered, attrs), dict(
        inexact_cell_holds=inexact_holds, maximum_consecutive_inexact_holds=peak,
        configured_max_hold=max_hold or None, maximum_changed_pixels=maximum_changed,
        rmse_limit=rmse_limit, reference_error_checked_each_frame=True)


def encode(states, distance, group_frames):
    if distance not in (1, 2) or not 1 <= group_frames <= 65535:
        raise ValueError('invalid prediction/group')
    delta = states.copy()
    delta[distance:] ^= states[:-distance]
    output = bytearray(b'TRS1' + struct.pack('<BI', distance, len(states)))
    for start in range(0, len(states), group_frames):
        group = delta[start:start + group_frames]
        output += struct.pack('<H', len(group))
        output += np.packbits(group != 0, axis=1).tobytes()
        output += group[group != 0].tobytes()
    return bytes(output)


def decode(data):
    offset = 0

    def read(count):
        nonlocal offset
        if count < 0 or offset + count > len(data):
            raise ValueError('truncated temporal residual stream')
        value = data[offset:offset + count]
        offset += count
        return value

    if read(4) != b'TRS1':
        raise ValueError('unknown stream')
    distance, total = struct.unpack('<BI', read(5))
    if distance not in (1, 2) or total > len(data) // 480:
        raise ValueError('invalid header')
    result = np.zeros((total, 3840), dtype=np.uint8)
    frame = 0
    while frame < total:
        count = int.from_bytes(read(2), 'little')
        if not 1 <= count <= total - frame:
            raise ValueError('invalid group count')
        masks = read(count * 480)
        for row in range(count):
            # Deliberately decode byte/bit addresses independently of np.packbits.
            screen = bytearray(result[frame - distance]) if frame >= distance else bytearray(3840)
            mask = masks[row * 480:(row + 1) * 480]
            for byte, flags in enumerate(mask):
                for bit in range(8):
                    if flags & (128 >> bit):
                        screen[byte * 8 + bit] ^= read(1)[0]
            result[frame] = np.frombuffer(screen, dtype=np.uint8)
            frame += 1
    if offset != len(data):
        raise ValueError('trailing bytes')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--dictionary-candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--max-holds', type=int, nargs='+', default=[1, 2, 0])
    parser.add_argument('--changed-pixels', type=int, nargs='+', default=[1, 2])
    parser.add_argument('--groups', type=int, nargs='+', default=[8, 16])
    parser.add_argument('--rmse', type=float, default=24)
    args = parser.parse_args()
    if (any(x < 0 for x in args.max_holds) or any(not 1 <= x <= 16 for x in args.changed_pixels)
            or any(not 1 <= x <= 65535 for x in args.groups)
            or not np.isfinite(args.rmse) or args.rmse < 0):
        parser.error('invalid hold/pixel/group/error bound')
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    if states.shape != (4971, 3840) or sha(states.tobytes()) != STATES_SHA256:
        raise ValueError('unexpected source movie')
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='a13c3fe', complete=False,
                  reference_states_sha256=STATES_SHA256, frames=len(states),
                  resolution=[256, 192], logical_resolution=[128, 96], fps='25/3',
                  player_changed=False, hot_path_delta_tstates=0,
                  audio='unchanged, excluded from sizes', rows=[])

    def candidates():
        yield 'exact', states, None
        if args.dictionary_candidate:
            with np.load(args.dictionary_candidate) as saved:
                candidate = saved['states'].astype(np.uint8)
            if candidate.shape != states.shape or not np.array_equal(candidate[:, 3072:], states[:, 3072:]):
                raise ValueError('invalid dictionary candidate')
            yield 'dictionary', candidate, None
        for pixels in args.changed_pixels:
            for hold in args.max_holds:
                candidate, stats = temporal_filter(states, pixels, args.rmse, hold)
                yield f'temporal_p{pixels}_hold{hold}_rmse{args.rmse:g}', candidate, stats

    for name, candidate, stats in candidates():
        np.savez_compressed(args.cache / (name + '.npz'), states=candidate)
        row = dict(name=name, states_sha256=sha(candidate.tobytes()),
                   filtering=stats, quality=quality(states, candidate), layouts=[])
        report['rows'].append(row)
        for distance in (1, 2):
            for group in args.groups:
                data = encode(candidate, distance, group)
                if not np.array_equal(decode(data), candidate):
                    raise AssertionError('decoded states differ')
                layout_name = f'{name}_n{distance}_g{group}'
                (args.cache / (layout_name + '.raw')).write_bytes(data)
                item = dict(name=layout_name, prediction_distance=distance, group_frames=group,
                            mask_ram_bytes=480 * group, raw_bytes=len(data), stream_sha256=sha(data),
                            exact_round_trip_to_candidate=True,
                            deflate={str(size): measure(data, size) for size in (8192, len(data))})
                row['layouts'].append(item)
                args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(item), flush=True)
        print(json.dumps({k: v for k, v in row.items() if k != 'layouts'}), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
