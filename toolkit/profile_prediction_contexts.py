"""Measure Huffman bit budgets conditioned on known motion-predicted pixels.

Diagnostic only: no FPC extension, Z80 table layout or final ZX0 size is
claimed. Validate the cache by reconstructing the exact source FPR1 before
using its predictor bytes. Attributes have one independent context.
"""
import argparse
import heapq
from itertools import product
import json
from pathlib import Path

import numpy as np

from probe_lossless_layouts import sha
from probe_motion_entropy import EXPECTED_SHA, huffman_lengths
import probe_motion_alphabet as alphabet
import probe_fine_motion as motion
import probe_motion_residual_order as ordering


def clustered_tables(histogram, requested=(4, 8, 16, 32, 64), baseline_bits=10245241):
    """Greedily merge bitmap distributions by increase in zero-order entropy.

    Attributes stay independent. A 256-byte predictor-to-cluster map is enough
    at runtime; the expensive search is entirely on the PC.
    """
    def entropy(row):
        nonzero = row[row != 0].astype(np.float64)
        total = nonzero.sum()
        return float(total*np.log2(total)-(nonzero*np.log2(nonzero)).sum()) if total else 0.

    hist = {i: row.copy() for i, row in enumerate(histogram[:256])}
    members = {i: [i] for i in hist}
    scores = {i: entropy(row) for i, row in hist.items()}
    heap = [(entropy(hist[i]+hist[j])-scores[i]-scores[j], i, j)
            for i in range(256) for j in range(i+1, 256)]
    heapq.heapify(heap)
    next_id, results = 256, []
    while len(hist) > min(requested):
        while True:
            _, left, right = heapq.heappop(heap)
            if left in hist and right in hist:
                break
        merged = hist.pop(left)+hist.pop(right)
        hist[next_id] = merged
        members[next_id] = members.pop(left)+members.pop(right)
        scores[next_id] = entropy(merged)
        for other, row in hist.items():
            if other != next_id:
                heapq.heappush(heap, (entropy(merged+row)-scores[next_id]-scores[other], other, next_id))
        next_id += 1
        if len(hist) in requested:
            ordered = sorted(hist, key=lambda node: min(members[node]))
            mapping = [0]*256
            for context, node in enumerate(ordered):
                for predictor in members[node]:
                    mapping[predictor] = context
            merged_hist = np.stack([hist[node] for node in ordered]+[histogram[256]])
            tables = [huffman_lengths(dict(enumerate(row))) for row in merged_hist]
            bits = int((np.array([list(t) for t in tables])*merged_hist).sum())
            results.append(dict(bitmap_contexts=len(hist), contexts=len(tables), context_map=mapping,
                tables=[list(t) for t in tables], bits=bits, table_file_bytes=256+len(tables)*256,
                byte_saving_before_tables=(baseline_bits-bits)/8,
                minimum_code_bits=min(n for t in tables for n in t if n),
                maximum_code_bits=max(max(t) for t in tables)))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.raw.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected source FPR1')
    with np.load(args.motion_cache) as cache:
        states, vectors, residual = (cache[name] for name in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected motion states')
    offsets = [(0, 0)]+[(x, y) for y in range(-4, 5) for x in range(-4, 5) if x or y]
    symbols = np.frombuffer(raw[4:20], dtype=np.uint8).reshape(4, 4)
    converted = alphabet.remap(states, residual, symbols)
    recreated = b'FPR1'+symbols.tobytes()+ordering.encode(motion.encode(vectors, converted, 8, offsets, 8), 8)
    if recreated != raw:
        raise AssertionError('predictor/cache does not reproduce source serialization')
    order = ordering.field_order(8)
    prediction = (states ^ residual)[:, order]
    values = converted[:, order]
    active = values != 0
    attribute = order >= 3072
    levels = np.stack([(prediction >> s) & 3 for s in (6, 4, 2, 0)], axis=2)
    uniform = np.all(levels == levels[:, :, :1], axis=2)
    population = np.stack([(levels == level).sum(axis=2) for level in range(4)], axis=2)
    majority = population.argmax(axis=2)
    modes = [
        ('uniform_or_mixed', np.where(uniform, levels[:, :, 0], 4), 5),
        ('first_level', levels[:, :, 0], 4),
        ('majority_level', majority, 4),
        ('majority_and_uniform', majority+4*(~uniform), 8),
        ('first_last_levels', levels[:, :, 0]*4+levels[:, :, 3], 16),
        ('exact_predicted_byte', prediction, 256),
    ]
    report = dict(scope=__doc__, baseline_commit='8b3f83f', input_sha256=sha(raw),
        states_sha256=sha(states.tobytes()), predictor_sha256=sha(prediction.tobytes()),
        frames=4971, values=int(active.sum()), source_cache_reconstruction_exact=True,
        baseline_huffman_bits=10245241, complete=False, rows=[])
    for name, labels, bitmap_contexts in modes:
        labels = labels.astype(np.int32)
        labels[:, attribute] = bitmap_contexts
        count = bitmap_contexts+1
        histogram = np.bincount((labels[active]*256+values[active]), minlength=count*256).reshape(count, 256)
        lengths = np.array([list(huffman_lengths(dict(enumerate(row)))) for row in histogram], dtype=np.int32)
        bits = int((lengths*histogram).sum())
        row = dict(name=name, contexts=count, populated_contexts=int(np.count_nonzero(histogram.sum(axis=1))),
            value_bits=bits, mean_value_bits=bits/report['values'],
            byte_equivalent_saving_before_tables=(report['baseline_huffman_bits']-bits)/8,
            serialized_lengths_bytes=count*256,
            minimum_code_bits=int(lengths[lengths != 0].min()), maximum_code_bits=int(lengths.max()))
        if name == 'exact_predicted_byte':
            ranked = np.sort(histogram, axis=1)[:, ::-1]
            cumulative = ranked.cumsum(axis=1).sum(axis=0)
            total = int(histogram.sum())
            palettes = []
            shapes = [(k,) for k in range(2, 7)]+[(2, 4), (2, 2, 4), (1, 2, 4), (1, 1, 2, 4)]
            for shape in shapes:
                slots, remaining, coded = 0, total, 0
                for width in shape:
                    coded += remaining*width
                    slots += (1 << width)-1
                    remaining = total-int(cumulative[slots-1])
                coded += remaining*8
                palettes.append(dict(prefix_bits=list(shape), table_symbols=slots,
                    serialized_table_bytes=slots*count, bits=coded, mean_bits=coded/total,
                    byte_equivalent_saving_before_tables=(report['baseline_huffman_bits']-coded)/8))
            row['palette_probes'] = palettes
            # Contexts have very different skew. Also choose prefix widths
            # separately per predictor, charging uncompressed palette bytes.
            catalog = [(k,) for k in range(1, 8)]
            catalog += list(product(range(1, 6), repeat=2))
            catalog += list(product(range(1, 5), repeat=3))
            adaptive = []
            per_context_cumulative = ranked.cumsum(axis=1)
            for context, hist in enumerate(histogram):
                amount = int(hist.sum())
                best = dict(context=context, prefix_bits=[], slots=0, bits=amount*8,
                            bits_plus_palette=amount*8)
                for shape in catalog:
                    remaining, coded, slots = amount, 0, 0
                    for width in shape:
                        coded += remaining*width
                        slots += (1 << width)-1
                        remaining = amount-int(per_context_cumulative[context, slots-1])
                    coded += remaining*8
                    score = coded+8*slots
                    if score < best['bits_plus_palette']:
                        best = dict(context=context, prefix_bits=list(shape), slots=slots,
                                    bits=coded, bits_plus_palette=score)
                adaptive.append(best)
            row['adaptive_palette'] = dict(contexts=adaptive,
                bits=sum(c['bits'] for c in adaptive),
                palette_bytes=sum(c['slots'] for c in adaptive),
                mode_bytes=count, pointer_bytes=2*count,
                byte_equivalent_saving_including_palette=(report['baseline_huffman_bits']-
                    sum(c['bits_plus_palette'] for c in adaptive))/8)
            row['clustered_huffman'] = clustered_tables(histogram)
        report['rows'].append(row)
        print(json.dumps({k: v for k,v in row.items() if k not in ('adaptive_palette', 'clustered_huffman')}), flush=True)
        if 'adaptive_palette' in row:
            print(json.dumps({k:v for k,v in row['adaptive_palette'].items() if k != 'contexts'}), flush=True)
            for cluster in row['clustered_huffman']:
                print(json.dumps({k:v for k,v in cluster.items() if k not in ('tables', 'context_map')}), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
