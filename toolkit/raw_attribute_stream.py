"""FSC2 optionally replaces attribute Huffman corrections by 768 final bytes.

One-frame FSC1 layout, flag bit 6 selects absolute attributes appended after
bitmap literals. Attribute masks must then be zero and Huffman contains only
bitmap corrections. Bit 7 still controls the temporal motion cache.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_context_values import Decoder
from probe_fast_fragments import SIZES
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_motion_metadata import transform
from probe_spatial_contexts import read_header, read_group, OFFSETS


def read_packet(r, remaining, *, extended=True):
    header = bytearray(r.take(11))
    n, vl, ml, flags, bits = struct.unpack('<HHHBI', header)
    if n != 1:
        raise ValueError('one-frame packet required')
    raw = extended and bool(flags & 64)
    if raw:
        header[6] &= ~64
    metadata = r.take(vl+ml)
    mask = r.take(80)
    encoded = r.take((bits+7)//8)
    check = Reader(bytes(header)+metadata+encoded)
    group = read_group(check, remaining, fast_fragments=True)
    check.end()
    if raw and any(group[5]):
        raise ValueError('raw attributes have correction masks')
    literals = r.take(sum(SIZES.get(v, 0) for v in group[3])+768*raw)
    return (n, flags, *group[2:], literals), mask


def packets(data):
    r = Reader(data)
    magic = data[:4]
    if magic not in (b'FSC1', b'FSC2'):
        raise ValueError('unexpected cell stream')
    model, _, count, mapping, tables = read_header(r, magic=magic)
    if model != 0:
        raise ValueError('unsupported model')
    header = data[:r.pos]
    result = [read_packet(r, count-i, extended=magic == b'FSC2') for i in range(count)]
    r.end()
    return header, tables, mapping, result


def decode(data):
    """Scalar causal replay: predictions come only from restored frames."""
    _, tables, mapping, groups = packets(data)
    decoder = Decoder(tables, allow_zero=True)
    previous, output = bytes(3840), bytearray()
    for group, _ in groups:
        _, flags, bits, vectors, bm, at, encoded, literal = group
        decoder.begin(encoded, bits)
        screen, offset = bytearray(previous), 0
        for tile, vector in enumerate(vectors):
            ty, tx = divmod(tile, 16)
            if vector >= 85:
                size = SIZES[vector]
                payload = literal[offset:offset+size]; offset += size
                if vector == 85:
                    fragment = payload
                elif vector == 86:
                    fragment = payload*8
                elif vector == 88:
                    fragment = payload*16
                else:
                    selector = payload[4]
                    if selector & 128 or not selector or payload[:2] == payload[2:4]:
                        raise ValueError('invalid row fragment')
                    fragment = b''.join(payload[2:4] if selector & (128 >> y) else payload[:2] for y in range(8))
                for field, value in enumerate(fragment):
                    screen[(ty*8+field//2)*32+tx*2+field % 2] = value
                continue
            dx, dy = OFFSETS[vector] if vector < 81 else (0, 0)
            for field in range(16):
                y, x = ty*8+field//2, tx*2+field % 2
                address, predicted, sy = y*32+x, 0, y-dy
                if vector == 82:
                    predicted = screen[address-32] if y else 0
                elif vector == 83:
                    predicted = screen[address-1] if x else 0
                elif vector == 84:
                    predicted = screen[address-64] if y >= 2 else 0
                elif vector < 81 and 0 <= sy < 96:
                    for pixel in range(4):
                        sx = x*4+pixel-dx
                        if 0 <= sx < 128:
                            predicted |= ((previous[sy*32+sx//4] >> (6-2*(sx % 4))) & 3) << (6-2*pixel)
                value = predicted
                if bm[tile*2+field//8] & (128 >> (field % 8)):
                    value = decoder.value(mapping[predicted])
                    if value == predicted:
                        raise ValueError('unchanged bitmap correction')
                screen[address] = value
        if flags & 64:
            screen[3072:] = literal[offset:offset+768]; offset += 768
        else:
            for field in range(768):
                if at[field//8] & (128 >> (field % 8)):
                    value = decoder.value(len(tables)-1)
                    if not value:
                        raise ValueError('zero attribute correction')
                    screen[3072+field] ^= value
        if decoder.position != bits or offset != len(literal):
            raise ValueError('unused frame payload')
        previous = bytes(screen); output += previous
    return bytes(output)


def pack(cells, states, selected):
    header, tables, _, groups = packets(cells)
    if cells[:4] != b'FSC1' or states.shape != (len(groups), 3840) or len(selected) != len(groups):
        raise ValueError('wrong source shape/format')
    out, rows, previous = bytearray(b'FSC2'+header[4:]), [], bytes(768)
    for index, ((group, mask), state) in enumerate(zip(groups, states)):
        n, flags, bits, vectors, bm, at, encoded, literal = group
        corrections = bytes(a ^ b for a, b in zip(state[3072:], previous))
        if np.packbits(np.frombuffer(corrections, dtype=np.uint8) != 0).tobytes() != at:
            raise ValueError('source attribute corrections differ')
        if selected[index]:
            attr_bits = sum(tables[-1][v] for v in corrections if v)
            if any(not tables[-1][v] for v in corrections if v) or attr_bits > bits:
                raise ValueError('invalid attribute codes')
            bits -= attr_bits
            encoded = bytearray(encoded[:(bits+7)//8])
            if bits % 8:
                encoded[-1] &= 255 << (8-bits % 8) & 255
            literal += state[3072:].tobytes()
            at, flags = bytes(96), flags | 64
        vv, mm = transform(vectors, 192, 2), transform(bm+at, 480, 4)
        out += struct.pack('<HHHBI', n, len(vv), len(mm), flags, bits)+vv+mm+mask+encoded+literal
        rows.append(dict(index=index, raw_attributes=bool(selected[index]),
            changed_attributes=sum(bool(v) for v in corrections), coded_bytes=len(encoded)+len(literal)+2))
        previous = state[3072:].tobytes()
    return bytes(out), rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cells', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--threshold', type=int, default=128)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    if not 1 <= args.threshold <= 768:
        p.error('threshold must be in 1..768')
    cells = args.cells.read_bytes()
    with np.load(args.states, allow_pickle=False) as source:
        states = source['states']
    if decode(cells) != states.tobytes():
        raise ValueError('input screens differ')
    attrs = states[:, 3072:]
    prior = np.zeros_like(attrs); prior[1:] = attrs[:-1]
    selected = (attrs != prior).sum(axis=1) >= args.threshold
    data, rows = pack(cells, states, selected)
    if decode(data) != states.tobytes():
        raise AssertionError('raw attributes changed screens')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    report = dict(scope=__doc__, complete=True, baseline_commit='11dc864',
        input_sha256=sha(cells), states_sha256=sha(states.tobytes()), stream_sha256=sha(data),
        threshold=args.threshold, frames=len(states), raw_attribute_frames=int(selected.sum()),
        raw_bytes=len(data), raw_delta_bytes=len(data)-len(cells),
        max_coded_input_bytes=max(row['coded_bytes'] for row in rows),
        exact_causal_frame_decode=True, no_additional_pixel_changes=True,
        full_frame_delivery_measured=False, rows=rows)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
