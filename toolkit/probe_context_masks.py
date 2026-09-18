"""Lossless permutations of FPC2 masks before the existing sparse/ZX0 stages.

FPC3 = magic, permutation u8, original header length u16, FPC2 header;
then unchanged group format with masks permuted before sparse mode 4.
Reconstruct the entire FPC2 byte stream, including its coded corrections.
No new pixel errors, player code or release timing claims.
"""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import struct

import numpy as np

from probe_motion_entropy import Reader, parse_header
from probe_motion_metadata import transform, restore
from probe_lossless_layouts import measure, sha

MODES = ['control', 'frame_split', 'group_split', 'group_byte_planes',
         'frame_bit_planes', 'eight_tile_planes', 'time_bits']
EXPECTED_SHA = '54a743ca9805333e2f0c0d0c9cfc9f3275f41a8c3e21649b1a4ace32262c8a22'


def split(data):
    r = Reader(data)
    if r.take(4) != b'FPC2':
        raise ValueError('not FPC2')
    count = r.take(1)[0]
    hr = Reader(r.take(r.u16()))
    _, remaining = parse_header(hr)
    hr.end()
    r.take(256+256*count)
    header = data[:r.pos]
    groups = []
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(8, remaining):
            raise ValueError('group length')
        v = r.take(vl)
        masks = restore(r.take(ml), n, 480, 4)
        size = r.take(4)
        values = size+r.take((int.from_bytes(size, 'little')+7)//8)
        groups.append((n, v, masks, values))
        remaining -= n
    r.end()
    return header, groups


def permute(masks, n, mode):
    bits = np.unpackbits(np.frombuffer(masks, dtype=np.uint8)).reshape(n, 192, 20)
    if mode == 0:
        reordered = bits.ravel()
    elif mode == 1:
        reordered = np.concatenate((bits[:, :, :16].reshape(n, -1), bits[:, :, 16:].reshape(n, -1)), axis=1).ravel()
    elif mode == 2:
        reordered = np.concatenate((bits[:, :, :16].ravel(), bits[:, :, 16:].ravel()))
    elif mode == 3:
        reordered = np.concatenate((bits[:, :, :16].reshape(n, 192, 2, 8).transpose(2, 0, 1, 3).ravel(), bits[:, :, 16:].ravel()))
    elif mode == 4:
        reordered = bits.transpose(0, 2, 1).ravel()
    elif mode == 5:
        reordered = bits.reshape(n, 24, 8, 20).transpose(0, 1, 3, 2).ravel()
    elif mode == 6:
        reordered = bits.transpose(1, 2, 0).ravel()
    else:
        raise ValueError('unknown mode')
    return np.packbits(reordered).tobytes()


@lru_cache(maxsize=16)
def inverse_addresses(n, mode):
    # Independent scalar address definitions, not inverse encoder transposes.
    addresses = []
    for frame in range(n):
        for tile in range(192):
            for field in range(20):
                if mode == 0:
                    address = frame*3840+tile*20+field
                elif mode == 1:
                    address = frame*3840+(tile*16+field if field < 16 else 3072+tile*4+field-16)
                elif mode == 2:
                    address = frame*3072+tile*16+field if field < 16 else n*3072+frame*768+tile*4+field-16
                elif mode == 3:
                    address = ((field//8)*n*192+frame*192+tile)*8+field % 8 if field < 16 else n*3072+frame*768+tile*4+field-16
                elif mode == 4:
                    address = frame*3840+field*192+tile
                elif mode == 5:
                    address = frame*3840+(tile//8)*160+field*8+tile % 8
                elif mode == 6:
                    address = (tile*20+field)*n+frame
                else:
                    raise ValueError('unknown mode')
                addresses.append(address)
    return np.array(addresses, dtype=np.int32)


def unpermute(data, n, mode):
    if len(data) != n*480:
        raise ValueError('mask length')
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return np.packbits(bits[inverse_addresses(n, mode)]).tobytes()


def encode(header, groups, mode):
    output = bytearray(b'FPC3'+bytes([mode])+struct.pack('<H', len(header))+header)
    for n, vectors, masks, values in groups:
        changed = transform(permute(masks, n, mode), 480, 4)
        output += struct.pack('<HHH', n, len(vectors), len(changed))+vectors+changed+values
    return bytes(output)


def decode(data):
    r = Reader(data)
    if r.take(4) != b'FPC3':
        raise ValueError('not FPC3')
    mode = r.take(1)[0]
    if mode >= len(MODES):
        raise ValueError('invalid mode')
    header = r.take(r.u16())
    hr = Reader(header)
    if hr.take(4) != b'FPC2':
        raise ValueError('bad nested header')
    count = hr.take(1)[0]
    original = Reader(hr.take(hr.u16()))
    _, remaining = parse_header(original)
    original.end(); hr.take(256+256*count); hr.end()
    output = bytearray(header)
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(remaining, 8):
            raise ValueError('group length')
        vectors = r.take(vl)
        masks = unpermute(restore(r.take(ml), n, 480, 4), n, mode)
        m = transform(masks, 480, 4)
        size = r.take(4)
        values = size+r.take((int.from_bytes(size, 'little')+7)//8)
        output += struct.pack('<HHH', n, vl, len(m))+vectors+m+values
        remaining -= n
    r.end()
    return bytes(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpc', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.fpc.read_bytes()
    if sha(data) != EXPECTED_SHA:
        raise ValueError('unexpected 64-context full movie')
    header, groups = split(data)
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='8e0812b', input_sha256=sha(data),
        frames=4971, groups=len(groups), no_additional_pixel_changes=True,
        player_changed=False, integrated_player_delta_tstates=0, complete=False, rows=[])
    for mode, name in enumerate(MODES):
        encoded = encode(header, groups, mode)
        if decode(encoded) != data:
            raise AssertionError('FPC2 was not restored exactly')
        (args.cache/(name+'.raw')).write_bytes(encoded)
        row = dict(name=name, mode=mode, raw_bytes=len(encoded), sha256=sha(encoded),
            exact_fpc2_round_trip=True, deflate_8192=measure(encoded, 8192))
        report['rows'].append(row)
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
