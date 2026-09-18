"""Serialize and independently decode FHD1 full-movie word dictionaries.

Reuses the exact FHF1 fast-tile selection. Mode 89 uses fixed-width row
indices only if shorter than a raw tile. No machine decoder or speedup is
claimed. The full dictionary is charged once in the serialized stream.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from fragment_dictionary import train
from probe_fast_fragments import encode
from probe_lossless_layouts import sha, measure
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, decode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--baseline-cpu', type=Path, required=True)
    p.add_argument('--bits', type=int, nargs='+', choices=range(8, 13), default=[8, 10, 11, 12])
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.fhs.read_bytes()
    model, original, count, mapping, tables = read_header(Reader(data))
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    with np.load(args.selection, allow_pickle=False) as saved:
        selected = saved['selected']
    baseline = json.loads(args.baseline_cpu.read_text(encoding='utf-8'))
    if (not baseline['complete'] or model != 0 or count != 4971 or states.shape != (count, 3840)
            or baseline['input_sha256'] != sha(data) or baseline['states_sha256'] != sha(states.tobytes())):
        raise ValueError('baseline mismatch')
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='d17f2ab', complete=False,
        input_sha256=sha(data), states_sha256=sha(states.tobytes()), selection_sha256=sha(selected.tobytes()),
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        z80_not_implemented=True, rows=[])
    for bits in args.bits:
        dictionary = train(states, selected, bits)
        encoded, detail = encode(original, states, vectors, residual, mapping, tables, selected, dictionary=dictionary)
        restored, rows = decode(encoded, fast_fragments=True, fragment_dictionary=True)
        if restored != states.tobytes() or rows != detail['frames']:
            raise AssertionError('independent FHD1 restoration differs')
        name = f'words_{bits}'
        (args.cache/(name+'.raw')).write_bytes(encoded)
        row = dict(name=name, index_bits=bits, raw_bytes=len(encoded), sha256=sha(encoded),
            dictionary_bytes=len(dictionary[1]), dictionary_sha256=sha(dictionary[1]),
            frames=count, exact_causal_frame_decode=True, fast_kinds=detail['fast_kinds'],
            groups=len(detail['groups']), max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
            bits=sum(f['bits'] for f in rows), values=sum(f['values'] for f in rows),
            deflate_8192_screen_only=measure(encoded, 8192))
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
