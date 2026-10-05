"""Copy the completed bounded study into a byte-authenticated evidence set."""
import argparse
import gzip
from pathlib import Path
import shutil

from g726.codec import save, sha


def archive(source, destination, smoke, preliminary):
    destination.mkdir(parents=True, exist_ok=True)

    def copy(origin, relative):
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix=='.gz':
            target.write_bytes(gzip.compress(origin.read_bytes(), mtime=0))
        else:
            shutil.copy2(origin, target)

    for name in ('summary.json', 'host-checks.json', 'native-full.json', 'native-edge-cases.json'):
        copy(source/name, name)
    for name in ('report.json', 'source-preview.wav', 'decoded-preview.wav', 'soundtrack.g726'):
        copy(source/'audition'/name, Path('audition')/name)
    for opt in range(4):
        base = Path(f'opt{opt}')
        copy(source/base/'speech-prefix.json', base/'speech-prefix.json')
        for name in ('build.json', 'build.log', 'kernel.c', 'small_tables.inc', 'inverse_tables.inc'):
            copy(source/base/'host'/name, base/'host'/name)
        for name in ('build.json', 'build.log', 'decoder.c', 'decoder.ihx', 'decoder.map',
                     'decoder.asm', 'decoder.lst', 'small_tables.inc', 'inverse_tables.inc'):
            relative = base/'z80'/name
            copy(source/relative, str(relative)+'.gz' if name.endswith(('.asm', '.lst')) else relative)
    copy(smoke/'report.json', 'cli-smoke.json')
    if preliminary:
        for opt in range(4):
            copy(preliminary/f'z80-{opt}/smoke.json', f'preliminary/random-opt{opt}.json')
        for name in ('decoder.c', 'decoder.ihx', 'decoder.map', 'build.json', 'decoder.asm'):
            copy(preliminary/'z80-3'/name, 'preliminary/lookup-only/'+name+('.gz' if name.endswith('.asm') else ''))
        copy(preliminary/'z80-3-final/smoke.json', 'preliminary/random-opt3-signs.json')
    # Preserve the scripts actually used to check this archive, including the
    # independently maintained opcode timing table and generated-comment logic.
    here = Path(__file__).resolve().parent
    for name in ('core.c', 'codec.py', 'study.py', 'verify_z80.py', 'test_cli.py', 'archive.py'):
        copy(here/name, Path('scripts/g726')/name)
    copy(here.parent/'convert_g726_audio.py', 'scripts/convert_g726_audio.py')
    for name in ('benchmark_z80_c_compilers.py', 'benchmark_lzma_z80.py'):
        copy(here.parents[1]/'toolkit'/name, Path('scripts/toolkit')/name)
    files = {path.relative_to(destination).as_posix(): sha(path)
             for path in sorted(destination.rglob('*')) if path.is_file() and path.name!='manifest.json'}
    save(destination/'manifest.json', dict(algorithm='sha256', files=files))
    assert all(sha(destination/name)==digest for name, digest in files.items())
    return len(files)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--smoke', type=Path, required=True)
    parser.add_argument('--preliminary', type=Path)
    args = parser.parse_args()
    print(f'Archived and verified {archive(args.source, args.destination, args.smoke, args.preliminary)} files')
