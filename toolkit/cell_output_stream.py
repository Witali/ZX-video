"""FSC1: put 80-byte native update maps before each FSF1 group's values.

Header matches FSF1 except magic. Group layout: unchanged 11-byte header,
encoded vectors/masks, n*80 native-map bytes, Huffman bytes, fragment bytes.
This provides one causal stream for a future player; it is not a release.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from probe_fast_fragments import SIZES
from probe_fragment_channels import restore
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, read_group
from probe_lossless_layouts import sha


def pack(source, maps):
    r = Reader(source)
    _, _, count, _, _ = read_header(r, magic=b'FSF1')
    if len(maps) != 80*count:
        raise ValueError('incorrect map length')
    result, index = bytearray(b'FSC1'+source[4:r.pos]), 0
    while index < count:
        start = r.pos
        n, _, _, vectors, _, _, _ = read_group(r, count-index, fast_fragments=True)
        r.take(sum(SIZES.get(v, 0) for v in vectors))
        vl, ml = struct.unpack_from('<HH', source, start+2)
        insertion = start+11+vl+ml
        result += source[start:insertion]+maps[index*80:(index+n)*80]+source[insertion:r.pos]
        index += n
    r.end()
    return bytes(result)


def unpack(source):
    r = Reader(source)
    _, _, count, _, _ = read_header(r, magic=b'FSC1')
    result, maps, groups, index = bytearray(b'FSF1'+source[4:r.pos]), bytearray(), [], 0
    while index < count:
        header = r.take(11)
        n, vl, ml, _, bits = struct.unpack('<HHHBI', header)
        if not 1 <= n <= min(8, count-index):
            raise ValueError('invalid group length')
        metadata = r.take(vl+ml)
        maps += r.take(n*80)
        encoded = r.take((bits+7)//8)
        old = header+metadata+encoded
        temp = Reader(old)
        _, _, _, vectors, _, _, _ = read_group(temp, count-index, fast_fragments=True)
        temp.end()
        literal = r.take(sum(SIZES.get(v, 0) for v in vectors))
        result += old+literal
        groups.append(dict(start=index, frames=n, coded_bytes=len(encoded)+len(literal),
            coded_bytes_with_guards=len(encoded)+len(literal)+2,
            expanded_metadata_bytes=n*672, native_map_bytes=n*80))
        index += n
    r.end()
    return bytes(result), bytes(maps), groups


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fsf', type=Path, required=True)
    p.add_argument('--maps', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    fsf, maps = args.fsf.read_bytes(), args.maps.read_bytes()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    data = pack(fsf, maps)
    original, recovered, groups = unpack(data)
    if original != fsf or recovered != maps or restore(original)[1] != states.tobytes():
        raise AssertionError('stream/screens changed')
    raster = states[:, 256:2816].reshape(-1, 20, 4, 32)
    previous = np.zeros_like(raster); previous[2:] = raster[:-2]
    flags = np.unpackbits(np.frombuffer(maps, dtype=np.uint8)).reshape(-1, 20, 32).astype(bool)
    if (np.any(states[:, :256]) or np.any(states[:, 2816:3072])
            or np.any((raster != previous) & ~flags[:, :, None, :])):
        raise AssertionError('native output map misses screen changes')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    single = all(g['frames'] == 1 for g in groups)
    maximum = max(g['coded_bytes_with_guards'] for g in groups)
    report = dict(scope=__doc__, complete=True, states_sha256=sha(states.tobytes()),
        fsf_sha256=sha(fsf), maps_sha256=sha(maps), stream_sha256=sha(data),
        frames=len(states), groups=len(groups), raw_bytes=len(data),
        exact_serialized_roundtrip=True, exact_causal_frames=True, exact_native_map_coverage=True,
        one_frame_groups=single, max_coded_bytes_with_guards=maximum,
        max_expanded_metadata_bytes=max(g['expanded_metadata_bytes'] for g in groups),
        proposed_input_window=dict(first=0xa6a0, end_exclusive=0xb900, bytes=4704,
            fits=single and maximum <= 4704,
            note='Requires relocating one frame of metadata to A400..A69F and maps to 7300..734F; not an integrated memory validation.'),
        full_frame_delivery_measured=False, player_changed=False, integrated_player_delta_tstates=0)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
