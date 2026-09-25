"""Cold-play three TRDs with cached Huffman, compiled masks and demand decode.

Relocate compact/cache to bank 2 and packets to bank 5. These are debugger
integration fixtures, not rebuilt release bootstraps or capacity proofs.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fuse','directory','raw-directory','states','zx0','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=('baseline','relocated'),default='relocated')
    args=p.parse_args()
    for part in (1,2,3):
        stem=f'ZX-video-huffman-preview_part{part:02}'
        meta=json.loads((args.directory/(stem+'.json')).read_bytes())
        if not meta.get('cached_huffman_byte'):raise ValueError('cached-Huffman bootstrap required')
        command=[sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
            '--fuse',str(args.fuse),'--trd',str(args.directory/(stem+'.trd')),
            '--metadata',str(args.directory/(stem+'.json')),'--raw',str(args.raw_directory/f'volume-{part}.raw'),
            '--states',str(args.states),'--output',str(args.output/f'part{part:02}.json'),'--timeout','300',
            '--slot-queue','--compiled-masks','--cached-huffman-byte','--inline-literals',
            '--demand-decode','--fixture-zx0',str(args.zx0)]
        if args.mode=='relocated':command.append('--uncontended-frame')
        subprocess.run(command,check=True)
        report=json.loads((args.output/f'part{part:02}.json').read_bytes())
        if not report['complete'] or report['errors'] or report['failure']:
            raise ValueError(('incomplete playback',part))


if __name__=='__main__':main()
