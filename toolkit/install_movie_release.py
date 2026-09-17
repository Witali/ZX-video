"""Install a verified movie release in the repository root for Git LFS.

Only numbered ZX-video-full-50Hz_partNN.trd files are replaced/removed.
Validate every new image before copying; delete obsolete parts only after
all replacements match the package hashes. Git staging remains explicit.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

from build_full_movie import digest
from inspect_frame_cadence import require_smooth


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('release', type=Path)
    p.add_argument('--repository', type=Path, required=True)
    args = p.parse_args(); root = args.repository.resolve()
    git_root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=root, text=True).strip()).resolve()
    if root != git_root:
        raise ValueError('destination must be the Git repository root')
    report = json.loads((args.release / 'measurements.json').read_text())
    require_smooth(report['cadence'])
    names = [part['file'] for part in report['parts']]
    if len(set(names)) != len(names) or not names:
        raise ValueError('duplicate or empty release parts')
    for part in report['parts']:
        name = part['file']
        if not re.fullmatch(r'ZX-video-full-50Hz_part[0-9]{2}\.trd', name):
            raise ValueError('unexpected release filename')
        if (root / name).resolve().parent != root:
            raise ValueError('disk destination escapes repository root')
        if digest(args.release / name) != part['sha256']:
            raise ValueError(f'changed release image: {name}')
        attr = subprocess.check_output(['git', 'check-attr', 'filter', '--', name], cwd=root, text=True)
        if attr.strip() != f'{name}: filter: lfs':
            raise ValueError(f'Git LFS rule missing: {name}')
    for name in names:
        shutil.copyfile(args.release / name, root / name)
    for part in report['parts']:
        if digest(root / part['file']) != part['sha256']:
            raise ValueError('installed image differs from release')
    removed = []
    for old in root.glob('ZX-video-full-50Hz_part[0-9][0-9].trd'):
        if old.name in names:
            continue
        if old.resolve().parent != root:
            raise ValueError('obsolete disk path escapes repository root')
        old.unlink(); removed.append(old.name)
    shutil.copyfile(args.release / 'README.md', root / 'ZX-video-full-50Hz.md')
    shutil.copyfile(args.release / 'measurements.json', root / 'toolkit/full_movie_measurements.json')
    print(json.dumps(dict(installed=len(names), removed=removed), indent=2))


if __name__ == '__main__':
    main()
