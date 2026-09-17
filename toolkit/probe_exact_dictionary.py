"""Lossless tile dictionary/RAM sweep; offline screening, not a Z80 player.

Each physical 8x8 cell is represented by four compact bitmap bytes and one
attribute. Groups reset prediction to zero and store <frames:u16, entries:u16>,
then entries*5 dictionary bytes. Per frame, tokens encode 1..64 cells:
00xxxxxx skip, 01xxxxxx dictionary indices, 10xxxxxx literal cells.
Indices occupy one byte for <=256 entries, otherwise two little-endian bytes.
The optional tiered mode sets bit 15 in the entry count: indices 0..254 use
one byte, others use FF followed by a u16 index (only for >256 entries).
DEFLATE only screens layouts; its size does not predict ZX0 or playback speed.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np

from probe_lossless_layouts import measure

STATES_SHA256 = '9cc006a31408e2c3c3f96f96901b003756c2a480497e12d6b124baedafaeb35d'


def tile_frames(states):
    pixels = states[:, :3072].reshape(-1, 24, 4, 32).transpose(0, 1, 3, 2)
    tiles = np.concatenate((pixels.reshape(-1, 768, 4), states[:, 3072:, None]), axis=2)
    return [[bytes(cell) for cell in frame] for frame in tiles]


def encode(frames, group_frames, maximum_entries, index_mode='fixed'):
    output = bytearray()
    stats = Counter()
    for start in range(0, len(frames), group_frames):
        group = frames[start:start + group_frames]
        previous = [bytes(5)] * 768
        counts = Counter()
        for frame in group:
            counts.update(cell for cell, old in zip(frame, previous) if cell != old)
            previous = frame
        # Do not buy entries used only once. Stable tie-break: first occurrence.
        table = [cell for cell, count in counts.most_common(maximum_entries) if count > 1]
        lookup = {cell: i for i, cell in enumerate(table)}
        width = 1 if len(table) <= 256 else 2
        tiered = index_mode == 'tiered' and len(table) > 256
        output += struct.pack('<HH', len(group), len(table) | (0x8000 if tiered else 0)) + b''.join(table)
        stats['table_bytes'] += 5 * len(table)
        stats['max_entries'] = max(stats['max_entries'], len(table))
        previous = [bytes(5)] * 768
        for frame in group:
            kinds = [0 if cell == old else 1 if cell in lookup else 2
                     for cell, old in zip(frame, previous)]
            cursor = 0
            while cursor < 768:
                kind = kinds[cursor]
                end = cursor + 1
                while end < min(768, cursor + 64) and kinds[end] == kind:
                    end += 1
                output.append((kind << 6) | (end - cursor - 1))
                if kind == 1:
                    for cell in frame[cursor:end]:
                        reference = lookup[cell]
                        if tiered:
                            output += bytes([reference]) if reference < 255 else b'\xff' + reference.to_bytes(2, 'little')
                        else:
                            output += reference.to_bytes(width, 'little')
                elif kind == 2:
                    output += b''.join(frame[cursor:end])
                stats[('skipped_cells', 'indexed_cells', 'literal_cells')[kind]] += end - cursor
                cursor = end
            previous = frame
    return bytes(output), dict(stats)


def decode(data):
    """Independent parser; reconstruct compact screens, including attributes."""
    cursor = 0
    restored = []

    def read(size):
        nonlocal cursor
        if cursor + size > len(data):
            raise ValueError('truncated dictionary stream')
        chunk = data[cursor:cursor + size]
        cursor += size
        return chunk

    while cursor < len(data):
        count, entries = struct.unpack('<HH', read(4))
        tiered = bool(entries & 0x8000)
        entries &= 0x7fff
        if not count:
            raise ValueError('empty group')
        table = [read(5) for _ in range(entries)]
        width = 1 if entries <= 256 else 2
        screen = [bytes(5)] * 768
        for _ in range(count):
            position = 0
            while position < 768:
                token = read(1)[0]
                kind, length = token >> 6, (token & 63) + 1
                if kind == 3 or position + length > 768:
                    raise ValueError('invalid tile run')
                for index in range(position, position + length):
                    if kind == 1:
                        if tiered:
                            reference = read(1)[0]
                            if reference == 255:
                                reference = int.from_bytes(read(2), 'little')
                        else:
                            reference = int.from_bytes(read(width), 'little')
                        if reference >= entries:
                            raise ValueError('invalid dictionary index')
                        screen[index] = table[reference]
                    elif kind == 2:
                        screen[index] = read(5)
                position += length
            cells = np.frombuffer(b''.join(screen), dtype=np.uint8).reshape(24, 32, 5)
            restored.append(np.concatenate((cells[:, :, :4].transpose(0, 2, 1).ravel(),
                                            cells[:, :, 4].ravel())))
    return np.array(restored, dtype=np.uint8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--groups', type=int, nargs='+', default=[64, 256, 1024])
    parser.add_argument('--entries', type=int, nargs='+', default=[0, 128, 256, 512, 1024, 2048, 4096])
    parser.add_argument('--index-mode', choices=('fixed', 'tiered'), default='fixed')
    args = parser.parse_args()
    if any(not 1 <= n <= 65535 for n in args.groups) or any(not 0 <= n <= 32767 for n in args.entries):
        parser.error('group count must fit u16; entries must fit 15 bits; groups must not be empty')
    with np.load(args.checkpoint) as checkpoint:
        states = checkpoint['states'].astype(np.uint8)
    digest = hashlib.sha256(states.tobytes()).hexdigest()
    if states.shape != (4971, 3840) or digest != STATES_SHA256:
        raise ValueError('not the accepted full movie checkpoint')
    frames = tile_frames(states)
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='27d2c92', frames=len(states),
                  states_sha256=digest, current_ring_sectors=320,
                  video_only=True, player_changed=False, hot_path_delta_tstates=0, index_mode=args.index_mode,
                  complete=False, rows_expected=len(args.groups) * len(args.entries),
                  ram_model='Expanded 9 bytes/cell; whole 16KiB banks taken from 80KiB ring; excludes new decoder/tables and bank-crossing costs.',
                  rows=[])
    for group in args.groups:
        for entries in args.entries:
            name = f'group{group}_entries{entries}' + ('_tiered' if args.index_mode == 'tiered' else '')
            data, stats = encode(frames, group, entries, args.index_mode)
            if not np.array_equal(decode(data), states):
                raise AssertionError('dictionary round trip differs')
            (args.cache / (name + '.raw')).write_bytes(data)
            expanded = stats['max_entries'] * 9
            banks = math.ceil(expanded / 16384)
            row = dict(name=name, group_frames=group, requested_entries=entries,
                       raw_bytes=len(data), stream_sha256=hashlib.sha256(data).hexdigest(),
                       exact_round_trip=True, **stats,
                       dictionary_compact_ram_bytes=stats['max_entries'] * 5,
                       dictionary_expanded_ram_bytes=expanded,
                       ring_sectors_if_compact_whole_banks_reserved=320 - math.ceil(stats['max_entries'] * 5 / 16384) * 64,
                       ring_sectors_if_whole_banks_reserved=320 - banks * 64,
                       deflate={str(size): measure(data, size) for size in (6144, len(data))})
            report['rows'].append(row)
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
