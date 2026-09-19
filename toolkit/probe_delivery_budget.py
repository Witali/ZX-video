"""Choose fast fragments against measured per-frame native-output cost.

Frame limits reserve the requested budget minus actual output and an
explicit heuristic margin. ZX0/metadata/IRQ/disk still require measurement.
Preserves edited screens, masks, AY and forced independent splice frames.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

import cell_output_stream
import probe_fast_fragments as fast
from probe_cache_aware_fragments import cache_cost, choose
from prepare_edited_movie import frame_map
from repack_edited_fragments import splice_arrays
from probe_fragment_channels import split, restore
from probe_spatial_contexts import read_header, decode
from probe_motion_entropy import Reader
from probe_lossless_layouts import sha, measure


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--cpu-report', type=Path, required=True)
    p.add_argument('--output-cpu', type=Path, required=True)
    p.add_argument('--maps', type=Path, required=True)
    p.add_argument('--timeline', type=Path, default=Path(__file__).with_name('movie_no_credits.json'))
    p.add_argument('--frame-budget', type=int, default=375000)
    p.add_argument('--estimate-margin', type=int, default=8000)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    source = args.fhs.read_bytes()
    model, original, count, mapping, tables = read_header(Reader(source))
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
    draw = json.loads(args.output_cpu.read_text(encoding='utf-8'))
    timeline = json.loads(args.timeline.read_text(encoding='utf-8'))
    indices = frame_map(count, timeline['remove_frames'])
    maps = args.maps.read_bytes()
    if (model != 0 or count != timeline['source_frames'] or not cpu['complete'] or not draw['complete']
            or args.frame_budget <= 0 or args.estimate_margin < 0
            or cpu['input_sha256'] != sha(source) or cpu['states_sha256'] != sha(states.tobytes())
            or sha(states.tobytes()) not in timeline['accepted_states_sha256']
            or draw['states_sha256'] != sha(states[indices].tobytes())
            or draw['masks_sha256'] != sha(maps) or len(maps) != 80*len(indices)
            or [f['index'] for f in cpu['frames']] != list(range(count))
            or [f['index'] for f in draw['frames']] != list(range(len(indices)))
            or not cpu['unrolled_motion'] or cpu['fast_fragments']
            or decode(source)[0] != states.tobytes()):
        raise ValueError('input/baseline/timeline mismatch')
    prof = fast.profile(states, vectors, residual, mapping, tables, unrolled_motion=True)
    overhead, measured = cache_cost(tables, mapping)
    intra = vectors >= 82
    gains = prof['estimated_gains']+64+27*intra
    extra = prof['extra_bits']-7
    costs = np.asarray([f['total_tstates'] for f in cpu['frames']])+27*intra.sum(axis=1)
    limits = args.frame_budget-args.estimate_margin-np.asarray([f['tstates'] for f in draw['frames']])
    chosen, choice = choose(gains[indices], extra[indices], vectors[indices], costs[indices], limits, overhead)
    full_choice = np.zeros_like(vectors, dtype=bool); full_choice[indices] = chosen
    screens, vv, rr, selected, joins = splice_arrays(states, vectors, residual, full_choice, indices)
    header = bytearray(original); struct.pack_into('<I', header, 31, len(screens))
    interleaved, detail = fast.encode(bytes(header), screens, vv, rr, mapping, tables, selected, group_frames=1)
    fsf, groups = split(interleaved, screens, vv, rr)
    rebuilt, actual = restore(fsf)
    if rebuilt != interleaved or actual != screens.tobytes():
        raise AssertionError('causal frame/serialization mismatch')
    stream = cell_output_stream.pack(fsf, maps)
    decoded, flags, records = cell_output_stream.unpack(stream)
    if decoded != fsf or flags != maps:
        raise AssertionError('cell stream roundtrip mismatch')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'separated.raw').write_bytes(fsf)
    (args.output/'cells.raw').write_bytes(stream)
    np.savez_compressed(args.output/'motion.npz', states=screens, vectors=vv, residual=rr, source_frames=indices)
    np.savez_compressed(args.output/'selection.npz', selected=selected)
    report = dict(scope=__doc__, complete=True, baseline_commit='6103e11',
        source_sha256=sha(source), states_sha256=sha(actual), fsf_sha256=sha(fsf), stream_sha256=sha(stream),
        maps_sha256=sha(maps), frame_budget_tstates=args.frame_budget, estimate_margin_tstates=args.estimate_margin,
        frames=len(screens), groups=len(groups), fast_tiles=int(selected.sum()), fast_kinds=detail['fast_kinds'],
        raw_bytes=len(stream), fsf_raw_bytes=len(fsf), deflate_8192_bytes=measure(stream, 8192),
        max_coded_bytes_with_guards=max(g['coded_bytes_with_guards'] for g in records),
        limits_min=int(limits.min()), limits_max=int(limits.max()),
        forced_join_frames=joins.tolist(), estimate_excludes_forced_join=True,
        choice=choice, cache_cost=measured, exact_causal_frame_decode=True,
        exact_serialized_roundtrip=True, no_additional_pixel_changes=True,
        selection_cpu_is_estimate=True, full_frame_delivery_measured=False,
        player_changed=False, integrated_player_delta_tstates=0)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('choice', 'cache_cost')}), flush=True)


if __name__ == '__main__':
    main()
