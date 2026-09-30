"""Native token-cost model for canonical LZSA2 distance selection.

Measure actual fixed decoder code on the independent full-flags Z80 core.
Exclude ReadToken/quota/wrapper work: it is invariant when command output
positions and lengths are fixed. Full-block verification must confirm deltas.
"""
from functools import lru_cache
from z80 import Z80Machine
import resumable_lzsa2

DISTANCES=(1,2,33,257,513,769,8705,1)
LITERALS=(0,1,2,3,18,256)
MATCHES=(2,9,24,256)


def mode(d,last):
    if d==last:return 7
    if d<=32:return (((-d)&1)^1)
    if d<=512:return 2|((((-d)&256)>>8)^1)
    if d<=8704:return 4|(((-(d-512)&256)>>8)^1)
    return 6


def command(literals,n,kind,pending):
    """One model command, optionally consuming an earlier cached low nibble."""
    data=bytearray(b'\0' if pending else b'');slot=0 if pending else None
    def half(value):
        nonlocal slot
        if slot is None:slot=len(data);data.append(value<<4)
        else:data[slot]|=value;slot=None
    def length(value,base,escape):
        if value<base:return
        half(min(value-base,15))
        if value>=base+15:
            data.append(value-base-15 if value<256 else escape)
            if value>=256:data.extend(value.to_bytes(2,'little'))
    d=DISTANCES[kind]
    data.append((kind<<5)|(min(literals,3)<<3)|(min(n-2,7) if n else 7))
    length(literals,3,239);data.extend(b'A'*literals)
    if kind<2:half(((-d)&30)>>1)
    elif kind<4:data.append((-d)&255)
    elif kind<6:half(((-(d-512))>>9)&15);data.append((-(d-512))&255)
    elif kind==6:data.extend(((-d)&65535).to_bytes(2,'big'))
    if n:length(n,9,233)
    else:half(15);data.append(232)
    return bytes(data[1:] if pending else data),(data[0]&15 if pending else 0),slot is not None


class Costs:
    def __init__(self):
        self.regions,self.labels,self.native=resumable_lzsa2.build();self.rows=[]

    @lru_cache(maxsize=None)
    def measured(self,literals,n,kind,pending):
        data,cached,after=command(literals,n,kind,pending)
        m=Z80Machine();m.memory[:]=b'A'*65536
        for address,blob in self.regions:m.set_memory_block(address,blob)
        m.set_memory_block(0x1000,data)
        m.set_memory_block(self.labels['offset'],b'\xff\xff')
        stop=self.labels['ReadToken' if n else 'finished']
        m.set_breakpoint(stop);m.set_memory_block(0xbfee,stop.to_bytes(2,'little'))
        m.pc=self.labels['Token'];m.hl=0x1000;m.de=0xc000;m.bc=0;m.sp=0xbfee
        m.alt_af=(cached<<8)|(0 if pending else 1)
        budget=400000;m.ticks_to_stop=budget
        while m.pc!=stop:
            event=m.run()
            assert not event&m._TICKS_LIMIT_HIT
        assert m.hl==0x1000+len(data) and m.de==0xc000+literals+n
        assert (not bool(m.alt_af&1))==after
        ticks=budget-m.ticks_to_stop
        self.rows.append(dict(literals=literals,match=n,mode=kind,pending=pending,tstates=ticks,
            final_pending=after,input_bytes=len(data)))
        return ticks

    def token(self,literals,n,kind,pending):
        ll=next(x for x in reversed(LITERALS) if literals>=x)
        mm=next(x for x in reversed(MATCHES) if n>=x) if n else 0
        return self.measured(ll,mm,kind,bool(pending))+21*(literals-ll+n-mm)
