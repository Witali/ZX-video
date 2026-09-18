"""Exact runtime table sizes for two Huffman layouts, not Z80 timing.

Each internal node is two little-endian u16 edges. Bit 15 tags a leaf,
whose low byte is the nonzero symbol; other edges are internal node indices.
Identical subtrees are shared across contexts. Runtime tables comprise the
256-byte predictor/context map, u16 roots and 4-byte nodes. No alignment,
code, stream state, paging or bank scheduling is included in this size.
Also test compact canonical counts: fixed max-depth counts followed by
symbols sorted by (length, value). Canonical decoding maintains the rank
among still-unresolved prefixes rather than an 18-bit absolute code. With
at most 255 leaves, rank and symbol index both fit in one byte.
"""
import argparse
import json
from pathlib import Path
import struct

from probe_lossless_layouts import sha
from probe_motion_entropy import codes_for


def shared_tree(tables):
    nodes, interned, roots = [], {}, []

    def visit(tree):
        if isinstance(tree, int):
            return 0x8000 | tree
        if set(tree) != {0, 1}:
            raise ValueError('expected complete binary Huffman tree')
        pair = (visit(tree[0]), visit(tree[1]))
        if pair not in interned:
            if len(nodes) >= 32768:
                raise ValueError('too many nodes')
            interned[pair] = len(nodes)
            nodes.append(pair)
        return interned[pair]

    for lengths in tables:
        tree = {}
        for value, (code, length) in enumerate(codes_for(255, lengths)):
            if not length:
                continue
            if value == 0:
                raise ValueError('zero value is absent from correction stream')
            node = tree
            for bit in range(length-1, 0, -1):
                node = node.setdefault((code >> bit) & 1, {})
            node[code & 1] = value
        roots.append(visit(tree))
    data = b''.join(struct.pack('<HH', *pair) for pair in nodes)
    return roots, data


def check_all_codes(tables, roots, data):
    checked = 0
    for root, lengths in zip(roots, tables):
        for value, (code, length) in enumerate(codes_for(255, lengths)):
            if not length:
                continue
            node = root
            for bit in range(length-1, -1, -1):
                if node & 0x8000:
                    raise AssertionError('premature leaf')
                address = node*4+2*((code >> bit) & 1)
                node = int.from_bytes(data[address:address+2], 'little')
            if node != (0x8000 | value):
                raise AssertionError('wrong leaf')
            checked += 1
    return checked


def canonical_counts(tables):
    depth = max(max(table) for table in tables)
    roots, blob = [], bytearray()
    for lengths in tables:
        roots.append(len(blob))
        blob += bytes(lengths.count(n) for n in range(1, depth+1))
        blob += bytes(value for _, value in sorted((n, v) for v, n in enumerate(lengths) if n))
    return depth, roots, bytes(blob)


def check_canonical_counts(tables, depth, roots, blob):
    checked = maximum_rank = maximum_index = 0
    for table, root in zip(tables, roots):
        for value, (code, size) in enumerate(codes_for(255, table)):
            if not size:
                continue
            rank = index = 0
            for length in range(1, size+1):
                rank = rank*2+((code >> (size-length)) & 1)
                count = blob[root+length-1]
                maximum_rank = max(maximum_rank, rank)
                if rank < count:
                    if length != size or blob[root+depth+index+rank] != value:
                        raise AssertionError('wrong canonical leaf')
                else:
                    if length == size:
                        raise AssertionError('missing canonical leaf')
                    rank -= count
                    index += count
                maximum_index = max(maximum_index, index+rank)
                if rank > 255 or index+rank > 255:
                    raise AssertionError('canonical arithmetic needs more than 8 bits')
            checked += 1
    return checked, maximum_rank, maximum_index


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    if not profile['complete']:
        raise ValueError('incomplete profile')
    candidates = next(row['clustered_huffman'] for row in profile['rows'] if row['name'] == 'exact_predicted_byte')
    result = dict(scope=__doc__, profile_sha256=sha(args.profile.read_bytes()), complete=False,
                  player_changed=False, integrated_player_delta_tstates=0, rows=[])
    for candidate in candidates:
        tables = [bytes(t) for t in candidate['tables']]
        roots, data = shared_tree(tables)
        checked = check_all_codes(tables, roots, data)
        depth, compact_roots, compact_data = canonical_counts(tables)
        canonical_checked, max_rank, max_index = check_canonical_counts(tables, depth, compact_roots, compact_data)
        unshared_nodes = sum(sum(bool(n) for n in table)-1 for table in tables)
        row = dict(bitmap_contexts=candidate['bitmap_contexts'], contexts=len(tables),
            shared_nodes=len(data)//4, unshared_nodes=unshared_nodes,
            node_bytes=len(data), roots_bytes=2*len(roots), context_map_bytes=256,
            total_table_bytes=len(data)+2*len(roots)+256,
            table_sha256=sha(bytes(candidate['context_map'])+b''.join(struct.pack('<H', root) for root in roots)+data),
            all_codes_verified=checked, binary_steps_per_value=candidate['bits']/profile['values'],
            canonical_counts=dict(max_depth=depth, data_bytes=len(compact_data),
                roots_bytes=2*len(compact_roots), context_map_bytes=256,
                total_table_bytes=len(compact_data)+2*len(compact_roots)+256,
                all_codes_verified=canonical_checked, maximum_rank=max_rank,
                maximum_index=max_index, arithmetic_bits=8,
                data_sha256=sha(compact_data)))
        result['rows'].append(row)
        print(json.dumps(row), flush=True)
    result['complete'] = True
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
