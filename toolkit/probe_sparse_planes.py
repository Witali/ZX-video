"""Reversible change masks plus densely packed nonzero temporal differences."""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_lossless_layouts import layouts, measure, sha


def pack(values, bits):
    per_byte = 8 // bits
    values = np.pad(values, (0, (-len(values)) % per_byte)).reshape(-1, per_byte)
    return np.bitwise_or.reduce(values << np.arange(8 - bits, -1, -bits, dtype=np.uint8), axis=1).tobytes()


def unpack(data, bits, count):
    return ((np.frombuffer(data, dtype=np.uint8)[:, None] >> np.arange(8 - bits, -1, -bits, dtype=np.uint8)) & ((1 << bits) - 1)).ravel()[:count]


def decode(data, frames, bits, order):
    mask_bytes = 3840 // bits
    cursor = frames * mask_bytes if order == 'separate' else 0
    restored = np.empty((frames, 3840), dtype=np.uint8)
    for frame in range(frames):
        if order == 'separate':
            bitmap = data[frame * mask_bytes:(frame + 1) * mask_bytes]
            saved_length = None
        else:
            saved_length = struct.unpack_from('<H', data, cursor)[0]
            cursor += 2
            bitmap = data[cursor:cursor + mask_bytes]
            cursor += mask_bytes
        mask = np.unpackbits(np.frombuffer(bitmap, dtype=np.uint8)).astype(bool)
        count = int(mask.sum())
        length = (count * bits + 7) // 8
        assert saved_length is None or saved_length == length
        fields = np.zeros(mask.size, dtype=np.uint8)
        fields[mask] = unpack(data[cursor:cursor + length], bits, count)
        cursor += length
        restored[frame] = np.frombuffer(pack(fields, bits), dtype=np.uint8)
        if frame:
            restored[frame] ^= restored[frame - 1]
    assert cursor == len(data)
    return restored


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--verify-only', action='store_true', help='decode previously generated raw experiments and compare every screen')
    args = p.parse_args()
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    assert sha(states.tobytes()) == '9cc006a31408e2c3c3f96f96901b003756c2a480497e12d6b124baedafaeb35d'
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, states_sha256=sha(states.tobytes()), frames=len(states),
                  exact_round_trip=True, note='Video only; measurements do not constitute a playable disk build.', layouts=[])
    for layout, matrix in layouts(states):
        if layout not in ('packed', 'gray_planes'):
            continue
        delta = matrix.copy()
        delta[1:] ^= matrix[:-1]
        assert np.array_equal(np.bitwise_xor.accumulate(delta, axis=0), matrix)
        for bits in (8, 4, 2):
            if args.verify_only:
                for order in ('frame', 'separate'):
                    name = f'{layout}_{bits}_{order}'
                    data = (args.cache / (name + '.raw')).read_bytes()
                    assert np.array_equal(decode(data, len(states), bits, order), matrix)
                    print(f'Verified all {len(states)} screens: {name}', flush=True)
                continue
            masks = []
            values = []
            packets = []
            for row in delta:
                fields = unpack(row.tobytes(), bits, 3840 * 8 // bits)
                mask = fields != 0
                bitmap = np.packbits(mask).tobytes()
                packed = pack(fields[mask], bits)
                restored = np.zeros_like(fields)
                restored[np.unpackbits(np.frombuffer(bitmap, dtype=np.uint8)).astype(bool)] = unpack(packed, bits, int(mask.sum()))
                assert pack(restored, bits) == row.tobytes()
                masks.append(bitmap)
                values.append(packed)
                packets.append(struct.pack('<H', len(packed)) + bitmap + packed)
            for order, data in (('frame', b''.join(packets)), ('separate', b''.join(masks) + b''.join(values))):
                assert np.array_equal(decode(data, len(states), bits, order), matrix)
                name = f'{layout}_{bits}_{order}'
                (args.cache / (name + '.raw')).write_bytes(data)
                result = dict(name=name, raw_bytes=len(data), sha256=sha(data),
                              deflate={str(size): measure(data, size) for size in (8192, 32768, len(data))})
                report['layouts'].append(result)
                args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
