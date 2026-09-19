"""Validate conservative back-screen dirty flags from existing FSF1 metadata.

No additional bytes, pixel changes, or speed improvement are claimed. These
flags can be computed on Z80 from expanded vectors and masks. Union with
the previous frame is necessary because the back screen contains frame n-2.
This host audit proves coverage; it is not a measured Z80 flag generator.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, read_group
from probe_fast_fragments import SIZES
from probe_motion_residual_order import field_order
from probe_lossless_layouts import sha


def audit(data, states):
    r = Reader(data)
    _, _, count, _, _ = read_header(r, magic=b'FSF1')
    if states.shape != (count, 3840):
        raise ValueError('different state count')
    order = field_order(8).reshape(192, 20)[:, :16]
    previous = np.zeros(3840, dtype=np.uint8)
    screens = [previous.copy(), previous.copy()]
    previous_bitmap = np.zeros(192, dtype=bool)
    previous_attrs = np.zeros(768, dtype=bool)
    index, results = 0, []
    while index < count:
        n, _, _, vectors, bm, at, _ = read_group(r, count-index, fast_fragments=True)
        r.take(sum(SIZES.get(v, 0) for v in vectors))
        vectors = np.frombuffer(vectors, dtype=np.uint8).reshape(n, 192)
        masks = np.frombuffer(bm, dtype=np.uint8).reshape(n, 192, 2)
        attr_masks = np.unpackbits(np.frombuffer(at, dtype=np.uint8)).reshape(n, 768).astype(bool)
        for i in range(n):
            current = states[index]
            dirty = (vectors[i] != 0) | masks[i].any(axis=1)
            attrs = attr_masks[i]
            if (np.any(np.any(current[order] != previous[order], axis=1) & ~dirty)
                    or not np.array_equal(current[3072:] != previous[3072:], attrs)):
                raise AssertionError('metadata omits adjacent-frame changes')
            union = dirty | previous_bitmap
            attr_union = attrs | previous_attrs
            back = screens[index % 2]
            actual = np.any(current[order] != back[order], axis=1)
            actual_attrs = current[3072:] != back[3072:]
            if np.any(actual & ~union) or np.any(actual_attrs & ~attr_union):
                raise AssertionError('back-screen change omitted')
            results.append(dict(index=index, current_tiles=int(dirty.sum()),
                union_tiles=int(union.sum()), actual_tiles=int(actual.sum()),
                union_stripes=int(union.reshape(12, 16).any(axis=1).sum()),
                union_attributes=int(attr_union.sum()), actual_attributes=int(actual_attrs.sum())))
            previous_bitmap, previous_attrs, previous = dirty, attrs, current
            screens[index % 2] = current
            index += 1
    r.end()
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stream', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.stream.read_bytes()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    results = audit(data, states)
    outside = np.concatenate((states[:, :12*32], states[:, 84*32:3072]), axis=1)
    affected = np.flatnonzero(outside.any(axis=1))
    metrics = ('current_tiles', 'union_tiles', 'actual_tiles', 'union_stripes', 'union_attributes', 'actual_attributes')
    summary = {key: dict(total=sum(r[key] for r in results), maximum=max(r[key] for r in results),
                         mean=sum(r[key] for r in results)/len(results)) for key in metrics}
    report = dict(scope=__doc__, complete=True, frames=len(results), input_sha256=sha(data),
        states_sha256=sha(states.tobytes()), rows=results, summary=summary,
        nominal_72_row_crop=dict(first=12, rows=72, safe=not bool(len(affected)),
            affected_frames=len(affected), first_affected_frame=int(affected[0]) if len(affected) else None,
            nonzero_bytes=int(np.count_nonzero(outside))),
        added_disk_bytes=0, full_frame_delivery_measured=False, player_changed=False,
        integrated_player_delta_tstates=0)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
