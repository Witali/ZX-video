"""Compare real ZX0 block sizes and inventory far references on the full FPM1.

Exact reconstruction and token counts are measured with the reference decoder.
Does not infer Z80 paging time, a valid combined RAM layout or disk cadence.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from probe_lossless_layouts import measure, sha
from zx0_codec import decompress

EXPECTED_SHA = '3528936f51d9ee2adf2419478dfd0058bef2d34fd666f6b124972ceaaf464c1b'


def inspect(raw, report, cache):
    if (not report['complete'] or report['input_sha256'] != sha(raw)
            or len(report['blocks']) != report['blocks_expected']):
        raise ValueError('incomplete or mismatched full-film report')
    total = Counter()
    offsets, lengths = Counter(), Counter()
    rows = []
    cursor = 0
    for index, block in enumerate(report['blocks']):
        counts = Counter()
        span = [0]

        def match(position, offset, length):
            offsets[offset] += 1
            lengths[length] += 1
            counts['matches'] += 1
            counts['match_bytes'] += length
            span[0] = max(span[0], offset)
            for threshold in (8192, 16384):
                if offset > threshold:
                    counts[f'matches_beyond_{threshold}'] += 1
                    counts[f'bytes_beyond_{threshold}'] += length
            # Which copy spans would cross a 16 KiB virtual history boundary?
            # No paging cost is assigned: source/destination mapping is not implemented.
            for start, name in ((position, 'destination'), (position-offset, 'source')):
                if start//16384 != (start+length-1)//16384:
                    counts[name+'_crossings_16k'] += 1

        def literal(position, length):
            counts['literals'] += 1
            counts['literal_bytes'] += length

        expected = raw[cursor:cursor+block['decoded_bytes']]
        cursor += len(expected)
        if sha(expected) != block['sha256']:
            raise ValueError('block/source mismatch')
        packed = (cache/(block['sha256']+'.zx0')).read_bytes()
        if len(packed) != block['zx0_bytes']:
            raise ValueError('compressed block mismatch')
        restored = decompress(packed, limit=len(expected), on_match=match, on_literals=literal)
        if restored != expected or counts['literal_bytes']+counts['match_bytes'] != len(expected):
            raise AssertionError('reference coverage/output mismatch')
        total.update(counts)
        rows.append(dict(index=index, max_offset=span[0], **counts))
    if cursor != len(raw):
        raise AssertionError('not all movie bytes inspected')
    return dict(block_bytes=report['block_bytes'], blocks=len(rows),
        bytes_with_headers=report['zx0_with_headers_bytes'], max_compressed_block=max(b['zx0_bytes'] for b in report['blocks']),
        max_offset=max(offsets, default=0), tokens=dict(total),
        offset_histogram=dict(sorted(offsets.items())), match_length_histogram=dict(sorted(lengths.items())),
        block_details=rows, exact_round_trip=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--report', type=Path, action='append', required=True)
    p.add_argument('--cache', type=Path, action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if len(args.report) != len(args.cache):
        p.error('one cache path is required for each storage report')
    raw = args.raw.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected FPM1 candidate')
    report = dict(scope=__doc__, baseline_commit='539110d', input_sha256=sha(raw), frames=4971,
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        audio_estimate_bytes=77696, three_trd_budget_bytes=1937664, complete=False, rows=[])
    for path, cache in zip(args.report, args.cache):
        source = json.loads(path.read_text())
        row = inspect(raw, source, cache)
        row['report_sha256'] = sha(path.read_bytes())
        row['deflate_with_headers'] = measure(raw, source['block_bytes'])
        row['with_audio_bytes'] = row['bytes_with_headers']+report['audio_estimate_bytes']
        row['deficit_before_extra_overheads'] = row['with_audio_bytes']-report['three_trd_budget_bytes']
        report['rows'].append(row)
        print(json.dumps({k:v for k,v in row.items() if not isinstance(v, (list, dict))}), flush=True)
    if sorted(r['block_bytes'] for r in report['rows']) != [8192, 16384, 32768]:
        raise ValueError('need complete 8/16/32 KiB comparison')
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
