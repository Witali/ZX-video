"""Independent raw LZ4 parser and per-write forward-overlap proof.

Specification: https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md
Project blocks must finish at the declared output length and consume every
input byte. Native playback accepts only host-validated, bank-fitting blocks.
"""
import hashlib


def trace(data, *, limit, input_start=None, bank_bytes=16384):
    data=bytes(data);at=0;out=bytearray();minimum=0;digest=hashlib.sha256()
    memory=None;literal_runs=[];match_runs=[];match_offsets=[]
    if not 0<=limit<=bank_bytes:raise ValueError('output exceeds bank')
    if input_start is not None:
        if input_start<0 or input_start+len(data)>bank_bytes:raise ValueError('input exceeds bank')
        memory=bytearray(bank_bytes);memory[input_start:input_start+len(data)]=data
    def byte():
        nonlocal at
        if at>=len(data):raise ValueError('truncated LZ4')
        value=data[at] if memory is None else memory[input_start+at]
        if value!=data[at]:raise ValueError('overwritten input')
        at+=1;return value
    def length(base,extended):
        if extended:
            while True:
                extra=byte();base+=extra
                if base>limit:raise ValueError('oversized length')
                if extra!=255:break
        return base
    def write(value):
        nonlocal minimum
        pos=len(out)
        if pos>=limit:raise ValueError('oversized output')
        if at<len(data):
            minimum=max(minimum,pos+1-at)
            if memory is not None and input_start+at<=pos<input_start+len(data):raise ValueError('overlapping unread input')
        out.append(value);digest.update(at.to_bytes(4,'little'))
        if memory is not None:memory[pos]=value
    while True:
        token=byte();count=length(token>>4,token>>4==15);literal_runs.append(count)
        for _ in range(count):write(byte())
        if len(out)==limit:
            if at!=len(data):raise ValueError('trailing data')
            return bytes(out),dict(decoded_bytes=len(out),input_bytes=at,minimum_input_start=minimum,
                minimum_footprint=max(len(out),minimum+len(data)),write_input_cursors_sha256=digest.hexdigest(),
                shared_memory_verified=memory is not None,literal_runs=literal_runs,match_runs=match_runs,
                match_offsets=match_offsets)
        offset=byte()+256*byte()
        if not 0<offset<=len(out):raise ValueError('invalid offset')
        match_offsets.append(offset)
        count=length((token&15)+4,(token&15)==15);match_runs.append(count)
        for _ in range(count):
            pos=len(out)-offset;value=out[pos] if memory is None else memory[pos]
            if value!=out[pos]:raise ValueError('overwritten history')
            write(value)
