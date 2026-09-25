"""Cold-play the three cached-Huffman TRDs with optional inline ZX0 literals."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fuse','directory','raw-directory','states','zx0','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=('baseline','inline'),default='inline')
    args=p.parse_args()
    for part in (1,2,3):
        stem=f'ZX-video-huffman-preview_part{part:02}'
        meta=json.loads((args.directory/(stem+'.json')).read_bytes())
        if not meta.get('cached_huffman_byte'):raise ValueError('cached-Huffman bootstrap required')
        command=[sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
            '--fuse',str(args.fuse),'--trd',str(args.directory/(stem+'.trd')),
            '--metadata',str(args.directory/(stem+'.json')),'--raw',str(args.raw_directory/f'volume-{part}.raw'),
            '--states',str(args.states),'--output',str(args.output/f'part{part:02}.json'),'--timeout','300',
            '--slot-queue','--compiled-masks','--cached-huffman-byte','--trace-pipeline','--fixture-zx0',str(args.zx0)]
        if args.mode=='inline':command.append('--inline-literals')
        subprocess.run(command,check=True)


if __name__=='__main__':main()
