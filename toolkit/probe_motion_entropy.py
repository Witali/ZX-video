"""Lossless short codes for FPR1 correction bytes before ZX0.

FPE1: magic, mode u8 (0 raw, 2..6 common-symbol prefix bits, 255 Huffman),
table length u16, table, original header length u16, original FPR1 header.
Each group preserves count/vectors/masks verbatim, followed by coded bit
length u32 and ceil(bits/8) MSB-first bytes. Padding must be zero. The masks
give the decoded symbol count. Raw and prefix escapes carry eight-bit bytes.
Huffman stores 256 canonical code lengths, including unused zero lengths.
This offline transform does not establish Z80 frame timing or playable TRDs.
"""
import argparse
from collections import Counter
import heapq
import json
from pathlib import Path
import struct

from probe_lossless_layouts import measure, sha

EXPECTED_SHA = '843eb9756ef43927236207692a84075bc1c733012d5fccc5729eb113e8b59c24'


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, count):
        if count < 0 or self.pos + count > len(self.data):
            raise ValueError('truncated stream')
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result

    def u16(self):
        return int.from_bytes(self.take(2), 'little')

    def end(self):
        if self.pos != len(self.data):
            raise ValueError('trailing bytes')


def parse_header(reader):
    fixed = reader.take(35)
    if fixed[:4] != b'FPR1' or fixed[20:25] != b'FMO1\x08' or fixed[25:30] != b'FMR1\x08':
        raise ValueError('expected tile-8 FPR1/FMO1/FMR1')
    offsets, frames = fixed[30], int.from_bytes(fixed[31:35], 'little')
    if not 1 <= offsets <= 254 or not frames:
        raise ValueError('invalid header')
    return fixed + reader.take(2 * offsets), frames


def groups(data):
    reader = Reader(data)
    header, frames = parse_header(reader)
    result = []
    while frames:
        count = reader.u16()
        if not 1 <= count <= frames:
            raise ValueError('invalid group count')
        vectors = reader.take(192 * count)
        masks = reader.take(480 * count)
        values = reader.take(sum(b.bit_count() for b in masks))
        if 0 in values:
            raise ValueError('zero value in a nonzero correction stream')
        result.append((struct.pack('<H', count) + vectors + masks, values))
        frames -= count
    reader.end()
    return header, result


def huffman_lengths(histogram):
    heap = [(count, value, value) for value, count in histogram.items() if count]
    heapq.heapify(heap)
    result = [0] * 256
    if not heap:
        return bytes(result)
    serial = 256
    while len(heap) > 1:
        a, b = heapq.heappop(heap), heapq.heappop(heap)
        heapq.heappush(heap, (a[0] + b[0], serial, (a[2], b[2])))
        serial += 1

    def visit(node, depth):
        if isinstance(node, int):
            result[node] = max(depth, 1)
        else:
            visit(node[0], depth + 1)
            visit(node[1], depth + 1)
    visit(heap[0][2], 0)
    return bytes(result)


def codes_for(mode, table):
    if mode == 0:
        if table:
            raise ValueError('raw mode table')
        return [(value, 8) for value in range(256)]
    if 2 <= mode <= 6:
        escape = (1 << mode) - 1
        if len(table) != escape or len(set(table)) != len(table):
            raise ValueError('invalid prefix table')
        codes = [(escape << 8 | value, mode + 8) for value in range(256)]
        for code, value in enumerate(table):
            codes[value] = (code, mode)
        return codes
    if mode != 255 or len(table) != 256 or max(table) > 24:
        raise ValueError('invalid Huffman table')
    codes = [(0, 0)] * 256
    code = previous = 0
    for length, symbol in sorted((n, i) for i, n in enumerate(table) if n):
        code <<= length - previous
        if code >= 1 << length:
            raise ValueError('oversubscribed Huffman table')
        codes[symbol] = code, length
        code += 1
        previous = length
    return codes


def pack(values, codes):
    result = bytearray()
    accumulator = filled = total = 0
    for value in values:
        code, length = codes[value]
        if not length:
            raise ValueError('uncoded value')
        accumulator = (accumulator << length) | code
        filled += length
        total += length
        while filled >= 8:
            filled -= 8
            result.append((accumulator >> filled) & 255)
        accumulator &= (1 << filled) - 1
    if filled:
        result.append(accumulator << (8 - filled))
    return total, bytes(result)


