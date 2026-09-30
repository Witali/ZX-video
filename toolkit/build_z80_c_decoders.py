"""Build the same standalone C decoder with three local Z80 toolchains."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from prepare_z80_c_compilers import HREV, ZREV, run

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tmp/z80-c-compilers'
BASE = ROOT / '.tmp/z80-c-probe'
SOURCE = ROOT / 'toolkit/lzma_decoder_c89.c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linux(path):
    p = path.resolve().as_posix()
    assert len(p) > 2 and p[1] == ':'
    return '/mnt/' + p[0].lower() + p[2:]


def build(name):
    folder = BASE / name
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, folder / 'decoder.c')
    env = os.environ.copy()
    if name == 'sdcc':
        binary = TOOLS / 'sdcc/bin/sdcc.exe'
        env['PATH'] = str(binary.parent) + os.pathsep + env['PATH']
        flags = ['-mz80', '--std-c89', '--opt-code-speed', '--max-allocs-per-node', '100000',
                 '--no-std-crt0', '--code-loc', '0x0200', '--data-loc', '0x9000']
        run([str(binary), *flags, 'decoder.c', '-o', 'decoder.ihx'], folder / 'build.log', cwd=folder, env=env)
        assert (folder/'decoder.ihx').stat().st_size > 100
        version = run([str(binary), '--version'], folder/'version.log', env=env).strip()
    elif name == 'hitech':
        dist = TOOLS / f'HI-TECH-Z80-C-{HREV}/dist'
        runner = TOOLS / f'ZXCC-{ZREV}/winbuild/Install/x64-Release/zxcc.exe'
        binary = dist / 'C309-21.COM'
        for key in ('BINDIR80', 'LIBDIR80', 'INCDIR80'):
            env[key] = str(dist)
        # CP/M tools can return success after printing errors: require fresh artifacts.
        for filename in ('decoder.obj', 'decoder.out', 'decoder.map'):
            (folder/filename).unlink(missing_ok=True)
        flags = ['--O', '--C', '--V']
        run([str(runner), 'C309-21.COM', *flags, 'decoder.c'], folder/'compile.log', cwd=folder, env=env)
        assert (folder/'decoder.obj').stat().st_size > 100
        shutil.copyfile(folder/'$ctmp2.$$$', folder/'decoder.asm')
        link = ['--Ptext=0200h,bss=9000h', '--C0200h', '--Odecoder.out', '--Mdecoder.map', 'decoder.obj', 'B:LIBC.LIB']
        run([str(runner), 'LINQ.COM', *link], folder/'link.log', cwd=folder, env=env)
        assert (folder/'decoder.out').stat().st_size > 100
        flags += ['; LINQ.COM', *link]
        version = 'HI-TECH C 3.09-21; maintainer revision ' + HREV
    elif name == 'z88dk':
        kit = TOOLS / 'z88dk-source/z88dk'
        binary = kit / 'bin/z88dk-zsdcc'
        flags = ['+embedded', '-clib=sdcc_ix', '-SO3', '-O3', '--opt-code-speed',
                 '--max-allocs-per-node100000', '--no-crt', '-m', '-vn', '--list']
        # Use a script to preserve argument boundaries across PowerShell, WSL and bash.
        layout = ROOT/'toolkit/z80_c_benchmark_layout.asm'
        cmd = ['zcc', *flags, linux(layout), 'decoder.c', '-o', 'decoder']
        script = folder/'build.sh'
        script.write_text('set -euo pipefail\n'
            + 'export PATH=' + shlex.quote(linux(kit/'bin')) + ':"$PATH"\n'
            + 'export ZCCCFG=' + shlex.quote(linux(kit/'lib/config')) + '\n'
            + 'cd ' + shlex.quote(linux(folder)) + '\n'
            + shlex.join(cmd) + '\n'
            + 'z88dk-zsdcc --version > version.log\n', newline='\n')
        run(['wsl', '-d', 'Ubuntu', '--', 'bash', linux(script)], folder/'build.log')
        assert (folder/'decoder.map').exists()
        version = (folder/'version.log').read_text().strip()
    else:
        raise ValueError(name)
    metadata = dict(name=name, flags=flags, version=version,
                    executable_sha256=sha(binary),
                    source_sha256_lf=hashlib.sha256(SOURCE.read_text().encode()).hexdigest())
    (folder/'build.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(name, 'built', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variants', nargs='+', choices=['sdcc', 'hitech', 'z88dk'], default=['sdcc', 'hitech', 'z88dk'])
    a = p.parse_args()
    for name in a.variants:
        build(name)


if __name__ == '__main__':
    main()
