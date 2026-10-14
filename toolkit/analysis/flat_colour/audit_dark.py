"""Audit measured archive bytes and real Git/LFS object identities."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path);p.add_argument('--revision', default=':')
    p.add_argument('--root-disk', type=Path);args = p.parse_args()
    archive = args.archive.resolve();manifest = json.loads((archive/'manifest.json').read_bytes())
    entries = dict(manifest['files'])
    entries['manifest.json'] = dict(bytes=(archive/'manifest.json').stat().st_size,
        sha256=hashlib.sha256((archive/'manifest.json').read_bytes()).hexdigest())
    paths = [((archive/name).relative_to(ROOT).as_posix(), row) for name,row in entries.items()]
    if args.root_disk:
        disk = args.root_disk.resolve();paths.append((disk.relative_to(ROOT).as_posix(),
            dict(bytes=disk.stat().st_size,sha256=hashlib.sha256(disk.read_bytes()).hexdigest())))
        assert disk.read_bytes() == (archive/disk.name).read_bytes()
    refs = [args.revision+name if args.revision == ':' else args.revision+':'+name for name,_ in paths]
    output = subprocess.check_output(['git','cat-file','--batch'],input=('\n'.join(refs)+'\n').encode(),cwd=ROOT)
    at = lfs = 0
    for (name, expected), ref in zip(paths, refs):
        end = output.index(b'\n',at);header = output[at:end].split();at = end+1
        assert header[1] == b'blob', (ref,header)
        size = int(header[2]);blob = output[at:at+size];at += size+1
        path = ROOT/name;actual = path.read_bytes()
        assert len(actual) == expected['bytes'] and hashlib.sha256(actual).hexdigest() == expected['sha256'], name
        if blob.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            identity = blob.decode().splitlines();assert 'oid sha256:'+expected['sha256'] in identity
            assert 'size '+str(expected['bytes']) in identity;lfs += 1
        else:assert blob == actual, name
    assert at == len(output)
    print(json.dumps(dict(complete=True,revision=args.revision,measured_objects=len(paths),
        lfs_identities=lfs,every_source_and_git_or_lfs_byte_exact=True)))


if __name__ == '__main__':main()
