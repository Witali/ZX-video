"""FSF1: separate Huffman bits and complete fragment payloads per FHF1 group.

Preserves group boundaries, metadata, code tables and selected modes. The
group bit count now covers Huffman only, followed by byte-aligned fragment
payloads. Their total size is determined by the vector bytes, without a new
length field. Independent causal decoding rebuilds the original FHF1 stream
byte for byte. No Spectrum two-cursor/window implementation is claimed.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_context_values import Decoder
from probe_fast_fragments import SIZES
from probe_hybrid_tiles import Writer, MAX_CODED, OFFSETS
from probe_lossless_layouts import sha, measure
from probe_motion_entropy import Reader, codes_for
from probe_motion_residual_order import field_order
from probe_spatial_contexts import read_header, read_group


def bit_value(data, position, length):
    byte, offset = divmod(position, 8)
    width = (offset+length+7)//8
    return (int.from_bytes(data[byte:byte+width], 'big') >> (8*width-offset-length)) & ((1 << length)-1)


def split(source, states, vectors, residual):
    r = Reader(source)
    model, _, count, mapping, tables = read_header(r, magic=b'FHF1')
    if model != 0 or states.shape != (count, 3840) or residual.shape != states.shape or vectors.shape != (count, 192):
        raise ValueError('unexpected source model/shapes')
    out = bytearray(b'FSF1'+source[4:r.pos])
    codes = [codes_for(255, t) for t in tables]
    order = field_order(8).reshape(192, 20)[:, :16]
    groups, first = [], 0
    while first < count:
        group_start = r.pos
        n, flags, bits, vv, bm, at, encoded = read_group(r, count-first, fast_fragments=True)
        metadata = source[group_start+11:r.pos-len(encoded)]
        vl, ml = struct.unpack_from('<HH', source, group_start+2)
        writer, literals, position, padding = Writer(), bytearray(), 0, 0
        def copy_code(context, value):
            nonlocal position
            code, length = codes[context][value]
            if not length or position+length > bits or bit_value(encoded, position, length) != code:
                raise ValueError('input code differs from cached frame')
            writer.put(code, length); position += length
        for frame in range(n):
            index = first+frame
            for tile, vector in enumerate(vv[frame*192:(frame+1)*192]):
                if vector >= 85:
                    aligned = (position+7)//8*8
                    if aligned > position and bit_value(encoded, position, aligned-position):
                        raise ValueError('nonzero source padding')
                    size = SIZES[vector]
                    if aligned+size*8 > bits:
                        raise ValueError('truncated source fragment')
                    literals.extend(encoded[aligned//8:aligned//8+size])
                    padding += aligned-position; position = aligned+size*8
                else:
                    if vectors[index, tile] != vector:
                        raise ValueError('source predictor differs')
                    for field, address in enumerate(order[tile]):
                        mask = bm[frame*384+tile*2+field//8] & (128 >> (field % 8))
                        if bool(mask) != bool(residual[index, address]):
                            raise ValueError('source mask differs')
                        if mask:
                            prediction = int(states[index, address] ^ residual[index, address])
                            copy_code(mapping[prediction], int(states[index, address]))
            for field in range(768):
                mask = at[frame*96+field//8] & (128 >> (field % 8))
                if bool(mask) != bool(residual[index, 3072+field]):
                    raise ValueError('attribute mask differs')
                if mask:
                    copy_code(len(tables)-1, int(residual[index, 3072+field]))
        if position != bits:
            raise ValueError('incomplete source group')
        entropy = writer.finish()
        if len(entropy)+len(literals) > MAX_CODED:
            raise ValueError('split group exceeds fixture capacity')
        out.extend(struct.pack('<HHHBI', n, vl, ml, flags, writer.bits)+metadata+entropy+literals)
        groups.append(dict(start=first, frames=n, original_bits=bits, huffman_bits=writer.bits,
            literal_bytes=len(literals), removed_alignment_bits=padding, combined_bytes=len(entropy)+len(literals)))
        first += n
    r.end()
    return bytes(out), groups


def restore(data):
    """No encoder arrays: all predictors use previously restored bytes."""
    r = Reader(data)
    model, _, count, mapping, tables = read_header(r, magic=b'FSF1')
    if model != 0:
        raise ValueError('unsupported split context')
    original = bytearray(b'FHF1'+data[4:r.pos])
    decoder, codes = Decoder(tables, allow_zero=True), [codes_for(255, t) for t in tables]
    previous, output, remaining = bytes(3840), bytearray(), count
    while remaining:
        start = r.pos
        n, flags, bits, vectors, bm, at, encoded = read_group(r, remaining, fast_fragments=True)
        metadata = data[start+11:r.pos-len(encoded)]
        vl, ml = struct.unpack_from('<HH', data, start+2)
        literal_size = sum(SIZES.get(vector, 0) for vector in vectors)
        if len(encoded)+literal_size > MAX_CODED:
            raise ValueError('split group exceeds capacity')
        literal, offset, writer = r.take(literal_size), 0, Writer()
        decoder.begin(encoded, bits)
        def value(context):
            current = decoder.value(context)
            writer.put(*codes[context][current])
            return current
        for frame in range(n):
            screen = bytearray(previous)
            for tile, vector in enumerate(vectors[frame*192:(frame+1)*192]):
                ty, tx = divmod(tile, 16)
                if vector >= 85:
                    size = SIZES[vector]
                    payload = literal[offset:offset+size]; offset += size
                    writer.literal(payload)
                    if vector == 85:
                        fragment = payload
                    elif vector == 86:
                        fragment = payload*8
                    elif vector == 88:
                        fragment = payload*16
                    else:
                        selector = payload[4]
                        if selector & 128 or not selector or payload[:2] == payload[2:4]:
                            raise ValueError('noncanonical row fragment')
                        fragment = b''.join(payload[2:4] if selector & (128 >> row) else payload[:2] for row in range(8))
                    for field, current in enumerate(fragment):
                        screen[(ty*8+field//2)*32+tx*2+field % 2] = current
                    continue
                dx, dy = OFFSETS[vector] if vector < 81 else (0, 0)
                for field in range(16):
                    y, x = ty*8+field//2, tx*2+field % 2
                    address, prediction, sy = y*32+x, 0, y-dy
                    if vector == 82:
                        prediction = screen[address-32] if y else 0
                    elif vector == 83:
                        prediction = screen[address-1] if x else 0
                    elif vector == 84:
                        prediction = screen[address-64] if y >= 2 else 0
                    elif vector < 81 and 0 <= sy < 96:
                        for pixel in range(4):
                            sx = x*4+pixel-dx
                            if 0 <= sx < 128:
                                prediction |= ((previous[sy*32+sx//4] >> (6-2*(sx % 4))) & 3) << (6-2*pixel)
                    current = prediction
                    if bm[frame*384+tile*2+field//8] & (128 >> (field % 8)):
                        current = value(mapping[prediction])
                        if current == prediction:
                            raise ValueError('unchanged correction')
                    screen[address] = current
            for field in range(768):
                if at[frame*96+field//8] & (128 >> (field % 8)):
                    correction = value(len(tables)-1)
                    if not correction:
                        raise ValueError('zero attribute correction')
                    screen[3072+field] ^= correction
            previous = bytes(screen); output.extend(previous)
        if decoder.position != bits or offset != literal_size:
            raise ValueError('unused split payload')
        original.extend(struct.pack('<HHHBI', n, vl, ml, flags, writer.bits)+metadata+writer.finish())
        remaining -= n
    r.end()
    return bytes(original), bytes(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--raw-output', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.input.read_bytes()
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    split_data, groups = split(source, states, vectors, residual)
    original, restored = restore(split_data)
    if original != source or restored != states.tobytes():
        raise AssertionError('causal inverse differs')
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_bytes(split_data)
    report = dict(scope=__doc__, complete=True, baseline_commit='6c5c818', input_sha256=sha(source),
        sha256=sha(split_data), states_sha256=sha(restored), frames=len(states),
        exact_original_stream_roundtrip=True, exact_causal_frame_decode=True,
        original_bytes=len(source), raw_bytes=len(split_data), raw_delta_bytes=len(split_data)-len(source),
        huffman_bits=sum(g['huffman_bits'] for g in groups), literal_bytes=sum(g['literal_bytes'] for g in groups),
        removed_alignment_bits=sum(g['removed_alignment_bits'] for g in groups),
        max_group_bytes=max(g['combined_bytes'] for g in groups), groups=groups,
        deflate_8192=measure(split_data, 8192), player_changed=False, integrated_player_delta_tstates=0,
        full_z80_reconstruction_verified=False, full_frame_delivery_measured=False,
        two_input_cursors_and_stream_windows_not_implemented=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'groups'}), flush=True)


if __name__ == '__main__':
    main()
