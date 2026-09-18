"""FPD1: contextual frequency/XOR corrections or final bitmap bytes.

Header: magic, value kind u8 (0 frequency, 1 XOR, 2 direct), context count
u8, original FPR1 header length u16, header, predictor map 256 bytes,
256 canonical lengths/context. Groups retain FPC2 framing but their masks
use the FPC3 group-split layout. Attributes stay XOR in every value kind.
Direct values may be zero. The independent causal decoder also reconstructs
the original frequency FPR1, proving masks/vectors/pixels unchanged.
Offline storage prototype; no integrated player or frame delivery claim.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_context_values import Decoder, pack
from probe_context_masks import permute, unpermute
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, EXPECTED_SHA, groups, parse_header, codes_for
from probe_motion_metadata import transform, restore
import probe_motion_alphabet as alphabet
import probe_fine_motion as motion
import probe_motion_residual_order as ordering

KINDS = ['frequency', 'xor', 'direct']


def encode(raw, prediction, values_matrix, kind, mapping, tables):
    header, parsed = groups(raw)
    frames = int.from_bytes(header[31:35], 'little')
    if prediction.shape != (frames, 3840) or values_matrix.shape != prediction.shape:
        raise ValueError('input shape')
    if kind not in range(3) or len(mapping) != 256 or not 2 <= len(tables) <= 255 or max(mapping) >= len(tables)-1:
        raise ValueError('invalid kind/map/context count')
    output = bytearray(b'FPD1'+bytes([kind, len(tables)])+struct.pack('<H', len(header))+header+bytes(mapping)+b''.join(tables))
    codes = [codes_for(255, table) for table in tables]
    mapping = np.array(mapping, dtype=np.uint8)
    attributes = np.arange(3840) % 20 >= 16
    start = total = 0
    for fixed, _ in parsed:
        n = int.from_bytes(fixed[:2], 'little')
        if not 1 <= n <= 8:
            raise ValueError('group size')
        masks = fixed[2+n*192:]
        active = np.unpackbits(np.frombuffer(masks, dtype=np.uint8)).reshape(n, 3840).astype(bool)
        contexts = mapping[prediction[start:start+n]]
        contexts[:, attributes] = len(tables)-1
        bits, data = pack(values_matrix[start:start+n][active].tobytes(), contexts[active], codes)
        v = transform(fixed[2:2+n*192], 192, 2)
        m = transform(permute(masks, n, 2), 480, 4)
        output += struct.pack('<HHH', n, len(v), len(m))+v+m+struct.pack('<I', bits)+data
        start += n; total += bits
    return bytes(output), total


def decode(data):
    r = Reader(data)
    if r.take(4) != b'FPD1':
        raise ValueError('not FPD1')
    kind, contexts = r.take(2)
    if kind not in range(3) or contexts < 2:
        raise ValueError('kind/context count')
    header = r.take(r.u16())
    hr = Reader(header)
    _, remaining = parse_header(hr)
    hr.end()
    symbols = [list(header[4+i*4:8+i*4]) for i in range(4)]
    if any(sorted(row) != [0, 1, 2, 3] or row[0] != i for i, row in enumerate(symbols)):
        raise ValueError('invalid original alphabet')
    inverse = [[row.index(target) for target in range(4)] for row in symbols]
    offset_count = header[30]
    offsets = [struct.unpack_from('<bb', header, 35+2*i) for i in range(offset_count)]
    mapping = r.take(256)
    if max(mapping) >= contexts-1:
        raise ValueError('invalid map')
    decoder = Decoder([r.take(256) for _ in range(contexts)], allow_zero=(kind == 2))
    output, frames = bytearray(header), bytearray()
    previous = bytes(3840)
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(remaining, 8):
            raise ValueError('group size')
        vectors = restore(r.take(vl), n, 192, 2)
        masks = unpermute(restore(r.take(ml), n, 480, 4), n, 2)
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
                        address, predicted = y*32+byte_x, 0
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
                    current = predicted
                    if masks[flag//8] & (128 >> (flag % 8)):
                        value = decoder.value(context)
                        if field >= 16 or kind == 1:
                            current = predicted ^ value
                        elif kind == 2:
                            current = value
                        else:
                            current = sum(symbols[(predicted >> s) & 3][(value >> s) & 3] << s for s in (6, 4, 2, 0))
                        if current == predicted:
                            raise ValueError('active mask has unchanged value')
                        original = (current ^ predicted) if field >= 16 else sum(
                            inverse[(predicted >> s) & 3][(current >> s) & 3] << s for s in (6, 4, 2, 0))
                        values.append(original)
                    screen[address] = current
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
    p.add_argument('--variants', nargs='+', default=['frequency:64', 'xor:64', 'direct:16', 'direct:32', 'direct:64'])
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.raw.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected FPR1')
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[name] for name in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected states')
    symbols = np.frombuffer(raw[4:20], dtype=np.uint8).reshape(4, 4)
    remapped = alphabet.remap(states, residual, symbols)
    offsets = [(0, 0)]+[(x, y) for y in range(-4, 5) for x in range(-4, 5) if x or y]
    if b'FPR1'+symbols.tobytes()+ordering.encode(motion.encode(vectors, remapped, 8, offsets, 8), 8) != raw:
        raise ValueError('cache does not reproduce source')
    order = ordering.field_order(8)
    prediction = (states ^ residual)[:, order]
    direct = states.copy(); direct[:, 3072:] = residual[:, 3072:]
    matrices = [m[:, order] for m in (remapped, residual, direct)]
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    if not profile['complete'] or profile['input_sha256'] != sha(raw) or profile['states_sha256'] != sha(states.tobytes()):
        raise ValueError('profile mismatch')
    report = dict(scope=__doc__, baseline_commit='fbf351e', input_sha256=sha(raw),
        states_sha256=sha(states.tobytes()), frames=4971, no_additional_pixel_changes=True,
        player_changed=False, integrated_player_delta_tstates=0, complete=False, rows=[])
    args.cache.mkdir(parents=True, exist_ok=True)
    for variant in args.variants:
        name, count = variant.split(':'); kind, count = KINDS.index(name), int(count)
        model = next(row for row in profile['rows'] if row['name'] == name)
        candidate = next(row for row in model['groups'] if row['bitmap_contexts'] == count)
        data, bits = encode(raw, prediction, matrices[kind], kind, candidate['context_map'], [bytes(t) for t in candidate['tables']])
        restored, frames = decode(data)
        if restored != raw or frames != states.tobytes() or bits != candidate['bits']:
            raise AssertionError('independent full-movie restoration differs')
        stem = f'{name}_{count}'
        (args.cache/(stem+'.raw')).write_bytes(data)
        row = dict(name=stem, kind=kind, bitmap_contexts=count, raw_bytes=len(data),
            sha256=sha(data), bits=bits, exact_fpr1_restoration=True,
            exact_causal_frame_decode=True, decoded_states_sha256=sha(frames),
            deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
