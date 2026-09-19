"""FAP4/FAP5: unchanged tile runs for direct Z80 traversal, inside FAP3.

Vectors 0..88 retain their meaning. 129..144 skip 1..16 zero-vector,
zero-mask tiles, never crossing a 16-tile stripe. Commands are followed
by zero padding to the existing 192-byte vector field in FAP4. FAP5 keeps
original vector positions, marking the first entry of each selected run.
Other packet bytes and offsets stay unchanged. Neither format is a release.
"""
import argparse
import json
from pathlib import Path
import struct

from bulk_frame_stream import read_packet,unpack as validate_fap3
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha


def encode_vectors(vectors,masks, *, inplace=False, minimum=1):
    if len(vectors) != 192 or len(masks) != 384 or any(v>88 for v in vectors):
        raise ValueError('one valid vector/mask frame required')
    if not 1 <= minimum <= 16: raise ValueError('minimum run must be 1..16')
    result = bytearray()
    for first in range(0,192,16):
        i,end = first,first+16
        while i < end:
            if vectors[i] or masks[i*2:i*2+2] != b'\0\0':
                result.append(vectors[i]); i += 1
            else:
                start = i
                while i < end and not vectors[i] and masks[i*2:i*2+2] == b'\0\0': i += 1
                count = i-start
                if count < minimum: result.extend(bytes(count))
                else:
                    result.append(128+count)
                    if inplace: result.extend(bytes(count-1))
    return bytes(result)+bytes(192-len(result)),len(result)


def decode_vectors(commands,masks, *, inplace=False):
    if len(commands) != 192 or len(masks) != 384: raise ValueError('wrong vector/mask size')
    result,pos = bytearray(),0
    while len(result) < 192:
        value = commands[pos]; pos += 1
        if value <= 88: result.append(value)
        elif 129 <= value <= 144:
            count = value-128
            if count > 16-len(result)%16 or any(masks[2*len(result):2*(len(result)+count)]):
                raise ValueError('run crosses stripe or skips a correction')
            if inplace:
                if any(commands[pos:pos+count-1]): raise ValueError('nonzero skipped command')
                pos += count-1
            result.extend(bytes(count))
        else: raise ValueError('invalid vector command')
    if any(commands[pos:]): raise ValueError('nonzero command padding')
    return bytes(result),pos


def transcode(source, *, inverse=False,inplace=False,minimum=1):
    if inverse: inplace = source[:4] == b'FAP5'
    magic = (b'FAP5' if inplace else b'FAP4') if inverse else b'FAP3'
    if not inverse: validate_fap3(source)
    r = Reader(source); _,_,count,_,_ = read_header(r,magic=magic)
    result = bytearray((b'FAP3' if inverse else b'FAP5' if inplace else b'FAP4')+source[4:r.pos]); rows=[]
    for index in range(count):
        offset = r.pos
        _,packet = read_packet(r,stored_guards=False)
        body = bytearray(packet['payload']); start = sum(map(len,packet['ticks']))+8
        masks = restore(bytes(body[start+192:start+192+packet['mask_bytes']]),1,480,4)[:384]
        before = bytes(body[start:start+192])
        after,used = (decode_vectors(before,masks,inplace=inplace) if inverse else
            encode_vectors(before,masks,inplace=inplace,minimum=minimum))
        body[start:start+192] = after
        commands = 192-sum(v-129 for v in (before if inverse else after) if v >= 129) if inplace else used
        rows.append(dict(index=index,offset=offset,commands=commands,padding_bytes=0 if inplace else 192-used))
        result += struct.pack('<H',len(body))+body
    r.end()
    if inverse: validate_fap3(bytes(result))
    return bytes(result),rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','report'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--inplace',action='store_true',help='FAP5 preserves vector column positions')
    p.add_argument('--minimum',type=int,default=1,help='Encode runs at least this long (1..16)')
    args = p.parse_args(); source = args.source.read_bytes()
    raw,rows = transcode(source,inplace=args.inplace,minimum=args.minimum)
    if transcode(raw,inverse=True)[0] != source: raise AssertionError('FAP3 roundtrip differs')
    report = dict(scope=__doc__,complete=True,baseline_commit='2f8535e',input_sha256=sha(source),
        output_sha256=sha(raw),raw_bytes=len(raw),raw_delta_bytes=len(raw)-len(source),
        inplace=args.inplace,minimum_run=args.minimum,
        exact_fap3_roundtrip=True,no_additional_pixel_changes=True,exact_ay_bytes=True,
        commands=sum(r['commands'] for r in rows),padding_bytes=sum(r['padding_bytes'] for r in rows),
        frames=len(rows),cpu_measured=False,disk_delivery_verified=False,release=False,packets=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(raw)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'packets'}))


if __name__ == '__main__': main()
