"""Inspect real packet command costs without ROM, IRQ, ULA or decompression."""
import argparse
from collections import Counter
import json
from pathlib import Path

from benchmark_rle_pairs import packet as measure_packet
import build_fast_sparse_trd as codec
import packed_stream


def records(packet):
    result=[r for i,s in enumerate(packet.sectors) for r in packed_stream.sector_records(s,i==0)]
    return sorted(result,key=lambda r:256 if r[0] in (2,4) else r[1])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-build',type=Path,required=True)
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--frames',type=int,nargs='+',default=[623,624,630])
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    states,audio,_=codec.decode_compact_build(args.source_build/'VIDEO_full.C.bin')
    _,packets=codec.make_volume_packets(states,audio,0,0x100000,packed=True)
    full_rows=other_tokens=0;selected=[]
    for i,frame in enumerate(packets):
        rs=records(frame)
        for r in rs:
            if r[0]!=5:continue
            if r[3]==31:full_rows+=1;continue
            pos=3
            while pos<len(r):
                token=r[pos];pos+=1;other_tokens+=1
                pos+=1 if token&128 else token+1
        if i in args.frames:
            data=b''.join(rs)+b'\0'
            before,bt=measure_packet(args.baseline_build,data);after,at=measure_packet(args.build,data)
            assert before==after
            selected.append(dict(frame=i,commands=dict(Counter(r[0] for r in rs)),bytes=len(data),
                mask_changed_counts=[int.from_bytes(r[2:6],'big').bit_count() for r in rs if r[0]==1],
                zero_mask_groups=sum(r[2:6].count(0) for r in rs if r[0]==1),
                previous_drawing_tstates=bt,current_drawing_tstates=at,delta_tstates=at-bt))
    report=dict(frames=selected,full_literal_rows=full_rows,other_rle_tokens=other_tokens,
                predicted_full_row_unrolling_total_delta_tstates=-473*full_rows+17*other_tokens,
                scope='1000-frame unsplit encoding; drawing only, unchanged fake screen contents for timing')
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
