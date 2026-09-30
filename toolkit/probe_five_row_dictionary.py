"""Compare a 256-entry row dictionary after whole-cell dictionaries missed too often.

Four dictionary bytes reconstruct a cell through two 256-byte native lookup
tables. A cell with any missing row keeps its five-byte radix-5 payload.
The existing cell mode bit distinguishes these cases; no per-row branching.
"""
from collections import Counter
import argparse
import json
from pathlib import Path
import struct

from audit_dither_phase import sha
import five_level_dither as five
import probe_five_cell_dictionary as cell


def rows(data):
    cell.unpack_cell(data)
    value = int.from_bytes(data,'big')
    return tuple((value >> shift) & 1023 for shift in (30,20,10,0))


def encode_packet(packet, lookup):
    prefix, cells = cell.parts(packet); flags = bytearray((len(cells)+7)//8); body = bytearray()
    for i, data in enumerate(cells):
        words = rows(data)
        if all(word in lookup for word in words):
            flags[i//8] |= 128 >> (i % 8); body.extend(lookup[word] for word in words)
        else: body.extend(data)
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
            indices = packet[pos:pos+4]; pos += 4
            if len(indices) != 4 or any(index >= len(dictionary) for index in indices): raise ValueError('invalid dictionary index')
            out.extend(cell.pack_cell(b''.join(dictionary[index] for index in indices)))
        else:
            data = packet[pos:pos+5]; cell.unpack_cell(data); out.extend(data); pos += 5
    if pos != len(packet): raise ValueError('trailing data')
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path(__file__).with_name('hybrid_five_level_canonical_probe.json'))
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--zx0',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args(); reference = json.loads(a.input.read_text())
    cache = a.cache/sha(a.zx0.read_bytes())
    if reference['zx0_sha256'] != cache.name: raise ValueError('ZX0 executable differs')
    result = dict(complete=False,release=False,scope=__doc__,dictionary_limit=256,windows=[],
                  source_report_sha256=sha(a.input.read_bytes().replace(b'\r\n',b'\n')),
                  cpu_scope='installed Fast ZX0 and mocked sector producer; no IRQ/ULA/ROM latency, frame rendering, dictionary installation or playback',
                  native_five_consumer_implemented=False,physical_latency_measured=False,
                  format='u16 count, count*2 native bytes in two planes; packets retain masks/attribute XORs, hit bits, four row indices or five-byte cells')
    def save(): a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    for window in reference['windows']:
        raw = cell.read_control(window['compression']['five'],cache); source = list(cell.packets(raw))
        cells = [data for packet in source for data in cell.parts(packet)[1]]
        frequency = Counter(word for data in cells for word in rows(data))
        chosen = sorted(frequency,key=lambda k:(-frequency[k],k))[:256]
        lookup = {word:i for i,word in enumerate(chosen)}
        header = struct.pack('<H',len(chosen))+bytes(five.TOP[w] for w in chosen)+bytes(five.BOTTOM[w] for w in chosen)
        dictionary = [bytes([header[2+i],header[2+len(chosen)+i]]) for i in range(len(chosen))]
        stream = bytearray(header)
        for packet in source:
            encoded = encode_packet(packet,lookup)
            if decode_packet(encoded,dictionary) != packet: raise AssertionError('five-level packet differs')
            stream += struct.pack('<H',len(encoded))+encoded
        measured = cell.store(bytes(stream),a.zx0.resolve(),cache)
        row = dict(start=window['start'],frames=len(source),unique_rows=len(frequency),changed_cells=len(cells),
                   dictionary_hits=sum(all(word in lookup for word in rows(data)) for data in cells),
                   dictionary_asset_bytes=len(header),dictionary_sha256=sha(header),
                   hybrid=window['compression']['hybrid'],dictionary=measured)
        result['windows'].append(row); save()
        for name in ('hybrid','dictionary'):
            row[name+'_cpu'] = cell.cpu_cost(row[name],cache); save()
        print(json.dumps(dict(start=row['start'],hit_fraction=row['dictionary_hits']/len(cells),unique_rows=len(frequency),
                              bytes={n:row[n]['zx0_bytes'] for n in ('hybrid','dictionary')},
                              cpu={n:{k:row[n+'_cpu'][k] for k in ('decoder_tstates','producer_tstates','sectors')} for n in ('hybrid','dictionary')})),flush=True)
    result['complete'] = True
    result['source_sha256_lf'] = {name:sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n',b'\n'))
        for name in ('probe_five_row_dictionary.py','probe_five_cell_dictionary.py','five_level_dither.py',
                     'benchmark_faster_zx0.py','faster_zx0.py','benchmark_inplace_slot.py','benchmark_inplace_streaming.py','zx0_codec.py')}
    save()


if __name__ == '__main__': main()
