"""Remove selected two-byte matches within original byte and native CPU budgets.

The retained nibble/last-offset model ranks choices; complete native replay
decides whether the budget is met. Check budget_met and retain a baseline fallback.
"""
from .distance_cost import mode
from .oracle import encode, literal_extra, match_extra, offset_extra
from .distances import parse
from . import codec as lzsa2_stream

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


def fit(payload,raw,byte_budget,cpu_budget,costs,regions,z,native,*,source=0x4000,execute=None):
    if execute is None:
        from .native import execute
    _,rows,_=parse(payload,len(raw));matches=[(r['position'],r['length'],r['distance']) for r in rows]
    current=execute(regions,z,native,payload,raw,source=source);steps=[];original=payload
    while current['tstates']>cpu_budget:
        choices,size,ticks=model(matches,len(raw),costs);assert size==len(payload)
        allowed=[c for c in choices if c['bytes']<=byte_budget]
        if not allowed:break
        chosen=min(allowed,key=lambda c:(max(c['byte_delta'],0)/-c['token_delta_tstates'],c['bytes'],c['index']))
        matches.pop(chosen['index']);coded=encode(raw,matches)
        assert len(coded)==chosen['bytes'] and lzsa2_stream.trace(coded,limit=len(raw))[0]==raw
        _,actual_size,actual_ticks=model(matches,len(raw),costs)
        assert actual_size==len(coded) and actual_ticks==chosen['token_tstates']
        measured=execute(regions,z,native,coded,raw,source=source)
        steps.append(dict(chosen,native_before=current['tstates'],native_after=measured['tstates']))
        payload,current=coded,measured
    return payload,current,dict(steps=steps,removed_matches=len(steps),before_bytes=len(original),after_bytes=len(payload),
        cpu_budget=cpu_budget,byte_budget=byte_budget,budget_met=current['tstates']<=cpu_budget and len(payload)<=byte_budget)
