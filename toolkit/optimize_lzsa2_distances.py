"""Optimize canonical match distances on a complete, fixed-command LZSA2 block.

Retain literal/match positions and lengths. Minimize modeled native cycles
under the original byte budget, with exact last-offset and nibble state.
The suffix size bound and forward DP do not use a beam or candidate limit.
"""
import argparse,json,struct,time
from collections import defaultdict
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save
from lzsa2_distance_cost import Costs,mode
from lzsa2_oracle import encode,literal_extra,match_extra,offset_extra
import lzsa2_stream


def parse(payload,n):
    raw,_=lzsa2_stream.trace(payload,limit=n)
    at=position=0;pending=None;last=0;rows=[]
    def byte():
        nonlocal at
        value=payload[at];at+=1;return value
    def half():
        nonlocal pending
        if pending is not None:v=pending;pending=None;return v
        v=byte();pending=v&15;return v>>4
    def length(value,base):
        if value!=base:return value
        value+=half()
        if value!=base+15:return value
        value+=byte()
        if value<256:return value
        if value==256:return 0
        return byte()+256*byte()
    while True:
        phase=pending is not None;token=byte();ll=length((token>>3)&3,3)
        for _ in range(ll):byte()
        position+=ll;kind=token>>5
        if kind<2:d=65536-(0xffe0|(half()<<1)|(1-kind))
        elif kind<4:d=65536-(0xfe00|((1-(kind&1))<<8)|byte())
        elif kind<6:d=65536-(0xe000|(half()<<9)|((1-(kind&1))<<8)|byte())+512
        elif kind==6:d=65536-((byte()<<8)|byte())
        else:d=last
        count=length((token&7)+2,9)
        if not count:
            assert at==len(payload) and position==n
            break
        rows.append(dict(position=position,length=count,distance=d,literals=ll,mode=kind,pending=phase))
        position+=count;last=d
    assert encode(raw,[(r['position'],r['length'],r['distance']) for r in rows])==payload,'noncanonical baseline'
    return raw,rows,ll


def candidates(raw,p,n):
    needle=raw[p:p+n];q=raw.find(needle,0,p+n-1);result=[]
    while 0<=q<p:
        result.append(p-q);q=raw.find(needle,q+1,p+n-1)
    return sorted(result)


def body_units(row):
    return 2+2*row['literals']+literal_extra(row['literals'])+match_extra(row['length'])


def evaluate(rows,distances,tail,costs):
    assert len(rows)==len(distances)
    units=cycles=last=0
    for row,d in zip(rows,distances):
        kind=mode(d,last)
        cycles+=costs.token(row['literals'],row['length'],kind,units&1)
        units+=body_units(row)+(offset_extra(d) if d!=last else 0);last=d
    cycles+=costs.token(tail,0,7,units&1)
    units+=2*tail+literal_extra(tail)+5
    return units,cycles


