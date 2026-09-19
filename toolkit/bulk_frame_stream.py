"""FAP2: a whole frame packet fits the existing 4704-byte input window.

Packet = u16 payload length, six AY records, flags:u8/masks:u16/coded:u16,
cache[3], vectors[192], masks, native-map[80], coded, zero, literals, zero.
Literal length follows from packet end. Compared with FAP1 the two-byte
length replaces the explicit literal length; only the two guards are added.
This enables two stream reads per frame without moving its value streams.
"""
import argparse
import json
from pathlib import Path
import struct

from cell_audio_stream import take_tick
from frame_packet_stream import unpack as validate_fap1
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha

WINDOW = 4704


def pack(source):
    validate_fap1(source)
    r = Reader(source); _, _, count, _, _ = read_header(r,magic=b'FAP1')
    out, rows = bytearray(b'FAP2'+source[4:r.pos]), []
    for index in range(count):
        ay = b''.join(take_tick(r) for _ in range(6))
        flags, ml, coded, literals = struct.unpack('<BHHH',r.take(7))
        body = ay+struct.pack('<BHH',flags,ml,coded)+r.take(3+192+ml+80)
        coded_offset = len(body)
        body += r.take(coded)+b'\0'+r.take(literals)+b'\0'
        if not 296 <= len(body) <= WINDOW: raise ValueError('packet does not fit input window')
        rows.append(dict(index=index,offset=len(out),payload_bytes=len(body),ay_bytes=len(ay),
            masks_offset=len(ay)+5+3+192,coded_offset=coded_offset,
            literal_offset=coded_offset+coded+1,coded_bytes=coded,literal_bytes=literals))
        out += struct.pack('<H',len(body))+body
    r.end()
    return bytes(out), rows


def read_packet(r):
    length = r.u16()
    if not 296 <= length <= WINDOW: raise ValueError('invalid packet length')
    body = r.take(length); p = Reader(body)
    ticks = [take_tick(p) for _ in range(6)]
    flags, ml, coded = struct.unpack('<BHH',p.take(5))
    if flags & 0x38 or not 8 <= ml <= 548 or (not coded and flags & 7):
        raise ValueError('invalid packet header')
    prefix = p.take(3+192+ml+80)
    coded_offset = p.pos
    encoded = p.take(coded)
    if p.take(1) != b'\0': raise ValueError('missing coded guard')
    literal_offset = p.pos
    literals = p.take(length-p.pos-1)
    if p.take(1) != b'\0': raise ValueError('missing literal guard')
    p.end()
    old = b''.join(ticks)+struct.pack('<BHHH',flags,ml,coded,len(literals))+prefix+encoded+literals
    return old, dict(payload=body,ticks=ticks,flags=flags,mask_bytes=ml,coded_bytes=coded,
        literal_bytes=len(literals),cache=prefix[:3],coded_offset=coded_offset,literal_offset=literal_offset)


def unpack(source):
    r = Reader(source); _, _, count, _, _ = read_header(r,magic=b'FAP2')
    out = bytearray(b'FAP1'+source[4:r.pos])
    for _ in range(count): out += read_packet(r)[0]
    r.end(); validate_fap1(bytes(out))
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','report'): p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args(); source = args.source.read_bytes()
    result, rows = pack(source)
    if unpack(result) != source: raise AssertionError('FAP1 changed')
    report = dict(scope=__doc__,complete=True,baseline_commit='a875d18',
        input_sha256=sha(source),output_sha256=sha(result),frames=len(rows),raw_bytes=len(result),
        delta_raw_bytes=len(result)-len(source),max_payload_bytes=max(r['payload_bytes'] for r in rows),
        exact_fap1_roundtrip=True,exact_ay_bytes=True,no_additional_pixel_changes=True,
        cpu_measured=False,disk_delivery_verified=False,release=False,packets=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(result)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'packets'}),flush=True)


if __name__ == '__main__': main()
