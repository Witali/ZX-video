"""FHS1: lossless spatial contexts for masked causal motion corrections.

The motion, masks, attributes and candidate pixels remain unchanged.
Model selection is global; above/left bytes belong to the already decoded
current frame. Frame edges use zero. This is an offline codec experiment.
FHS1: model u8, count u8, original FPR1 header length/header, context map256,
lengths256/context; then FHT1 groups. Vectors82/83/84 predict from the
current frame's above/left/second-above byte, interleaved with corrections.
Frame edges are zero; there are no literal vectors.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from prefix_huffman_z80 import prepare
from probe_context_values import Decoder
from probe_hybrid_tiles import Writer, OFFSETS, MAX_CODED
from probe_hybrid_tiles import read_header as read_fht_header
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, parse_header, codes_for
from probe_motion_metadata import transform, restore
from probe_motion_residual_order import field_order
from profile_prediction_contexts import clustered_tables

MODELS = ('motion', 'above', 'left', 'xor_above', 'xor_left',
          'joint_above', 'joint_left', 'joint_direct_above')


def model_arrays(states, residual, model):
    current = states[:, :3072].reshape(-1, 96, 32)
    predicted = (states[:, :3072] ^ residual[:, :3072]).reshape(current.shape)
    neighbour = np.zeros_like(current)
    if model in (1, 3, 5, 7):
        neighbour[:, 1:] = current[:, :-1]
    elif model in (2, 4, 6):
        neighbour[:, :, 1:] = current[:, :, :-1]
    if model == 0:
        context, values = predicted, current
    elif model in (1, 2):
        context, values = neighbour, current
    elif model in (3, 4):
        context, values = predicted ^ neighbour, current ^ neighbour
    elif model in (5, 6, 7):
        context = (predicted & 240) | (neighbour >> 4)
        values = current if model == 7 else current ^ neighbour
    else:
        raise ValueError('unknown model')
    return context.reshape(-1, 3072), values.reshape(-1, 3072)


def profile(states, residual, model, counts):
    context, values = model_arrays(states, residual, model)
    active = residual[:, :3072] != 0
    keys = context[active].astype(np.int32)*256+values[active]
    hist = np.zeros((257, 256), dtype=np.int64)
    hist[:256] = np.bincount(keys, minlength=65536).reshape(256, 256)
    attrs = residual[:, 3072:]
    hist[-1] = np.bincount(attrs[attrs != 0], minlength=256)
    groups = clustered_tables(hist, requested=counts, baseline_bits=8497717)
    for group in groups:
        try:
            layout = prepare([bytes(t) for t in group['tables']], group['context_map'])
            group['prefix_layout'] = dict(fits_existing_bank=True, depth=layout['depth'], body_bytes=layout['body_bytes'])
        except ValueError as error:
            group['prefix_layout'] = dict(fits_existing_bank=False, reason=str(error))
    return dict(name=MODELS[model], model=model, active_values=int(hist.sum()), groups=groups)


def encode(original, states, vectors, residual, model, mapping, tables, *, cap=MAX_CODED):
    hr = Reader(original); _, count = parse_header(hr); hr.end()
    if states.shape != (count, 3840) or residual.shape != states.shape or vectors.shape != (count, 192):
        raise ValueError('invalid shapes')
    if not 1 <= cap <= MAX_CODED or np.any(vectors > 84):
        raise ValueError('invalid cap/vectors')
    order = field_order(8).reshape(192, 20)[:, :16].ravel()
    labels, vals = model_arrays(states, residual, model)
    contexts = np.frombuffer(bytes(mapping), dtype=np.uint8)[labels[:, order]]
    values = vals[:, order]
    active = residual[:, order] != 0
    attrs = residual[:, 3072:] != 0
    bm, at = np.packbits(active, axis=1), np.packbits(attrs, axis=1)
    codes = [codes_for(255, table) for table in tables]
    out = bytearray(b'FHS1'+bytes([model, len(tables)])+struct.pack('<H', len(original))+original+bytes(mapping)+b''.join(tables))
    writer, start, index, groups, rows = Writer(), 0, 0, [], []

    def flush(end):
        nonlocal writer, start
        n = end-start
        v = transform(vectors[start:end].tobytes(), 192, 2)
        m = transform(bm[start:end].tobytes()+at[start:end].tobytes(), 480, 4)
        flags = sum(int(np.any((vectors[i] > 0) & (vectors[i] < 81))) << (7-i+start) for i in range(start, end))
        encoded = writer.finish()
        out.extend(struct.pack('<HHHBI', n, len(v), len(m), flags, writer.bits)+v+m+encoded)
        groups.append(dict(start=start, frames=n, bits=writer.bits, encoded_bytes=len(encoded)))
        start, writer = end, Writer()

    while index < count:
        saved = writer.snapshot()
        for field in np.flatnonzero(active[index]):
            writer.put(*codes[contexts[index, field]][values[index, field]])
        for field in np.flatnonzero(attrs[index]):
            writer.put(*codes[-1][residual[index, 3072+field]])
        if (writer.bits+7)//8 > cap:
            if index == start:
                raise ValueError('frame exceeds capacity')
            writer.rewind(saved); flush(index); continue
        rows.append(dict(index=index, bits=writer.bits-saved[3], values=int(active[index].sum()+attrs[index].sum())))
        index += 1
        if index-start == 8 or index == count:
            flush(index)
    return bytes(out), dict(groups=groups, frames=rows)


def read_header(reader, *, magic=b'FHS1'):
    if reader.take(4) != magic:
        raise ValueError('unexpected spatial magic')
    model, count = reader.take(2)
    original = reader.take(reader.u16())
    hr = Reader(original); _, frames = parse_header(hr); hr.end()
    offsets = [struct.unpack_from('<bb', original, 35+2*i) for i in range(original[30])]
    if model >= len(MODELS) or count < 2 or offsets != OFFSETS:
        raise ValueError('invalid model/contexts/offsets')
    mapping, tables = reader.take(256), [reader.take(256) for _ in range(count)]
    if max(mapping) >= count-1:
        raise ValueError('invalid context map')
    return model, original, frames, mapping, tables


def decode(data, *, fast_fragments=False):
    r = Reader(data)
    model, _, remaining, mapping, tables = read_header(r, magic=b'FHF1' if fast_fragments else b'FHS1')
    if fast_fragments and model != 0:
        raise ValueError('fast fragments require motion contexts')
    decoder = Decoder(tables, allow_zero=True)
    previous, out, rows = bytes(3840), bytearray(), []
    while remaining:
        n, _, bits, vectors, bm, at, encoded = read_group(r, remaining, fast_fragments=fast_fragments)
        decoder.begin(encoded, bits)
        for frame in range(n):
            screen, first, values = bytearray(previous), decoder.position, 0
            for tile in range(192):
                ty, tx = divmod(tile, 16)
                vector = vectors[frame*192+tile]
                if vector >= 85:
                    start = (decoder.position+7)//8*8
                    for bit in range(decoder.position, start):
                        if encoded[bit//8] & (128 >> (bit % 8)):
                            raise ValueError('nonzero fragment padding')
                    size = {85: 16, 86: 2, 87: 5, 88: 1}[vector]
                    if start+size*8 > bits:
                        raise ValueError('truncated fragment')
                    payload = encoded[start//8:start//8+size]
                    decoder.position = start+size*8
                    if vector == 85:
                        fragment = payload
                    elif vector == 86:
                        fragment = payload*8
                    elif vector == 88:
                        fragment = payload*16
                    else:
                        selector = payload[4]
                        if selector & 128 or not selector or payload[:2] == payload[2:4]:
                            raise ValueError('noncanonical two-row fragment')
                        fragment = b''.join(payload[2:4] if selector & (128 >> row) else payload[:2]
                                            for row in range(8))
                    for field, value in enumerate(fragment):
                        screen[(ty*8+field//2)*32+tx*2+field % 2] = value
                    continue
                dx, dy = OFFSETS[vector] if vector < 81 else (0, 0)
                for field in range(16):
                    y, bx = ty*8+field//2, tx*2+field % 2
                    address, predicted = y*32+bx, 0
                    sy = y-dy
                    if vector == 82:
                        predicted = screen[address-32] if y else 0
                    elif vector == 83:
                        predicted = screen[address-1] if bx else 0
                    elif vector == 84:
                        predicted = screen[address-64] if y >= 2 else 0
                    elif vector < 81 and 0 <= sy < 96:
                        for pixel in range(4):
                            sx = bx*4+pixel-dx
                            if 0 <= sx < 128:
                                predicted |= ((previous[sy*32+sx//4] >> (6-2*(sx % 4))) & 3) << (6-2*pixel)
                    flag = frame*3072+tile*16+field
                    current = predicted
                    if bm[flag//8] & (128 >> (flag % 8)):
                        # Scalar decoder computes its neighbours from values
                        # it has actually restored, never encoder matrices.
                        neighbour = (screen[address-32] if y else 0) if model in (1, 3, 5, 7) else (screen[address-1] if bx else 0)
                        if model == 0:
                            context = predicted
                        elif model in (1, 2):
                            context = neighbour
                        elif model in (3, 4):
                            context = predicted ^ neighbour
                        else:
                            context = (predicted & 240) | (neighbour >> 4)
                        current = decoder.value(mapping[context]); values += 1
                        if model in (3, 4, 5, 6):
                            current ^= neighbour
                        if current == predicted:
                            raise ValueError('unchanged correction')
                    screen[address] = current
            for field in range(768):
                flag = frame*768+field
                if at[flag//8] & (128 >> (flag % 8)):
                    value = decoder.value(len(tables)-1); values += 1
                    if not value:
                        raise ValueError('zero attribute correction')
                    screen[3072+field] ^= value
            rows.append(dict(index=len(rows), bits=decoder.position-first, values=values))
            previous = bytes(screen); out += previous
        if decoder.position != bits:
            raise ValueError('unused group bits')
        remaining -= n
    r.end()
    return bytes(out), rows


def read_group(r, remaining, *, fast_fragments=False):
    n, vl, ml = r.u16(), r.u16(), r.u16()
    flags = r.take(1)[0]
    bits = int.from_bytes(r.take(4), 'little')
    if not 1 <= n <= min(8, remaining) or (bits+7)//8 > MAX_CODED:
        raise ValueError('invalid group size')
    vectors = restore(r.take(vl), n, 192, 2)
    masks = restore(r.take(ml), n, 480, 4)
    if any(v > (88 if fast_fragments else 84) for v in vectors):
        raise ValueError('invalid vector')
    if fast_fragments and any(v >= 85 and masks[2*i:2*i+2] != b'\0\0' for i, v in enumerate(vectors)):
        raise ValueError('fast fragment has corrections')
    wanted = sum(int(any(0 < v < 81 for v in vectors[i*192:(i+1)*192])) << (7-i) for i in range(n))
    if flags != wanted:
        raise ValueError('invalid motion cache flags')
    encoded = r.take((bits+7)//8)
    if bits % 8 and encoded[-1] & ((1 << (8-bits % 8))-1):
        raise ValueError('nonzero padding')
    return n, flags, bits, vectors, masks[:n*384], masks[n*384:], encoded


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--baseline-fht', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--models', nargs='+', choices=MODELS, default=list(MODELS))
    p.add_argument('--counts', type=int, nargs='+', default=[16, 32, 64])
    p.add_argument('--profile', type=Path, help='reuse saved models and encode instead of profiling')
    p.add_argument('--cache', type=Path)
    args = p.parse_args()
    baseline = args.baseline_fht.read_bytes()
    original, count, _, _, _ = read_fht_header(Reader(baseline))
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if states.shape != (count, 3840) or not set(args.counts) <= {4, 8, 16, 32, 64, 128}:
        raise ValueError('input shape/context counts')
    from probe_hybrid_tiles import decode as decode_baseline
    if decode_baseline(baseline)[0] != states.tobytes():
        raise ValueError('baseline differs from candidate')
    report = dict(scope=__doc__, baseline_commit='e7727cd', states_sha256=sha(states.tobytes()),
        baseline_sha256=sha(baseline), frames=count, no_additional_pixel_changes=True,
        player_changed=False, integrated_player_delta_tstates=0, complete=False, rows=[])
    if args.profile:
        source = json.loads(args.profile.read_text(encoding='utf-8'))
        if not source['complete'] or source['states_sha256'] != report['states_sha256'] or not args.cache:
            raise ValueError('profile mismatch/cache missing')
        args.cache.mkdir(parents=True, exist_ok=True)
    for name in args.models:
        model = MODELS.index(name)
        if not args.profile:
            row = profile(states, residual, model, args.counts)
            report['rows'].append(row)
            print(json.dumps(dict(name=name, groups=[{k:v for k,v in g.items() if k not in ('tables', 'context_map')} for g in row['groups']])), flush=True)
        else:
            prof = next(x for x in source['rows'] if x['name'] == name)
            for contexts in args.counts:
                g = next(x for x in prof['groups'] if x['bitmap_contexts'] == contexts)
                data, detail = encode(original, states, vectors, residual, model, bytes(g['context_map']), [bytes(t) for t in g['tables']])
                restored, rows = decode(data)
                if restored != states.tobytes() or rows != detail['frames'] or sum(f['bits'] for f in rows) != g['bits']:
                    raise AssertionError('independent restoration differs')
                stem = f'{name}_{contexts}'
                (args.cache/(stem+'.raw')).write_bytes(data)
                row = dict(name=stem, model=model, contexts=contexts, raw_bytes=len(data), sha256=sha(data),
                    exact_causal_frame_decode=True, bits=g['bits'], groups=len(detail['groups']),
                    max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']), deflate_8192=measure(data, 8192))
                report['rows'].append(row); print(json.dumps(row), flush=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
