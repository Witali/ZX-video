"""Summarize packet-byte changes and unchanged fast-fragment instruction costs.

Costs use causal_tile_z80's previously verified instruction-table formula.
They are ONLY the paired whole-fragment subroutines, excluding the caller,
Huffman, cache, metadata, output, ZX0, IRQ/ULA, ROM and physical disk.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from bulk_frame_stream import read_packet
from causal_tile_z80 import fast_tstates
from probe_fast_fragments import SIZES
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


def inspect(data):
    r=Reader(data);_,_,count,_,_=read_header(r,magic=b'FAP3')
    sizes=Counter(header=r.pos);frames=[]
    for _ in range(count):
        _,d=read_packet(r,stored_guards=False);ay=sum(map(len,d['ticks']));base=ay+8
        vectors=d['payload'][base:base+192];literal=d['payload'][d['literal_offset']:];pos=0;costs=[]
        for v in vectors:
            if v in SIZES:
                payload=literal[pos:pos+SIZES[v]];pos+=SIZES[v]
                costs.append(fast_tstates(v,selector=payload[4] if v==87 else 0,split_literals=True))
            else:costs.append(None)
        attrs=768 if d['flags']&64 else 0
        assert pos+attrs==len(literal)
        sizes.update(ay=ay,packet_headers=7,cache=3,vectors=192,masks=d['mask_bytes'],
            native_map=80,coded=d['coded_bytes'],bitmap_literals=pos,raw_attributes=attrs)
        frames.append(costs)
    r.end();assert sum(sizes.values())==len(data)
    return dict(sizes),frames


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','candidate','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();source=args.source.read_bytes();candidate=args.candidate.read_bytes()
    old,old_frames=inspect(source);new,new_frames=inspect(candidate)
    assert len(old_frames)==len(new_frames)
    pairs=[(a,b) for aa,bb in zip(old_frames,new_frames) for a,b in zip(aa,bb) if a is not None and b is not None]
    report=dict(complete=True,release=False,scope=__doc__,source_sha256=sha(source),candidate_sha256=sha(candidate),
        baseline_bytes=old,candidate_bytes=new,byte_deltas={k:new[k]-v for k,v in old.items()},
        common_fast_tiles=len(pairs),previous_fast_body_tstates=sum(a for a,b in pairs),
        candidate_fast_body_tstates=sum(b for a,b in pairs),delta_common_fast_body_tstates=sum(b-a for a,b in pairs),
        player_machine_code_changed=False,player_instruction_delta_tstates=0,
        whole_player_timing_measured=False,new_ram_bytes=0,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
