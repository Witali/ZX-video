"""Separate FPD1 metadata from its unchanged Huffman byte stream.

MDV1 metadata: magic, value-byte count u32, FPD1 header size u16/header;
then groups (n/vlen/mlen u16, bit length u32, vector bytes, mask bytes).
Values retain original per-group padding. Exact FPD1 inverse is checked.
Independent-stream sizes exclude a physical multiplex schedule and are
estimates until a sequential on-disk container and reader are constructed.
"""
import argparse
import json
from pathlib import Path
import struct

from probe_lossless_layouts import measure, sha
from probe_motion_entropy import Reader, parse_header


def header(reader):
    start = reader.pos
    if reader.take(4) != b'FPD1':
        raise ValueError('requires FPD1')
    kind, contexts = reader.take(2)
    if kind not in range(3) or contexts < 2:
        raise ValueError('invalid FPD1 kind/contexts')
    original = Reader(reader.take(reader.u16()))
    _, frames = parse_header(original); original.end()
    mapping = reader.take(256)
    if max(mapping) >= contexts-1:
        raise ValueError('invalid map')
    reader.take(contexts*256)
    return reader.data[start:reader.pos], frames


def split(data):
    reader = Reader(data)
    original, remaining = header(reader)
    descriptors, values = bytearray(), bytearray()
    while remaining:
        n, vl, ml = reader.u16(), reader.u16(), reader.u16()
        if not 1 <= n <= min(8, remaining):
            raise ValueError('group count')
        v, m, bits = reader.take(vl), reader.take(ml), reader.take(4)
        value = reader.take((int.from_bytes(bits, 'little')+7)//8)
        descriptors += struct.pack('<HHH', n, vl, ml)+bits+v+m
        values += value
        remaining -= n
    reader.end()
    metadata = b'MDV1'+struct.pack('<IH', len(values), len(original))+original+descriptors
    return bytes(metadata), bytes(values)


def join(metadata, values):
    r, stream = Reader(metadata), Reader(values)
    if r.take(4) != b'MDV1' or int.from_bytes(r.take(4), 'little') != len(values):
        raise ValueError('bad metadata/value lengths')
    original = r.take(r.u16())
    hr = Reader(original)
    _, remaining = header(hr); hr.end()
    output = bytearray(original)
    while remaining:
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(8, remaining):
            raise ValueError('invalid group')
        bits = r.take(4)
        v, m = r.take(vl), r.take(ml)
        output += struct.pack('<HHH', n, vl, ml)+v+m+bits
        output += stream.take((int.from_bytes(bits, 'little')+7)//8)
        remaining -= n
    r.end(); stream.end()
    return bytes(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpd', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--zx0-reports', type=Path, help='directory containing completed part and direct_16 storage reports')
    args = p.parse_args()
    data = args.fpd.read_bytes()
    metadata, values = split(data)
    if join(metadata, values) != data:
        raise AssertionError('FPD1 inverse differs')
    args.cache.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, part in [('metadata', metadata), ('values', values)]:
        (args.cache/(name+'.raw')).write_bytes(part)
        rows.append(dict(name=name, bytes=len(part), sha256=sha(part), deflate_8192=measure(part, 8192)))
    report = dict(scope=__doc__, baseline_commit='2f3ce3f', complete=True,
        input_sha256=sha(data), input_bytes=len(data), exact_fpd1_inverse=True, rows=rows,
        combined_deflate_estimate_bytes=sum(row['deflate_8192'] for row in rows),
        raw_values_plus_metadata_deflate_estimate_bytes=len(values)+rows[0]['deflate_8192'],
        player_changed=False, integrated_player_delta_tstates=0)
    if args.zx0_reports:
        native = []
        for row in rows:
            measured = json.loads((args.zx0_reports/f'split_metadata_{row["name"]}_zx0.json').read_text(encoding='utf-8'))
            if (not measured['complete'] or measured['input_sha256'] != row['sha256']
                    or len(measured['blocks']) != measured['blocks_expected']):
                raise ValueError('incomplete/mismatched native measurement')
            size = sum(b['zx0_bytes']+4 for b in measured['blocks'])
            if size != measured['zx0_with_headers_bytes']:
                raise ValueError('native size differs')
            native.append(dict(name=row['name'], bytes_with_block_headers=size, blocks=len(measured['blocks'])))
        baseline = json.loads((args.zx0_reports/'direct_values_direct_16_zx0.json').read_text(encoding='utf-8'))
        if not baseline['complete'] or baseline['input_sha256'] != sha(data):
            raise ValueError('baseline mismatch')
        combined = sum(r['bytes_with_block_headers'] for r in native)
        raw_values = len(values)+native[0]['bytes_with_block_headers']
        report['native_zx0'] = dict(parts=native, baseline_bytes=baseline['zx0_with_headers_bytes'],
            combined_streams_estimate_bytes=combined, delta_bytes=combined-baseline['zx0_with_headers_bytes'],
            raw_values_plus_zx0_metadata_estimate_bytes=raw_values,
            raw_values_delta_bytes=raw_values-baseline['zx0_with_headers_bytes'],
            unchanged_ay_estimate_bytes=77696, generous_three_trd_budget_bytes=1937664,
            combined_minimum_three_trd_deficit_bytes=combined+77696-1937664,
            physical_multiplex_overhead_included=False, integrated_cpu_measured=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
