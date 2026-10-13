"""Authenticate archived Git blobs and their local LFS objects against manifests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archives', nargs='+')
    p.add_argument('--index', action='store_true')
    p.add_argument('--root-trd', action='store_true')
    args = p.parse_args();revision = '' if args.index else 'HEAD'
    common = Path(subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT).decode().strip())
    if not common.is_absolute():common = (ROOT/common).resolve()
    lfs = set();checked = 0
    def blob(relative):
        data = subprocess.check_output(['git', 'cat-file', 'blob', revision+':'+relative], cwd=ROOT)
        if data.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            values = dict(line.split(' ', 1) for line in data.decode().splitlines())
            oid = values['oid'].removeprefix('sha256:')
            data = (common/'lfs/objects'/oid[:2]/oid[2:4]/oid).read_bytes()
            assert len(data) == int(values['size']) and hashlib.sha256(data).hexdigest() == oid
            lfs.add(relative)
        return data
    for archive in args.archives:
        manifest = json.loads(blob(archive+'/manifest.json'))
        for name, expected in manifest['files'].items():
            data = blob(archive+'/'+name)
            assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256'], name
            checked += 1
        qualification = json.loads(blob(archive+'/qualification.json'))
        for name, path in qualification['producer_source_snapshots'].items():
            assert hashlib.sha256(blob(archive+'/'+path)).hexdigest() == qualification['producer_sources_sha256_lf'][name]
        if args.root_trd and qualification['frames'] == 900:
            data = blob('ZX-video-sea-foam_part01.trd')
            assert hashlib.sha256(data).hexdigest() == qualification['volumes'][0]['sha256']
            checked += 1
    print(json.dumps(dict(complete=True, authenticated_artifacts=checked, lfs_objects=len(lfs), index=args.index)))


if __name__ == '__main__':main()
