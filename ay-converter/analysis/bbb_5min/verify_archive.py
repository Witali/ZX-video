"""Verify every archived byte, optionally including Git blobs and local LFS."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision');args=parser.parse_args()
    evidence=HERE/'evidence';manifest=json.loads((evidence/'manifest.json').read_bytes())
    report=json.loads((evidence/'report.json').read_bytes())
    assert report['all_disks_fuse_verified'] and report['fuse_ticks_verified']==15000
    assert report['fuse_register_writes_verified']==195145
    for name,expected in report['producer_sources_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==expected,name
    batch=None;lfs_files=0
    if args.revision:
        batch=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT).decode().strip())
        if not common.is_absolute():common=ROOT/common
    for name,expected in manifest['files'].items():
        data=(evidence/name).read_bytes()
        assert len(data)==expected['bytes'] and sha(data)==expected['sha256'],name
        if batch:
            ref=f'{args.revision}:{(evidence/name).relative_to(ROOT).as_posix()}'
            batch.stdin.write((ref+'\n').encode());batch.stdin.flush()
            header=batch.stdout.readline().decode().split()
            assert len(header)==3 and header[1]=='blob',ref
            stored=batch.stdout.read(int(header[2]));assert batch.stdout.read(1)==b'\n'
            if stored.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                fields=dict(line.split(' ',1) for line in stored.decode().splitlines())
                assert fields['oid']=='sha256:'+expected['sha256'] and int(fields['size'])==expected['bytes'],ref
                digest=expected['sha256'];stored=(common/'lfs/objects'/digest[:2]/digest[2:4]/digest).read_bytes()
                lfs_files+=1
            assert len(stored)==expected['bytes'] and sha(stored)==expected['sha256'],ref
    if batch:batch.stdin.close();batch.wait();assert batch.returncode==0
    print(json.dumps(dict(complete=True,files=len(manifest['files']),revision=args.revision,lfs_objects_verified=lfs_files,
        ticks=15000,disks=3,register_writes=195145)))


if __name__=='__main__':main()
