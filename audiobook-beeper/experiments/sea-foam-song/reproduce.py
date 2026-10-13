"""Reassemble the archived song byte for byte, optionally rerunning full playback."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BEEPER = HERE.parents[1]
sys.path[:0] = [str(BEEPER), str(BEEPER.parent / 'toolkit')]
from ima4_series import build_volume
from verify_pcm import save
import verify_ima3_series as verifier
from build import qualify_legacy_phase


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--fuse', type=Path)
    parser.add_argument('--ffmpeg')
    args = parser.parse_args()
    archive = HERE / 'evidence'
    manifest = json.loads((archive / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(archive / name) == expected['sha256'], name
    report = json.loads((archive / 'report.json').read_bytes())
    volumes = json.loads((archive / 'volumes.json').read_bytes())
    assert report['complete'] and len(volumes) == 1
    out = args.output.resolve()
    assert not out.exists() or not any(out.iterdir()), 'output must be empty'
    out.mkdir(parents=True, exist_ok=True)
    selected = [archive / 'selected' / f'part-{i+1:05d}' for i in range(len(report['parts']))]
    disk, metadata = build_volume(selected, out / 'volume', bytes.fromhex(volumes[0]['series_id']), 1, 1)
    assert hashlib.sha256(disk).hexdigest() == report['trd_sha256']
    (out / 'audio.trd').write_bytes(disk)
    save(out / 'volumes.json', [dict(file='audio.trd', **metadata)])
    if not args.build_only:
        assert args.fuse and args.ffmpeg, 'full playback requires --fuse and --ffmpeg'
        verifier.qualify_ready_phase = qualify_legacy_phase
        assert verifier.verify_series(out, args.fuse, args.ffmpeg)['complete']
    print(json.dumps(dict(rebuilt_byte_exact=True, complete_playback_reverified=not args.build_only,
                          trd_sha256=report['trd_sha256'])))


if __name__ == '__main__':
    main()
