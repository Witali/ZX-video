"""Measure the cached Huffman byte on independent cold-boot TRDs in Fuse."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('fuse', 'directory', 'raw-directory', 'states', 'zx0', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--mode', choices=('baseline', 'cached'), default='cached')
    p.add_argument('--parts', default='1,2,3')
    args = p.parse_args()
    for part in map(int, args.parts.split(',')):
        if part not in (1,2,3):
            raise ValueError('requires parts of the current three-volume experiment')
        stem = f'ZX-video-huffman-preview_part{part:02}'
        metadata = json.loads((args.directory/(stem+'.json')).read_bytes())
        if bool(metadata.get('cached_huffman_byte')) != (args.mode == 'cached'):
            raise ValueError('mode differs from the decoder in the real bootstrap')
        command = [sys.executable, str(Path(__file__).with_name('measure_fap3_fuse.py')),
            '--fuse', str(args.fuse), '--trd', str(args.directory/(stem+'.trd')),
            '--metadata', str(args.directory/(stem+'.json')),
            '--raw', str(args.raw_directory/f'volume-{part}.raw'), '--states', str(args.states),
            '--output', str(args.output/f'part{part:02}.json'), '--timeout', '300',
            '--slot-queue', '--compiled-masks', '--trace-pipeline', '--fixture-zx0', str(args.zx0)]
        if args.mode == 'cached':
            command.append('--cached-huffman-byte')
        subprocess.run(command, check=True)


if __name__ == '__main__':
    main()
