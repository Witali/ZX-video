"""Fetch and verify the exact upstream source, instrument it, and build on Linux."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

from patch_fuse import patch

COMMIT='e997e2bc32c888348f862f69f2c53babfedf7791'
ARCHIVE_SHA256='3b8af49fda13ed29ac6b9b03038a2761e397cc06a004dc499be64d5d3917d4a0'

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--roms',type=Path,required=True,help='Existing legitimate ROM directory')
    args=ap.parse_args();work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
    tree=work/'fuse-libretro-master'
    if tree.exists():raise SystemExit('Use a fresh work directory; refusing to overwrite a build')
    archive=work/'source-pinned.tar.gz'
    data=urllib.request.urlopen('https://codeload.github.com/libretro/fuse-libretro/tar.gz/'+COMMIT,timeout=60).read()
    assert hashlib.sha256(data).hexdigest()==ARCHIVE_SHA256
    archive.write_bytes(data)
    with tarfile.open(archive) as t:t.extractall(work,filter='data')
    (work/('fuse-libretro-'+COMMIT)).rename(tree)
    patch(tree)
    with (work/'build.log').open('w') as log:
        subprocess.run(['make','-j4'],cwd=tree,stdout=log,stderr=subprocess.STDOUT,check=True)
    romdir=work/'system/fuse';romdir.mkdir(parents=True,exist_ok=True)
    for filename in ('128p-0.rom','128p-1.rom','trdos.rom'):
        shutil.copyfile(args.roms/filename,romdir/filename)
