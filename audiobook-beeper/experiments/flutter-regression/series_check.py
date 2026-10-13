"""Execute corrected IMA4 tables through a real automatic part transition."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parents[2]/'toolkit')]
from ima4_series import build_volume
from verify_ima3_series import verify_series
from verify_pcm import save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selected', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fuse', type=Path, required=True)
    p.add_argument('--ffmpeg', required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    identity = hashlib.sha256((a.selected/'soundtrack.ima.gz').read_bytes()).digest()[:16]
    # A repeated fully verified excerpt tests the same independent reload as
    # different recordings would. This is an integration test, not new source.
    disk, metadata = build_volume([a.selected,a.selected], a.output/'volume', identity, 1, 1)
    (a.output/'audio.trd').write_bytes(disk)
    save(a.output/'volumes.json', [dict(file='audio.trd', **metadata)])
    result = verify_series(a.output, a.fuse, a.ffmpeg)
    assert result['complete']
    print(json.dumps(dict(complete=True, trd_sha256=metadata['trd_sha256'],
        source_repeated_for_integration_test=True, independently_bootable=metadata['independently_bootable'])))


if __name__ == '__main__':
    main()
