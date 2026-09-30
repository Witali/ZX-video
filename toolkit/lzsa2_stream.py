"""LZSA2 raw-block reference and forward overlap proof.

Implements the pinned BlockFormat_LZSA2 specification by Emmanuel Marty.
This independent host parser verifies each native output write/input cursor.
"""
import hashlib


def trace(data,*,limit,input_start=None,bank_bytes=16384):
    data=bytes(data);at=0;nibble=None;last=None;out=bytearray();minimum=0;digest=hashlib.sha256()
    mem=None
    if input_start is not None:
        if input_start<0 or input_start+len(data)>bank_bytes or limit>bank_bytes:raise ValueError('block exceeds bank')
        mem=bytearray(bank_bytes);mem[input_start:input_start+len(data)]=data
    def byte():
        nonlocal at
        if at>=len(data):raise ValueError('truncated LZSA2')
        value=data[at] if mem is None else mem[input_start+at]
        if value!=data[at]:raise ValueError('overwritten LZSA2 input')
        at+=1;return value
    def half():
        nonlocal nibble
        if nibble is not None:
            value=nibble;nibble=None;return value
        value=byte();nibble=value&15;return value>>4
    def length(value,base):
        if value!=base:return value
        value+=half()
        if value!=base+15:return value
        extra=byte();value+=extra
        if value<256:return value
        if value==256:
            if base!=9:raise ValueError('invalid literal EOD')
            return 0
        if value!=257:raise ValueError('invalid extended length')
        return byte()+256*byte()
    def write(value):
        nonlocal minimum
        pos=len(out)
        if pos>=limit:raise ValueError('oversized output')
        if at<len(data):
            minimum=max(minimum,pos+1-at)
            if mem is not None and input_start+at<=pos<input_start+len(data):raise ValueError('overlapping unread input')
        digest.update(at.to_bytes(4,'little'));out.append(value)
        if mem is not None:mem[pos]=value
    while True:
        token=byte();literals=length((token>>3)&3,3)
        for _ in range(literals):write(byte())
        mode=token>>5
        if mode<2:offset=(0xffe0|(half()<<1)|(1-mode))-65536
        elif mode<4:offset=(0xfe00|((1-(mode&1))<<8)|byte())-65536
        elif mode<6:offset=(0xe000|(half()<<9)|((1-(mode&1))<<8)|byte())-65536-512
        elif mode==6:offset=(byte()<<8|byte())-65536
        else:offset=last
        last=offset;count=length((token&7)+2,9)
        if not count:
            if at!=len(data) or len(out)!=limit:raise ValueError('incomplete LZSA2 block')
            return bytes(out),dict(decoded_bytes=len(out),input_bytes=at,minimum_input_start=minimum,
                minimum_footprint=max(len(out),minimum+len(data)),write_input_cursors_sha256=digest.hexdigest(),
                shared_memory_verified=mem is not None)
        if offset is None or offset>=0 or len(out)+offset<0:raise ValueError('invalid offset')
        for _ in range(count):
            source=len(out)+offset;value=out[source] if mem is None else mem[source]
            if value!=out[source]:raise ValueError('overwritten LZSA2 history')
            write(value)
