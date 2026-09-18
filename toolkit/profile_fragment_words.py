"""Measure a 255-word dictionary for exact fast-tile payloads, offline only.

A word is two packed bytes (eight 2-bit pixels). Tokens 0..254 name words;
255 escapes a literal word, costing three bytes. Arbitrary 16-byte tiles
can choose this row representation when shorter. Structured fast tiles
keep their existing representation. This is a payload estimate, not a
serialized codec, ZX0 size, Z80 implementation or release memory layout.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from probe_fast_fragments import pack_fragment
from probe_lossless_layouts import sha
from probe_motion_residual_order import field_order


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--widths', type=int, nargs='+', choices=range(8, 13), help='also estimate wider fixed-index dictionaries')
    args = p.parse_args()
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states = saved['states']
    with np.load(args.selection, allow_pickle=False) as saved:
        selected = saved['selected']
    if selected.dtype != bool or selected.shape != (len(states), 192):
        raise ValueError('invalid selection')
    order = field_order(8).reshape(192, 20)[:, :16]
    current = states[:, order][selected]
    kinds = np.array([pack_fragment(tile.tobytes())[0] for tile in current])
    arbitrary = current[kinds == 85].astype(np.uint16)
    words = arbitrary[:, ::2]+256*arbitrary[:, 1::2]
    histogram = np.bincount(words.ravel(), minlength=65536)
    ranked = np.argsort(-histogram, kind='stable')[:255]
    lookup = np.zeros(65536, dtype=bool); lookup[ranked] = True
    misses = (~lookup[words]).sum(axis=1)
    payload = 8+2*misses
    adopted = payload < 16
    savings = int((16-payload[adopted]).sum())
    report = dict(scope=__doc__, complete=True, states_sha256=sha(states.tobytes()),
        selection_sha256=sha(selected.tobytes()), frames=len(states), selected_tiles=len(current),
        fast_kinds=dict(Counter(int(k) for k in kinds)), arbitrary_tiles=len(arbitrary),
        dictionary_entries=255, dictionary_payload_bytes=510,
        proposed_lookup_ram_bytes=512, allocation_and_z80_not_implemented=True,
        dictionary_words=[dict(word=int(word), count=int(histogram[word])) for word in ranked],
        words=int(words.size), dictionary_hits=int(lookup[words].sum()),
        misses_per_tile=dict(Counter(int(m) for m in misses)), adopted_tiles=int(adopted.sum()),
        old_arbitrary_payload_bytes=int(arbitrary.size),
        estimated_new_arbitrary_payload_bytes=int(np.minimum(payload, 16).sum()),
        estimated_payload_saving=savings, estimated_payload_saving_less_dictionary=savings-510,
        does_not_include_metadata_alignment_or_zx0=True, player_changed=False)
    if args.widths:
        ranking = np.argsort(-histogram, kind='stable')
        variants = []
        for bits in args.widths:
            entries = (1 << bits)-1
            member = np.zeros(65536, dtype=bool); member[ranking[:entries]] = True
            missing = (~member[words]).sum(axis=1)
            size = bits+2*missing  # Eight fixed-width indices, then 16-bit escapes.
            shorter = size < 16
            saving = int((16-size[shorter]).sum())
            variants.append(dict(index_bits=bits, dictionary_entries=entries,
                dictionary_bytes=entries*2, dictionary_hits=int(member[words].sum()),
                adopted_tiles=int(shorter.sum()), payload_saving=saving,
                payload_saving_less_dictionary=saving-2*entries,
                miss_histogram=dict(Counter(int(m) for m in missing))))
        report['width_variants'] = variants
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'dictionary_words'}), flush=True)


if __name__ == '__main__':
    main()
