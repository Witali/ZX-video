"""Exact metadata-derived and previous-value Huffman contexts for FPR1.

FPC1: magic, model u8, table count u8, original-header length u16,
original FPR1 header, one 256-byte canonical-length table per context.
Each group: frame count u16, vector length u16, mask length u16,
vector mode 2 data, mask mode 4 data, value bit count u32, MSB-first bits.
Context comes from decoded masks/vectors and earlier residual bytes; no
per-value context tags. Original group/frame order and all values stay exact.
This is a storage experiment, not a Z80 player or a cadence/RAM claim.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from probe_lossless_layouts import measure, sha
from probe_motion_entropy import (Reader, EXPECTED_SHA, groups, parse_header,
                                  huffman_lengths, codes_for)
from probe_motion_metadata import transform, restore

MODELS = [('global', 1), ('kind', 2), ('density', 4), ('motion', 4),
          ('density_motion', 10), ('previous_population', 6), ('previous_motion', 16)]
POP2 = np.array([sum(bool((b >> s) & 3) for s in (6, 4, 2, 0)) for b in range(256)], dtype=np.uint8)


def context_ids(fixed, values, mode, zero_index):
    n = int.from_bytes(fixed[:2], 'little')
    vectors = np.frombuffer(fixed[2:2+n*192], dtype=np.uint8).reshape(n, 192)
    if len(fixed) != 2+n*672 or np.any(vectors > zero_index):
        raise ValueError('invalid fixed group fields')
    mask = np.unpackbits(np.frombuffer(fixed[2+n*192:], dtype=np.uint8)).reshape(n, 192, 20).astype(bool)
    residual = np.zeros(mask.shape, dtype=np.uint8)
    residual[mask] = np.frombuffer(values, dtype=np.uint8)
    labels = np.zeros(mask.shape, dtype=np.uint8)
    count = mask[:, :, :16].sum(axis=2)
    density = (count > 2).astype(np.uint8)+(count > 6)
    motion = np.where(vectors == 0, 0, np.where(vectors == zero_index, 2, 1)).astype(np.uint8)
    previous = np.zeros_like(residual)
    previous[:, :, 1:] = residual[:, :, :-1]
    if mode == 1:
        labels[:, :, 16:] = 1
    elif mode in (2, 3, 4):
        base = density if mode == 2 else motion if mode == 3 else motion*3+density
        labels[:, :, :16] = base[:, :, None]
        labels[:, :, 16:] = MODELS[mode][1]-1
    elif mode in (5, 6):
        labels[:, :, :16] = POP2[previous[:, :, :16]]
        if mode == 6:
            labels[:, :, :16] += motion[:, :, None]*5
        labels[:, :, 16:] = MODELS[mode][1]-1
    elif mode != 0:
        raise ValueError('unknown context model')
    return labels[mask]


def train(parsed, mode, zero_index):
    counts = np.zeros((MODELS[mode][1], 256), dtype=np.int64)
    for fixed, values in parsed:
        ids = context_ids(fixed, values, mode, zero_index)
        labels = ids.astype(np.int32)*256+np.frombuffer(values, dtype=np.uint8)
        counts += np.bincount(labels, minlength=counts.size).reshape(counts.shape)
    tables = [huffman_lengths(dict(enumerate(row))) for row in counts]
    return tables, counts


def pack(values, ids, code_tables):
    if len(values) != len(ids):
        raise ValueError('context count differs from value count')
    out, acc, filled, total = bytearray(), 0, 0, 0
    for value, context in zip(values, ids):
        code, size = code_tables[context][value]
        if not size:
            raise ValueError('uncoded value')
        acc = (acc << size) | code
        filled += size; total += size
        while filled >= 8:
            filled -= 8
            out.append((acc >> filled) & 255)
        acc &= (1 << filled)-1
    if filled:
        out.append(acc << (8-filled))
    return total, bytes(out)


def encode(header, parsed, mode, tables):
    codes = [codes_for(255, t) for t in tables]
    out = bytearray(b'FPC1'+bytes([mode, len(tables)])+struct.pack('<H', len(header))+header+b''.join(tables))
    total = 0
    for fixed, values in parsed:
        n = int.from_bytes(fixed[:2], 'little')
        v = transform(fixed[2:2+n*192], 192, 2)
        m = transform(fixed[2+n*192:], 480, 4)
        bits, packed = pack(values, context_ids(fixed, values, mode, header[30]), codes)
        out += struct.pack('<HHH', n, len(v), len(m))+v+m+struct.pack('<I', bits)+packed
        total += bits
    return bytes(out), total


class Decoder:
    def __init__(self, tables):
        # Independent canonical first-code construction, not codes_for().
        self.lookups, self.maxima = [], []
        for lengths in tables:
            if len(lengths) != 256 or max(lengths) > 24 or lengths[0]:
                raise ValueError('invalid context table')
            counts = Counter(n for n in lengths if n)
            first, lookup = 0, {}
            for n in range(1, max(lengths)+1):
                first = (first+counts[n-1]) << 1
                if first+counts[n] > 1 << n:
                    raise ValueError('oversubscribed table')
                for i, symbol in enumerate(s for s, size in enumerate(lengths) if size == n):
                    lookup[n, first+i] = symbol
            self.lookups.append(lookup); self.maxima.append(max(lengths))

    def begin(self, data, bits):
        if len(data) != (bits+7)//8 or (bits % 8 and data[-1] & ((1 << (8-bits % 8))-1)):
            raise ValueError('invalid coded length/padding')
        self.data, self.bits, self.position = data, bits, 0

    def value(self, context):
        code = 0
        for n in range(1, self.maxima[context]+1):
            if self.position == self.bits:
                raise ValueError('truncated code')
            code = code*2 + ((self.data[self.position//8] >> (7-self.position % 8)) & 1)
            self.position += 1
            if (n, code) in self.lookups[context]:
                return self.lookups[context][n, code]
        raise ValueError('unassigned code')

    def group(self, masks, vectors, mode, zero_index):
        output = bytearray()
        # Scalar masks/context state, separate from encoder's numpy classifier.
        for tile, vector in enumerate(vectors):
            if vector > zero_index:
                raise ValueError('invalid vector')
            present = [bool(masks[(tile*20+i)//8] & (128 >> ((tile*20+i) % 8))) for i in range(20)]
            changed = sum(present[:16])
            density = 0 if changed <= 2 else 1 if changed <= 6 else 2
            motion = 0 if vector == 0 else 2 if vector == zero_index else 1
            previous = 0
            for i, active in enumerate(present):
                if not active:
                    previous = 0
                    continue
                if mode == 0:
                    context = 0
                elif i >= 16:
                    context = MODELS[mode][1]-1
                elif mode == 1:
                    context = 0
                elif mode == 2:
                    context = density
                elif mode == 3:
                    context = motion
                elif mode == 4:
                    context = motion*3+density
                else:
                    context = sum(bool((previous >> shift) & 3) for shift in (0, 2, 4, 6))
                    if mode == 6:
                        context += motion*5
                previous = self.value(context)
                output.append(previous)
        if self.position != self.bits:
            raise ValueError('unused coded bits')
        return bytes(output)


def decode(data):
    r = Reader(data)
    if r.take(4) != b'FPC1':
        raise ValueError('not FPC1')
    mode, count = r.take(2)
    if mode >= len(MODELS) or count != MODELS[mode][1]:
        raise ValueError('unknown model/table count')
    header = r.take(r.u16())
    hr = Reader(header)
    _, remaining = parse_header(hr)
    hr.end()
    decoder = Decoder([r.take(256) for _ in range(count)])
    output = bytearray(header)
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(remaining, 8):
            raise ValueError('invalid group size')
        vectors = restore(r.take(vl), n, 192, 2)
        masks = restore(r.take(ml), n, 480, 4)
        bits = int.from_bytes(r.take(4), 'little')
        decoder.begin(r.take((bits+7)//8), bits)
        values = decoder.group(masks, vectors, mode, header[30])
        output += struct.pack('<H', n)+vectors+masks+values
        remaining -= n
    r.end()
    return bytes(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.raw.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected full-movie FPR1')
    header, parsed = groups(raw)
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='8b3f83f', input_sha256=sha(raw), frames=4971,
        groups=len(parsed), values=sum(len(v) for _, v in parsed), no_additional_pixel_changes=True,
        player_changed=False, integrated_player_delta_tstates=0, complete=False, rows=[])
    for mode, (name, contexts) in enumerate(MODELS):
        tables, counts = train(parsed, mode, header[30])
        data, bits = encode(header, parsed, mode, tables)
        if decode(data) != raw:
            raise AssertionError('FPR1 was not reconstructed exactly')
        (args.cache/(name+'.raw')).write_bytes(data)
        row = dict(name=name, mode=mode, contexts=contexts, tables=[list(t) for t in tables],
            context_value_counts=counts.sum(axis=1).tolist(), raw_bytes=len(data), sha256=sha(data),
            encoded_value_bits=bits, mean_value_bits=bits/report['values'],
            minimum_code_bits=min(n for t in tables for n in t if n),
            maximum_code_bits=max(max(t) for t in tables), exact_round_trip=True,
            deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k:v for k,v in row.items() if k not in ('tables', 'context_value_counts')}), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
