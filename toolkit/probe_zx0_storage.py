"""Measure real ZX0 blocks and verify each with the independent decoder.

This is a storage experiment, not a playable TRD builder. Blocks larger than
8192 bytes and transformed screens require a new Spectrum decoder/scheduler.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

import numpy as np

from probe_lossless_layouts import layouts, predictors, sha
import zx0_codec


def main():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--checkpoint', type=Path)
    source.add_argument('--raw', type=Path)
    p.add_argument('--layout', choices=('packed', 'bit_planes', 'gray_planes', 'tiles'), default='packed')
    p.add_argument('--prediction', choices=('absolute', 'xor1', 'xor2', 'subtract1'), default='absolute')
    p.add_argument('--time-group', type=int, default=1)
    p.add_argument('--block-bytes', type=int, default=32768)
    p.add_argument('--zx0', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--jobs', type=int, choices=range(1, 5), default=2)
    p.add_argument('--quick', action='store_true', help='use ZX0 -q; record the non-optimal mode and use a separate cache')
    args = p.parse_args()
    if not 1 <= args.block_bytes <= 65535 or args.time_group < 1:
        p.error('invalid block size or temporal group')
    if args.raw:
        data = args.raw.read_bytes()
        description = dict(raw_file=args.raw.name)
    else:
        with np.load(args.checkpoint) as saved:
            states = saved['states'].astype(np.uint8)
        assert sha(states.tobytes()) == '9cc006a31408e2c3c3f96f96901b003756c2a480497e12d6b124baedafaeb35d'
        matrix = next(array for name, array in layouts(states) if name == args.layout)
        residual = next(array for name, array in predictors(matrix) if name == args.prediction)
        data = residual.tobytes() if args.time_group == 1 else b''.join(
            residual[i:i + args.time_group].T.tobytes() for i in range(0, len(residual), args.time_group))
        description = dict(layout=args.layout, prediction=args.prediction, time_group=args.time_group,
                           states_sha256=sha(states.tobytes()))
    chunks = [data[i:i + args.block_bytes] for i in range(0, len(data), args.block_bytes)]
    args.cache = args.cache / ('quick' if args.quick else 'optimal')
    args.cache.mkdir(parents=True, exist_ok=True)
    executable = str(args.zx0.resolve())

    def compress(chunk):
        digest = sha(chunk)
        packed = args.cache / (digest + '.zx0')
        # Identical chunks may run concurrently: give each invocation its own
        # output, then atomically publish the verified deterministic encoding.
        if packed.exists():
            encoded = packed.read_bytes()
        else:
            import tempfile
            with tempfile.TemporaryDirectory(dir=args.cache) as temporary:
                src = Path(temporary) / 'input.raw'
                dst = Path(temporary) / 'output.zx0'
                src.write_bytes(chunk)
                subprocess.run([executable, '-f', *(['-q'] if args.quick else []), str(src.resolve()), str(dst.resolve())], check=True, capture_output=True)
                encoded = dst.read_bytes()
            assert zx0_codec.decompress(encoded, limit=len(chunk)) == chunk
            # Concurrent writes contain identical bytes; publishing a temp
            # avoids another worker observing a partial cache entry.
            import os
            with tempfile.NamedTemporaryFile(dir=args.cache, delete=False) as stream:
                stream.write(encoded)
                temporary_name = stream.name
            os.replace(temporary_name, packed)
        assert zx0_codec.decompress(encoded, limit=len(chunk)) == chunk
        return dict(decoded_bytes=len(chunk), zx0_bytes=len(encoded), sha256=digest)

    report = dict(scope=__doc__, input=description, input_sha256=sha(data), input_bytes=len(data),
                  block_bytes=args.block_bytes, blocks_expected=len(chunks), encoder_sha256=sha(args.zx0.read_bytes()),
                  encoder_mode='quick ZX0 v2' if args.quick else 'optimal ZX0 v2', complete=False, blocks=[])
    def save():
        report['zx0_bytes'] = sum(block['zx0_bytes'] for block in report['blocks'])
        report['zx0_with_headers_bytes'] = report['zx0_bytes'] + 4 * len(report['blocks'])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for index, block in enumerate(pool.map(compress, chunks)):
            report['blocks'].append(block)
            if index % 20 == 0:
                save()
                print(f'Verified ZX0 block {index + 1}/{len(chunks)}', flush=True)
    report['complete'] = True
    save()
    print(json.dumps({k: v for k, v in report.items() if k != 'blocks'}), flush=True)


if __name__ == '__main__':
    main()
