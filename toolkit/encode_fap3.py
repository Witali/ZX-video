"""Lossless FAP3 encoding of arbitrary compact Spectrum frames and AY states.

Reuses the current motion/intra predictors, Huffman decoder, native update maps
and fragments. All search happens on the host; the Z80 player is unchanged.
"""
from collections import Counter
import struct

import numpy as np

import ay_interrupt
import bulk_frame_stream
import cell_audio_stream
import frame_packet_stream
import prefix_huffman_z80
import raw_attribute_stream
import probe_sparse_motion_cache as cache
from build_fap3_trd import player_harness
from causal_tile_z80 import validate_static_stripes
from probe_cell_output_masks import masks
from probe_fast_fragments import pack_fragment
from probe_fine_motion import predict
from probe_hybrid_tiles import OFFSETS, Writer
from probe_motion_entropy import codes_for
from probe_motion_metadata import transform
from probe_motion_residual_order import field_order
from probe_spatial_contexts import profile
from probe_spatial_predictors import choose


def train_tables(states, residual):
    # Small clips may leave entire contexts unused or with a single symbol.
    # The native prefix decoder requires complete trees even for those tables.
    groups = profile(states, residual, 0, (4, 8, 16))['groups']
    candidates = []
    for group in groups:
        tables = []
        for source in group['tables']:
            table = bytearray(source)
            used = [i for i, length in enumerate(table) if length]
            if len(used) < 2:
                table = bytearray(256)
                symbol = used[0] if used else 0
                table[symbol] = table[(symbol+1) % 256] = 1
            tables.append(bytes(table))
        mapping = bytes(group['context_map'])
        try:
            prefix_huffman_z80.prepare(tables, mapping)
        except ValueError:
            continue
        candidates.append((group['bits']+8*group['table_file_bytes'], mapping, tables))
    for _, mapping, tables in sorted(candidates, key=lambda item: item[0]):
        try:
            # A table may fit bank 6 but its long-code decoder may not fit code RAM.
            player_harness(bytes(4), tables, mapping, 1)
        except ValueError:
            continue
        return mapping, tables
    # A valid bounded escape for pathological distributions, still ZX0 coded.
    return bytes(256), [bytes([8])*256]*2


def encode(states, ay_frames):
    if (states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840
            or not 0 < len(states) <= 0xffffffff or len(ay_frames) != len(states)*6):
        raise ValueError('expected N compact frames and exactly 6*N AY states')
    # These are format invariants, not assumptions about a particular movie.
    if (np.any(states[:, :384]) or np.any(states[:, 2688:3072])
            or np.any(states[:, 3072:3168] != 1) or np.any(states[:, 3744:] != 1)):
        raise ValueError('FAP3 requires black 24-pixel top/bottom borders with attribute 1')
    vectors, residual = predict(states, 8, OFFSETS, 8)
    vectors, residual = choose(states, vectors, residual)
    # The static-stripe shortcut promises unchanged top/bottom eight logical rows.
    vectors[:, :16] = vectors[:, -16:] = 0
    mapping, tables = train_tables(states, residual)
    codes = [codes_for(255, table) for table in tables]
    order = field_order(8).reshape(192, 20)[:, :16]
    native_maps = masks(states)[0].tobytes()
    ticks = ay_interrupt.encode_ticks(ay_frames)
    original = (b'FPR1'+bytes(a ^ b for a in range(4) for b in range(4))
                + b'FMO1\x08FMR1\x08'+struct.pack('<BI', len(OFFSETS), len(states))
                + b''.join(struct.pack('<bb', *offset) for offset in OFFSETS))
    header = (b'FSC2'+bytes([0, len(tables)])+struct.pack('<H', len(original))
              + original+mapping+b''.join(tables))
    cells, rows = bytearray(header), []
    kinds = Counter()

    def packet(index, force_literals=False):
        state, delta = states[index], residual[index]
        vv, active = vectors[index].copy(), delta[order] != 0
        writer, literals = Writer(), bytearray()
        frame_kinds = Counter()
        for tile, addresses in enumerate(order):
            values = state[addresses]
            predictions = values ^ delta[addresses]
            kind, payload = pack_fragment(values.tobytes())
            fields = np.flatnonzero(active[tile])
            bits = sum(tables[mapping[int(predictions[f])]][int(values[f])] for f in fields)
            # Prefer a whole fragment when it costs no more than masked codes.
            use_fragment = (force_literals or len(payload)*8 <= bits+8*np.count_nonzero(
                active[tile].reshape(2, 8).any(axis=1))) and (len(fields) or vv[tile])
            if use_fragment:
                vv[tile] = kind
                literals += payload
                active[tile] = False
                frame_kinds[kind] += 1
            else:
                for field in fields:
                    writer.put(*codes[mapping[int(predictions[field])]][int(values[field])])
        attrs = delta[3072:]
        changed = np.flatnonzero(attrs)
        raw_attrs = force_literals or len(changed) >= 128
        if raw_attrs:
            literals += state[3072:].tobytes()
            at = bytes(96)
        else:
            at = np.packbits(attrs != 0).tobytes()
            for field in changed:
                writer.put(*codes[-1][int(attrs[field])])
        bm = np.packbits(active.reshape(-1)).tobytes()
        validate_static_stripes(vv.tobytes(), bm)
        mm = transform(bm+at, 480, 4)
        flags = (128 if np.any((vv > 0) & (vv < 81)) else 0) | (64 if raw_attrs else 0)
        entropy = writer.finish()
        result = (struct.pack('<HHHBI', 1, 192, len(mm), flags, writer.bits)
                  + vv.tobytes()+mm+native_maps[index*80:(index+1)*80]+entropy+literals)
        # FAP3 replaces this header and adds AY records + 3 cache bytes.
        body_size = len(result)-11+5+3+sum(map(len, ticks[index*6:(index+1)*6]))
        return result, body_size, frame_kinds

    for index in range(len(states)):
        data, size, histogram = packet(index)
        fallback = size >= bulk_frame_stream.WINDOW
        if fallback:
            data, size, histogram = packet(index, True)
        if size >= bulk_frame_stream.WINDOW:
            raise AssertionError('bounded fragment escape does not fit FAP3')
        cells += data
        kinds.update(histogram)
        rows.append(dict(frame=index, payload_bytes=size, literal_fallback=fallback))
    # Independent scalar decoder uses only previous decoded frames, never encoder arrays.
    if raw_attribute_stream.decode(bytes(cells)) != states.tobytes():
        raise AssertionError('FAP3 preparation changed a compact frame')
    audio = b''.join(ticks)
    av = cell_audio_stream.pack(bytes(cells), audio)
    cached, _ = cache.pack(av, states, 32, 4)
    fixed, _ = frame_packet_stream.pack(cached)
    result, _ = bulk_frame_stream.pack(fixed, stored_guards=False)
    restored = cache.unpack(frame_packet_stream.unpack(bulk_frame_stream.unpack(result)), 32, 4)
    checked_cells, checked_audio, _ = cell_audio_stream.unpack(restored)
    if checked_cells != cells or checked_audio != audio:
        raise AssertionError('FAP3 framing changed video or AY records')
    return result, dict(frames=len(states), ay_ticks=len(ticks), contexts=len(tables),
        exact_compact_frames=True, exact_ay_records=True, additional_pixel_changes=False,
        max_payload_bytes=max(row['payload_bytes'] for row in rows),
        literal_fallback_frames=sum(row['literal_fallback'] for row in rows),
        fragment_counts=dict(kinds), packets=rows)
