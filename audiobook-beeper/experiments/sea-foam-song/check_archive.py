import hashlib
import json
from pathlib import Path
import re
import subprocess

e = Path('audiobook-beeper/experiments/sea-foam-song/evidence')
m = json.loads((e / 'manifest.json').read_bytes())
checks = [(str(e / k).replace('\\', '/'), v) for k, v in m['files'].items()]
checks.append(('ZX-music-Sea-Foam-IMA4-direct.trd', m['root_disk']))
checks.append((str(e / 'manifest.json').replace('\\', '/'),
               dict(sha256=hashlib.sha256((e / 'manifest.json').read_bytes()).hexdigest(),
                    bytes=(e / 'manifest.json').stat().st_size)))
data = subprocess.check_output(['git', 'cat-file', '--batch'],
                              input=''.join(':'+p+'\n' for p,v in checks).encode())
offset = lfs = 0
failures = []
for p, v in checks:
    end = data.index(b'\n', offset)
    size = int(data[offset:end].split()[-1])
    blob = data[end+1:end+1+size]
    offset = end+size+2
    if blob.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        actual = re.search(rb'oid sha256:([0-9a-f]+)', blob).group(1).decode()
        length = int(re.search(rb'size ([0-9]+)', blob).group(1))
        lfs += 1
    else:
        actual = hashlib.sha256(blob).hexdigest()
        length = len(blob)
    if actual != v['sha256'] or length != v['bytes']:
        failures.append(dict(path=p, expected=v['sha256'], actual=actual, expected_bytes=v['bytes'], actual_bytes=length))
print(json.dumps(dict(complete=not failures, staged_artifacts_authenticated=len(checks),
                     lfs_artifacts=lfs, failures=failures), indent=2))
raise SystemExit(bool(failures))
