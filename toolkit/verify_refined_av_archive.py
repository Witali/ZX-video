"""Recheck saved content hashes, source identities and staged Git LFS pointers."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('report', 'evidence', 'root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--index', action='store_true')
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    assert report['complete']
    images = []
    for record in report['artifacts']:
        path = args.evidence / record['file']
        packed = path.read_bytes()
        assert len(packed) == record['archive_bytes'] and sha(packed) == record['archive_sha256'], path
        raw = gzip.decompress(packed) if path.suffix == '.gz' else packed
        assert len(raw) == record['raw_bytes'] and sha(raw) == record['raw_sha256'], path
        if path.suffix == '.trd':
            images.append((path, sha(raw), len(raw)))
    for record in report.get('root_images', []):
        path = args.root / record['file']
        raw = path.read_bytes()
        assert sha(raw) == record['sha256'] and len(raw) == 655360, path
        images.append((path, sha(raw), len(raw)))
    for name, expected in report['source_sha256_lf'].items():
        path = Path(__file__).with_name(name)
        assert sha(path.read_bytes().replace(b'\r\n', b'\n')) == expected, path
    if args.index:
        for path, identity, size in images:
            relative = path.resolve().relative_to(args.root.resolve()).as_posix()
            pointer = subprocess.check_output(['git', 'show', ':' + relative], cwd=args.root)
            expected = f'version https://git-lfs.github.com/spec/v1\noid sha256:{identity}\nsize {size}\n'
            assert pointer.decode('ascii') == expected, relative
    result = dict(complete=True, report_sha256_lf=sha(args.report.read_bytes().replace(b'\r\n', b'\n')),
                  artifacts=len(report['artifacts']), root_images=len(report.get('root_images', [])),
                  source_files=len(report['source_sha256_lf']),
                  staged_lfs_pointers_checked=len(images) if args.index else 0,
                  verifier_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
