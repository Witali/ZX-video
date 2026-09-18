"""Exact FPC2 Huffman contexts selected by the motion-predicted bitmap byte.

FPC2: magic, context count u8 (including the attribute context), original
FPR1 header length u16, header, 256-byte predictor/context map, count*256
canonical code lengths. Groups use the FPC1 metadata and bit layout.
The PC encoder uses a verified cache. The independent decoder derives every
prediction from its own preceding decoded frame; it never reads that cache.
This is a storage prototype, not an integrated player or timing result.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_context_values import Decoder, pack
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, EXPECTED_SHA, groups, parse_header, codes_for
from probe_motion_metadata import transform, restore
import probe_motion_alphabet as alphabet
import probe_fine_motion as motion
import probe_motion_residual_order as ordering


def encode(raw, prediction, mapping, tables):
    header, parsed = groups(raw)
    if prediction.shape != (int.from_bytes(header[31:35], 'little'), 3840):
        raise ValueError('prediction shape')
    if len(mapping) != 256 or not 2 <= len(tables) <= 255 or max(mapping) >= len(tables)-1:
        raise ValueError('context map')
    codes = [codes_for(255, t) for t in tables]
    output = bytearray(b'FPC2'+bytes([len(tables)])+struct.pack('<H', len(header))+header+bytes(mapping)+b''.join(tables))
    map_array = np.array(mapping, dtype=np.uint8)
    attribute = np.arange(3840) % 20 >= 16
    start = total = 0
    for fixed, values in parsed:
        n = int.from_bytes(fixed[:2], 'little')
        if not 1 <= n <= 8:
            raise ValueError('group size')
        mask = np.unpackbits(np.frombuffer(fixed[2+n*192:], dtype=np.uint8)).reshape(n, 3840).astype(bool)
        labels = map_array[prediction[start:start+n]]
        labels[:, attribute] = len(tables)-1
        bits, packed = pack(values, labels[mask], codes)
        v = transform(fixed[2:2+n*192], 192, 2)
        m = transform(fixed[2+n*192:], 480, 4)
        output += struct.pack('<HHH', n, len(v), len(m))+v+m+struct.pack('<I', bits)+packed
        total += bits
        start += n
    return bytes(output), total


def decode(data):
    r = Reader(data)
    if r.take(4) != b'FPC2':
        raise ValueError('not FPC2')
    contexts = r.take(1)[0]
    if contexts < 2:
        raise ValueError('context count')
    header = r.take(r.u16())
    hr = Reader(header)
    _, remaining = parse_header(hr)
    hr.end()
    symbols = [list(header[4+i*4:8+i*4]) for i in range(4)]
    if any(sorted(row) != [0, 1, 2, 3] or row[0] != i for i, row in enumerate(symbols)):
        raise ValueError('invalid alphabet')
    offset_count = header[30]
    offsets = [struct.unpack_from('<bb', header, 35+2*i) for i in range(offset_count)]
    mapping = r.take(256)
    if max(mapping) >= contexts-1:
        raise ValueError('invalid context map')
    decoder = Decoder([r.take(256) for _ in range(contexts)])
    output, frames = bytearray(header), bytearray()
    previous = bytes(3840)
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(remaining, 8):
            raise ValueError('invalid group size')
        vectors = restore(r.take(vl), n, 192, 2)
        masks = restore(r.take(ml), n, 480, 4)
        bits = int.from_bytes(r.take(4), 'little')
        decoder.begin(r.take((bits+7)//8), bits)
        values = bytearray()
        for frame in range(n):
            screen = bytearray(3840)
            for tile in range(192):
                ty, tx = divmod(tile, 16)
                vector = vectors[frame*192+tile]
                if vector > offset_count:
                    raise ValueError('invalid vector')
                dx, dy = offsets[vector] if vector < offset_count else (0, 0)
                for field in range(20):
                    if field < 16:
                        y, byte_x = ty*8+field//2, tx*2+field%2
                        address = y*32+byte_x
                        predicted = 0
                        sy = y-dy
                        if vector < offset_count and 0 <= sy < 96:
                            for pixel in range(4):
                                sx = byte_x*4+pixel-dx
                                if 0 <= sx < 128:
                                    level = (previous[sy*32+sx//4] >> (6-2*(sx % 4))) & 3
                                    predicted |= level << (6-2*pixel)
                        context = mapping[predicted]
                    else:
                        a = field-16
                        address = 3072+(ty*2+a//2)*32+tx*2+a%2
                        predicted = previous[address]
                        context = contexts-1
                    flag = frame*3840+tile*20+field
                    if masks[flag//8] & (128 >> (flag % 8)):
                        value = decoder.value(context)
                        values.append(value)
                        if field < 16:
                            predicted = sum(symbols[(predicted >> s) & 3][(value >> s) & 3] << s
                                            for s in (6, 4, 2, 0))
                        else:
                            predicted ^= value
                    screen[address] = predicted
            previous = bytes(screen)
            frames += previous
        if decoder.position != decoder.bits:
            raise ValueError('unused coded bits')
        output += struct.pack('<H', n)+vectors+masks+values
        remaining -= n
    r.end()
    return bytes(output), bytes(frames)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--profile', type=Path, required=True)
    p.add_argument('--clusters', type=int, nargs='+', default=[16, 32])
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.raw.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected FPR1')
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[name] for name in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected motion states')
    header, _ = groups(raw)
    offsets = [struct.unpack_from('<bb', header, 35+2*i) for i in range(header[30])]
    symbols = np.frombuffer(header[4:20], dtype=np.uint8).reshape(4, 4)
    converted = alphabet.remap(states, residual, symbols)
    if b'FPR1'+symbols.tobytes()+ordering.encode(motion.encode(vectors, converted, 8, offsets, 8), 8) != raw:
        raise ValueError('cache does not reproduce source')
    prediction = (states ^ residual)[:, ordering.field_order(8)]
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    if not profile['complete'] or profile['input_sha256'] != sha(raw) or profile['predictor_sha256'] != sha(prediction.tobytes()):
        raise ValueError('profile input mismatch')
    candidates = next(row['clustered_huffman'] for row in profile['rows'] if row['name'] == 'exact_predicted_byte')
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='8b3f83f', input_sha256=sha(raw),
        states_sha256=sha(states.tobytes()), profile_sha256=sha(args.profile.read_bytes()),
        frames=4971, no_additional_pixel_changes=True, player_changed=False,
        integrated_player_delta_tstates=0, complete=False, rows=[])
    for count in args.clusters:
        candidate = next(row for row in candidates if row['bitmap_contexts'] == count)
        tables = [bytes(t) for t in candidate['tables']]
        data, bits = encode(raw, prediction, candidate['context_map'], tables)
        restored, decoded_states = decode(data)
        if restored != raw or decoded_states != states.tobytes() or bits != candidate['bits']:
            raise AssertionError('causal full-movie reconstruction differs')
        name = f'prediction_{count}'
        (args.cache/(name+'.raw')).write_bytes(data)
        row = dict(name=name, bitmap_contexts=count, contexts=len(tables),
            raw_bytes=len(data), sha256=sha(data), encoded_value_bits=bits,
            table_file_bytes=256+256*len(tables), exact_fpr1_round_trip=True,
            exact_causal_frame_decode=True, decoded_states_sha256=sha(decoded_states),
            deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
