"""Choose FSF1 fragments with the whole-frame motion-cache cost included.

For each frame compare normal selection against replacing every remaining
temporal-motion tile, which disables the frame cache. The CPU budget remains
an estimate until a complete Z80 run. Serialized output is causally decoded
and exactly reinterleaved to the intermediate FHF1 stream before acceptance.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_causal_tiles import Harness
import probe_fast_fragments as fast
from probe_fragment_channels import split, restore
from probe_spatial_contexts import read_header, decode, OFFSETS
from probe_motion_entropy import Reader
from probe_lossless_layouts import sha, measure


def cache_cost(tables, mapping):
    rows = []
    for enabled in (False, True):
        h = Harness(tables, mapping, OFFSETS, hybrid=True, skip_empty=True, intra_above=True,
                    intra_extended=True, fast_fragments=True, unrolled_motion=True, split_literals=True)
        h.begin(b'', bytes(192), bytes(384), bytes(96), literals=b'')
        h.cache_frames[0] = enabled
        rows.append(h.run(0, bytes(3840)))
    delta = rows[1]['total_tstates']-rows[0]['total_tstates']
    if any(rows[0]['stages'].get(stage, 0) != rows[1]['stages'].get(stage, 0)
           for stage in set(rows[0]['stages']) | set(rows[1]['stages']) if stage not in ('cache', 'control')):
        raise AssertionError('cache cost changed unrelated stages')
    return delta, dict(disabled=rows[0], enabled=rows[1], delta_tstates=delta,
                      timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


def choose(gains, extra_bits, vectors, frame_costs, target, cache_overhead):
    limits = np.broadcast_to(np.asarray(target, dtype=np.int64), (len(vectors),))
    if np.any(limits <= 0):
        raise ValueError('frame limits must be positive')
    motion = (vectors > 0) & (vectors < 81)
    selected = np.zeros_like(vectors, dtype=bool)
    costs = np.empty(len(vectors), dtype=np.int64)
    forced_wins = 0
    for frame in range(len(vectors)):
        limit = int(limits[frame])
        order = sorted(range(192), key=lambda t: (-gains[frame, t]/max(1, int(extra_bits[frame, t])), t))
        cases = []
        for force in ((False, True) if motion[frame].any() else (False,)):
            pick = motion[frame].copy() if force else np.zeros(192, dtype=bool)
            ticks = int(frame_costs[frame]-gains[frame, pick].sum()-(cache_overhead if force else 0))
            for tile in order:
                if ticks <= limit:
                    break
                if not pick[tile] and gains[frame, tile] > 0:
                    pick[tile] = True; ticks -= int(gains[frame, tile])
            if not force and motion[frame].any() and np.all(pick[motion[frame]]):
                ticks -= cache_overhead
            added = int(extra_bits[frame, pick].sum())
            # Prefer a feasible budget, then fewer estimated bytes. If no
            # candidate reaches it, retain the least CPU work explicitly.
            key = (ticks > limit, added if ticks <= limit else ticks, ticks, force)
            cases.append((key, pick, ticks, force))
        _, pick, ticks, force = min(cases, key=lambda item: item[0])
        selected[frame] = pick; costs[frame] = ticks; forced_wins += force
    return selected, dict(target_tstates=int(target) if np.ndim(target) == 0 else limits.tolist(), estimated_total_tstates=int(costs.sum()),
        estimated_max_frame_tstates=int(costs.max()), estimated_frames_over_target=int((costs > limits).sum()),
        forced_no_cache_winning_frames=forced_wins,
        cache_frames_before=int(motion.any(axis=1).sum()),
        cache_frames_after=int((motion & ~selected).any(axis=1).sum()),
        selected_frames=int(selected.any(axis=1).sum()),
        estimated_added_bits=int(extra_bits[selected].sum()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--cpu-report', type=Path, required=True)
    p.add_argument('--target', type=int, default=300000)
    p.add_argument('--baseline-commit', default='1659579')
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.fhs.read_bytes()
    model, original, count, mapping, tables = read_header(Reader(source))
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
    if (args.target <= 0 or model != 0 or states.shape != (count, 3840)
            or not cpu['complete'] or cpu['input_sha256'] != sha(source)
            or cpu['states_sha256'] != sha(states.tobytes()) or not cpu['unrolled_motion']
            or cpu.get('fast_fragments') or [f['index'] for f in cpu['frames']] != list(range(count))
            or decode(source)[0] != states.tobytes()):
        raise ValueError('input/baseline mismatch')
    prof = fast.profile(states, vectors, residual, mapping, tables, unrolled_motion=True)
    overhead, measured = cache_cost(tables, mapping)
    intra = vectors >= 82
    # FSF removes 54 body T plus the conservative 10 unaligned T from
    # FHF's estimated fast cost. Retained intra still adds 27 dispatch T.
    gains = prof['estimated_gains']+64+27*intra
    extra = prof['extra_bits']-7  # No per-fragment bit alignment in FSF.
    frame_costs = np.asarray([f['total_tstates'] for f in cpu['frames']])+27*intra.sum(axis=1)
    selected, choice = choose(gains, extra, vectors, frame_costs, args.target, overhead)
    interleaved, detail = fast.encode(original, states, vectors, residual, mapping, tables, selected)
    data, groups = split(interleaved, states, vectors, residual)
    restored, frames = restore(data)
    if restored != interleaved or frames != states.tobytes():
        raise AssertionError('independent restoration differs')
    args.cache.mkdir(parents=True, exist_ok=True)
    (args.cache/'interleaved.raw').write_bytes(interleaved)
    (args.cache/'separated.raw').write_bytes(data)
    np.savez_compressed(args.cache/'selection.npz', selected=selected)
    report = dict(scope=__doc__, complete=True, baseline_commit=args.baseline_commit, input_sha256=sha(source),
        states_sha256=sha(frames), cpu_report_sha256=sha(args.cpu_report.read_bytes()), sha256=sha(data),
        frames=count, **choice, cache_cost=measured, fast_tiles=int(selected.sum()), fast_kinds=detail['fast_kinds'],
        raw_bytes=len(data), interleaved_bytes=len(interleaved), groups=len(groups),
        huffman_bits=sum(g['huffman_bits'] for g in groups), literal_bytes=sum(g['literal_bytes'] for g in groups),
        max_group_bytes=max(g['combined_bytes'] for g in groups), exact_causal_frame_decode=True,
        exact_interleaved_roundtrip=True, deflate_8192=measure(data, 8192),
        player_changed=False, integrated_player_delta_tstates=0, no_additional_pixel_changes=True,
        selection_cpu_is_estimate=True, full_frame_delivery_measured=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
