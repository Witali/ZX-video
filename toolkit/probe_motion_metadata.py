"""Reversible vector/mask representations around unchanged FPE1 Huffman values.

FPM1: magic, vector mode u8, mask mode u8, original header length u16,
original FPE1 header. Per group: frame count u16, vector length u16,
mask length u16, transformed vectors, transformed masks, original bit length
u32 and coded value bytes. All group/frame boundaries and values stay exact.
This storage probe is not an integrated Z80 decoder or a disk release.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from benchmark_huffman_z80 import FPE_SHA
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, parse_header


def split(data):
    r = Reader(data)
    if r.take(5) != b'FPE1\xff':
        raise ValueError('requires Huffman FPE1')
    r.take(r.u16())
    original = r.take(r.u16())
    hr = Reader(original)
    _, frames = parse_header(hr)
    hr.end()
    header = data[:r.pos]
    result = []
    while frames:
        n = r.u16()
        if not 1 <= n <= min(frames, 8):
            raise ValueError('requires groups of at most eight frames')
        vectors, masks = r.take(n*192), r.take(n*480)
        bit_size = r.take(4)
        values = bit_size + r.take((int.from_bytes(bit_size, 'little')+7)//8)
        result.append((n, vectors, masks, values))
        frames -= n
    r.end()
    return header, result


def sparse(data):
    flags = np.packbits(np.frombuffer(data, dtype=np.uint8) != 0).tobytes()
    return flags, bytes(b for b in data if b)


def unsparse(reader, flags, count):
    if count % 8 and flags[-1] & ((1 << (8-count % 8))-1):
        raise ValueError('nonzero sparse padding')
    result = bytearray(count)
    for i in range(count):
        if flags[i//8] & (128 >> (i % 8)):
            value = reader.take(1)[0]
            if not value:
                raise ValueError('zero sparse value')
            result[i] = value
    return bytes(result)


def transform(data, width, mode):
    rows = np.frombuffer(data, dtype=np.uint8).reshape(-1, width)
    if mode == 0:
        return data
    if mode == 1:  # Temporal XOR, independent at each group.
        changed = rows.copy()
        changed[1:] ^= rows[:-1]
        return changed.tobytes()
    if mode == 2:  # Same field in consecutive frames is adjacent.
        return rows.T.tobytes()
    if mode == 3:  # One presence bit per nonzero metadata byte.
        flags, values = sparse(data)
        return flags+values
    if mode == 4:  # Presence bits for the presence bytes as well.
        flags, values = sparse(data)
        upper, nonzero = sparse(flags)
        return upper+nonzero+values
    if mode == 5:  # Bounded literal / zero / FF byte runs.
        out, pos = bytearray(), 0
        while pos < len(data):
            value = data[pos]
            n = 1
            if value in (0, 255):
                while n < 64 and pos+n < len(data) and data[pos+n] == value:
                    n += 1
                out.append((64 if value == 0 else 128)+n-1)
            else:
                while n < 64 and pos+n < len(data) and data[pos+n] not in (0, 255):
                    n += 1
                out.append(n-1)
                out += data[pos:pos+n]
            pos += n
        return bytes(out)
    if mode == 6:  # Left vector in each 16-tile row.
        if width != 192:
            raise ValueError('spatial vector mode only')
        rows = rows.reshape(-1, 16)
        changed = rows.copy()
        changed[:, 1:] ^= rows[:, :-1]
        return changed.tobytes()
    raise ValueError('unknown mode')


def restore(data, count, width, mode):
    size = count*width
    r = Reader(data)
    if mode == 0:
        out = r.take(size)
    elif mode in (1, 2, 6):
        source = r.take(size)
        out = bytearray(size)
        # Independent scalar inverse, avoiding the encoder's array operations.
        for frame in range(count):
            for column in range(width):
                i = frame*width+column
                if mode == 2:
                    out[i] = source[column*count+frame]
                elif mode == 1:
                    out[i] = source[i] ^ (out[i-width] if frame else 0)
                else:
                    if width != 192:
                        raise ValueError('spatial vector mode only')
                    out[i] = source[i] ^ (out[i-1] if column % 16 else 0)
        out = bytes(out)
    elif mode in (3, 4):
        flag_size = (size+7)//8
        if mode == 3:
            flags = r.take(flag_size)
        else:
            upper = r.take((flag_size+7)//8)
            flags = unsparse(r, upper, flag_size)
        out = unsparse(r, flags, size)
    elif mode == 5:
        out = bytearray()
        while len(out) < size:
            tag = r.take(1)[0]
            if tag >= 192:
                raise ValueError('invalid run tag')
            n = (tag & 63)+1
            if len(out)+n > size:
                raise ValueError('run exceeds field')
            out += r.take(n) if tag < 64 else bytes([0 if tag < 128 else 255])*n
        out = bytes(out)
    else:
        raise ValueError('unknown mode')
    r.end()
    return out


def encode(header, groups, vector_mode, mask_mode):
    output = bytearray(b'FPM1'+bytes([vector_mode, mask_mode])+struct.pack('<H', len(header))+header)
    for n, vectors, masks, values in groups:
        v = transform(vectors, 192, vector_mode)
        m = transform(masks, 480, mask_mode)
        output += struct.pack('<HHH', n, len(v), len(m))+v+m+values
    return bytes(output)


def decode(data):
    r = Reader(data)
    if r.take(4) != b'FPM1':
        raise ValueError('not FPM1')
    vm, mm = r.take(2)
    header = r.take(r.u16())
    hr = Reader(header)
    if hr.take(5) != b'FPE1\xff':
        raise ValueError('requires Huffman header')
    hr.take(hr.u16())
    original = Reader(hr.take(hr.u16()))
    _, remaining = parse_header(original)
    original.end(); hr.end()
    output = bytearray(header)
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(remaining, 8):
            raise ValueError('invalid group size')
        output += struct.pack('<H', n)
        output += restore(r.take(vl), n, 192, vm)
        output += restore(r.take(ml), n, 480, mm)
        bits = r.take(4)
        output += bits+r.take((int.from_bytes(bits, 'little')+7)//8)
        remaining -= n
    r.end()
    return bytes(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpe', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.fpe.read_bytes()
    if sha(source) != FPE_SHA:
        raise ValueError('unexpected full-movie candidate')
    header, groups = split(source)
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='821005a', frames=4971,
        input_sha256=sha(source), input_bytes=len(source), complete=False,
        no_additional_pixel_changes=True, player_changed=False,
        integrated_hot_path_delta_tstates=0, component_profile={}, rows=[])
    for index, name in ((1, 'vectors'), (2, 'masks'), (3, 'coded_values_with_lengths')):
        data = b''.join(g[index] for g in groups)
        counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
        report['component_profile'][name] = dict(raw_bytes=len(data),
            histogram=counts.tolist(), deflate_8192=measure(data, 8192))
    variants = [('control', 0, 0)]
    variants += [(f'vector_{v}', v, 0) for v in (1, 2, 6)]
    variants += [(f'mask_{m}', 0, m) for m in (1, 2, 3, 4, 5)]
    # Also combine the independently most compact DEFLATE vector/mask modes.
    for name, vm, mm in variants:
        data = encode(header, groups, vm, mm)
        if decode(data) != source:
            raise AssertionError('serialized FPE1 changed')
        (args.cache/(name+'.raw')).write_bytes(data)
        row = dict(name=name, vector_mode=vm, mask_mode=mm, raw_bytes=len(data),
            sha256=sha(data), exact_round_trip=True, deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
        if name == 'mask_5':
            best_v = min((r for r in report['rows'] if r['mask_mode'] == 0),
                         key=lambda r: r['deflate_8192'])['vector_mode']
            best_m = min((r for r in report['rows'] if r['vector_mode'] == 0),
                         key=lambda r: r['deflate_8192'])['mask_mode']
            if best_v and best_m:
                variants.append(('combined', best_v, best_m))
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