def optimize(payload,n,costs):
    if not 0<=n<=15872:raise ValueError('input exceeds the native independent-block limit')
    start=time.perf_counter();raw,rows,tail=parse(payload,n)
    choices=[candidates(raw,r['position'],r['length']) for r in rows]
    assert all(r['distance'] in c for r,c in zip(rows,choices))
    budget=2*len(payload);suffix=[None]*(len(rows)+1)
    suffix[-1]=(2*tail+literal_extra(tail)+5,{})
    def lookup(item,d):return item[1].get(d,item[0])
    for i in range(len(rows)-1,-1,-1):
        future={d:lookup(suffix[i+1],d) for d in choices[i]};base=body_units(rows[i])
        common=base+min(offset_extra(d)+v for d,v in future.items())
        suffix[i]=(common,{d:base+v for d,v in future.items() if base+v<common})
    # (previous distance, total nibble cost): (token T-states, linked path)
    states={(0,0):(0,None)};peak=1;transitions=0
    for i,(row,ds) in enumerate(zip(rows,choices)):
        top=defaultdict(list);by_distance=defaultdict(list)
        for (last,used),value in states.items():
            top[used].append((value[0],last,value[1]));by_distance[last].append((used,value))
        top={used:sorted(values,key=lambda v:(v[0],v[1]))[:2] for used,values in top.items()}
        new={};base=body_units(row)
        def offer(d,used,ticks,path):
            nonlocal transitions
            transitions+=1
            if used+lookup(suffix[i+1],d)>budget:return
            key=(d,used);prior=new.get(key)
            if prior is None or ticks<prior[0]:new[key]=(ticks,(d,path))
        for d in ds:
            extra=offset_extra(d);kind=mode(d,0)
            for used,values in top.items():
                v=values[0] if values[0][1]!=d else values[1] if len(values)>1 else None
                if v is not None:
                    ticks=v[0]+costs.token(row['literals'],row['length'],kind,used&1)
                    offer(d,used+base+extra,ticks,v[2])
            for used,(ticks,path) in by_distance.get(d,[]):
                offer(d,used+base,ticks+costs.token(row['literals'],row['length'],7,used&1),path)
        if not new:raise AssertionError(('baseline path lost',i))
        states=new;peak=max(peak,len(states))
    final_units=2*tail+literal_extra(tail)+5
    used,value=min(((used,v) for (_,used),v in states.items() if used+final_units<=budget),
        key=lambda pair:(pair[1][0]+costs.token(tail,0,7,pair[0]&1),pair[0]))
    chosen=[];path=value[1]
    while path is not None:d,path=path;chosen.append(d)
    chosen.reverse();assert len(chosen)==len(rows)
    result=encode(raw,[(r['position'],r['length'],d) for r,d in zip(rows,chosen)])
    old_units,old_t=evaluate(rows,[r['distance'] for r in rows],tail,costs)
    new_units,new_t=evaluate(rows,chosen,tail,costs)
    assert (new_units+1)//2==len(result)<=len(payload)
    assert old_t>=new_t and old_units<=budget
    assert lzsa2_stream.trace(result,limit=n)[0]==raw
    return result,dict(complete=True,release=False,commands=len(rows),candidate_distances=sum(map(len,choices)),
        max_distances=max(map(len,choices),default=0),peak_states=peak,transitions=transitions,
        baseline_bytes=len(payload),candidate_bytes=len(result),baseline_nibbles=old_units,candidate_nibbles=new_units,
        minimum_nibbles=lookup(suffix[0],0),baseline_token_tstates=old_t,candidate_token_tstates=new_t,
        modeled_delta_tstates=new_t-old_t,changed_distances=sum(r['distance']!=d for r,d in zip(rows,chosen)),
        raw_sha256=sha(raw),baseline_sha256=sha(payload),candidate_sha256=sha(result),
        seconds=time.perf_counter()-start,rows=[dict(r,candidate_distance=d) for r,d in zip(rows,chosen)],
        scope='Fixed command positions and lengths; canonical offsets only; modeled token CPU optimum under original physical byte budget. Excludes invariant quota/wrapper costs and real IRQ/ULA/disk effects.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('stream','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--block',type=int,default=11)
    a=p.parse_args();stream=a.stream.read_bytes();at=0;blocks=[];raw=bytearray()
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4;payload=stream[at:at+size];at+=size
        blocks.append((n,payload));raw.extend(lzsa2_stream.trace(payload,limit=n)[0])
    n,payload=blocks[a.block];costs=Costs();result,report=optimize(payload,n,costs)
    candidate=bytearray()
    for i,(size,data) in enumerate(blocks):
        if i==a.block:data=result
        candidate+=struct.pack('<HH',size,len(data))+data
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'video.stream').write_bytes(candidate);(a.output/'video.raw').write_bytes(raw)
    report.update(block=a.block,native_cost_model=costs.rows,native=costs.native,
        baseline_stream_sha256=sha(stream),candidate_stream_sha256=sha(candidate))
    save(a.output/'probe.json',report)
    print(json.dumps({k:report[k] for k in ('commands','candidate_distances','peak_states','baseline_bytes',
        'candidate_bytes','modeled_delta_tstates','changed_distances','seconds')}),flush=True)


if __name__=='__main__':main()
