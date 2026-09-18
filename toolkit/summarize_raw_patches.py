"""Native sizes and instruction-formula CPU bounds for FHR1 variants.

Formula rows are not full CPU executions. The direct_0 run independently
checks every stage/frame; mixed modes also have opcode/IRQ fixtures. All
queue bounds exclude ZX0/metadata, native drawing, input refill/paging and
IRQ/ULA/ROM/disk. Larger-block DEFLATE is only a storage screening result.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from benchmark_prefix_huffman import Harness as Prefix
from probe_raw_patches import read_header, read_group
from probe_lossless_layouts import sha, measure
from probe_motion_entropy import Reader
from probe_motion_residual_order import field_order
from summarize_context_cpu import minimum_capacity


def formula(data, states, residual, baseline):
    r = Reader(data)
    kind, _, remaining, mapping, tables, _ = read_header(r)
    if kind not in (0, 1):
        raise ValueError('no Z80 formula for frequency raw patches')
    primitive = Prefix(tables, mapping)
    order = field_order(8).reshape(192, 20)[:, :16]
    current, predicted = states[:, order], (states ^ residual)[:, order]
    frames, start = [], 0
    while remaining:
        n, _, bits, vectors, bm, at, _ = read_group(r, remaining)
        position = 0
        for i in range(n):
            frame = start+i
            # These stages traverse identical vectors/cache and attribute
            # masks. The old report executed all of them on actual opcodes.
            stages = Counter({k: baseline['frames'][frame]['stages'].get(k, 0) for k in ('control', 'cache', 'motion', 'attribute_pass')})
            stages['control'] += 4800
            raw_values = raw_tiles = unaligned = huff_values = 0
            first = position
            for tile, v in enumerate(vectors[i*192:(i+1)*192]):
                a, b = bm[i*384+tile*2:i*384+tile*2+2]
                count = a.bit_count()+b.bit_count()
                if v & 128:
                    stages['control'] -= 10
                    raw_tiles += 1; raw_values += count
                    unaligned += int(position % 8 != 0)
                    stages['raw_patch'] += (649 if a and b else 444 if a else 434)+(20 if kind == 0 else 27)*count+10*int(position % 8 != 0)
                    position = (position+7)//8*8+count*8
                else:
                    stages['patch'] += (581 if a and b else 376 if a else 366 if b else 86)+39*count
                    for field in range(16):
                        if (a if field < 8 else b) & (128 >> (field % 8)):
                            ticks, length, _ = primitive.formula([(0, int(predicted[frame, tile, field]))], [int(current[frame, tile, field])], position)
                            stages['huffman'] += ticks; position += length; huff_values += 1
            for field in range(768):
                if at[i*96+field//8] & (128 >> (field % 8)):
                    ticks, length, _ = primitive.formula([(1, 0)], [int(residual[frame, 3072+field])], position)
                    stages['huffman'] += ticks; position += length; huff_values += 1
            frames.append(dict(index=frame, bits=position-first, stages=dict(stages), total_tstates=sum(stages.values()),
                values=huff_values, raw_values=raw_values, raw_tiles=raw_tiles, unaligned_raw_tiles=unaligned))
        if position != bits:
            raise AssertionError('formula bit count differs')
        start += n; remaining -= n
    r.end()
    return frames


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-partial', action='store_true')
    args = p.parse_args()
    load = lambda name: json.loads((args.reports/name).read_text(encoding='utf-8'))
    source, baseline = load('raw_patches_measurements.json'), load('hybrid_tiles_control_cpu.json')
    baseline_zx0 = load('hybrid_tiles_control_zx0_cpu.json')
    if not source['complete'] or not baseline['complete'] or source['states_sha256'] != baseline['states_sha256']:
        raise ValueError('incomplete/incomparable source')
    with np.load(args.motion_cache) as saved:
        states, residual = saved['states'], saved['residual']
    if sha(states.tobytes()) != source['states_sha256']:
        raise ValueError('unexpected states')
    result = dict(scope=__doc__, baseline_commit='2de2203', states_sha256=source['states_sha256'],
        complete=True, player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        formulas=dict(raw_direct='649/444/434 for both/first-only/second-only halves +20*values +10*unaligned',
            raw_xor='same base, +27*values +10*unaligned',
            control='FHT1 control +4800 -10*raw_tiles per frame',
            reused_stages='motion, cache and attributes unchanged from executed FHT1 control; Huffman uses its prefix formula at the new bit positions'), rows=[])
    for entry in source['rows']:
        name = entry['name']; data = (args.cache/(name+'.raw')).read_bytes()
        if sha(data) != entry['sha256']:
            raise ValueError('different encoded stream')
        row = dict(**entry, deflate_screening={str(n): measure(data, n) for n in (16384, 32768, 65536, len(data))})
        path = args.reports/f'raw_patches_{name}_zx0.json'
        if path.exists():
            native = load(path.name)
            if native['input_sha256'] != sha(data):
                raise ValueError('native input differs')
            if native['complete']:
                size = sum(b['zx0_bytes']+4 for b in native['blocks'])
                if len(native['blocks']) != native['blocks_expected'] or size != native['zx0_with_headers_bytes']:
                    raise ValueError('incomplete native blocks')
                row['native_zx0'] = dict(bytes_with_headers=size, block_bytes=native['block_bytes'], blocks=len(native['blocks']),
                    delta_to_fht_control_bytes=size-2033040, generous_three_trd_deficit_with_ay=size+77696-1937664)
            elif not args.allow_partial:
                raise ValueError(f'incomplete native compression: {name}')
            else:
                result['complete'] = False
        if entry['kind'] in ('direct', 'xor'):
            frames = formula(data, states, residual, baseline)
            stages = Counter()
            for f in frames:
                stages.update(f['stages'])
            totals = [f['total_tstates'] for f in frames]
            row['cpu_formula'] = dict(method='instruction formulas; not a full Z80 execution', frames=len(frames),
                total_tstates=sum(totals), mean_frame_tstates=sum(totals)/len(totals), max_frame_tstates=max(totals),
                worst_frame=totals.index(max(totals)), frames_over_nominal_425448=sum(t > 425448 for t in totals),
                delta_to_fht_control_tstates=sum(totals)-baseline['summary']['total_tstates'], stages=dict(stages),
                frame_tstates=totals, idealized_queue=[dict(budget_tstates=b, minimum_complete_frame_capacity=minimum_capacity(totals, b))
                    for b in (425448, 350000, 300000, 250000)])
            path = args.reports/f'raw_patches_{name}_cpu.json'
            if path.exists():
                actual = load(path.name)
                if actual['input_sha256'] != sha(data):
                    raise ValueError('CPU input differs')
                complete = actual['complete'] and len(actual['frames']) == len(frames)
                if not complete and not args.allow_partial:
                    raise ValueError('incomplete CPU run')
                for want, got in zip(frames, actual['frames']):
                    for key in ('bits', 'values', 'raw_values', 'raw_tiles', 'unaligned_raw_tiles', 'total_tstates'):
                        if want[key] != got[key]:
                            raise AssertionError(f'{name}/{want["index"]}: {key} differs')
                    if Counter(want['stages']) != Counter(got['stages']):
                        raise AssertionError('stage formula differs')
                row['z80_validation'] = dict(complete=complete, exact_formula_frames=len(actual['frames']),
                    code_bytes=actual['code_bytes'], state_bytes=actual['state_bytes'])
                result['complete'] &= complete
                zx0_path = args.reports/f'raw_patches_{name}_zx0_cpu.json'
                if zx0_path.exists():
                    zx0 = load(zx0_path.name)
                    if zx0['input_sha256'] != sha(data) or not zx0['complete'] or not baseline_zx0['complete']:
                        raise ValueError('ZX0 CPU coverage differs')
                    total = sum(b['tstates'] for b in zx0['blocks'])
                    if total != zx0['summary']['total_tstates']:
                        raise ValueError('ZX0 CPU sum differs')
                    row['zx0_cpu'] = dict(total_tstates=total, blocks=len(zx0['blocks']),
                        max_block_tstates=zx0['summary']['max_block_tstates'],
                        delta_to_fht_control_tstates=total-baseline_zx0['summary']['total_tstates'])
                    if complete:
                        combined = sum(totals)+total
                        old = baseline['summary']['total_tstates']+baseline_zx0['summary']['total_tstates']
                        row['two_stage_cpu'] = dict(total_tstates=combined, baseline_tstates=old,
                            delta_tstates=combined-old, fraction_saved=1-combined/old,
                            full_frame_delivery_measured=False)
        result['rows'].append(row)
        print(json.dumps(dict(name=name, deflate=row['deflate_screening'],
            cpu={k: v for k, v in row.get('cpu_formula', {}).items() if k not in ('frame_tstates', 'stages')})), flush=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
