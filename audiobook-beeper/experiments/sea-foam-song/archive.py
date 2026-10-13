"""Archive only a complete, authenticated legacy song build and its evidence."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--reference-report', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    build = args.build.resolve()
    report = json.loads((build / 'report.json').read_bytes())
    assert report['complete'] and report['full_selected_song_retained']
    assert report['disk_count'] == 1 and report['verification']['complete']
    assert sha(build / 'audio.trd') == report['trd_sha256']
    evidence = HERE / 'evidence'
    assert not evidence.exists(), 'archive must be new'
    shutil.copytree(build, evidence, ignore=shutil.ignore_patterns('audio.trd'))
    reference = json.loads(args.reference_report.read_bytes())
    assert reference['reference_rebuilt_byte_exact']
    assert reference['sha256'] == report['reference_disk_sha256']
    shutil.copy2(args.reference_report, evidence / 'reference-rebuild.json')
    shutil.copy2(args.log, evidence / 'build.log')
    producers = evidence / 'producer-source'
    producers.mkdir()
    identity = json.loads((build / 'run.json').read_bytes())
    beeper = HERE.parents[1]
    for name, expected in identity['producers'].items():
        path = beeper / name
        assert sha(path) == expected, f'producer changed: {name}'
        (producers / (name + '.gz')).write_bytes(gzip.compress(path.read_bytes(), mtime=0))
    (producers / 'build.py.gz').write_bytes(gzip.compress((HERE / 'build.py').read_bytes(), mtime=0))
    disk = ROOT / 'ZX-music-Sea-Foam-IMA4-direct.trd'
    assert not disk.exists()
    shutil.copy2(build / 'audio.trd', disk)
    assert sha(disk) == report['trd_sha256']
    manifest = {str(p.relative_to(evidence)).replace('\\', '/'): dict(sha256=sha(p), bytes=p.stat().st_size)
                for p in sorted(evidence.rglob('*')) if p.is_file()}
    (evidence / 'manifest.json').write_text(json.dumps(dict(complete=True,
        root_disk=dict(file=disk.name, sha256=sha(disk), bytes=disk.stat().st_size),
        files=manifest), indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, files=len(manifest),
                         bytes=sum(p['bytes'] for p in manifest.values()), disk=str(disk))))


if __name__ == '__main__':
    main()
