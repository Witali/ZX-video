"""FAP1: fixed one-frame headers with explicit coded/literal byte lengths.

Compared with SC04, replace n:u16, vectors:u16, masks:u16, flags:u8, bits:u32
by flags:u8, masks:u16, coded:u16, literals:u16. Low three flag bits retain
the final coded-byte bit count for exact roundtrip. Flags 6/7 keep raw
attributes/cache. Six AY records, 3 cache-map bytes, 192 vectors, serialized
masks, 80 output-map bytes and value streams remain unchanged. A Spectrum
packet reader can copy literals without rescanning 192 vectors for lengths.
No Z80 parser or timing/scheduling result is claimed by this PC container.
"""
import argparse
import json
from pathlib import Path
import struct

from cell_audio_stream import take_tick
from probe_lossless_layouts import sha, measure
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_sparse_motion_cache import unpack as unpack_cache
from raw_attribute_stream import read_packet


def pack(source):
    r = Reader(source)
    _, _, count, _, _ = read_header(r, magic=b'SC04')
    out, rows = bytearray(b'FAP1'+source[4:r.pos]), []
    for index in range(count):
        for _ in range(6): out += take_tick(r)
        cache = r.take(3)
        start = r.pos
        group, native = read_packet(r, count-index)
        _, vl, ml = struct.unpack_from('<HHH', source, start)
        if vl != 192 or len(group[6])+len(group[7])+2 > 4704:
            raise ValueError('wrong vector layout or oversized value window')
        flags, bits = group[1:3]
        header = struct.pack('<BHHH', flags | (bits & 7), ml, len(group[6]), len(group[7]))
        out += header+cache+source[start+11:start+11+vl+ml]+native+group[6]+group[7]
        rows.append(dict(index=index, mask_bytes=ml, coded_bytes=len(group[6]), literal_bytes=len(group[7])))
    r.end()
    return bytes(out), rows


def unpack(data):
    r = Reader(data)
    _, _, count, _, _ = read_header(r, magic=b'FAP1')
    out = bytearray(b'SC04'+data[4:r.pos])
    for index in range(count):
        for _ in range(6): out += take_tick(r)
        flags, ml, coded, literals = struct.unpack('<BHHH', r.take(7))
        if flags & 0x38 or not 8 <= ml <= 548 or coded+literals+2 > 4704 or (not coded and flags & 7):
            raise ValueError('invalid packet header')
        cache = r.take(3)
        body = r.take(192+ml+80+coded+literals)
        bits = coded*8-((8-(flags & 7)) & 7)
        original = struct.pack('<HHHBI', 1, 192, ml, flags & 0xc0, bits)+body
        checked = Reader(original)
        read_packet(checked, count-index); checked.end()
        out += cache+original
    r.end()
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'output', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    source = args.source.read_bytes()
    # Validate coverage independently before re-framing; ensure AY/video are
    # byte-identical after restoring all old headers and lengths.
    old_av = unpack_cache(source, 32, 4)
    encoded, rows = pack(source)
    restored = unpack(encoded)
    if restored != source or unpack_cache(restored, 32, 4) != old_av:
        raise AssertionError('source headers/maps/audio/video changed')
    report = dict(scope=__doc__, complete=True, source_sha256=sha(source),
        stream_sha256=sha(encoded), frames=len(rows), raw_bytes=len(encoded),
        delta_raw_bytes=len(encoded)-len(source), deflate_8192_bytes=measure(encoded, 8192),
        exact_sc04_roundtrip=True, no_additional_pixel_changes=True, exact_ay_bytes=True,
        max_value_bytes_with_guards=max(r['coded_bytes']+r['literal_bytes']+2 for r in rows),
        packet_lengths=rows, cpu_measured=False, disk_delivery_verified=False, release=False)
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_bytes(encoded)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'packet_lengths'}, indent=2))


if __name__ == '__main__':
    main()
