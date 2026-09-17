"""Compare the full-row fast path against saved pre-change player binaries."""
import argparse
import json
from pathlib import Path

from benchmark_player_relocation import draw,fixture
from benchmark_rle_pairs import packet


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    rows={}
    def record(name,fn,expected):
        old,bt=fn(args.baseline_build);new,nt=fn(args.build)
        assert old==new,name
        assert nt-bt==expected,(name,nt,bt,expected)
        rows[name]=dict(previous_tstates=bt,current_tstates=nt,delta_tstates=nt-bt)
    for n in range(1,33):
        tail=bytes([0x80+30-n,97]) if n<31 else bytes([0,97]) if n==31 else b''
        encoded=bytes([n-1])+bytes(range(n))+tail
        payload=bytes([95,len(encoded)])+encoded
        record(f'literal_{n}',lambda b,p=payload:draw(b,'command_row_rle',p),-473 if n==32 else 34)
    for n in range(2,33):
        tail=bytes([31-n])+bytes(range(32-n)) if n<32 else b''
        encoded=bytes([0x80+n-2,197])+tail
        payload=bytes([95,len(encoded)])+encoded
        record(f'repeat_{n}',lambda b,p=payload:draw(b,'command_row_rle',p),17 if n==32 else 34)
    for count in (1,2,4,96):
        data=b''.join(bytes([5,row,33,31])+bytes(range(32)) for row in range(count))+b'\0'
        record(f'full_literal_chain_{count}',lambda b,d=data:packet(b,d),-473*count)
    report=dict(baseline='v11 AY IRQ player before full-row unrolling',
        source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='command entry to command_loop; chains include dispatch and END; excludes ROM/ULA/IRQ/disk',
        instruction_counts=dict(unrolled_pairs=16,pair_tstates=106,unrolled_body_tstates=1696,
            previous_literal_core=2209,current_literal_core=1736,full_row_delta=-473,
            other_token_probe=17,adjacent_chain_discount_unchanged=172),
        bootstrap=dict(previous=fixture(args.baseline_build)[2],current=fixture(args.build)[2]),routines=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in rows.items() if k in ('literal_32','repeat_32','full_literal_chain_96')},indent=2))


if __name__=='__main__':main()
