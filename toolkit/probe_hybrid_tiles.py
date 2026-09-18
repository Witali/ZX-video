"""FHT1: direct Huffman tiles or byte-aligned 16-byte literal bitmap tiles.

Header: FHT1, context count u8, FPR1 header length u16/header, map256,
canonical lengths256/context. Group: n/vlen/mlen u16, cache flags u8,
bit count u32, transformed vectors, transformed masks, mixed bitstream.
Vector 82 is literal (zero bitmap mask); 0..81 retain FPD1 prediction.
Masks are all tile-order bitmap masks, then raster-order attribute masks.
Per frame, tile bitmap values precede raster XOR attributes. Literals skip
zero bits to the next byte then read 16 bytes. Bits include inline padding,
but not final group padding. Cache flag bit7 describes the first frame.
Groups have <=8 frames and <=9215 coded bytes. Offline, not a disk player.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_context_values import Decoder
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, parse_header, codes_for
from probe_motion_metadata import transform, restore
from probe_motion_residual_order import field_order
import probe_motion_alphabet as alphabet

MAX_CODED = 9215
OFFSETS = [(0, 0)]+[(x, y) for y in range(-4, 5) for x in range(-4, 5) if x or y]


class Writer:
    def __init__(self):
        self.data, self.acc, self.filled, self.bits = bytearray(), 0, 0, 0

    def put(self, code, size):
        if not size:
            raise ValueError('uncoded value')
        self.acc = (self.acc << size) | code
        self.filled += size; self.bits += size
        while self.filled >= 8:
            self.filled -= 8
            self.data.append((self.acc >> self.filled) & 255)
        self.acc &= (1 << self.filled)-1

    def literal(self, data):
        if self.filled:
            self.put(0, 8-self.filled)
        self.data += data; self.bits += 8*len(data)

    def snapshot(self):
        return len(self.data), self.acc, self.filled, self.bits

    def rewind(self, snapshot):
        length, self.acc, self.filled, self.bits = snapshot
        del self.data[length:]

    def finish(self):
        return bytes(self.data)+(bytes([self.acc << (8-self.filled)]) if self.filled else b'')


def read_header(r):
    if r.take(4) != b'FHT1':
        raise ValueError('not FHT1')
    count = r.take(1)[0]
    original = r.take(r.u16())
    hr = Reader(original)
    _, frames = parse_header(hr); hr.end()
    offsets = [struct.unpack_from('<bb', original, 35+2*i) for i in range(original[30])]
    if count < 2 or offsets != OFFSETS:
        raise ValueError('invalid contexts/motion alphabet')
    mapping, tables = r.take(256), [r.take(256) for _ in range(count)]
    if max(mapping) >= count-1:
        raise ValueError('invalid context map')
    return original, frames, offsets, mapping, tables


def read_group(r, remaining):
    n, vl, ml = r.u16(), r.u16(), r.u16()
    flags = r.take(1)[0]
    bits = int.from_bytes(r.take(4), 'little')
    if not 1 <= n <= min(8, remaining) or (bits+7)//8 > MAX_CODED:
        raise ValueError('invalid group size')
    vectors = restore(r.take(vl), n, 192, 2)
    masks = restore(r.take(ml), n, 480, 4)
    if any(v > 82 for v in vectors):
        raise ValueError('invalid vector')
    wanted = sum(int(any(0 < v < 81 for v in vectors[i*192:(i+1)*192])) << (7-i) for i in range(n))
    if flags != wanted:
        raise ValueError('invalid motion cache flags')
    bm, at = masks[:n*384], masks[n*384:]
    if any(v == 82 and bm[2*i:2*i+2] != b'\0\0' for i, v in enumerate(vectors)):
        raise ValueError('literal has bitmap corrections')
    encoded = r.take((bits+7)//8)
    if bits % 8 and encoded[-1] & ((1 << (8-bits % 8))-1):
        raise ValueError('nonzero final group padding')
    return n, flags, bits, vectors, bm, at, encoded


def encode(original, states, vectors, residual, mapping, tables, threshold, *, cap=MAX_CODED):
    """threshold=None: unchanged motion, 0: all changed tiles, >0: bit cost.

    Control and positive thresholds retain the original predictor for each
    nonliteral tile. The all-changed variant explicitly uses vector0 for
    same-position unchanged tiles and literal82 otherwise.
    """
    hr = Reader(original); _, count = parse_header(hr); hr.end()
    if states.shape != (count, 3840) or residual.shape != states.shape or vectors.shape != (count, 192):
        raise ValueError('input shape')
    if not 1 <= cap <= MAX_CODED or threshold is not None and threshold < 0:
        raise ValueError('invalid cap/threshold')
    bm_order = field_order(8).reshape(192, 20)[:, :16]
    current = states[:, bm_order]
    predicted = (states ^ residual)[:, bm_order]
    active = current != predicted
    contexts = np.asarray(list(mapping), dtype=np.uint8)[predicted]
    lengths = np.asarray([list(t) for t in tables], dtype=np.uint8)
    if np.any(active & (lengths[contexts, current] == 0)):
        raise ValueError('uncoded bitmap value')
    cost = (lengths[contexts, current]*active).sum(axis=2)
    vectors = vectors.copy()
    if threshold is None:
        literals = np.zeros(vectors.shape, dtype=bool)
    elif threshold == 0:
        previous = np.zeros_like(current); previous[1:] = current[:-1]
        literals = np.any(current != previous, axis=2)
        vectors[:] = 0
    else:
        literals = cost >= threshold
    vectors[literals] = 82
    if threshold == 0:
        active[:] = False
    else:
        active[literals] = False
    bm = np.packbits(active.reshape(count, 3072), axis=1)
    attr_active = residual[:, 3072:] != 0
    at = np.packbits(attr_active, axis=1)
    codes = [codes_for(255, t) for t in tables]
    out = bytearray(b'FHT1'+bytes([len(tables)])+struct.pack('<H', len(original))+original+mapping+b''.join(tables))
    writer, group_start, index = Writer(), 0, 0
    groups, rows = [], []

    def flush(end):
        nonlocal writer, group_start
        n = end-group_start
        v = transform(vectors[group_start:end].tobytes(), 192, 2)
        m = transform(bm[group_start:end].tobytes()+at[group_start:end].tobytes(), 480, 4)
        flags = sum(int(np.any((vectors[i] > 0) & (vectors[i] < 81))) << (7-i+group_start) for i in range(group_start, end))
        encoded = writer.finish()
        out.extend(struct.pack('<HHHBI', n, len(v), len(m), flags, writer.bits)+v+m+encoded)
        groups.append(dict(start=group_start, frames=n, bits=writer.bits, encoded_bytes=len(encoded), cache_flags=flags))
        group_start, writer = end, Writer()

    while index < count:
        saved = writer.snapshot()
        huff_values = 0
        for tile in range(192):
            if literals[index, tile]:
                writer.literal(current[index, tile].tobytes())
            else:
                for field in np.flatnonzero(active[index, tile]):
                    writer.put(*codes[contexts[index, tile, field]][current[index, tile, field]])
                    huff_values += 1
        for field in np.flatnonzero(attr_active[index]):
            writer.put(*codes[-1][residual[index, 3072+field]])
            huff_values += 1
        if (writer.bits+7)//8 > cap:
            if index == group_start:
                raise ValueError('one frame exceeds group capacity')
            writer.rewind(saved); flush(index)
            continue
        rows.append(dict(index=index, bits=writer.bits-saved[3], values=huff_values,
            literals=int(literals[index].sum()), cache=bool(np.any((vectors[index] > 0) & (vectors[index] < 81)))))
        index += 1
        if index-group_start == 8 or index == count:
            flush(index)
    return bytes(out), dict(groups=groups, frames=rows)


def decode(data):
    r = Reader(data)
    _, remaining, offsets, mapping, tables = read_header(r)
    decoder = Decoder(tables, allow_zero=True)
    output, previous, rows = bytearray(), bytes(3840), []
    while remaining:
        n, flags, bits, vectors, bm, at, encoded = read_group(r, remaining)
        decoder.begin(encoded, bits)
        for frame in range(n):
            screen, start, values, literals = bytearray(previous), decoder.position, 0, 0
            for tile in range(192):
                ty, tx = divmod(tile, 16)
                vector = vectors[frame*192+tile]
                if vector == 82:
                    end = (decoder.position+7)//8*8
                    for bit in range(decoder.position, end):
                        if decoder.data[bit//8] & (128 >> (bit % 8)):
                            raise ValueError('nonzero inline padding')
                    if end+128 > bits:
                        raise ValueError('truncated literal')
                    literal = decoder.data[end//8:end//8+16]
                    decoder.position = end+128; literals += 1
                else:
                    dx, dy = offsets[vector] if vector < 81 else (0, 0)
                for field in range(16):
                    y, bx = ty*8+field//2, tx*2+field % 2
                    address = y*32+bx
                    if vector == 82:
                        screen[address] = literal[field]
                        continue
                    predicted, sy = 0, y-dy
                    if vector < 81 and 0 <= sy < 96:
                        for pixel in range(4):
                            sx = bx*4+pixel-dx
                            if 0 <= sx < 128:
                                predicted |= ((previous[sy*32+sx//4] >> (6-2*(sx % 4))) & 3) << (6-2*pixel)
                    flag = frame*3072+tile*16+field
                    if bm[flag//8] & (128 >> (flag % 8)):
                        current = decoder.value(mapping[predicted]); values += 1
                        if current == predicted:
                            raise ValueError('unchanged correction')
                        screen[address] = current
                    else:
                        screen[address] = predicted
            for field in range(768):
                flag = frame*768+field
                if at[flag//8] & (128 >> (flag % 8)):
                    value = decoder.value(len(tables)-1); values += 1
                    if not value:
                        raise ValueError('zero attribute correction')
                    screen[3072+field] ^= value
            rows.append(dict(index=len(rows), bits=decoder.position-start, values=values, literals=literals,
                cache=bool(flags & (128 >> frame))))
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
    p.add_argument('--variants', nargs='+', default=['control', '128', '96', '64', 'all'])
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    fpd = args.fpd.read_bytes(); r = Reader(fpd)
    if sha(fpd) != 'a0f2ad8434576ff0a233d6066558383ba3c4fe9ebf4eb898b0a634125a874fd3' or r.take(5) != b'FPD1\x02':
        raise ValueError('unexpected direct/16 input')
    count = r.take(1)[0]; original = r.take(r.u16())
    mapping, tables = r.take(256), [r.take(256) for _ in range(count)]
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected source states')
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='608e57b', complete=False,
        input_sha256=sha(fpd), states_sha256=sha(states.tobytes()), no_additional_pixel_changes=True,
        player_changed=False, integrated_player_delta_tstates=0, rows=[])
    for name in args.variants:
        threshold = None if name == 'control' else 0 if name == 'all' else int(name)
        data, detail = encode(original, states, vectors, residual, mapping, tables, threshold)
        restored, decoded_rows = decode(data)
        if restored != states.tobytes() or detail['frames'] != decoded_rows:
            raise AssertionError('independent causal restoration differs')
        (args.cache/(name+'.raw')).write_bytes(data)
        (args.cache/(name+'.frames.json')).write_text(json.dumps(detail, indent=2)+'\n', encoding='utf-8')
        row = dict(name=name, threshold=threshold, frames=len(decoded_rows), raw_bytes=len(data), sha256=sha(data),
            exact_causal_frame_decode=True, decoded_states_sha256=sha(restored), groups=len(detail['groups']),
            max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
            bits=sum(f['bits'] for f in decoded_rows), values=sum(f['values'] for f in decoded_rows),
            literals=sum(f['literals'] for f in decoded_rows), cache_frames=sum(f['cache'] for f in decoded_rows),
            deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
