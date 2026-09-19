"""FAP2/FAP3: whole frame packets in the existing 4704-byte input window.

Packet = u16 payload length, six AY records, flags:u8/masks:u16/coded:u16,
cache[3], vectors[192], masks, native-map[80], coded, zero, literals, zero.
Literal length follows from packet end. Compared with FAP1 the two-byte
length replaces the explicit literal length; only the two guards are added.
This enables two stream reads per frame without moving its value streams.
FAP3 omits both stored guards: literals supply Huffman lookahead, and the
parser writes a single zero at packet end in RAM (one byte is reserved).
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


def pack(source, *, stored_guards=True):
    validate_fap1(source)
    r = Reader(source); _, _, count, _, _ = read_header(r,magic=b'FAP1')
    out, rows = bytearray((b'FAP2' if stored_guards else b'FAP3')+source[4:r.pos]), []
    guard = b'\0' if stored_guards else b''
    for index in range(count):
        ay = b''.join(take_tick(r) for _ in range(6))
        flags, ml, coded, literals = struct.unpack('<BHHH',r.take(7))
        body = ay+struct.pack('<BHH',flags,ml,coded)+r.take(3+192+ml+80)
        coded_offset = len(body)
        body += r.take(coded)+guard+r.take(literals)+guard
        if not 294+2*stored_guards <= len(body) <= WINDOW-int(not stored_guards):
            raise ValueError('packet does not fit input window')
        rows.append(dict(index=index,offset=len(out),payload_bytes=len(body),ay_bytes=len(ay),
            masks_offset=len(ay)+5+3+192,coded_offset=coded_offset,
            literal_offset=coded_offset+coded+stored_guards,coded_bytes=coded,literal_bytes=literals))
        out += struct.pack('<H',len(body))+body
    r.end()
    return bytes(out), rows


def read_packet(r, *, stored_guards=True):
    length = r.u16()
    if not 294+2*stored_guards <= length <= WINDOW-int(not stored_guards):
        raise ValueError('invalid packet length')
    body = r.take(length); p = Reader(body)
    ticks = [take_tick(p) for _ in range(6)]
    flags, ml, coded = struct.unpack('<BHH',p.take(5))
    if flags & 0x38 or not 8 <= ml <= 548 or (not coded and flags & 7):
        raise ValueError('invalid packet header')
    prefix = p.take(3+192+ml+80)
    coded_offset = p.pos
    encoded = p.take(coded)
    if stored_guards and p.take(1) != b'\0': raise ValueError('missing coded guard')
    literal_offset = p.pos
    literals = p.take(length-p.pos-stored_guards)
    if stored_guards and p.take(1) != b'\0': raise ValueError('missing literal guard')
    p.end()
    old = b''.join(ticks)+struct.pack('<BHHH',flags,ml,coded,len(literals))+prefix+encoded+literals
    return old, dict(payload=body,ticks=ticks,flags=flags,mask_bytes=ml,coded_bytes=coded,
        literal_bytes=len(literals),cache=prefix[:3],coded_offset=coded_offset,literal_offset=literal_offset)


def unpack(source):
    if source[:4] not in (b'FAP2',b'FAP3'): raise ValueError('unknown bulk packet format')
    stored_guards = source[:4] == b'FAP2'
    r = Reader(source); _, _, count, _, _ = read_header(r,magic=source[:4])
    out = bytearray(b'FAP1'+source[4:r.pos])
    for _ in range(count): out += read_packet(r,stored_guards=stored_guards)[0]
    r.end(); validate_fap1(bytes(out))
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','report'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--omit-guards',action='store_true',help='FAP3: create final lookahead in RAM')
    args = p.parse_args(); source = args.source.read_bytes()
    result, rows = pack(source,stored_guards=not args.omit_guards)
    if unpack(result) != source: raise AssertionError('FAP1 changed')
    report = dict(scope=__doc__,complete=True,baseline_commit='17f079c' if args.omit_guards else 'a875d18',
        format=result[:4].decode(),stored_guards=not args.omit_guards,
        input_sha256=sha(source),output_sha256=sha(result),frames=len(rows),raw_bytes=len(result),
        delta_raw_bytes=len(result)-len(source),max_payload_bytes=max(r['payload_bytes'] for r in rows),
        exact_fap1_roundtrip=True,exact_ay_bytes=True,no_additional_pixel_changes=True,
        cpu_measured=False,disk_delivery_verified=False,release=False,packets=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(result)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'packets'}),flush=True)


if __name__ == '__main__': main()
