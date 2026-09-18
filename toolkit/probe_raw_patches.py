"""FHR1: byte-aligned raw corrections on selected tiles, Huffman elsewhere.

Header: FHR1, raw kind u8 (0 direct, 1 XOR, 2 frequency alphabet), context
count u8, FPR1 header length u16/header, map256, canonical lengths/context.
Groups have FHT1 framing: n/vlen/mlen u16, motion flags u8, bits u32,
vectors, two-level sparse masks, mixed bitstream. Vector bit7 selects raw
corrections; low7 retains the original vector0..81. Raw tiles align once
to a byte boundary and transmit only masked bytes. Attributes remain
Huffman XOR, raster ordered. Masks/prediction/pixels unchanged.
Offline codec, not an integrated Z80 player or a disk delivery claim.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_context_values import Decoder
from probe_hybrid_tiles import Writer, MAX_CODED, OFFSETS
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, parse_header, codes_for
from probe_motion_metadata import transform, restore
from probe_motion_residual_order import field_order
import probe_motion_alphabet as alphabet

KINDS = ('direct', 'xor', 'frequency')


def read_header(r):
    if r.take(4) != b'FHR1':
        raise ValueError('not FHR1')
    kind, count = r.take(2)
    original = r.take(r.u16())
    hr = Reader(original); _, frames = parse_header(hr); hr.end()
    offsets = [struct.unpack_from('<bb', original, 35+2*i) for i in range(original[30])]
    mapping, tables = r.take(256), [r.take(256) for _ in range(count)]
    symbols = [list(original[4+4*i:8+4*i]) for i in range(4)]
    if (kind >= 3 or count < 2 or max(mapping) >= count-1 or offsets != OFFSETS
            or any(sorted(row) != list(range(4)) or row[0] != i for i, row in enumerate(symbols))):
        raise ValueError('invalid header')
    return kind, original, frames, mapping, tables, symbols


def read_group(r, remaining):
    n, vl, ml = r.u16(), r.u16(), r.u16()
    flags, bits = r.take(1)[0], int.from_bytes(r.take(4), 'little')
    if not 1 <= n <= min(8, remaining) or (bits+7)//8 > MAX_CODED:
        raise ValueError('invalid group size')
    vectors = restore(r.take(vl), n, 192, 2)
    masks = restore(r.take(ml), n, 480, 4)
    if any((v & 127) > 81 for v in vectors):
        raise ValueError('invalid vector')
    wanted = sum(int(any(0 < (v & 127) < 81 for v in vectors[192*i:192*(i+1)])) << (7-i) for i in range(n))
    bm, at = masks[:n*384], masks[n*384:]
    if flags != wanted or any(v & 128 and bm[2*i:2*i+2] == b'\0\0' for i, v in enumerate(vectors)):
        raise ValueError('invalid cache flags/empty raw tile')
    data = r.take((bits+7)//8)
    if bits % 8 and data[-1] & ((1 << (8-bits % 8))-1):
        raise ValueError('nonzero final padding')
    return n, flags, bits, vectors, bm, at, data


def encode(original, states, vectors, residual, mapping, tables, kind, threshold, *, cap=MAX_CODED):
    if kind not in range(3) or threshold is not None and threshold < 0 or not 1 <= cap <= MAX_CODED:
        raise ValueError('invalid options')
    hr = Reader(original); _, frames = parse_header(hr); hr.end()
    if states.shape != (frames, 3840) or residual.shape != states.shape or vectors.shape != (frames, 192):
        raise ValueError('input shape')
    order = field_order(8).reshape(192, 20)[:, :16]
    current, predicted = states[:, order], (states ^ residual)[:, order]
    active = current != predicted
    contexts = np.asarray(list(mapping), dtype=np.uint8)[predicted]
    lengths = np.asarray([list(t) for t in tables], dtype=np.uint8)
    cost = (lengths[contexts, current]*active).sum(axis=2)
    raw_tiles = np.zeros(vectors.shape, dtype=bool) if threshold is None else (cost >= threshold) & active.any(axis=2)
    vectors = vectors.copy(); vectors[raw_tiles] |= 128
    if kind == 0:
        raw_values = current
    elif kind == 1:
        raw_values = residual[:, order]
    else:
        raw_values = alphabet.remap(states, residual, np.frombuffer(original[4:20], dtype=np.uint8).reshape(4, 4))[:, order]
    bm = np.packbits(active.reshape(frames, 3072), axis=1)
    attr_active = residual[:, 3072:] != 0
    at = np.packbits(attr_active, axis=1)
    codes = [codes_for(255, t) for t in tables]
    out = bytearray(b'FHR1'+bytes([kind, len(tables)])+struct.pack('<H', len(original))+original+mapping+b''.join(tables))
    writer, start, index, groups, rows = Writer(), 0, 0, [], []

    def flush(end):
        nonlocal writer, start
        n = end-start
        v = transform(vectors[start:end].tobytes(), 192, 2)
        m = transform(bm[start:end].tobytes()+at[start:end].tobytes(), 480, 4)
        flags = sum(int(np.any(((vectors[i] & 127) > 0) & ((vectors[i] & 127) < 81))) << (7-i+start) for i in range(start, end))
        data = writer.finish()
        out.extend(struct.pack('<HHHBI', n, len(v), len(m), flags, writer.bits)+v+m+data)
        groups.append(dict(start=start, frames=n, bits=writer.bits, encoded_bytes=len(data)))
        start, writer = end, Writer()

    while index < frames:
        before, raw_count, coded_count = writer.snapshot(), 0, 0
        for tile in range(192):
            if raw_tiles[index, tile]:
                values = raw_values[index, tile][active[index, tile]].tobytes()
                writer.literal(values); raw_count += len(values)
            else:
                for field in np.flatnonzero(active[index, tile]):
                    writer.put(*codes[contexts[index, tile, field]][current[index, tile, field]])
                    coded_count += 1
        for field in np.flatnonzero(attr_active[index]):
            writer.put(*codes[-1][residual[index, 3072+field]]); coded_count += 1
        if (writer.bits+7)//8 > cap:
            if start == index:
                raise ValueError('one frame exceeds capacity')
            writer.rewind(before); flush(index)
            continue
        rows.append(dict(index=index, bits=writer.bits-before[3], raw_values=raw_count,
            coded_values=coded_count, raw_tiles=int(raw_tiles[index].sum())))
        index += 1
        if index-start == 8 or index == frames:
            flush(index)
    return bytes(out), dict(groups=groups, frames=rows)


def decode(data):
    r = Reader(data)
    kind, _, remaining, mapping, tables, symbols = read_header(r)
    decoder = Decoder(tables, allow_zero=True)
    output, previous, rows = bytearray(), bytes(3840), []
    while remaining:
        n, _, bits, vectors, bm, at, encoded = read_group(r, remaining)
        decoder.begin(encoded, bits)
        for frame in range(n):
            screen, first, raw_count, coded_count, raw_tiles = bytearray(previous), decoder.position, 0, 0, 0
            for tile in range(192):
                ty, tx = divmod(tile, 16)
                vector = vectors[frame*192+tile]
                raw = bool(vector & 128); vector &= 127
                dx, dy = OFFSETS[vector] if vector < 81 else (0, 0)
                if raw:
                    end = (decoder.position+7)//8*8
                    for bit in range(decoder.position, end):
                        if encoded[bit//8] & (128 >> (bit % 8)):
                            raise ValueError('nonzero inline padding')
                    decoder.position = end; raw_tiles += 1
                for field in range(16):
                    y, bx = ty*8+field//2, tx*2+field % 2
                    address, sy, prediction = y*32+bx, y-dy, 0
                    if vector < 81 and 0 <= sy < 96:
                        for pixel in range(4):
                            sx = bx*4+pixel-dx
                            if 0 <= sx < 128:
                                prediction |= ((previous[sy*32+sx//4] >> (6-2*(sx % 4))) & 3) << (6-2*pixel)
                    flag = frame*3072+tile*16+field
                    current = prediction
                    if bm[flag//8] & (128 >> (flag % 8)):
                        if raw:
                            if decoder.position+8 > bits:
                                raise ValueError('truncated raw value')
                            value = encoded[decoder.position//8]; decoder.position += 8; raw_count += 1
                            if kind == 1:
                                current = prediction ^ value
                            elif kind == 2:
                                current = sum(symbols[(prediction >> s) & 3][(value >> s) & 3] << s for s in (6, 4, 2, 0))
                            else:
                                current = value
                        else:
                            current = decoder.value(mapping[prediction]); coded_count += 1
                        if current == prediction:
                            raise ValueError('unchanged bitmap correction')
                    screen[address] = current
            for field in range(768):
                flag = frame*768+field
                if at[flag//8] & (128 >> (flag % 8)):
                    value = decoder.value(len(tables)-1); coded_count += 1
                    if not value:
                        raise ValueError('zero attribute correction')
                    screen[3072+field] ^= value
            rows.append(dict(index=len(rows), bits=decoder.position-first, raw_values=raw_count,
                coded_values=coded_count, raw_tiles=raw_tiles))
            previous = bytes(screen); output += previous
        if decoder.position != bits:
            raise ValueError('unused group bits')
        remaining -= n
    r.end()
    return bytes(output), rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpd', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--variants', nargs='+', default=['direct:control', 'direct:64', 'direct:32', 'direct:0', 'xor:0', 'frequency:0'])
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.fpd.read_bytes(); r = Reader(source)
    if sha(source) != 'a0f2ad8434576ff0a233d6066558383ba3c4fe9ebf4eb898b0a634125a874fd3' or r.take(5) != b'FPD1\x02':
        raise ValueError('unexpected source')
    count = r.take(1)[0]; original = r.take(r.u16())
    mapping, tables = r.take(256), [r.take(256) for _ in range(count)]
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected states')
    report = dict(scope=__doc__, baseline_commit='2de2203', input_sha256=sha(source),
        states_sha256=sha(states.tobytes()), complete=False, no_additional_pixel_changes=True,
        player_changed=False, integrated_player_delta_tstates=0, rows=[])
    args.cache.mkdir(parents=True, exist_ok=True)
    for variant in args.variants:
        name, threshold = variant.split(':')
        limit = None if threshold == 'control' else int(threshold)
        data, detail = encode(original, states, vectors, residual, mapping, tables, KINDS.index(name), limit)
        actual, rows = decode(data)
        if actual != states.tobytes() or detail['frames'] != rows:
            raise AssertionError('causal decode differs')
        stem = variant.replace(':', '_')
        (args.cache/(stem+'.raw')).write_bytes(data)
        (args.cache/(stem+'.frames.json')).write_text(json.dumps(detail, indent=2)+'\n', encoding='utf-8')
        row = dict(name=stem, kind=name, threshold=limit, raw_bytes=len(data), sha256=sha(data),
            exact_causal_frame_decode=True, decoded_states_sha256=sha(actual), frames=len(rows),
            groups=len(detail['groups']), max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
            bits=sum(f['bits'] for f in rows), raw_values=sum(f['raw_values'] for f in rows),
            coded_values=sum(f['coded_values'] for f in rows), raw_tiles=sum(f['raw_tiles'] for f in rows),
            deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
