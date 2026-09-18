"""Compare frequency corrections, XOR and direct final bytes in known contexts.

All use exactly the same motion and change masks. Direct bytes include zero;
attributes stay XOR. These are bit budgets and lookup-memory inventories,
not packed streams, Z80 timings or release sizes. Direct final bitmap bytes
could remove the per-value reconstruction step from a future decoder.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import probe_motion_alphabet as alphabet
import probe_fine_motion as motion
import probe_motion_residual_order as ordering
from probe_motion_entropy import EXPECTED_SHA, huffman_lengths, codes_for
from probe_lossless_layouts import sha
from profile_prediction_contexts import clustered_tables


def prefix_inventory(tables, hist, width):
    direct = int(sum(sum(int(row[value]) for value, length in enumerate(table) if 0 < length <= width)
                     for row, table in zip(hist, tables)))
    tails = sum(sum(length > width for length in table) for table in tables)
    depth = max(max(table) for table in tables)
    # Root entries are (final byte, consumed bits) or a marked tail state.
    # Tail counts/indices use two bytes per remaining depth. Only long-code
    # symbols remain in the tail symbol vector; zero is a valid direct byte.
    return dict(prefix_bits=width, direct_values=direct, direct_fraction=direct/int(hist.sum()),
        root_bytes=len(tables)*(1 << width)*2, tail_symbols=tails,
        tail_count_bytes=len(tables)*2*max(0, depth-width),
        total_before_context_lookup=len(tables)*(1 << width)*2+tails+len(tables)*2*max(0, depth-width))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.raw.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected FPR1')
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected states')
    symbols = np.frombuffer(raw[4:20], dtype=np.uint8).reshape(4, 4)
    remapped = alphabet.remap(states, residual, symbols)
    offsets = [(0, 0)]+[(x, y) for y in range(-4, 5) for x in range(-4, 5) if x or y]
    if b'FPR1'+symbols.tobytes()+ordering.encode(motion.encode(vectors, remapped, 8, offsets, 8), 8) != raw:
        raise ValueError('cache differs from source')
    order = ordering.field_order(8)
    predicted = (states ^ residual)[:, order]
    active = residual[:, order] != 0
    labels = predicted.astype(np.int32)
    labels[:, order >= 3072] = 256
    target = states.copy(); target[:, 3072:] = residual[:, 3072:]
    report = dict(scope=__doc__, baseline_commit='fbf351e', input_sha256=sha(raw),
        states_sha256=sha(states.tobytes()), frames=4971, values=int(active.sum()),
        complete=False, rows=[])
    for name, data in [('frequency', remapped), ('xor', residual), ('direct', target)]:
        values = data[:, order][active]
        histogram = np.bincount(labels[active]*256+values, minlength=257*256).reshape(257, 256)
        global_hist = histogram.sum(axis=0)
        global_lengths = huffman_lengths(dict(enumerate(global_hist)))
        global_bits = int(np.dot(global_hist, list(global_lengths)))
        candidates = clustered_tables(histogram, requested=(16, 32, 64, 128), baseline_bits=8418269)
        for row in candidates:
            count = row['bitmap_contexts']
            clustered = np.zeros((count+1, 256), dtype=np.int64)
            for predicted_byte, context in enumerate(row['context_map']):
                clustered[context] += histogram[predicted_byte]
            clustered[count] = histogram[256]
            tables = [bytes(t) for t in row['tables']]
            # Validate every canonical code including a possible zero symbol.
            for table in tables:
                codes_for(255, table)
            row['prefix_inventory'] = [prefix_inventory(tables, clustered, k) for k in (4, 5, 6, 7, 8)]
            row['zero_coded_contexts'] = sum(bool(t[0]) for t in tables)
        entry = dict(name=name, global_bits=global_bits, groups=candidates)
        report['rows'].append(entry)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(dict(name=name, global_bits=global_bits,
            groups=[{k:v for k,v in r.items() if k not in ('tables', 'context_map')} for r in candidates])), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
