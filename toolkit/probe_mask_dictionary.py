"""FHD1: replace FHT1 two-level sparse bitmap masks with dictionary tokens.

Same header as FHT1, then dictionary count u16 and two bytes per entry.
Same group header/vectors/values. Mask payload: one token per bitmap tile,
0..count-1 indexes the dictionary, FF escapes to two literal mask bytes;
then mode-4 sparse raster attribute masks. 1..255 entries. No pixel,
vector, Huffman, group boundary or AY change. Exact FHT1 inverse required.
Storage experiment only; new mask decoder/CPU/disk delivery not implemented.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from probe_hybrid_tiles import read_header, read_group, MAX_CODED
from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader
from probe_motion_metadata import transform, restore


def train(data, count):
    if not 1 <= count <= 255:
        raise ValueError('dictionary count')
    r = Reader(data); _, remaining, _, _, _ = read_header(r)
    counts = Counter()
    while remaining:
        n, _, _, _, bm, _, _ = read_group(r, remaining)
        counts.update(bm[i:i+2] for i in range(0, len(bm), 2))
        remaining -= n
    r.end()
    return [key for key in sorted(counts, key=lambda k: (-counts[k], k))[:count]]


def encode(data, table):
    if not 1 <= len(table) <= 255 or any(len(k) != 2 for k in table) or len(set(table)) != len(table):
        raise ValueError('invalid dictionary')
    r = Reader(data); _, remaining, _, _, _ = read_header(r)
    output = bytearray(b'FHD1'+data[4:r.pos]+struct.pack('<H', len(table))+b''.join(table))
    lookup = {key: index for index, key in enumerate(table)}
    tokens, escapes = 0, 0
    while remaining:
        n, flags, bits, vectors, bm, at, values = read_group(r, remaining)
        v = transform(vectors, 192, 2)
        masks = bytearray()
        for i in range(0, len(bm), 2):
            key = bm[i:i+2]
            if key in lookup:
                masks.append(lookup[key])
            else:
                masks.append(255); masks += key; escapes += 1
            tokens += 1
        masks += transform(at, 96, 4)
        output += struct.pack('<HHHBI', n, len(v), len(masks), flags, bits)+v+masks+values
        remaining -= n
    r.end()
    return bytes(output), dict(tiles=tokens, escapes=escapes, dictionary_hits=tokens-escapes)


def decode(data):
    if data[:4] != b'FHD1':
        raise ValueError('not FHD1')
    r = Reader(b'FHT1'+data[4:]); _, remaining, _, _, _ = read_header(r)
    output = bytearray(r.data[:r.pos])
    count = r.u16()
    if not 1 <= count <= 255:
        raise ValueError('invalid dictionary size')
    table = [r.take(2) for _ in range(count)]
    if len(set(table)) != count:
        raise ValueError('duplicate dictionary entry')
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        flags = r.take(1)[0]; bits = int.from_bytes(r.take(4), 'little')
        if not 1 <= n <= min(8, remaining) or (bits+7)//8 > MAX_CODED:
            raise ValueError('invalid group')
        v = r.take(vl)
        masks = Reader(r.take(ml)); bm = bytearray()
        for _ in range(n*192):
            token = masks.take(1)[0]
            if token == 255:
                bm += masks.take(2)
            elif token < count:
                bm += table[token]
            else:
                raise ValueError('invalid dictionary index')
        at = restore(masks.take(len(masks.data)-masks.pos), n, 96, 4)
        masks.end()
        m = transform(bytes(bm)+at, 480, 4)
        encoded = r.take((bits+7)//8)
        group = struct.pack('<HHHBI', n, len(v), len(m), flags, bits)+v+m+encoded
        # The regular FHT1 metadata reader independently checks vectors,
        # literal masks, exact cache flags and metadata lengths.
        check = Reader(group); read_group(check, remaining); check.end()
        output += group; remaining -= n
    r.end()
    return bytes(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fht', type=Path, required=True)
    p.add_argument('--entries', nargs='+', type=int, default=[16, 64, 128, 255])
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline-commit', default='a007c09')
    p.add_argument('--zx0-reports', type=Path, help='attach completed native reports for --native-entries')
    p.add_argument('--native-entries', nargs='+', type=int, default=[16, 255])
    args = p.parse_args()
    data = args.fht.read_bytes()
    args.cache.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit=args.baseline_commit, input_sha256=sha(data), input_bytes=len(data), complete=False,
        player_changed=False, integrated_player_delta_tstates=0, rows=[])
    for count in args.entries:
        table = train(data, count)
        encoded, stats = encode(data, table)
        if decode(encoded) != data:
            raise AssertionError('FHT1 inverse differs')
        stem = str(count)
        (args.cache/(stem+'.raw')).write_bytes(encoded)
        row = dict(name=stem, requested_entries=count, entries=len(table), dictionary_hex=[k.hex() for k in table],
            raw_bytes=len(encoded), sha256=sha(encoded), exact_fht1_inverse=True, **stats,
            deflate_8192=measure(encoded, 8192))
        if args.zx0_reports and count in args.native_entries:
            measured = json.loads((args.zx0_reports/f'mask_dictionary_{stem}_zx0.json').read_text(encoding='utf-8'))
            baseline = json.loads((args.zx0_reports/'hybrid_tiles_control_zx0.json').read_text(encoding='utf-8'))
            if (not measured['complete'] or measured['input_sha256'] != sha(encoded)
                    or len(measured['blocks']) != measured['blocks_expected']
                    or not baseline['complete'] or baseline['input_sha256'] != sha(data)):
                raise ValueError('incomplete/mismatched native report')
            size = sum(b['zx0_bytes']+4 for b in measured['blocks'])
            if size != measured['zx0_with_headers_bytes']:
                raise AssertionError('native size differs')
            row['native_zx0'] = dict(blocks=len(measured['blocks']), bytes_with_headers=size,
                baseline_bytes=baseline['zx0_with_headers_bytes'], delta_bytes=size-baseline['zx0_with_headers_bytes'],
                unchanged_ay_estimate_bytes=77696, generous_three_trd_budget_bytes=1937664,
                minimum_three_trd_deficit_bytes=size+77696-1937664)
        report['rows'].append(row)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in row.items() if k != 'dictionary_hex'}), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
