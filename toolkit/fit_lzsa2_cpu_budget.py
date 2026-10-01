"""Trade selected two-byte matches for literals within each original CPU budget.

Use a smaller dictionary-numbered stream as the starting point. Dropping a
short match can save token dispatch at a small byte cost. Exact suffix costs
retain nibble phase and repeat-offset effects; independent native execution
decides whether each block meets its original decoding budget.
"""
import argparse
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from convert_video import write_json
from inplace_zx0 import layout
from lzsa2_distance_cost import Costs,mode
from lzsa2_oracle import encode,literal_extra,match_extra,offset_extra
from optimize_lzsa2_distances import parse
from verify_lzsa2_dispatch import execute
import lzsa2_stream
import resumable_lzsa2


def model(matches,n,costs):
    rows=[];position=last=0
    for p,length,distance in matches:
        rows.append((p-position,length,distance,mode(distance,last)))
        position=p+length;last=distance
    rows.append((n-position,0,last,7))
    def unit(ll,length,distance,kind):
        return (2*ll+literal_extra(ll)+5 if not length else
            2+2*ll+literal_extra(ll)+match_extra(length)+(0 if kind==7 else offset_extra(distance)))
    units=[unit(*r) for r in rows];prefix_units=[0];prefix_cycles=[0]
    for r,u in zip(rows,units):
        prefix_cycles.append(prefix_cycles[-1]+costs.token(r[0],r[1],r[3],prefix_units[-1]&1))
        prefix_units.append(prefix_units[-1]+u)
    suffix=[[0,0] for _ in range(len(rows)+1)]
    for i in reversed(range(len(rows))):
        r=rows[i]
        for parity in (0,1):suffix[i][parity]=costs.token(r[0],r[1],r[3],parity)+suffix[i+1][(parity+units[i])&1]
    choices=[];old_bytes=(prefix_units[-1]+1)//2;old_cycles=prefix_cycles[-1]
    for i,r in enumerate(rows[:-1]):
        if r[1]!=2:continue
        nxt=rows[i+1];last=rows[i-1][2] if i else 0
        ll=r[0]+r[1]+nxt[0];kind=mode(nxt[2],last) if nxt[1] else 7
        u=unit(ll,nxt[1],nxt[2],kind);after=prefix_units[i]+u
        cycles=prefix_cycles[i]+costs.token(ll,nxt[1],kind,prefix_units[i]&1)+suffix[i+2][after&1]
        total=after+prefix_units[-1]-prefix_units[i+2];size=(total+1)//2
        if cycles<old_cycles:
            choices.append(dict(index=i,bytes=size,token_tstates=cycles,byte_delta=size-old_bytes,
                token_delta_tstates=cycles-old_cycles,nibbles=total))
    return choices,old_bytes,old_cycles


def fit(payload,raw,byte_budget,cpu_budget,costs,regions,z,native):
    _,rows,_=parse(payload,len(raw));matches=[(r['position'],r['length'],r['distance']) for r in rows]
    current=execute(regions,z,native,payload,raw);steps=[];original=payload
    while current['tstates']>cpu_budget:
        choices,size,ticks=model(matches,len(raw),costs);assert size==len(payload)
        allowed=[c for c in choices if c['bytes']<=byte_budget]
        if not allowed:break
        chosen=min(allowed,key=lambda c:(max(c['byte_delta'],0)/-c['token_delta_tstates'],c['bytes'],c['index']))
        matches.pop(chosen['index']);coded=encode(raw,matches)
        assert len(coded)==chosen['bytes'] and lzsa2_stream.trace(coded,limit=len(raw))[0]==raw
        _,actual_size,actual_ticks=model(matches,len(raw),costs)
        assert actual_size==len(coded) and actual_ticks==chosen['token_tstates']
        measured=execute(regions,z,native,coded,raw)
        steps.append(dict(chosen,native_before=current['tstates'],native_after=measured['tstates']))
        payload,current=coded,measured
    return payload,current,dict(steps=steps,removed_matches=len(steps),before_bytes=len(original),after_bytes=len(payload),
        cpu_budget=cpu_budget,byte_budget=byte_budget,budget_met=current['tstates']<=cpu_budget and len(payload)<=byte_budget)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('metadata','directory'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.metadata.read_bytes());report=json.loads((a.directory/'report.json').read_bytes())
    flat=report['variants']['flat'];source=a.directory/'flat';raw=(source/'video.raw').read_bytes();stream=(source/'video.stream').read_bytes()
    assert sha(a.metadata.read_bytes())==report['metadata_sha256'] and sha(stream)==flat['stream_sha256']
    costs=Costs();regions,z,native=resumable_lzsa2.build(core=m['decoder_labels']['start'],core_limit=0x8e80)
    at=out=0;result=bytearray();blocks=[];changes=[]
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4;payload=stream[at:at+size];at+=size
        data=raw[out:out+n];index=len(blocks);baseline=report['baseline_blocks'][index]
        coded,cpu,change=fit(payload,data,m['blocks'][index]['compressed_bytes'],baseline['tstates'],costs,regions,z,native)
        restored,proof=lzsa2_stream.trace(coded,limit=n);assert restored==data
        place=layout(len(coded),n,proof['minimum_input_start'],len(result));assert place['sector_aligned_fits']
        lzsa2_stream.trace(coded,limit=n,input_start=place['input_start'])
        blocks.append(dict(index=index,decoded_bytes=n,compressed_bytes=len(coded),native=cpu,
            inplace_layout=place,sha256=sha(data),codec='lzsa2',inplace_proof=proof,raw_start=out,raw_end=out+n))
        changes.append(change);result+=struct.pack('<HH',n,len(coded))+coded;out+=n
        print(index,len(coded)-size,'bytes;',cpu['tstates']-baseline['tstates'],'T vs original;',change['budget_met'],flush=True)
    assert out==len(raw)
    folder=a.directory/'budgeted';folder.mkdir(exist_ok=True)
    (folder/'video.raw').write_bytes(raw);(folder/'video.stream').write_bytes(result)
    (folder/'rows.json').write_bytes((source/'rows.json').read_bytes())
    cpu=sum(b['native']['tstates'] for b in blocks)
    row=dict(flat,bytes=len(result),sectors=(len(result)+255)//256,decoder_tstates=cpu,
        bytes_delta=len(result)-report['baseline_bytes'],decoder_delta_tstates=cpu-report['baseline_decoder_tstates'],
        stream_sha256=sha(result),blocks=blocks,changes=changes,
        every_block_within_original_byte_and_cpu_budget=all(c['budget_met'] for c in changes),
        host_candidate_eligible=len(result)<report['baseline_bytes'] and all(c['budget_met'] for c in changes))
    report['variants']['budgeted']=row;write_json(a.directory/'report.json',report)
    print({k:row[k] for k in ('bytes','sectors','bytes_delta','decoder_delta_tstates','host_candidate_eligible')})


if __name__=='__main__':main()
