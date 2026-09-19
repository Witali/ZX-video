"""FHC1: select fused raw spatial corrections or complete fast fragments.

Raw flags 210..212 mean predictors 82..84 with byte-aligned final values
only for masked fields. No predictor is calculated for these fields on Z80.
Ordinary temporal tiles keep FHF1 coding. Selection CPU costs are estimates;
independent PC restoration, actual ZX0 and Z80 measurement are separate.
"""
import argparse
import heapq
import json
from pathlib import Path

import numpy as np

import probe_fast_fragments as fast
from probe_spatial_contexts import read_header, decode
from probe_motion_entropy import Reader
from probe_lossless_layouts import sha, measure


def select(prof, states, vectors, residual, frame_costs, target):
    intra = (vectors >= 82) & (vectors <= 84)
    active = residual[:, prof['order']] != 0
    values = active.sum(axis=2)
    raw_cost = 693+np.where(vectors == 83, 17, 34)+10+39*values
    for tile in range(192):
        for vector in (82, 83, 84):
            used = vectors[:, tile] == vector
            if not used.any():
                continue
            for field in range(16):
                if vector == 83:
                    read = 0 if field % 2 else (32 if tile % 16 == 0 else 42)
                else:
                    read = (32 if tile < 16 else 53) if field < (2 if vector == 82 else 4) else 26
                raw_cost[used, tile] += read*(~active[used, tile, field])
    # FHF adds 27 T to retained intra. FHC adds 18 T there and 28 T
    # to complete fragments (flag dispatch plus jump past raw-intra call).
    gains = [prof['old_cpu']+45-(52+raw_cost), prof['estimated_gains']+45*intra-28]
    gains[0][~intra | (values == 0)] = -1
    bits = [8*values+7-prof['existing_bits'], prof['extra_bits']]
    costs = np.asarray(frame_costs, dtype=np.int64)+45*intra.sum(axis=1)
    choices = np.zeros_like(vectors, dtype=np.uint8)
    for frame in range(len(states)):
        if costs[frame] <= target:
            continue
        queue = []
        def offer(tile, mode, previous=0):
            gain = int(gains[mode-1][frame, tile])-(int(gains[previous-1][frame, tile]) if previous else 0)
            extra = int(bits[mode-1][frame, tile])-(int(bits[previous-1][frame, tile]) if previous else 0)
            if gain > 0:
                heapq.heappush(queue, (-gain/max(1, extra), tile, mode, previous, gain))
        for tile in range(192):
            offer(tile, 1); offer(tile, 2)
        while queue and costs[frame] > target:
            _, tile, mode, previous, gain = heapq.heappop(queue)
            if choices[frame, tile] != previous:
                continue
            choices[frame, tile] = mode; costs[frame] -= gain
            if mode == 1:
                offer(tile, 2, 1)
    return choices, dict(target_tstates=target, estimated_total_tstates=int(costs.sum()),
        estimated_max_frame_tstates=int(costs.max()), estimated_frames_over_target=int((costs > target).sum()),
        selected_frames=int((choices != 0).any(axis=1).sum()),
        estimate_excludes_alignment_and_cache_changes=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--cpu-report', type=Path, required=True)
    p.add_argument('--targets', type=int, nargs='+', default=[300000])
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.fhs.read_bytes()
    model, original, count, mapping, tables = read_header(Reader(source))
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
    if (model != 0 or states.shape != (count, 3840) or decode(source)[0] != states.tobytes()
            or not cpu['complete'] or cpu['input_sha256'] != sha(source) or cpu['states_sha256'] != sha(states.tobytes())
            or not cpu['unrolled_motion'] or [f['index'] for f in cpu['frames']] != list(range(count))
            or any(t <= 0 for t in args.targets)):
        raise ValueError('source/CPU baseline mismatch')
    prof = fast.profile(states, vectors, residual, mapping, tables, unrolled_motion=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, complete=False, baseline_commit='eea5d62', input_sha256=sha(source),
        states_sha256=sha(states.tobytes()), cpu_report_sha256=sha(args.cpu_report.read_bytes()),
        no_additional_pixel_changes=True, full_frame_delivery_measured=False, player_changed=False,
        integrated_player_delta_tstates=0, cpu_selection_is_estimate=True, rows=[])
    for target in args.targets:
        choices, selection = select(prof, states, vectors, residual, [f['total_tstates'] for f in cpu['frames']], target)
        data, detail = fast.encode(original, states, vectors, residual, mapping, tables, choices == 2, raw_intra=choices == 1)
        restored, rows = decode(data, fast_fragments=True, raw_intra=True)
        if restored != states.tobytes() or rows != detail['frames']:
            raise AssertionError('independent reconstruction differs')
        name = f'target_{target}'
        (args.cache/(name+'.raw')).write_bytes(data)
        np.savez_compressed(args.cache/(name+'.npz'), choices=choices)
        row = dict(name=name, **selection, raw_bytes=len(data), sha256=sha(data), frames=count,
            raw_intra_tiles=detail['raw_intra_tiles'], raw_intra_values=detail['raw_intra_values'],
            fast_tiles=int((choices == 2).sum()), fast_kinds=detail['fast_kinds'],
            groups=len(detail['groups']), max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
            bits=sum(f['bits'] for f in rows), values=sum(f['values'] for f in rows),
            exact_causal_frame_decode=True, deflate_8192=measure(data, 8192))
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
