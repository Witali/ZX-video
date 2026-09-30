"""Exact row-index frame CPU; excludes packet transfer, ZX0, IRQ, ULA and disk."""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from benchmark_direct_motion_target import (Harness,OPTIONS,Reader,frames,install_hl_masks,
    read_header,read_packet,serialized_masks,unpack,unpack_audio,unpack_bulk,unpack_cache,sha)
from profile_frame_hotspots import instrument
import cached_huffman_lookahead as lookahead
import compact_cursor
import inline_huffman_patches as inline
import uncontended_frame as relocation
from row_dictionary_video import reference_tables


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw','states','metadata','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); raw=a.raw.read_bytes(); m=json.loads(a.metadata.read_text())
    with np.load(a.states,allow_pickle=False) as saved:states=saved['states']
    cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets=frames(cells); masks=serialized_masks(cells)
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3')
    details=[read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
    if count!=len(states):raise ValueError('state count differs')
    h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,
        register_fragments=True,cached_huffman_byte=True,metadata_mode='compiled',**OPTIONS)
    install_hl_masks(h);c=h.cpu;c.guarding=False
    relocation.install_stage(h);lookahead.install_frame(h)
    generated=inline.install_stage(h,tables,mapping);compact_cursor.install_stage(h)
    data=bytes.fromhex(m['row_dictionary']['tables_hex'])
    for i,v in enumerate(data):c.write8(0x9e00+i,v)
    hist,stages,_,_=instrument(h,generated);rows=[];previous=Counter()
    with reference_tables(m['row_dictionary']):
        for index,(group,native) in enumerate(packets):
            actual=relocation.run_stage(h,group,native,states[index].tobytes(),index,masks[index],details[index]['cache'])
            delta=stages-previous;previous=stages.copy()
            if sum(delta.values())!=actual['total_tstates']:raise AssertionError('instruction sum differs')
            rows.append(dict(frame=index,tstates=actual['total_tstates'],stages=dict(delta)))
    report=dict(complete=True,release=False,scope=__doc__,frames=rows,tstates=sum(r['tstates'] for r in rows),
        stages=dict(stages),raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),full_compact_and_both_native_exact=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(frames=len(rows),tstates=report['tstates'],stages=dict(stages))))


if __name__=='__main__':main()
