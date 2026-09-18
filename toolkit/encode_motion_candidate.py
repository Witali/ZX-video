"""Encode bounded-motion candidates as FHT1 with a fixed context map.

Retrain canonical lengths on each candidate's actual direct bitmap bytes
and XOR attributes. Keep the baseline predictor-to-context map, framing and
decoder unchanged. Independently restore every causal frame before saving.
This is an offline storage experiment, not a quality or playback approval.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_hybrid_tiles import read_header, encode, decode
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, huffman_lengths
from prefix_huffman_z80 import prepare


def train(states, residual, mapping, count):
    predicted = states ^ residual
    active = residual[:, :3072] != 0
    contexts = np.frombuffer(mapping, dtype=np.uint8)[predicted[:, :3072]]
    keys = contexts[active].astype(np.int32)*256+states[:, :3072][active]
    histogram = np.zeros((count, 256), dtype=np.int64)
    histogram[:-1] = np.bincount(keys, minlength=(count-1)*256).reshape(count-1, 256)
    attributes = residual[:, 3072:]
    histogram[-1] = np.bincount(attributes[attributes != 0], minlength=256)
    tables = [huffman_lengths(dict(enumerate(row))) for row in histogram]
    bits = int((histogram*np.asarray([list(t) for t in tables])).sum())
    return tables, histogram, bits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-fht', type=Path, required=True)
    p.add_argument('--candidates', type=Path, nargs='+', required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline-commit', required=True)
    args = p.parse_args()
    baseline = args.baseline_fht.read_bytes()
    original, count, _, mapping, old_tables = read_header(Reader(baseline))
    report = dict(scope=__doc__, baseline_commit=args.baseline_commit,
        baseline_fht_sha256=sha(baseline), fixed_context_map_sha256=sha(mapping),
        complete=False, player_changed=False, integrated_player_delta_tstates=0, rows=[])
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for path in args.candidates:
        with np.load(path) as saved:
            states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
        if states.shape != (count, 3840) or states.dtype != np.uint8 or residual.dtype != np.uint8:
            raise ValueError('candidate shape/type differs')
        tables, histogram, expected_bits = train(states, residual, mapping, len(old_tables))
        layout = prepare(tables, mapping)
        data, detail = encode(original, states, vectors, residual, mapping, tables, None)
        restored, rows = decode(data)
        if restored != states.tobytes() or rows != detail['frames']:
            raise AssertionError('independent causal restoration differs')
        if sum(f['bits'] for f in rows) != expected_bits:
            raise AssertionError('trained bit budget differs from encoded stream')
        name = path.stem
        (args.cache/(name+'.fht')).write_bytes(data)
        entry = dict(name=name, frames=count, states_sha256=sha(restored),
            input_vectors_sha256=sha(vectors.tobytes()), input_residual_sha256=sha(residual.tobytes()),
            raw_bytes=len(data), sha256=sha(data), exact_causal_frame_decode=True,
            exact_baseline_stream=data == baseline, tables_equal_baseline=tables == old_tables,
            groups=len(detail['groups']), max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
            values=int(histogram.sum()), attribute_values=int(histogram[-1].sum()), bits=expected_bits,
            cache_frames=sum(f['cache'] for f in rows),
            prefix_depth=layout['depth'], prefix_body_bytes=layout['body_bytes'],
            prefix_ram_regions=[dict(base=base, bytes=len(blob), sha256=sha(blob)) for base, blob in layout['regions']],
            deflate_8192=measure(data, 8192), quality_approval=False, z80_cpu_measured=False)
        report['rows'].append(entry)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(entry), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
