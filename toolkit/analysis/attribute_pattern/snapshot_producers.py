"""Save only producer sources matching an existing qualification's exact hashes."""
import argparse
import hashlib
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('evidence', type=Path)
    args = p.parse_args();root = args.evidence
    q = json.loads((root/'qualification.json').read_bytes())
    saved = {}
    for name, expected in q['producer_sources_sha256_lf'].items():
        content = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(content).hexdigest() != expected and name.endswith('/rebuild.py'):
            # The optional verification override was added after this snapshot.
            # Recover that exact earlier source, accepting it ONLY by SHA256.
            source = content.decode('utf-8')
            source = source.replace("    parser.add_argument('--verification', choices=('none', 'cpu', 'fuse'), default='fuse')\n", '')
            first = source.index('    original_main = build_prefix.converter.main\n')
            last = source.index('    if args.colour_cache:\n', first)
            source = source[:first]+source[last:]
            source = source.replace('import sys\n', 'import shutil\nimport sys\n')
            content = source.encode('utf-8')
        assert hashlib.sha256(content).hexdigest() == expected, name
        target = root/'producer-sources'/name;target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content);saved[name] = target.relative_to(root).as_posix()
    q['producer_source_snapshots'] = saved
    (root/'qualification.json').write_text(json.dumps(q, indent=2)+'\n', encoding='utf-8')
    files = {f.relative_to(root).as_posix():dict(bytes=f.stat().st_size, sha256=hashlib.sha256(f.read_bytes()).hexdigest())
             for f in root.rglob('*') if f.is_file() and f != root/'manifest.json'}
    (root/'manifest.json').write_text(json.dumps(dict(files=files), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(complete=True, matched_sources=len(saved), files=len(files), bytes=sum(f['bytes'] for f in files.values()))))


if __name__ == '__main__':main()
