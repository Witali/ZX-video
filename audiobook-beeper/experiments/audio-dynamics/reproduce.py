"""Rebuild the saved complete IMA4 volume without repeating the PC search.

Use the public convert_audio.py command in README.md to encode a new input.
This evidence-only tool authenticates the saved selected streams, assembles
their players, requires a byte-identical disk, and reruns full verification.
"""
import argparse
import hashlib
import json
from pathlib import Path

from ima4_series import build_volume
from verify_ima3_series import verify_series
from verify_pcm import save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fuse', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--build-only', action='store_true',
                        help='authenticate and reproduce disk bytes without repeating the saved execution proof')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    hashes = json.loads((here/'artifact-hashes.json').read_bytes())
    for name, expected in hashes.items():
        assert hashlib.sha256((here/name).read_bytes()).hexdigest() == expected, name
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('output must be empty')
    out.mkdir(parents=True, exist_ok=True)
    saved = json.loads((here/'release/volumes.json').read_bytes())
    assert len(saved) == 1
    volume = saved[0]
    selected = [here/f'selected/part-{i:05d}' for i in range(1, len(volume['parts'])+1)]
    disk, metadata = build_volume(selected, out/'work/volume-0001',
                                  bytes.fromhex(volume['series_id']), 1, 1)
    assert hashlib.sha256(disk).hexdigest() == volume['trd_sha256']
    (out/'audio.trd').write_bytes(disk)
    save(out/'volumes.json', [dict(file='audio.trd', **metadata)])
    if not args.build_only:
        result = verify_series(out, args.fuse.resolve(), args.ffmpeg)
        assert result['complete']
    print(json.dumps(dict(disk=str(out/'audio.trd'), rebuilt_exactly=True,
                         execution_reverified=not args.build_only,
                         trd_sha256=metadata['trd_sha256'])))


if __name__ == '__main__':
    main()
