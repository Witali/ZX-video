"""Rebuild all debugger patches and compare with saved baseline/new Fuse input."""
import argparse
import json
from pathlib import Path
from slot_queue_player import build


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','raw-directory'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=Path('toolkit/combined_uncontended_evidence'))
    p.add_argument('--baseline',type=Path,default=Path('toolkit/demand_decode_evidence'))
    args=p.parse_args()
    for part in (1,2,3):
        stem=f'ZX-video-huffman-preview_part{part:02}'
        m=json.loads((args.directory/(stem+'.json')).read_bytes())
        raw=(args.raw_directory/f'volume-{part}.raw').read_bytes()
        for moved,folder in ((False,args.baseline),(True,args.evidence)):
            patches,meta=build(m,raw,uncontended=moved,compiled_masks=True,
                cached_huffman_byte=True,inline_literals=True,demand_decode=True)
            measured=json.loads((folder/f'part{part:02}.json').read_bytes())
            if [list(v) for v in patches]!=measured['slot_queue_fixture']['slot_queue_patches']:
                raise AssertionError(('fixture bytes changed',part,moved))
            if moved and meta['uncontended_frame']!=measured['uncontended_frame']:
                raise AssertionError(('relocation audit changed',part))
        print(f'Part {part}: relocated fixture exact; baseline bytes unchanged',flush=True)


if __name__=='__main__':main()