def unpack(data, bits, count, mode, table):
    # Independent bit reader / canonical first-code calculation. No encoder
    # code table or packer is used to reconstruct the original value bytes.
    if len(data) != (bits + 7) // 8 or bits > len(data) * 8:
        raise ValueError('invalid bit size')
    if bits % 8 and data[-1] & ((1 << (8 - bits % 8)) - 1):
        raise ValueError('nonzero padding')
    position = 0

    def read(n):
        nonlocal position
        if position + n > bits:
            raise ValueError('truncated bit code')
        value = 0
        for _ in range(n):
            value = value << 1 | ((data[position // 8] >> (7 - position % 8)) & 1)
            position += 1
        return value

    lookup, maximum = {}, 0
    if mode == 255:
        if len(table) != 256 or max(table) > 24:
            raise ValueError('invalid Huffman table')
        maximum = max(table)
        first = 0
        counts = Counter(n for n in table if n)
        for n in range(1, maximum + 1):
            first = (first + counts[n - 1]) << 1
            if first + counts[n] > 1 << n:
                raise ValueError('oversubscribed Huffman table')
            for offset, symbol in enumerate(i for i, length in enumerate(table) if length == n):
                lookup[n, first + offset] = symbol
    elif mode == 0:
        if table:
            raise ValueError('raw mode table')
    elif not 2 <= mode <= 6 or len(table) != (1 << mode) - 1 or len(set(table)) != len(table):
        raise ValueError('invalid prefix mode/table')
    output = bytearray()
    for _ in range(count):
        if mode == 0:
            output.append(read(8))
        elif mode != 255:
            code = read(mode)
            output.append(read(8) if code == len(table) else table[code])
        else:
            code = 0
            for length in range(1, maximum + 1):
                code = code << 1 | read(1)
                if (length, code) in lookup:
                    output.append(lookup[length, code])
                    break
            else:
                raise ValueError('unassigned Huffman code')
    if position != bits:
        raise ValueError('unused bits')
    return bytes(output)


def encode(header, parsed, mode, table):
    codes = codes_for(mode, table)
    output = bytearray(b'FPE1' + bytes([mode]) + struct.pack('<H', len(table)) + table
                       + struct.pack('<H', len(header)) + header)
    total_bits = 0
    for fixed, values in parsed:
        bits, packed = pack(values, codes)
        output += fixed + struct.pack('<I', bits) + packed
        total_bits += bits
    return bytes(output), total_bits


def decode(data):
    reader = Reader(data)
    if reader.take(4) != b'FPE1':
        raise ValueError('not FPE1')
    mode = reader.take(1)[0]
    table = reader.take(reader.u16())
    original = reader.take(reader.u16())
    header_reader = Reader(original)
    _, frames = parse_header(header_reader)
    header_reader.end()
    output = bytearray(original)
    while frames:
        count = reader.u16()
        if not 1 <= count <= frames:
            raise ValueError('invalid group count')
        fixed = reader.take(192 * count)
        masks = reader.take(480 * count)
        bits = int.from_bytes(reader.take(4), 'little')
        values = unpack(reader.take((bits + 7) // 8), bits,
                        sum(b.bit_count() for b in masks), mode, table)
        if 0 in values:
            raise ValueError('zero nonzero correction')
        output += struct.pack('<H', count) + fixed + masks + values
        frames -= count
    reader.end()
    return bytes(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.raw.read_bytes()
    if sha(data) != EXPECTED_SHA:
        raise ValueError('unexpected source candidate')
    header, parsed = groups(data)
    histogram = Counter(value for _, values in parsed for value in values)
    ranked = sorted(histogram, key=lambda value: (-histogram[value], value))
    variants = [('raw', 0, b'')]
    variants += [(f'prefix{k}', k, bytes(ranked[:(1 << k) - 1])) for k in range(2, 7)]
    variants += [('huffman', 255, huffman_lengths(histogram))]
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='cb7031f', input_sha256=sha(data),
                  input_bytes=len(data), frames=4971, groups=len(parsed),
                  value_bytes=sum(histogram.values()), input_header_bytes=len(header),
                  no_additional_pixel_changes=True, player_changed=False,
                  hot_path_delta_tstates=0, complete=False, rows=[])
    for name, mode, table in variants:
        converted, bits = encode(header, parsed, mode, table)
        if decode(converted) != data:
            raise AssertionError('serialized source stream changed')
        (args.cache / (name + '.raw')).write_bytes(converted)
        codes = codes_for(mode, table)
        length_counts = Counter()
        for value, count in histogram.items():
            length_counts[codes[value][1]] += count
        row = dict(name=name, mode=mode, table=list(table), raw_bytes=len(converted),
                   encoded_value_bits=bits, mean_value_bits=bits / sum(histogram.values()),
                   code_length_value_counts=dict(sorted(length_counts.items())),
                   maximum_code_bits=max(length_counts),
                   stream_sha256=sha(converted), exact_serialized_round_trip=True,
                   deflate={str(n): measure(converted, n) for n in (8192, len(converted))})
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in row.items() if k != 'table'}), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
