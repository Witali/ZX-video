"""Exact minimum-size standard raw LZSA2 parse for bounded short inputs.

Costs are in nibbles, including a repeat-offset EOD as emitted by upstream.
States retain last offset and literal-run length (saturated after 256).
Matching is exhaustive, including overlap, and no beam/pruning limit applies.
This is an analysis oracle, not a whole-video compressor.
"""


def literal_extra(n):
    return 0 if n<3 else 1 if n<18 else 3 if n<256 else 7


def match_extra(n):
    return 0 if n<9 else 1 if n<24 else 3 if n<256 else 7


def offset_extra(d):
    return 1 if d<=32 else 2 if d<=512 else 3 if d<=8704 else 4


def encode(raw,matches):
    """Serialize (position,length,distance) matches with canonical LZSA2 codes."""
    raw=bytes(raw);data=bytearray();pending=None;position=0;last=0
    def half(value):
        nonlocal pending
        if pending is None:pending=len(data);data.append(value<<4)
        else:data[pending]|=value;pending=None
    def length(n,base,escape):
        if n<base:return
        half(min(n-base,15))
        if n>=base+15:
            data.append(n-base-15 if n<256 else escape)
            if n>=256:data.extend(n.to_bytes(2,'little'))
    def literals(start,end):
        length(end-start,3,239);data.extend(raw[start:end])
    for start,n,d in matches:
        if not position<=start or not 2<=n<=65535 or start+n>len(raw) or not 1<=d<=min(start,65535):
            raise ValueError('invalid match extent')
        if any(raw[start+i]!=raw[start+i-d] for i in range(n)):raise ValueError('invalid match data')
        if d==last:mode=0xe0
        elif d<=32:mode=(((-d)&1)<<5)^0x20
        elif d<=512:mode=0x40|((((-d)&256)>>3)^0x20)
        elif d<=8704:mode=0x80|(((-(d-512)&256)>>3)^0x20)
        else:mode=0xc0
        data.append(mode|(min(start-position,3)<<3)|min(n-2,7));literals(position,start)
        if mode<0x40:half(((-d)&30)>>1)
        elif mode<0x80:data.append((-d)&255)
        elif mode<0xc0:half(((-(d-512))>>9)&15);data.append((-(d-512))&255)
        elif mode==0xc0:data.extend(((-d)&65535).to_bytes(2,'big'))
        length(n,9,233);position=start+n;last=d
    data.append(0xe7|(min(len(raw)-position,3)<<3));literals(position,len(raw))
    half(15);data.append(232)
    return bytes(data)


def all_matches(raw):
    raw=bytes(raw);n=len(raw);result=[]
    for p in range(n):
        row=[]
        for d in range(1,min(p,65535)+1):
            k=0
            while p+k<n and k<65535 and raw[p+k]==raw[p+k-d]:k+=1
            if k>=2:row.append((d,k))
        result.append(row)
    return result


def optimal(raw,*,max_bytes=256):
    raw=bytes(raw);n=len(raw)
    if n>min(max_bytes,65535):raise ValueError('oracle input exceeds explicit bound')
    candidates=all_matches(raw);states=[{} for _ in range(n+1)]
    # Value: nibble cost, match-command count, linked match path.
    states[0][0,0]=(0,0,None);visited=0;transitions=0
    for p in range(n):
        current=states[p];visited+=len(current);by_offset={}
        for (last,lit),value in current.items():
            old=by_offset.get(last)
            if old is None or value[:2]<old[:2]:by_offset[last]=value
            nxt=min(lit+1,256);cost=value[0]+2+literal_extra(nxt)-literal_extra(lit)
            key=(last,nxt);dest=states[p+1].get(key);transitions+=1
            if dest is None or (cost,value[1])<dest[:2]:states[p+1][key]=(cost,value[1],value[2])
        best=min(current.values(),key=lambda v:v[:2])
        for d,longest in candidates[p]:
            source=best;cost=best[0]+offset_extra(d)
            repeat=by_offset.get(d)
            if repeat is not None and (repeat[0],repeat[1])<(cost,best[1]):
                source=repeat;cost=repeat[0]
            count=source[1]+1
            for length in range(2,longest+1):
                total=cost+2+match_extra(length);key=(d,0);dest=states[p+length].get(key);transitions+=1
                if dest is None or (total,count)<dest[:2]:
                    states[p+length][key]=(total,count,(p,length,d,source[2]))
    best=min(states[n].values(),key=lambda v:v[:2]);path=best[2];matches=[]
    while path is not None:matches.append(path[:3]);path=path[3]
    matches.reverse();payload=encode(raw,matches);nibbles=best[0]+5
    if len(payload)!=(nibbles+1)//2:raise AssertionError('cost and serializer disagree')
    return payload,dict(exact=True,canonical_nibbles=nibbles,bytes=len(payload),matches=matches,
        states=visited+len(states[n]),transitions=transitions,
        scope='Minimum byte length for independently reset raw input, using canonical shortest offsets/lengths and upstream repeat-offset EOD; tie-breaking does not minimize Z80 cycles.')
