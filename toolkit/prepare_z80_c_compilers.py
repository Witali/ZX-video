"""Fetch pinned C toolchains locally. Never change antivirus settings.

Windows: SDCC + HI-TECH C via a locally built ZXCC.
Optional z88dk source build: existing Ubuntu/WSL with build dependencies.
The prebuilt z88dk Windows archive is deliberately not downloaded: Defender
quarantined that release during the initial experiment (see the assessment).
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

HREV = 'c7e943fb01855213a20e15dba9535be7d178d086'
ZREV = 'c45e5065eca63dd045d60511a8b21ab7f567303a'
ASSETS = {
 'sdcc-4.6.0-x64-setup.exe': (
  'https://downloads.sourceforge.net/project/sdcc/sdcc-win64/4.6.0/sdcc-4.6.0-x64-setup.exe',
  '0a165e155a052fcf7c29ea703ee77d5a8eb578eba58279e79e885618dc4b2e1a'),
 'hitech.zip': (f'https://codeload.github.com/agn453/HI-TECH-Z80-C/zip/{HREV}',
  '269b6e01fcb996eaece63b42c041cc76576d2c19055004a0ea335ec617b1cccd'),
 'zxcc.zip': (f'https://codeload.github.com/agn453/ZXCC/zip/{ZREV}',
  '2580273418813f4436c425fa80dbaa3592d79f0dd4e3791f72a56a1586e6ef59'),
 'z88dk-src-2.4.tgz': ('https://github.com/z88dk/z88dk/releases/download/v2.4/z88dk-src-2.4.tgz',
  '96a57a01d44ff1d65d84e38b04aebb0a4e10eccb4845cb71f5a26f10abe7c5ac'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(root, name):
    url, digest = ASSETS[name]
    path = root/name
    if path.exists() and sha(path) == digest:
        return
    for _ in range(3):
        data = urllib.request.urlopen(url,timeout=60).read()
        if hashlib.sha256(data).hexdigest() == digest:
            path.write_bytes(data)
            return
        # SourceForge can send its download landing page with an HTTP 200.
        match = re.search(r'content="5; url=([^"]+)',data.decode('utf-8',errors='ignore'))
        if not match:
            raise RuntimeError(f'Unexpected download contents: {name}')
        url = html.unescape(match[1])
        assert url.startswith('https://downloads.sourceforge.net/')
    raise RuntimeError(f'Hash verification failed: {name}')


def run(command, log, **kwargs):
    r = subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',**kwargs)
    log.write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:
        raise RuntimeError(f'{command[0]} failed; see {log}')
    return r.stdout


def bios(zxcc_root, root):
    lines=[]
    for line in (zxcc_root/'Z80/bios.zsm').read_text().splitlines():
        line=re.sub(r'\b([0-9][0-9a-fA-F]*)[hH]\b',r'0x\1',line)
        line=line.replace("'ZXCC04'",'90,88,67,67,48,52')
        m=re.match(r'\s*org\s+(\S+)',line,re.I)
        if m and int(m[1],16)!=0xfe00:
            line='        defs '+m[1]+'-$'
        if re.fullmatch(r'\s*END\s*',line,re.I):
            continue
        lines.append(line)
    src=root/'bios.asm'
    src.write_text('\n'.join(lines)+'\n')
    output=zxcc_root/'winbuild/Install/x64-Release/bios.bin'
    run([sys.executable,'-m','pyz80.pyz80','--obj='+str(output),str(src)],root/'bios-build.log')
    raw=output.read_bytes()
    assert raw[:6]==b'ZXCC04' and raw[256]==0xc3 and len(raw)<=512


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('.tmp/z80-c-compilers'))
    p.add_argument('--sevenzip',default='C:/Program Files/7-Zip/7z.exe')
    p.add_argument('--msbuild',default='C:/Program Files/Microsoft Visual Studio/18/Community/MSBuild/Current/Bin/MSBuild.exe')
    p.add_argument('--z88dk-source',action='store_true')
    a=p.parse_args(); root=a.output.resolve();root.mkdir(parents=True,exist_ok=True)
    for name in ('sdcc-4.6.0-x64-setup.exe','hitech.zip','zxcc.zip'):
        fetch(root,name)
    if not (root/'sdcc/bin/sdcc.exe').exists():
        run([a.sevenzip,'x',str(root/'sdcc-4.6.0-x64-setup.exe'),'-o'+str(root/'sdcc'),'-y'],root/'sdcc-extract.log')
    # NSIS normally applies this destination filename during installation.
    shutil.copyfile(root/'sdcc/bin/cc1',root/'sdcc/bin/cc1.exe')
    for name,folder in [('hitech.zip',f'HI-TECH-Z80-C-{HREV}'),('zxcc.zip',f'ZXCC-{ZREV}')]:
        if not (root/folder).exists():
            with zipfile.ZipFile(root/name) as z:
                assert all((root/f).resolve().is_relative_to(root) for f in z.namelist())
                z.extractall(root)
    zx=root/f'ZXCC-{ZREV}'; config=zx/'winbuild/install.cfg'
    if config.exists():
        config.rename(config.with_suffix('.cfg.disabled'))
    run([a.msbuild,str(zx/'winbuild/wzxcc.sln'),'/p:Configuration=Release','/p:Platform=x64',
         '/p:PlatformToolset=v145','/p:WindowsTargetPlatformVersion=10.0','/verbosity:quiet','/nologo'],
        root/'zxcc-build.log')
    shutil.copyfile(zx/'winbuild/external/x64-Release/pdcurses.dll',
                    zx/'winbuild/Install/x64-Release/pdcurses.dll')
    bios(zx,root)
    if a.z88dk_source:
        fetch(root,'z88dk-src-2.4.tgz')
        # Source compilation commands and prerequisites are in the companion shell script.
        print('z88dk source verified; run toolkit/build_z88dk_wsl.sh in Ubuntu/WSL')
    manifest=dict(assets={n:dict(url=u,sha256=h) for n,(u,h) in ASSETS.items()},
                  hitech_revision=HREV,zxcc_revision=ZREV,
                  zxcc_executable_sha256=sha(zx/'winbuild/Install/x64-Release/zxcc.exe'),
                  bios_sha256=sha(zx/'winbuild/Install/x64-Release/bios.bin'))
    (root/'toolchains.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('SDCC and HI-TECH toolchains prepared locally')


if __name__=='__main__':
    main()
