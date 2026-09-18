"""Compare actual FHT1 storage/CPU and independently count new hot paths.

Each frame's control, bitmap, attribute, literal, cache and prefix-Huffman
cost is checked against instruction formulas. Motion opcode code is retained.
Queue bounds omit ZX0/metadata, refill/paging, screen, IRQ/ULA/ROM/disk.
An incomplete report is never accepted, except explicit --allow-partial
for inspecting progress; that output is itself marked incomplete.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from benchmark_prefix_huffman import Harness as Prefix
from probe_hybrid_tiles import read_header, read_group
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_motion_residual_order import field_order
from summarize_context_cpu import minimum_capacity


def formulas(data, states, residual, original_vectors, old):
    r = Reader(data)
    _, remaining, _, mapping, tables = read_header(r)
    primitive = Prefix(tables, mapping)
    order = field_order(8).reshape(192, 20)[:, :16]
    current, predicted = states[:, order], (states ^ residual)[:, order]
    start = 0
    while remaining:
        n, flags, bits, vectors, bm, at, _ = read_group(r, remaining)
        position = 0
        for i in range(n):
            frame = start+i
            cache = bool(flags & (128 >> i))
            counts, stages, initial = Counter(), Counter(), position
            stages['control'] = old['frames'][frame]['stages']['control']-3532-1606*int(not cache)
            stages['cache'] = 58792*int(cache)
            stages['attribute_pass'] = 52
            for tile in range(192):
                v = vectors[i*192+tile]
                a, b = bm[i*384+tile*2:i*384+tile*2+2]
                if v == 82:
                    counts['literals'] += 1
                    stages['literal'] += 498+10*int(position % 8 != 0)
                    counts['unaligned_literals'] += int(position % 8 != 0)
                    position = (position+7)//8*8+128
                    stages['control'] += 20 if original_vectors[frame, tile] == 0 else 13
                    continue
                if v != original_vectors[frame, tile]:
                    raise ValueError('formula currently expects original nonliteral motion')
                base = 581 if a and b else 376 if a else 366 if b else 86
                stages['patch'] += base+39*(a.bit_count()+b.bit_count())
                for field in range(16):
                    if (a if field < 8 else b) & (128 >> (field % 8)):
                        ticks, length, _ = primitive.formula([(0, int(predicted[frame, tile, field]))], [int(current[frame, tile, field])], position)
                        stages['huffman'] += ticks; position += length
                        counts['bitmap_values'] += 1
            for index, mask in enumerate(at[i*96:(i+1)*96]):
                if not mask:
                    stages['attribute_pass'] += 75-int(index % 32 == 31)
                    counts['empty_attribute_masks'] += 1
                    continue
                stages['attribute_pass'] += 240+47*mask.bit_count()
                counts['nonempty_attribute_masks'] += 1
                for j in range(8):
                    if mask & (128 >> j):
                        ticks, length, _ = primitive.formula([(1, 0)], [int(residual[frame, 3072+index*8+j])], position)
                        stages['huffman'] += ticks; position += length
                        counts['attribute_values'] += 1
            yield frame, position-initial, counts, stages
        if position != bits:
            raise AssertionError('formula group bits differ')
        start += n; remaining -= n
    r.end()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-partial', action='store_true')
    args = p.parse_args()
    load = lambda name: json.loads((args.reports/name).read_text(encoding='utf-8'))
    old = load('causal_tiles_skip_empty_cpu_measurements.json')
    old_zx0 = load('direct_16_zx0_cpu_measurements.json')
    storage = load('hybrid_tiles_measurements.json')
    if (not old['complete'] or not old_zx0['complete'] or not storage['complete']
            or old['states_sha256'] != storage['states_sha256'] or old_zx0['input_sha256'] != old['input_sha256']):
        raise ValueError('incomplete/incomparable baseline')
    with np.load(args.motion_cache) as saved:
        states, residual, vectors = (saved[k] for k in ('states', 'residual', 'vectors'))
    if sha(states.tobytes()) != old['states_sha256']:
        raise ValueError('unexpected states')
    result = dict(scope=__doc__, baseline_commit='608e57b', complete=True, rows=[],
        cpu_rows=[], states_sha256=sha(states.tobytes()), old_cpu=old['summary'],
        formulas=dict(literal='498 +10*unaligned, including RET, excluding CALL',
            bitmap='base 86/376/366/581 for empty/first/second/both halves +39*values; literal tiles skipped',
            attributes='52 +75*zero_masks -zero_masks_at_page_end +240*nonzero_masks +47*values',
            cache='58792 when motion flag is set, otherwise zero',
            control='old_control -3532 -1606*no_cache +20*literal_from_vector0 +13*literal_from_nonzero',
            huffman='unchanged prefix_huffman formula, with the new order and alignment'),
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False)
    for entry in storage['rows']:
        name = entry['name']
        measured = load(f'hybrid_tiles_{name}_zx0.json')
        if (not measured['complete'] or measured['input_sha256'] != entry['sha256']
                or len(measured['blocks']) != measured['blocks_expected']):
            if not args.allow_partial:
                raise ValueError(f'incomplete/mismatched ZX0: {name}')
            result['complete'] = False
            continue
        size = sum(b['zx0_bytes']+4 for b in measured['blocks'])
        if size != measured['zx0_with_headers_bytes']:
            raise AssertionError('ZX0 sum differs')
        result['rows'].append(dict(**entry, zx0_with_headers_bytes=size,
            delta_to_fpd1_bytes=size-2034286, generous_three_trd_deficit_with_ay=size+77696-1937664,
            sequential_256_byte_sectors_lower_bound=(size+255)//256,
            sequential_sector_delta=(size+255)//256-(2034286+255)//256))
    for name in ('control', '64'):
        measured = load(f'hybrid_tiles_{name}_cpu.json')
        data = (args.cache/(name+'.raw')).read_bytes()
        if measured['input_sha256'] != sha(data) or measured['states_sha256'] != sha(states.tobytes()):
            raise ValueError('different CPU input')
        complete = measured['complete'] and len(measured['frames']) == 4971
        if not complete and not args.allow_partial:
            raise ValueError('incomplete CPU')
        result['complete'] &= complete
        zx0 = load(f'hybrid_tiles_{name}_zx0_cpu.json')
        if not zx0['complete'] or zx0['input_sha256'] != sha(data):
            raise ValueError('incomplete/different ZX0 CPU input')
        counts, stages, checked_stages = Counter(), Counter(), set()
        for expected, actual in zip(formulas(data, states, residual, vectors, old), measured['frames']):
            index, bits, fc, fs = expected
            if (actual['index'] != index or actual['bits'] != bits or actual['literals'] != fc['literals']
                    or actual['values'] != fc['bitmap_values']+fc['attribute_values']):
                raise AssertionError(f'{name}/{index}: formula coverage differs')
            for stage in ('literal', 'patch', 'attribute_pass', 'cache', 'control', 'huffman'):
                if actual['stages'].get(stage, 0) != fs[stage]:
                    raise AssertionError(f'{name}/{index}: {stage}: {actual["stages"].get(stage,0)} != {fs[stage]}')
                checked_stages.add(stage)
            counts.update(fc); stages.update(actual['stages'])
        totals = [row['total_tstates'] for row in measured['frames']]
        baseline = [row['total_tstates'] for row in old['frames'][:len(totals)]]
        result['cpu_rows'].append(dict(name=name, complete=complete, frames=len(totals),
            code_bytes=measured['code_bytes'], state_bytes=measured['state_bytes'],
            formula_counts=dict(counts), formula_checked_stages=sorted(checked_stages), stages=dict(stages),
            total_tstates=sum(totals), mean_frame_tstates=sum(totals)/len(totals),
            max_frame_tstates=max(totals), worst_frame=totals.index(max(totals)),
            delta_tstates=sum(totals)-sum(baseline),
            zx0=zx0['summary'], zx0_delta_tstates=zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates'],
            two_measured_stages_total_tstates=sum(totals)+zx0['summary']['total_tstates'] if complete else None,
            two_measured_stages_delta_tstates=sum(totals)+zx0['summary']['total_tstates']-sum(baseline)-old_zx0['summary']['total_tstates'] if complete else None,
            frames_over_nominal_425448=sum(t > 425448 for t in totals),
            idealized_queue=[dict(budget_tstates=b, minimum_complete_frame_capacity=minimum_capacity(totals, b))
                for b in (425448, 350000, 300000, 250000)] if complete else []))
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k in ('complete', 'cpu_rows')}, indent=2))


if __name__ == '__main__':
    main()
