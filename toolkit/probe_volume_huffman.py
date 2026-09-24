"""Losslessly retune FAP3 Huffman frequencies, preserving every packet choice.

Only entropy bytes and header code lengths change. Motion vectors, masks,
literal fragments, native output maps and AY records are copied verbatim.
Keep the original predictor-to-table map; train on actually coded symbols.
Every table retains every symbol used anywhere in the movie, so all generated
FAP3 files remain independently decodable in full, including outside training.
This is an offline storage experiment, not a timing or release certification.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from bulk_frame_stream import read_packet, WINDOW
from build_fap3_trd import player_harness, sha
from prefix_huffman_z80 import prepare
from probe_fine_motion import shifted_candidates
from probe_hybrid_tiles import OFFSETS, Writer
from probe_motion_entropy import Reader, codes_for, huffman_lengths
from probe_motion_metadata import restore
from probe_motion_residual_order import field_order
from probe_spatial_contexts import read_header
from reencode_bounded_fragments import validate
from run_deferred_disk import ReadThroughBuilder


def write_symbols(contexts, values, tables):
    codes = [codes_for(255, table) for table in tables]
    writer = Writer()
    for context, value in zip(contexts, values):
        code, length = codes[int(context)][int(value)]
        if not length:
            raise ValueError('missing symbol in retuned table')
        writer.put(code, length)
    return writer.bits, writer.finish()


def collect(source, states):
    r = Reader(source)
    model, original, count, mapping, tables = read_header(r, magic=b'FAP3')
    if model != 0 or states.shape != (count, 3840) or states.dtype != np.uint8:
        raise ValueError('requires motion-context FAP3 and matching compact frames')
    header = source[:r.pos]
    order = field_order(8).reshape(192, 20)[:, :16]
    previous = np.zeros(3840, np.uint8)
    packets = []
    hist = np.zeros((len(tables), 256), np.int64)
    for index, current in enumerate(states):
        _, detail = read_packet(r, stored_guards=False)
        body = detail['payload']; ay_bytes = sum(map(len, detail['ticks']))
        vector_at = ay_bytes+8
        vectors = np.frombuffer(body[vector_at:vector_at+192], np.uint8)
        mask_at = vector_at+192
        mask = restore(body[mask_at:mask_at+detail['mask_bytes']], 1, 480, 4)
        active = np.unpackbits(np.frombuffer(mask[:384], np.uint8)).reshape(192, 16)
        predictors = shifted_candidates(previous[:3072], OFFSETS)
        picture = current[:3072].reshape(96, 32)
        spatial = []
        for vector in (82, 83, 84):
            image = np.zeros_like(picture)
            if vector == 83: image[:, 1:] = picture[:, :-1]
            else:
                dy = 1 if vector == 82 else 2; image[dy:] = picture[:-dy]
            spatial.append(image.reshape(3072))
        contexts, values = [], []
        for tile, addresses in enumerate(order):
            v = int(vectors[tile])
            if v >= 85:
                if active[tile].any(): raise ValueError('literal tile has coded residuals')
                continue
            predicted = (predictors[v] if v <= 81 else spatial[v-82])[addresses]
            for field in np.flatnonzero(active[tile]):
                contexts.append(mapping[int(predicted[field])]); values.append(int(current[addresses[field]]))
        if not detail['flags'] & 64:
            delta = current[3072:] ^ previous[3072:]
            for field in np.flatnonzero(np.unpackbits(np.frombuffer(mask[384:], np.uint8))):
                contexts.append(len(tables)-1); values.append(int(delta[field]))
        contexts = np.array(contexts, np.uint8); values = np.array(values, np.uint8)
        bits, encoded = write_symbols(contexts, values, tables)
        if (encoded != body[detail['coded_offset']:detail['literal_offset']]
                or bits & 7 != detail['flags'] & 7):
            raise AssertionError(f'baseline entropy replay differs at frame {index}')
        counts = np.bincount(contexts.astype(np.int32)*256+values, minlength=hist.size).reshape(hist.shape)
        hist += counts
        packets.append(dict(detail=detail, contexts=contexts, values=values, hist=counts, bits=bits, ay_bytes=ay_bytes))
        previous = current
        if index % 500 == 0: print(f'Exact entropy replay: {index}/{count}', flush=True)
    r.end()
    return header, mapping, tables, packets, hist


def train(hist, global_hist, mapping, max_depth):
    result = []
    floors = []
    for row, all_used in zip(hist, global_hist):
        floor = 1
        while True:
            counts = np.where(all_used != 0, np.maximum(row, floor), 0)
            # Z80 needs a complete tree, including for empty/single-symbol contexts.
            if np.count_nonzero(counts) < 2:
                for symbol in range(256):
                    if not counts[symbol]: counts[symbol] = 1
                    if np.count_nonzero(counts) >= 2: break
            table = huffman_lengths(dict(enumerate(counts)))
            if max(table) <= max_depth: break
            floor *= 2
        result.append(table); floors.append(floor)
    prepare(result, mapping)
    player_harness(bytes(4), result, mapping, 1)
    return result, floors


def retable(header, mapping, old_tables, packets, tables):
    out = bytearray(header[:-256*len(old_tables)] + b''.join(tables))
    total_bits = 0
    for packet in packets:
        detail = packet['detail']; body = detail['payload']
        bits, encoded = write_symbols(packet['contexts'], packet['values'], tables)
        prefix = bytearray(body[:detail['coded_offset']])
        at = packet['ay_bytes']
        prefix[at] = (detail['flags'] & ~7) | (bits & 7)
        struct.pack_into('<H', prefix, at+3, len(encoded))
        payload = bytes(prefix)+encoded+body[detail['literal_offset']:]
        if len(payload) >= WINDOW: raise ValueError('retuned packet exceeds input window')
        out += struct.pack('<H', len(payload))+payload
        total_bits += bits
    return bytes(out), total_bits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('raw', 'states', 'zx0', 'output', 'report'): p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--read-cache', type=Path, action='append', default=[])
    p.add_argument('--ends', default='1614,2920,4221')
    args = p.parse_args()
    source = args.raw.read_bytes()
    with np.load(args.states, allow_pickle=False) as saved: states = saved['states']
    ends = [int(s) for s in args.ends.split(',')]
    if ends != sorted(set(ends)) or ends[0] <= 0 or ends[-1] != len(states): p.error('invalid partition')
    args.output.mkdir(parents=True, exist_ok=True); args.report.parent.mkdir(parents=True, exist_ok=True)
    header, mapping, original_tables, packets, all_hist = collect(source, states)
    control, original_bits = retable(header, mapping, original_tables, packets, original_tables)
    if control != source: raise AssertionError('original table replay changed source')
    original_audio = validate(source, states)
    report = dict(complete=False, release=False, baseline_commit='53d7a1e', raw_sha256=sha(source),
        states_sha256=sha(states.tobytes()), frames=len(states), ends=ends, original_bits=original_bits,
        baseline_byte_identical=True, motion_mask_literal_native_ay_preserved=True,
        predictor_map_preserved=True, player_algorithm_changed=False, timing_verified=False,
        table_count=len(original_tables), original_maximum_code_bits=max(map(max, original_tables)), variants=[])
    def save(): args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    save(); memo = {}
    ranges = list(zip([0]+ends, ends))
    candidates = [('baseline', original_tables, [])]
    for name, start, end in [('global', 0, len(states))]+[(f'volume-{i}', s, e) for i,(s,e) in enumerate(ranges, 1)]:
        hist = sum((x['hist'] for x in packets[start:end]), np.zeros_like(all_hist))
        tables, floors = train(hist, all_hist, mapping, max(map(max, original_tables)))
        candidates.append((name, tables, floors))
    for name, tables, floors in candidates:
        print(f'Retable and scalar-verify complete movie: {name}', flush=True)
        raw, bits = retable(header, mapping, original_tables, packets, tables)
        if name != 'baseline' and validate(raw, states) != original_audio: raise AssertionError('AY changed')
        path = args.output/(name+'.raw'); path.write_bytes(raw)
        builder = ReadThroughBuilder(raw, states, args.zx0.resolve(), args.output/'zx0',
            fast_disk=True, cached_seek=True, interleaved=True, cold_bitmaps=True, startup_delta=True)
        builder.memo = memo; builder.read_cache = args.read_cache; builder.ends = ends
        selected = range(len(ends)) if name in ('baseline', 'global') else [int(name.split('-')[1])-1]
        row = dict(name=name, raw_file=path.name, raw_sha256=sha(raw), raw_bytes=len(raw), bits=bits,
            full_scalar_video_ay_exact=True, maximum_code_bits=max(map(max,tables)), smoothing_floors=floors,
            volumes=[])
        report['variants'].append(row); save()
        for index in selected:
            start,end = ranges[index]; print(f'Build storage control {name}: {start}..{end}', flush=True)
            image, meta = builder.volume(start,end,index+1)
            meta_path = args.output/f'{name}-part{index+1}.json'
            meta_path.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
            # Volume-specific raws have distinct series IDs. Size controls only:
            # do not publish a mixed set until shared identity is implemented.
            row['volumes'].append({k:meta[k] for k in ('part','frames','video_bytes','used_sectors',
                'free_sectors','layout_padding_sectors','video_start_sector','sections','independently_bootable')})
            save()
    report['complete'] = True; save()


if __name__ == '__main__': main()
