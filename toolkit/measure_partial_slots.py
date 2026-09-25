"""Run three independent full disks sequentially, retaining queue wait traces."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('fuse', 'directory', 'raw_directory', 'states', 'zx0', 'output'):
        parser.add_argument('--'+name.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--mode', choices=('baseline', 'partial'), required=True)
    parser.add_argument('--parts', default='1,2,3')
    args = parser.parse_args()
    for part in map(int, args.parts.split(',')):
        if part not in (1, 2, 3):
            raise ValueError('part outside this three-disk experiment')
        stem = f'ZX-video-huffman-preview_part{part:02}'
        command = [sys.executable, str(Path(__file__).with_name('measure_fap3_fuse.py')),
            '--fuse', str(args.fuse), '--trd', str(args.directory/(stem+'.trd')),
            '--metadata', str(args.directory/(stem+'.json')),
            '--raw', str(args.raw_directory/f'volume-{part}.raw'), '--states', str(args.states),
            '--output', str(args.output/f'part{part:02}.json'), '--timeout', '300',
            '--slot-queue', '--compiled-masks', '--trace-pipeline', '--fixture-zx0', str(args.zx0)]
        if args.mode == 'partial':
            command.append('--partial-slots')
        subprocess.run(command, check=True)


if __name__ == '__main__':
    main()
