"""Compare single-byte or carry-based Huffman decoding on unchanged entropy.

Actual Z80 opcode cases cover every used symbol and all eight bit offsets.
The resulting formulas are summed over every real symbol with each volume's
tables. Reconstruction, ZX0, output, IRQ/ULA and disk latency are excluded.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark_prefix_huffman import Harness, INPUT
from build_fap3_trd import sha
from probe_motion_entropy import Reader,codes_for
from probe_spatial_contexts import read_header
from probe_volume_huffman import collect,retable
from profile_volume_huffman import costs


def verify(tables,mapping,histogram,variant):
    hs = [Harness(tables,mapping,**{variant:v}) for v in (False,True)]
    representatives = {c:mapping.index(c) for c in set(mapping)}
    cases = 0; observed = {}
    for ctx,value in np.argwhere(histogram):
        ctx,value = int(ctx),int(value)
        pair = (1,0) if ctx==len(tables)-1 else (0,representatives[ctx])
        code,length = codes_for(255,tables[ctx])[value]
        for offset in range(8):
            encoded = (code << ((-offset-length)%8)).to_bytes((offset+length+7)//8,'big')
            counts = []
            for h in hs:
                h.begin(encoded);h.cpu.write8(INPUT+len(encoded),255)
                h.cpu.write8(h.labels['bit_page'],h.bit_base+offset)
                counts.append(h.run([pair],bytes([value]))['primitive_tstates'])
            name = ('one_byte' if offset+length<=7 else 'short_fallback' if length<=8 else 'long_fallback') if variant=='single_byte' else (
                'short' if length<=8 else 'long_unaligned' if offset else 'long_aligned')
            change = counts[1]-counts[0]
            if change!={'one_byte':-50,'short_fallback':58,'long_fallback':47,'short':-8,'long_unaligned':8,'long_aligned':0}[name]:
                raise AssertionError((name,counts,ctx,value,offset))
            observed.setdefault(name,set()).add(change);cases+=1
    old,new=hs
    return old.layout,dict(paired_cases=cases,executed_symbols=2*cases,
        deltas={k:sorted(v) for k,v in observed.items()},
        baseline_primitive_bytes=old.labels['primitive_end']-0x8000,
        primitive_bytes=new.labels['primitive_end']-0x8000,
        extra_table_bytes=sum(len(b) for _,b in new.regions)-sum(len(b) for _,b in old.regions),
        new_instruction_listing=new.listing[:next(i for i,v in enumerate(new.listing) if v['address']==new.labels['primitive_end'])])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('directory','states','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--ends',default='1624,2921,4221')
    p.add_argument('--variant',choices=('single_byte','carry_huffman'),default='single_byte')
    args=p.parse_args();ends=list(map(int,args.ends.split(',')))
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if len(ends)!=3 or ends[-1]!=len(states) or ends!=sorted(set(ends)) or ends[0]<=0:
        p.error('requires a complete three-volume partition')
    source=(args.directory/'volume-1.raw').read_bytes()
    header,mapping,original,packets,hist=collect(source,states)
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='0cf64be',
        variant=args.variant,states_sha256=sha(states.tobytes()),ends=ends,full_player_verified=False,
        source_streams_changed=False,full_movie_disk_timing_verified=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',volumes=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for part,(start,end) in enumerate(zip([0]+ends,ends),1):
        raw=(args.directory/f'volume-{part}.raw').read_bytes()
        _,_,_,m,tables=read_header(Reader(raw),magic=b'FAP3')
        if m!=mapping or retable(header,mapping,original,packets,tables)[0]!=raw:
            raise AssertionError('source values or non-entropy fields changed')
        print(f'Paired opcodes, volume {part}',flush=True)
        layout,checks=verify(tables,mapping,hist,args.variant)
        old=costs(packets,tables,layout);lengths=np.array([list(t) for t in tables])
        rows=[]
        for i,packet in enumerate(packets[start:end],start):
            n=lengths[packet['contexts'],packet['values']].astype(np.int32)
            r=(np.cumsum(n)-n)%8
            fast=int(np.count_nonzero(r+n<=7));long=int(np.count_nonzero(n>8))
            short=len(n)-fast-long
            change=(-50*fast+58*short+47*long if args.variant=='single_byte'
                else -8*int(np.count_nonzero(n<=8))+8*int(np.count_nonzero((n>8)&(r!=0))))
            rows.append(dict(frame=i,values=len(n),one_byte=fast,short_fallback=short,long_fallback=long,
                baseline_tstates=old[i]['primitive_tstates'],tstates=old[i]['primitive_tstates']+change,delta_tstates=change))
        row=dict(part=part,start=start,end=end,raw_sha256=sha(raw),checks=checks,frames=rows)
        for key in ('values','one_byte','short_fallback','long_fallback','baseline_tstates','tstates','delta_tstates'):
            row[key]=sum(v[key] for v in rows)
        row['slower_frames']=sum(v['delta_tstates']>0 for v in rows)
        result['volumes'].append(row);save()
        print(json.dumps({k:v for k,v in row.items() if k not in ('frames','checks')}),flush=True)
    result.update(complete=True,decision='reject' if sum(v['delta_tstates'] for v in result['volumes'])>=0 else 'candidate_only')
    save()


if __name__=='__main__':main()
