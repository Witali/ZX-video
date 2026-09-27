"""AYH1: independently initialized lossless 50-Hz records, offline codec.

Header: magic, tick_count:u32, coded_bits:u32, initial AY registers[11],
then 13 sparse canonical tables (u16 count; symbol:u8/length:u8 pairs).
Two contexts encode the low/high register mask; eleven encode register
values. Singleton contexts consume zero bits. Empty ticks remain present.
No LZ history is needed. This module is not a Z80 decoder or release format.
"""
from collections import Counter
import struct

from cell_audio_stream import take_tick
from probe_motion_entropy import Reader, huffman_lengths, codes_for
from probe_hybrid_tiles import Writer


def symbols(ticks):
    result = [[] for _ in range(13)]
    sequence = []
    for tick in ticks:
        r = Reader(tick)
        if take_tick(r)!=tick: raise ValueError('invalid record')
        r.end()
        mask = sum(1<<v for v in tick[1::2])
        row = [(0,mask&255),(1,mask>>8)]
        row.extend((reg+2,value) for reg,value in zip(tick[1::2],tick[2::2],strict=True))
        for context,value in row:
            result[context].append(value)
            sequence.append((context,value))
    return result,sequence


def encode(ticks, initial=bytes(11)):
    if len(initial)!=11: raise ValueError('expected eleven initial registers')
    values,sequence = symbols(ticks)
    tables = []
    dictionaries = []
    for row in values:
        hist = Counter(row)
        if len(hist)<=1:
            entries = [(v,0) for v in hist]
            dictionary = {v:(0,0) for v in hist}
        else:
            lengths = huffman_lengths(hist)
            entries = [(v,n) for v,n in enumerate(lengths) if n]
            dictionary = dict(enumerate(codes_for(255,lengths)))
        tables.append(entries); dictionaries.append(dictionary)
    writer = Writer()
    for context,value in sequence:
        code,length = dictionaries[context][value]
        if length: writer.put(code,length)
    header = bytearray(b'AYH1'+struct.pack('<II',len(ticks),writer.bits)+initial)
    for entries in tables:
        header += struct.pack('<H',len(entries))+bytes(v for pair in entries for v in pair)
    payload = writer.finish()
    return bytes(header)+payload, dict(ticks=len(ticks),header_bytes=len(header),coded_bits=writer.bits,
        payload_bytes=len(payload),total_bytes=len(header)+len(payload),
        contexts=[dict(symbols=len(t),max_code_length=max((n for _,n in t),default=0),
            encoded_bits=sum(dict(t)[v] for v in row)) for t,row in zip(tables,values,strict=True)])


def decode(data):
    r = Reader(data)
    if r.take(4)!=b'AYH1': raise ValueError('expected AYH1')
    count,bits = struct.unpack('<II',r.take(8))
    initial = r.take(11)
    contexts = []
    for _ in range(13):
        size = r.u16()
        if size>256: raise ValueError('too many symbols')
        entries = [tuple(r.take(2)) for _ in range(size)]
        if len(set(v for v,_ in entries))!=size: raise ValueError('duplicate symbol')
        if size<=1:
            if any(n for _,n in entries): raise ValueError('invalid constant context')
            contexts.append((entries[0][0] if size else None,{},0))
            continue
        if any(not 1<=n<=24 for _,n in entries): raise ValueError('invalid code length')
        # Independent canonical first-code construction; not encoder codes.
        counts = Counter(n for _,n in entries); first = 0; lookup = {}
        for length in range(1,max(counts)+1):
            first = (first+counts[length-1])*2
            if first+counts[length]>1<<length: raise ValueError('oversubscribed table')
            for offset,value in enumerate(sorted(v for v,n in entries if n==length)):
                lookup[length,first+offset] = value
        contexts.append((None,lookup,max(counts)))
    payload = r.take((bits+7)//8); r.end()
    if bits%8 and payload[-1]&((1<<(8-bits%8))-1): raise ValueError('nonzero padding')
    position = 0
    def value(context):
        nonlocal position
        constant,lookup,maximum = contexts[context]
        if constant is not None: return constant
        code = 0
        for length in range(1,maximum+1):
            if position==bits: raise ValueError('truncated code')
            code = (code<<1)|((payload[position//8]>>(7-position%8))&1)
            position += 1
            if (length,code) in lookup: return lookup[length,code]
        raise ValueError('unassigned code or empty context')
    result = []
    for _ in range(count):
        mask = value(0)|(value(1)<<8)
        if mask>>11: raise ValueError('invalid AY mask')
        pairs = bytearray()
        for reg in range(11):
            if mask&(1<<reg): pairs.extend((reg,value(reg+2)))
        result.append(bytes([len(pairs)//2])+pairs)
    if position!=bits: raise ValueError('unused coded bits')
    return initial,result
