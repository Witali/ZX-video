"""Train Huffman contexts only on corrections retained after fragment selection.

Complete and raw-correction tiles are excluded from the bitmap histogram.
Selected modes/pixels/AY remain unchanged. Compares fixed context mapping
with a fresh 16-cluster mapping; all serialized streams are PC-decoded.
Instruction CPU work, actual ZX0 and full delivery must be measured separately.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from prefix_huffman_z80 import prepare
from probe_fast_fragments import encode
from probe_lossless_layouts import sha, measure
from probe_motion_entropy import Reader, huffman_lengths
from probe_motion_residual_order import field_order
from probe_spatial_contexts import read_header, decode
from profile_prediction_contexts import clustered_tables


def histogram(states, residual, excluded):
    order = field_order(8).reshape(192, 20)[:, :16]
    current, predicted = states[:, order], (states ^ residual)[:, order]
    active = (current != predicted) & ~excluded[:, :, None]
    keys = predicted[active].astype(np.int32)*256+current[active]
    hist = np.zeros((257, 256), dtype=np.int64)
    hist[:256] = np.bincount(keys, minlength=65536).reshape(256, 256)
    attributes = residual[:, 3072:]
    hist[-1] = np.bincount(attributes[attributes != 0], minlength=256)
    return hist


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.input.read_bytes(); raw = source[:4] == b'FHC1'
    if source[:4] not in (b'FHF1', b'FHC1'):
        raise ValueError('requires FHF1 or FHC1')
    model, original, count, mapping, tables = read_header(Reader(source), magic=source[:4])
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    with np.load(args.selection, allow_pickle=False) as saved:
        selected = saved['choices'] == 2 if raw else saved['selected']
        direct = saved['choices'] == 1 if raw else None
    control, detail = encode(original, states, vectors, residual, mapping, tables, selected, raw_intra=direct)
    if (model != 0 or count != 4971 or control != source
            or decode(source, fast_fragments=True, raw_intra=raw)[0] != states.tobytes()):
        raise ValueError('source/selection mismatch')
    hist = histogram(states, residual, selected | (direct if raw else False))
    if int(hist.sum()) != sum(r['values'] for r in detail['frames']):
        raise AssertionError('retained values differ')
    def stats(lookup, lengths):
        merged = np.zeros((len(lengths), 256), dtype=np.int64)
        for i, context in enumerate(lookup):
            merged[context] += hist[i]
        merged[-1] = hist[-1]
        sizes = np.asarray([list(t) for t in lengths])
        if np.any((merged != 0) & (sizes == 0)):
            raise ValueError('uncoded value')
        return merged, dict(bits=int((merged*sizes).sum()), values=int(merged.sum()),
            long_values=int(merged[sizes > 8].sum()), maximum_length=int(sizes.max()))
    merged, prior = stats(mapping, tables)
    fixed = [huffman_lengths(dict(enumerate(h))) if np.count_nonzero(h) >= 2 else old for h, old in zip(merged, tables)]
    cluster = clustered_tables(hist, requested=[16], baseline_bits=prior['bits'])[0]
    variants = [('fixed', mapping, fixed), ('clustered16', bytes(cluster['context_map']), [bytes(t) for t in cluster['tables']])]
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='6c5c818', complete=False, format=source[:4].decode(),
        input_sha256=sha(source), selection_sha256=sha(args.selection.read_bytes()),
        states_sha256=sha(states.tobytes()), before=prior, no_additional_pixel_changes=True,
        player_changed=False, full_frame_delivery_measured=False, rows=[])
    for name, lookup, lengths in variants:
        _, counts = stats(lookup, lengths)
        try:
            layout = prepare(lengths, lookup)
        except ValueError as error:
            row = dict(name=name, **counts, accepted=False, reason=str(error))
        else:
            data, detail = encode(original, states, vectors, residual, lookup, lengths, selected, raw_intra=direct)
            restored, frames = decode(data, fast_fragments=True, raw_intra=raw)
            if restored != states.tobytes() or frames != detail['frames']:
                raise AssertionError('independent reconstruction differs')
            (args.cache/(name+'.raw')).write_bytes(data)
            row = dict(name=name, **counts, accepted=True, frames=count, raw_bytes=len(data), sha256=sha(data),
                raw_delta_bytes=len(data)-len(source), groups=len(detail['groups']),
                max_group_bytes=max(g['encoded_bytes'] for g in detail['groups']),
                exact_causal_frame_decode=True, prefix_body_bytes=layout['body_bytes'],
                prefix_bank_bytes=layout['body_bytes']+4096, deflate_8192=measure(data, 8192),
                context_map=list(lookup), tables=[list(t) for t in lengths])
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in row.items() if k not in ('context_map', 'tables')}), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
