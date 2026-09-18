"""Size shared four-bit lookup nodes for the long Huffman fallback.

No stream, player or pixels are changed. Enumerates exact canonical trees
and deduplicates identical lookup nodes across contexts. Each node has 16
value bytes and 16 length bytes; a zero length means a child node. This is
a memory/traffic profile, not a Z80 implementation or measured speedup.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from prefix_huffman_z80 import prepare
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader, codes_for
from probe_spatial_contexts import read_header


def shared_nodes(tables):
    nodes, ids, roots = [], {}, []

    def intern(tree):
        entries = []
        for nibble in range(16):
            branch = tree
            consumed = 0
            while isinstance(branch, dict) and consumed < 4:
                branch = branch[(nibble >> (3-consumed)) & 1]
                consumed += 1
            entries.append((intern(branch), 0) if isinstance(branch, dict) else (branch, consumed))
        key = tuple(entries)
        if key not in ids:
            ids[key] = len(nodes)
            nodes.append(key)
        return ids[key]

    for table in tables:
        tree = {}
        for symbol, (code, length) in enumerate(codes_for(255, table)):
            if not length:
                continue
            branch = tree
            for bit in range(length-1, 0, -1):
                branch = branch.setdefault((code >> bit) & 1, {})
            branch[code & 1] = symbol
        context_roots = {}
        for prefix in range(256):
            branch = tree
            for bit in range(7, -1, -1):
                if not isinstance(branch, dict):
                    break
                branch = branch[(prefix >> bit) & 1]
            if isinstance(branch, dict):
                context_roots[prefix] = intern(branch)
        roots.append(context_roots)
        # Walk every code through generated tables independently of the
        # constructor, including every unused padding suffix after its end.
        for symbol, (code, length) in enumerate(codes_for(255, table)):
            if length <= 8:
                continue
            extra = length-8
            node = context_roots[code >> extra]
            consumed = 0
            while True:
                remain = extra-consumed
                nibble = (code >> (remain-4)) & 15 if remain >= 4 else (code << (4-remain)) & 15
                value, bits = nodes[node][nibble]
                if bits:
                    if value != symbol or consumed+bits != extra:
                        raise AssertionError('tail table code mismatch')
                    if remain < 4:
                        for suffix in range(1 << (4-remain)):
                            if nodes[node][nibble | suffix] != (symbol, remain):
                                raise AssertionError('tail padding mismatch')
                    break
                consumed += 4; node = value
    return nodes, roots


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.fhs.read_bytes()
    model, _, count, mapping, tables = read_header(Reader(data))
    with np.load(args.motion_cache, allow_pickle=False) as saved:
        states, residual = saved['states'], saved['residual']
    if model != 0 or states.shape != residual.shape or states.shape != (count, 3840):
        raise ValueError('unsupported source/model')
    nodes, roots = shared_nodes(tables)
    lengths = np.array([list(t) for t in tables], dtype=np.uint8)
    predicted = states ^ residual
    contexts = np.frombuffer(mapping, dtype=np.uint8)[predicted[:, :3072]]
    bitmap_lengths = lengths[contexts, states[:, :3072]][residual[:, :3072] != 0]
    attr_lengths = lengths[-1, residual[:, 3072:]][residual[:, 3072:] != 0]
    hist = Counter(int(n) for n in np.concatenate([bitmap_lengths, attr_lengths]))
    if hist.get(0):
        raise AssertionError('source contains uncoded values')
    old = prepare(tables, mapping)
    body = len(tables)*512+len(nodes)*32
    # Profile a bounded alternative: accelerate only 9..12-bit leaves of
    # selected root prefixes; any longer code retains the canonical path.
    # Root redirection/address maps and their CPU costs are not designed.
    active = residual[:, :3072] != 0
    keys = contexts[active].astype(np.int32)*256+states[:, :3072][active]
    traffic = np.bincount(keys, minlength=len(tables)*256).reshape(len(tables), 256)
    traffic[-1] = np.bincount(residual[:, 3072:][residual[:, 3072:] != 0], minlength=256)
    hot = Counter()
    for context, table in enumerate(tables):
        for symbol, (code, length) in enumerate(codes_for(255, table)):
            if not 9 <= length <= 12:
                continue
            node = nodes[roots[context][code >> (length-8)]]
            partial = tuple(entry if entry[1] else (-1, 0) for entry in node)
            hot[partial] += int(traffic[context, symbol])
    ranked = sorted(hot.values(), reverse=True)
    bounded = [dict(node_budget=n, table_bytes=n*32, accelerated_values=sum(ranked[:n]),
        root_redirection_and_address_tables_not_included=True) for n in (16, 32, 64, 128)]
    report = dict(scope=__doc__, complete=True, input_sha256=sha(data), states_sha256=sha(states.tobytes()),
        frames=count, contexts=len(tables), maximum_length=max(map(max, tables)),
        old_body_bytes=old['body_bytes'], root_bytes=len(tables)*512,
        unique_four_bit_nodes=len(nodes), long_prefix_roots=sum(map(len, roots)),
        node_bytes=len(nodes)*32, all_node_ids_fit_one_byte=len(nodes) <= 256,
        node_byte_estimate_requires_encoding_high_id_bits_when_over_256=True,
        estimated_body_bytes=body, estimated_bank_bytes_with_shift_tables=body+4096,
        spare_in_16k_bank_before_address_tables=16384-body-4096,
        proposed_node_address_tables_bytes=2*len(nodes),
        histogram=dict(sorted(hist.items())), long_values=sum(n for k, n in hist.items() if k > 8),
        four_bit_lookups=sum(((k-8+3)//4)*n for k, n in hist.items() if k > 8),
        old_single_bit_tail_steps=sum((k-8)*n for k, n in hist.items() if k > 8),
        all_codes_and_padding_verified=True, z80_cycles_not_measured=True,
        bounded_root_tables=bounded,
        player_changed=False, integrated_player_delta_tstates=0,
        nodes=nodes, roots=roots)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('nodes', 'roots')}), flush=True)


if __name__ == '__main__':
    main()
