"""Bounded lossless native-cell dictionary probe using archived five-level packets.

Reuses verified ZX0 cache bytes, without requantizing RGB or changing dither.
Includes each window's dictionary in compression. This is not a player codec.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import struct

from audit_dither_phase import compress, sha
from benchmark_faster_zx0 import fixture
import five_level_dither as five
import zx0_codec


def unpack_cell(data):
    if len(data) != 5: raise ValueError('expected five-byte cell')
    value = int.from_bytes(data,'big'); native = bytearray()
    for shift in (30,20,10,0):
        word = (value >> shift) & 1023
        if word >= 625: raise ValueError('invalid radix-5 word')
        native.extend((five.TOP[word],five.BOTTOM[word]))
    return bytes(native)


def pack_cell(native):
    if len(native) != 8: raise ValueError('expected eight native rows')
    value = 0
    for y in range(0,8,2):
        word = 0
        for shift in (6,4,2,0):
            pair = ((native[y] >> shift) & 3,(native[y+1] >> shift) & 3)
            if pair not in five.PATTERNS: raise ValueError('invalid 2x2 phase')
            word = word*5+five.PATTERNS.index(pair)
        value = (value << 10) | word
    return value.to_bytes(5,'big')


def packets(blob):
    pos = 0
    while pos < len(blob):
        if pos+2 > len(blob): raise ValueError('truncated length')
        n = int.from_bytes(blob[pos:pos+2],'little'); pos += 2
        packet = blob[pos:pos+n]; pos += n
        if len(packet) != n or n < 192: raise ValueError('truncated packet')
        yield packet


def parts(packet):
    attrs = sum(v.bit_count() for v in packet[:96])
    count = sum(v.bit_count() for v in packet[96:192])
    start = 192+attrs
    if len(packet) != start+5*count: raise ValueError('not a uniform-five packet')
    return packet[:start], [packet[i:i+5] for i in range(start,len(packet),5)]


def encode_packet(packet, lookup):
    prefix, cells = parts(packet); flags = bytearray((len(cells)+7)//8); body = bytearray()
    for i, cell in enumerate(cells):
        if cell in lookup:
            flags[i//8] |= 128 >> (i % 8); body.append(lookup[cell])
        else: body.extend(cell)
    return prefix+flags+body


def decode_packet(packet, dictionary):
    if len(packet) < 192: raise ValueError('truncated masks')
    pos = 192+sum(v.bit_count() for v in packet[:96])
    count = sum(v.bit_count() for v in packet[96:192]); size = (count+7)//8
    if pos+size > len(packet): raise ValueError('truncated attributes or flags')
    prefix, flags = packet[:pos],packet[pos:pos+size]; pos += size
    if count % 8 and flags[-1] & ((1 << (8-count % 8))-1): raise ValueError('invalid padding')
    out = bytearray(prefix)
    for i in range(count):
        if flags[i//8] & (128 >> (i % 8)):
            if pos >= len(packet) or packet[pos] >= len(dictionary): raise ValueError('invalid dictionary index')
            out.extend(pack_cell(dictionary[packet[pos]])); pos += 1
        else:
            cell = packet[pos:pos+5]; unpack_cell(cell); out.extend(cell); pos += 5
    if pos != len(packet): raise ValueError('trailing data')
    return bytes(out)


def read_control(item, cache):
    result = bytearray()
    for block in item['blocks']:
        data = (cache/(block['decoded_sha256']+'.zx0')).read_bytes()
        if sha(data) != block['zx0_sha256']: raise ValueError('cached block hash differs')
        raw = zx0_codec.decompress(data,limit=block['decoded_bytes'])
        if sha(raw) != block['decoded_sha256']: raise ValueError('decoded hash differs')
        result.extend(raw)
    if len(result) != item['raw_bytes'] or sha(result) != item['raw_sha256']: raise ValueError('stream identity differs')
    return bytes(result)


def store(blob, executable, cache):
    chunks = [blob[i:i+15872] for i in range(0,len(blob),15872)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        blocks = list(pool.map(lambda b:compress(b,executable,cache),chunks))
    return dict(raw_bytes=len(blob),raw_sha256=sha(blob),zx0_bytes=sum(b['zx0_bytes']+4 for b in blocks),blocks=blocks)


def cpu_cost(item, cache):
    stream = bytearray(); blocks = []
    for block in item['blocks']:
        packed = (cache/(block['decoded_sha256']+'.zx0')).read_bytes()
        raw = zx0_codec.decompress(packed,limit=block['decoded_bytes'])
        blocks.append((packed,raw)); stream += struct.pack('<HH',len(raw),len(packed))+packed
    h, layout = fixture(bytes(stream),160,'fast')
    rows = [h.block(packed,raw,index) for index,(packed,raw) in enumerate(blocks)]
    return dict(decoder_tstates=sum(r['decoder_tstates'] for r in rows),
                producer_tstates=sum(r['producer_tstates'] for r in rows),
                sectors=sum(r['sectors'] for r in rows),blocks=rows,layout=layout)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path(__file__).with_name('hybrid_five_level_canonical_probe.json'))
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--zx0',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args(); reference = json.loads(a.input.read_text())
    cache = a.cache/sha(a.zx0.read_bytes())
    if reference['zx0_sha256'] != cache.name: raise ValueError('ZX0 executable differs')
    result = dict(complete=False,release=False,source_report_sha256=sha(a.input.read_bytes().replace(b'\r\n',b'\n')),
                  scope=__doc__,dictionary_limit=256,window_frames=32,windows=[],
                  native_five_consumer_implemented=False,physical_latency_measured=False,
                  cpu_scope='installed Fast ZX0 and mocked sector producer; no IRQ/ULA/ROM latency, frame rendering, dictionary installation or playback',
                  format='u16 count, count*8 native rows in eight planes, then u16-length packets: original masks/attribute XORs, hit bits, one-byte indices or five-byte cells')
    def save(): a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    for window in reference['windows']:
        raw = read_control(window['compression']['five'],cache)
        source = list(packets(raw)); frequency = Counter(cell for packet in source for cell in parts(packet)[1])
        chosen = sorted(frequency,key=lambda k:(-frequency[k],k))[:256]
        dictionary = [unpack_cell(cell) for cell in chosen]; lookup = {cell:i for i,cell in enumerate(chosen)}
        # Eight planes allow one page increment per native row on the Z80.
        header = struct.pack('<H',len(chosen))+bytes(dictionary[i][row] for row in range(8) for i in range(len(chosen)))
        decoded_dict = [bytes(header[2+row*len(chosen)+i] for row in range(8)) for i in range(len(chosen))]
        stream = bytearray(header)
        for packet in source:
            encoded = encode_packet(packet,lookup)
            if decode_packet(encoded,decoded_dict) != packet: raise AssertionError('five-level packet differs')
            stream += struct.pack('<H',len(encoded))+encoded
        measured = store(bytes(stream),a.zx0.resolve(),cache)
        row = dict(start=window['start'],frames=len(source),unique_changed_cells=len(frequency),
                   changed_cells=sum(frequency.values()),dictionary_hits=sum(frequency[k] for k in chosen),
                   dictionary_asset_bytes=len(header),dictionary_sha256=sha(header),
                   hybrid=window['compression']['hybrid'],uniform_five=window['compression']['five'],dictionary=measured)
        result['windows'].append(row); save()
        print(json.dumps({k:v for k,v in row.items() if k not in ('hybrid','uniform_five','dictionary')},ensure_ascii=True),flush=True)
        for name in ('hybrid','dictionary'):
            row[name+'_cpu'] = cpu_cost(row[name],cache); save()
        print(json.dumps(dict(start=row['start'],bytes={n:row[n]['zx0_bytes'] for n in ('hybrid','dictionary')},
                              cpu={n:{k:row[n+'_cpu'][k] for k in ('decoder_tstates','producer_tstates','sectors')} for n in ('hybrid','dictionary')})),flush=True)
    result['complete'] = True
    result['source_sha256_lf'] = {name:sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n',b'\n'))
        for name in ('probe_five_cell_dictionary.py','five_level_dither.py','audit_dither_phase.py',
                     'benchmark_faster_zx0.py','benchmark_inplace_slot.py','benchmark_inplace_streaming.py','faster_zx0.py','zx0_codec.py')}
    save()


if __name__ == '__main__': main()
