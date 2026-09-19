"""Rebuild FSF1 around an edit, resetting prediction at each splice.

Keep all selected screens exact and all non-splice predictor decisions.
Splices use complete fragments plus new attribute XOR against the retained
predecessor. Re-encode groups/headers and independently decode every frame.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from prepare_edited_movie import frame_map
from probe_fast_fragments import encode
from probe_fragment_channels import split, restore
from probe_motion_entropy import Reader, huffman_lengths
from probe_spatial_contexts import read_header, decode
from probe_lossless_layouts import sha


def splice_arrays(states, vectors, residual, selected, indices):
    if (vectors.shape != (len(states), 192) or residual.shape != states.shape
            or selected.shape != vectors.shape):
        raise ValueError('invalid predictor arrays')
    screens, vv, rr, chosen = (x[indices].copy() for x in (states, vectors, residual, selected))
    boundaries = np.flatnonzero(np.r_[indices[0] != 0, np.diff(indices) != 1])
    for i in boundaries:
        vv[i] = 0
        rr[i] = screens[i] ^ (screens[i-1] if i else np.zeros(3840, dtype=np.uint8))
        chosen[i] = True
    return screens, vv, rr, chosen, boundaries


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--timeline', type=Path, default=Path(__file__).with_name('movie_no_credits.json'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--group-frames', type=int, choices=range(1, 9), default=8)
    args = p.parse_args()
    source = args.fhs.read_bytes()
    model, header, count, mapping, tables = read_header(Reader(source))
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    with np.load(args.selection, allow_pickle=False) as saved:
        selected = saved['selected']
    timeline = json.loads(args.timeline.read_text(encoding='utf-8'))
    if (model != 0 or count != len(states) or count != timeline['source_frames']
            or sha(states.tobytes()) not in timeline['accepted_states_sha256']
            or decode(source)[0] != states.tobytes()):
        raise ValueError('source/timeline mismatch')
    indices = frame_map(count, timeline['remove_frames'])
    screens, vv, rr, chosen, boundaries = splice_arrays(states, vectors, residual, selected, indices)
    original = bytearray(header)
    struct.pack_into('<I', original, 31, len(screens))
    attrs = rr[:, 3072:]
    missing = [int(v) for v in np.unique(attrs[attrs != 0]) if not tables[-1][v]]
    if missing:
        tables[-1] = huffman_lengths(Counter(attrs[attrs != 0].tolist()))
    interleaved, detail = encode(bytes(original), screens, vv, rr, mapping, tables, chosen, group_frames=args.group_frames)
    data, groups = split(interleaved, screens, vv, rr)
    rebuilt, actual = restore(data)
    if actual != screens.tobytes() or rebuilt != interleaved:
        raise AssertionError('causal decode or serialized roundtrip differs')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'separated.raw').write_bytes(data)
    np.savez_compressed(args.output/'motion.npz', states=screens, vectors=vv, residual=rr, source_frames=indices)
    np.savez_compressed(args.output/'selection.npz', selected=chosen)
    report = dict(scope=__doc__, complete=True, source_sha256=sha(source),
        source_states_sha256=sha(states.tobytes()), frames=len(screens),
        states_sha256=sha(actual), sha256=sha(data), raw_bytes=len(data),
        reset_frames=boundaries.tolist(), group_frame_limit=args.group_frames, attribute_table_retrained=bool(missing),
        new_attribute_symbols=missing, groups=len(groups), fast_kinds=detail['fast_kinds'],
        max_group_bytes=max(g['combined_bytes'] for g in groups),
        exact_causal_frame_decode=True, exact_interleaved_roundtrip=True,
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        full_frame_delivery_measured=False)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
