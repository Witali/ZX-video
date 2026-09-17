"""Round-trip checked storage probes; these are not playable disk builds.

All transforms preserve every compact screen byte. DEFLATE is a fast layout
screening tool, not a bound on ZX0 and not a proposed Spectrum decoder.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import zlib

import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def layouts(states):
    yield 'packed', states
    pixels = ((states[:, :3072, None] >> np.array([6, 4, 2, 0])) & 3).reshape(len(states), -1)
    for gray in (False, True):
        values = pixels ^ (pixels >> 1) if gray else pixels
        planes = np.concatenate([np.packbits((values >> bit) & 1, axis=1) for bit in (1, 0)], axis=1)
        recovered = np.unpackbits(planes[:, :1536], axis=1) * 2 + np.unpackbits(planes[:, 1536:], axis=1)
        if gray:
            recovered ^= recovered >> 1
        assert np.array_equal(recovered, pixels)
        yield ('gray_planes' if gray else 'bit_planes'), np.concatenate([planes, states[:, 3072:]], axis=1)
    tiled = states[:, :3072].reshape(-1, 24, 4, 32).transpose(0, 1, 3, 2).reshape(-1, 768, 4)
    tiles = np.concatenate([tiled, states[:, 3072:, None]], axis=2).reshape(-1, 3840)
    inverse = tiles.reshape(-1, 24, 32, 5)
    assert np.array_equal(inverse[:, :, :, :4].transpose(0, 1, 3, 2).reshape(-1, 3072), states[:, :3072])
    assert np.array_equal(inverse[:, :, :, 4].reshape(-1, 768), states[:, 3072:])
    yield 'tiles', tiles


def predictors(matrix):
    yield 'absolute', matrix
    for distance in (1, 2):
        residual = matrix.copy()
        residual[distance:] ^= matrix[:-distance]
        decoded = residual.copy()
        for phase in range(distance):
            decoded[phase::distance] = np.bitwise_xor.accumulate(residual[phase::distance], axis=0)
        assert np.array_equal(decoded, matrix)
        yield f'xor{distance}', residual
    residual = matrix.copy()
    residual[1:] -= matrix[:-1]
    assert np.array_equal(np.cumsum(residual, axis=0, dtype=np.uint8), matrix)
    yield 'subtract1', residual


def deflate(data):
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = compressor.compress(data) + compressor.flush()
    assert zlib.decompress(packed, -15) == data
    return packed


def measure(data, block_bytes):
    return sum(4 + min(len(chunk), len(deflate(chunk)))
               for offset in range(0, len(data), block_bytes)
               for chunk in (data[offset:offset + block_bytes],))


def temporal_bits(matrix, count):
    """Group the same bit over time; verify inverse including the last group."""
    chunks = []
    for index in range(0, len(matrix), count):
        block = matrix[index:index + count]
        bits = np.unpackbits(block, axis=1).T
        packed = np.packbits(bits, axis=1)
        inverse = np.packbits(np.unpackbits(packed, axis=1)[:, :len(block)].T, axis=1)
        assert np.array_equal(block, inverse)
        chunks.append(packed.tobytes())
    return b''.join(chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--xz', action='store_true')
    parser.add_argument('--layouts', nargs='+', choices=('packed', 'bit_planes', 'gray_planes', 'tiles'))
    parser.add_argument('--predictions', nargs='+', choices=('absolute', 'xor1', 'xor2', 'subtract1'))
    parser.add_argument('--orders', nargs='+', choices=('frame', 'time8', 'time32', 'timebits8', 'timebits32'), default=['frame', 'time8', 'time32'])
    parser.add_argument('--cache', type=Path, help='optionally retain transformed inputs for real ZX0 measurements')
    args = parser.parse_args()
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    assert states.shape == (4971, 3840)
    assert sha(states.tobytes()) == '9cc006a31408e2c3c3f96f96901b003756c2a480497e12d6b124baedafaeb35d'
    raw_audio = args.audio.read_bytes()
    assert sha(raw_audio) == 'c55ee9d570284c89a33bd582eb28f3c141676ec63e7ced4c00b5aac7cb575cae'
    report = dict(scope=__doc__, frames=len(states), states_sha256=sha(states.tobytes()),
                  audio_sha256=sha(raw_audio), three_disk_budget_bytes=3 * 645888,
                  note='Sizes exclude audio, frame/disk headers and decoder growth. Long blocks need a different player.',
                  layouts=[])
    for layout, matrix in layouts(states):
        if args.layouts and layout not in args.layouts:
            continue
        for prediction, residual in predictors(matrix):
            if args.predictions and prediction not in args.predictions:
                continue
            for order in args.orders:
                if order == 'frame':
                    data = residual.tobytes()
                elif order.startswith('timebits'):
                    data = temporal_bits(residual, int(order[8:]))
                else:
                    count = int(order[4:])
                    chunks = [residual[i:i + count] for i in range(0, len(residual), count)]
                    data = b''.join(chunk.T.tobytes() for chunk in chunks)
                    offset = 0
                    for chunk in chunks:
                        length = chunk.size
                        recovered = np.frombuffer(data[offset:offset + length], dtype=np.uint8).reshape(3840, len(chunk)).T
                        assert np.array_equal(chunk, recovered)
                        offset += length
                if args.cache:
                    args.cache.mkdir(parents=True, exist_ok=True)
                    (args.cache / f'{layout}_{prediction}_{order}.raw').write_bytes(data)
                result = dict(layout=layout, prediction=prediction, order=order,
                              raw_bytes=len(data), nonzero_bytes=int(np.count_nonzero(residual)),
                              deflate={str(size): measure(data, size) for size in (6144, 32768, len(data))})
                if args.xz and order == 'frame':
                    packed = lzma.compress(data, preset=6)
                    assert lzma.decompress(packed) == data
                    result['whole_xz_bytes'] = len(packed)
                report['layouts'].append(result)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(result), flush=True)
    print('Minimum video proxy bytes:', min(v for row in report['layouts'] for v in row['deflate'].values()))


if __name__ == '__main__':
    main()
