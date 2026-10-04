"""Write or verify the archived experiment's byte-exact artifact manifest."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--write', action='store_true')
a = p.parse_args()
root = Path(__file__).resolve().parent
manifest = root/'artifact-hashes.json'
if a.write:
    files = [f for f in root.rglob('*') if f.is_file() and f != manifest
             and f.suffix != '.fmf' and '__pycache__' not in f.parts]
    hashes = {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)}
    manifest.write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')
hashes = json.loads(manifest.read_bytes())
for name, expected in hashes.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
report = json.loads((root/'comparison.json').read_bytes())
release = root.parents[2]/'ZX-audiobook-IMA3-overlap-test.trd'
assert hashlib.sha256(release.read_bytes()).hexdigest() == report['new_trd_sha256']
assert (root/'audio.trd').read_bytes() == release.read_bytes()
for path in ('verification/report.json', 'qualified/fuse.json', 'qualified/native.json'):
    assert json.loads((root/path).read_bytes())['complete']
normal = json.loads((root/'normal/report.json').read_bytes())
assert normal['trd_sha256'] == report['new_trd_sha256'] and normal['first_part_reached_exit']
print(json.dumps(dict(complete=True, artifacts_verified=len(hashes), release_sha256=report['new_trd_sha256'])))
