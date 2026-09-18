"""FHF1: exact whole-tile alternatives to spatial/motion Huffman correction.

85: 16 final bytes; 86: two-byte row repeated eight times; 87: two row
pairs and one MSB-first selector; 88: one byte repeated sixteen times.
Payloads align to a byte using zero padding. Bitmap masks are zero for
fast tiles. FHS1 motion/attributes/contexts and group structure remain.
Selection estimates pre-ZX0 bit costs and primitive CPU work. The estimate
is not a full player benchmark. Every stream is independently restored.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine
from probe_hybrid_tiles import Writer, OFFSETS, MAX_CODED
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, parse_header, codes_for
from probe_motion_metadata import transform
from probe_motion_residual_order import field_order
from probe_spatial_contexts import read_header, decode

SIZES = {85: 16, 86: 2, 87: 5, 88: 1}


def pack_fragment(fragment):
    fragment = bytes(fragment)
    if len(fragment) != 16:
        raise ValueError('expected sixteen tile bytes')
    if fragment == fragment[:1]*16:
        return 88, fragment[:1]
    rows = [fragment[i:i+2] for i in range(0, 16, 2)]
    other = next((row for row in rows if row != rows[0]), None)
    if other is None:
        return 86, rows[0]
    if all(row in (rows[0], other) for row in rows):
        selector = sum((row != rows[0]) << (7-i) for i, row in enumerate(rows))
        return 87, rows[0]+other+bytes([selector])
    return 85, fragment


def motion_costs():
    """Measure existing motion stage on zero frames; branch cost is phase-only."""
    h = Harness([bytes([8]*256)]*2, bytes(256), OFFSETS,
        hybrid=True, skip_empty=True, intra_above=True, intra_extended=True)
    measured = {}
    for v in range(1, 82):
        phase = 2*((-OFFSETS[v][0]) % 4) if v < 81 else -1
        if phase in measured:
            continue
        h.begin(b'', bytes([v])*192, bytes(384), bytes(96))
        row = h.run(0, bytes(3840))
        cost = row['stages']['motion']
        if cost % 192:
            raise AssertionError('motion cost depends on position')
        measured[phase] = cost//192
    return [0]+[measured[2*((-dx) % 4)] for dx, _ in OFFSETS[1:]]+[measured[-1], 0, 0, 0], measured


def profile(states, vectors, residual, mapping, tables):
    order = field_order(8).reshape(192, 20)[:, :16]
    current = states[:, order]
    predicted = (states ^ residual)[:, order]
    active = current != predicted
    lengths = np.asarray([list(t) for t in tables], dtype=np.uint8)
    contexts = np.frombuffer(mapping, dtype=np.uint8)[predicted]
    length = lengths[contexts, current]
    if np.any(active & (length == 0)):
        raise ValueError('uncoded source')
    bits = (active*length).sum(axis=2)
    halves = active.reshape(len(states), 192, 2, 8).any(axis=3)
    mask_bytes = halves.sum(axis=2)
    old_bits = bits+mask_bytes*8+(vectors != 0)*8
    rows = current.reshape(len(states), 192, 8, 2).astype(np.uint16)
    words = rows[..., 0]+256*rows[..., 1]
    distinct = 1+np.count_nonzero(np.diff(np.sort(words, axis=2), axis=2), axis=2)
    kinds = np.where(distinct <= 2, 87, 85)
    kinds[distinct == 1] = 86
    kinds[np.all(current == current[:, :, :1], axis=2)] = 88
    payload_bytes = np.choose(kinds-85, [16, 2, 5, 1])
    # Seven padding bits is conservative; actual serialization decides it.
    extra_bits = payload_bytes*8+7+8-old_bits
    costs, measured = motion_costs()
    huff = np.where(length <= 8, 171, 493+53*(length.astype(np.int16)-9)+32*((np.maximum(length.astype(np.int16)-8, 0)+7)//8))
    huff = (huff*active).sum(axis=2)
    values = active.sum(axis=2)
    patch = np.where(mask_bytes == 0, 86,
        96+np.where(halves[:, :, 0], 248, 33)+4+np.where(halves[:, :, 1], 223, 18)+10+39*values)
    old_cpu = 58+7*(vectors != 0)+np.asarray(costs)[vectors]+patch+huff
    for tile in range(192):
        for vector in (82, 83, 84):
            selected = vectors[:, tile] == vector
            old_cpu[selected, tile] = (34+machine.intra_tstates(vector, tile, 0, extended=True)
                +25*values[selected, tile]+huff[selected, tile])
    # Conservative stand-alone fragment costs, including caller/unalignment.
    # Exact instruction listing/full CPU measurement must supersede these.
    fast_cpu = np.choose(kinds-85, [607, 602, 959, 574])
    gains = old_cpu-fast_cpu
    return dict(kinds=kinds.astype(np.uint8), extra_bits=extra_bits.astype(np.int32),
        estimated_gains=gains, old_cpu=old_cpu, measured_motion_stage=measured,
        existing_bits=bits, existing_values=values, current=current, order=order,
        kind_histogram={str(v): int(np.count_nonzero(kinds == v)) for v in SIZES})


def encode(original, states, vectors, residual, mapping, tables, selected, *, cap=MAX_CODED, dictionary=None):
    hr = Reader(original); _, count = parse_header(hr); hr.end()
    if states.shape != (count, 3840) or residual.shape != states.shape or vectors.shape != (count, 192):
        raise ValueError('invalid shapes')
    if selected.shape != vectors.shape or not 1 <= cap <= MAX_CODED or np.any(vectors > 84):
        raise ValueError('invalid selection/cap/vectors')
    order = field_order(8).reshape(192, 20)[:, :16]
    current, predicted = states[:, order], (states ^ residual)[:, order]
    active = current != predicted
    v = vectors.copy()
    payloads = {}
    for frame, tile in np.argwhere(selected):
        kind, payload = pack_fragment(current[frame, tile].tobytes())
        if dictionary is not None and kind == 85:
            from fragment_dictionary import pack as pack_words
            packed = pack_words(payload, dictionary)
            if len(packed) < len(payload):
                kind, payload = 89, packed
        v[frame, tile] = kind; active[frame, tile] = False
        payloads[int(frame), int(tile)] = payload
    bm = np.packbits(active.reshape(count, 3072), axis=1)
    attrs = residual[:, 3072:] != 0; at = np.packbits(attrs, axis=1)
    contexts = np.frombuffer(mapping, dtype=np.uint8)[predicted]
    codes = [codes_for(255, t) for t in tables]
    out = bytearray((b'FHD1' if dictionary is not None else b'FHF1')+bytes([0, len(tables)])+struct.pack('<H', len(original))+original+mapping+b''.join(tables))
    if dictionary is not None:
        bits, blob, lookup = dictionary
        if bits not in range(8, 13) or len(blob) != 2*((1 << bits)-1) or len(lookup) != 65536:
            raise ValueError('invalid dictionary')
        out.extend(bytes([bits])+blob)
    writer, start, index, groups, rows = Writer(), 0, 0, [], []

    def flush(end):
        nonlocal writer, start
        n = end-start
        vv = transform(v[start:end].tobytes(), 192, 2)
        mm = transform(bm[start:end].tobytes()+at[start:end].tobytes(), 480, 4)
        flags = sum(int(np.any((v[i] > 0) & (v[i] < 81))) << (7-i+start) for i in range(start, end))
        encoded = writer.finish()
        out.extend(struct.pack('<HHHBI', n, len(vv), len(mm), flags, writer.bits)+vv+mm+encoded)
        groups.append(dict(start=start, frames=n, bits=writer.bits, encoded_bytes=len(encoded)))
        start, writer = end, Writer()

    while index < count:
        saved = writer.snapshot()
        for tile in range(192):
            if selected[index, tile]:
                writer.literal(payloads[index, tile])
            else:
                for field in np.flatnonzero(active[index, tile]):
                    writer.put(*codes[contexts[index, tile, field]][current[index, tile, field]])
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
    return bytes(out), dict(groups=groups, frames=rows, fast_kinds=dict(Counter(int(x) for x in v[selected])))


def select_target(prof, vectors, frame_costs, target):
    """Spend bytes only on frames above a CPU target; still a heuristic.

    Includes the new +27 T retained-intra dispatch. Does not count possible
    removal of the motion cache or changed Huffman bit alignment. Actual
    Z80 execution must verify both the achieved time and exact frame output.
    """
    if target <= 0 or len(frame_costs) != len(vectors):
        raise ValueError('invalid target/frame costs')
    intra = (vectors >= 82) & (vectors <= 84)
    gains = prof['estimated_gains']+27*intra
    costs = np.asarray(frame_costs, dtype=np.int64)+27*intra.sum(axis=1)
    selected = np.zeros_like(vectors, dtype=bool)
    for frame in range(len(vectors)):
        if costs[frame] <= target:
            continue
        order = sorted(range(192), key=lambda t: (-gains[frame, t]/max(1, int(prof['extra_bits'][frame, t])), t))
        for tile in order:
            if gains[frame, tile] <= 0:
                continue
            selected[frame, tile] = True
            costs[frame] -= gains[frame, tile]
            if costs[frame] <= target:
                break
    return selected, dict(target_tstates=target, estimated_total_tstates=int(costs.sum()),
        estimated_max_frame_tstates=int(costs.max()), estimated_frames_over_target=int(np.count_nonzero(costs > target)),
        selected_frames=int(np.count_nonzero(selected.any(axis=1))),
        estimate_excludes_alignment_and_cache_changes=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--allowances', type=int, nargs='*', default=[0, 16, 32, 64])
    p.add_argument('--no-control', action='store_true')
    p.add_argument('--targets', type=int, nargs='*', default=[])
    p.add_argument('--cpu-report', type=Path)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.fhs.read_bytes()
    model, original, count, mapping, tables = read_header(Reader(source))
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if model != 0 or states.shape != (count, 3840) or decode(source)[0] != states.tobytes():
        raise ValueError('source mismatch')
    prof = profile(states, vectors, residual, mapping, tables)
    cpu = None
    if args.targets:
        if args.cpu_report is None:
            p.error('--targets requires --cpu-report')
        cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
        if (not cpu['complete'] or cpu['input_sha256'] != sha(source)
                or cpu['states_sha256'] != sha(states.tobytes()) or len(cpu['frames']) != count
                or [f['index'] for f in cpu['frames']] != list(range(count))):
            raise ValueError('incomplete/mismatched CPU baseline')
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='15b5638', complete=False,
        input_sha256=sha(source), states_sha256=sha(states.tobytes()),
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        measured_motion_stage=prof['measured_motion_stage'], all_tile_kinds=prof['kind_histogram'],
        cpu_selection_is_estimate=True, rows=[])
    variants = []
    if not args.no_control:
        variants.append(('control', np.zeros_like(vectors, dtype=bool), dict(allowance_bits=None)))
    for allowance in args.allowances:
        variants.append((f'allowance_{allowance}', (prof['extra_bits'] <= allowance) & (prof['estimated_gains'] > 0), dict(allowance_bits=allowance)))
    for target in args.targets:
        selected, selection = select_target(prof, vectors, [f['total_tstates'] for f in cpu['frames']], target)
        variants.append((f'target_{target}', selected, selection))
    if cpu is not None:
        report['cpu_report_sha256'] = sha(args.cpu_report.read_bytes())
    for name, selected, selection in variants:
        data, detail = encode(original, states, vectors, residual, mapping, tables, selected)
        restored, rows = decode(data, fast_fragments=True)
        if restored != states.tobytes() or rows != detail['frames']:
            raise AssertionError('independent causal restoration differs')
        if name == 'control' and b'FHS1'+data[4:] != source:
            raise AssertionError('control differs beyond magic')
        (args.cache/(name+'.raw')).write_bytes(data)
        np.savez_compressed(args.cache/(name+'.npz'), selected=selected)
        row = dict(name=name, **selection, raw_bytes=len(data), sha256=sha(data),
            frames=count, fast_tiles=int(selected.sum()), fast_kinds=detail['fast_kinds'],
            groups=len(detail['groups']), max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
            bits=sum(f['bits'] for f in rows), values=sum(f['values'] for f in rows),
            exact_causal_frame_decode=True, deflate_8192=measure(data, 8192),
            estimated_tile_cpu_saved=int(prof['estimated_gains'][selected].sum()),
            estimated_savings_exclude_new_dispatch_and_bit_position_changes=True)
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
