"""Validate full-movie extended-intra CPU evidence against two age3 baselines.

CPU work includes frame reconstruction and a separate ZX0 run, not delivery.
Pixel states are identical, but predictor choices and Huffman tables differ.
The actual disk layout, output, IRQ/ULA/ROM and sector latency are unmeasured.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import causal_tile_z80 as machine
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, OFFSETS
from summarize_context_cpu import minimum_capacity

STATE_SHA = '4b9e90d22df2809a70c1cb09890de0a9bb0a23d1b1e357b3f6c29ff830cc9c3b'


def cpu_summary(cpu):
    if not cpu['complete'] or len(cpu['frames']) != 4971 or cpu['states_sha256'] != STATE_SHA:
        raise ValueError('incomplete or different frame reconstruction')
    work, stages = [], Counter()
    for i, row in enumerate(cpu['frames']):
        if row['index'] != i or sum(row['stages'].values()) != row['total_tstates']:
            raise AssertionError('frame/stage coverage differs')
        work.append(row['total_tstates']); stages.update(row['stages'])
    if (sum(work) != cpu['summary']['total_tstates']
            or sum(r['count']*r['tstates'] for r in cpu['instruction_histogram']) != sum(work)):
        raise AssertionError('histogram total differs')
    branches = Counter()
    for row in cpu['instruction_histogram']:
        for name in ('bitmap', 'attribute', 'long'):
            if row['address'] == cpu['labels'][name]:
                branches[name] += row['count']
    if branches['bitmap']+branches['attribute'] != cpu['summary']['values']:
        raise AssertionError('value histogram differs')
    worst_windows = []
    for width in (8, 50, 100, 200):
        running = best = sum(work[:width]); first = 0
        for end in range(width, len(work)):
            running += work[end]-work[end-width]
            if running > best:
                best, first = running, end-width+1
        worst_windows.append(dict(frames=width, first=first, total_tstates=best, mean_tstates=best/width))
    return dict(cpu['summary'], code_bytes=cpu['code_bytes'], state_bytes=cpu['state_bytes'],
        input_sha256=cpu['input_sha256'], stages=dict(stages), huffman_branches=dict(branches),
        worst_frames=sorted(cpu['frames'], key=lambda r: r['total_tstates'], reverse=True)[:10],
        worst_windows=worst_windows, idealized_queue=[dict(budget_tstates=b,
            minimum_complete_frames=minimum_capacity(work, b)) for b in (425448, 350000, 300000, 250000)])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--above-fhs', type=Path, required=True, help='prior above-only input, for exact binary compatibility')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    load = lambda name: json.loads((args.reports/name).read_text(encoding='utf-8'))
    original = load('spatial_tiles_baseline_cpu.json')
    above = load('spatial_tiles_motion_16_cpu.json')
    new = load('spatial_extended_cpu.json')
    storage = load('spatial_predictors_cost_1_zx0.json')
    zx0 = load('spatial_extended_zx0_cpu.json')
    choices = load('spatial_predictors_cost_measurements.json')
    choice = next(row for row in choices['rows'] if row['name'] == 'iteration_1')
    if (not storage['complete'] or not zx0['complete'] or not choices['complete']
            or not new.get('intra_extended') or choices['states_sha256'] != STATE_SHA
            or len(zx0['blocks']) != storage['blocks_expected']
            or any(r['input_sha256'] != choice['sha256'] for r in (new, storage, zx0))
            or sum(g['frames'] for g in new['groups']) != 4971
            or sum(g['bits'] for g in new['groups']) != choice['bits']):
        raise ValueError('incomplete/different source coverage')
    for i, (a, b) in enumerate(zip(zx0['blocks'], storage['blocks'])):
        if (a['index'] != i or a['raw_sha256'] != b['sha256']
                or a['raw_bytes'] != b['decoded_bytes'] or a['compressed_bytes'] != b['zx0_bytes']):
            raise AssertionError('ZX0 block coverage differs')
    if (sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']
            or sum(b['zx0_bytes']+4 for b in storage['blocks']) != storage['zx0_with_headers_bytes']):
        raise AssertionError('ZX0 totals differ')
    modes = Counter()
    for frame in new['frames']:
        modes.update(frame['intra_modes'])
    if dict(modes) != choice['intra_vectors'] or dict(modes) != new['summary']['intra_modes']:
        raise AssertionError('predictor coverage differs')
    data = args.above_fhs.read_bytes()
    model, _, count, mapping, tables = read_header(Reader(data))
    if sha(data) != above['input_sha256'] or model != 0 or count != 4971:
        raise ValueError('different previous above-only stream')
    code, labels, listing, regions = machine.build(tables, mapping, OFFSETS,
        skip_empty=True, hybrid=True, intra_above=True)
    if (code.hex() != above['code_hex'] or labels != above['labels'] or listing != above['instruction_listing']
            or [dict(base=b, bytes=len(v), sha256=sha(v)) for b, v in regions] != above['tables']):
        raise AssertionError('old above-only binary changed')
    rows = [cpu_summary(x) for x in (original, above, new)]
    if (rows[-1]['huffman_branches']['bitmap'] != choice['bitmap_values']
            or len({r['huffman_branches']['attribute'] for r in rows}) != 1):
        raise AssertionError('bitmap/unchanged attribute coverage differs')
    deltas = []
    for stem, old in zip(('spatial_tiles_baseline', 'spatial_tiles_motion_16'), rows):
        old_zx0 = load(stem+'_zx0_cpu.json')
        if not old_zx0['complete'] or old_zx0['input_sha256'] != old['input_sha256']:
            raise ValueError('different baseline ZX0 input')
        before = old['total_tstates']+old_zx0['summary']['total_tstates']
        after = rows[-1]['total_tstates']+zx0['summary']['total_tstates']
        deltas.append(dict(baseline=stem, reconstruction_tstates=rows[-1]['total_tstates']-old['total_tstates'],
            zx0_tstates=zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates'],
            two_stage_tstates_before=before, two_stage_tstates_after=after, two_stage_delta_tstates=after-before,
            code_delta_bytes=rows[-1]['code_bytes']-old['code_bytes'],
            stages={k: rows[-1]['stages'].get(k, 0)-old['stages'].get(k, 0)
                for k in sorted(set(rows[-1]['stages']) | set(old['stages']))}))
    report = dict(scope=__doc__, baseline_commit='7dea054', complete=True, old_above_binary_unchanged=True,
        states_sha256=STATE_SHA, input_sha256=new['input_sha256'], player_changed=False,
        integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        video_bytes=storage['zx0_with_headers_bytes'], unchanged_ay_estimate_bytes=77696,
        video_plus_ay_estimate_bytes=storage['zx0_with_headers_bytes']+77696,
        preliminary_three_trd_margin_bytes=1937664-storage['zx0_with_headers_bytes']-77696,
        cpu=rows, zx0=zx0['summary'], deltas=deltas,
        intra_tstates=dict(above='1091 top /1133 below +25*N', left='902 left edge /982 elsewhere +25*N',
            above2='1103 top /1187 below +25*N', exclusions='external CALL and Huffman are separate stages'),
        same_above_stream_extended_dispatch_delta_formula='34*48267 =1641078 T; not an additional full CPU run')
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(new=rows[-1], deltas=deltas), indent=2))


if __name__ == '__main__':
    main()
