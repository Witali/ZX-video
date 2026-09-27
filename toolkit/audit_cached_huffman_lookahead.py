"""Execute every actual volume code at every bit offset; audit packet guard space.

The two-byte cache is compared with cached-byte Huffman using actual Z80
instructions. Input guards deliberately contain A5/3C, not zeros. Packet
lengths are inspected separately; this does not install a two-guard parser
or prove integrated playback. Raw sources must match the complete baseline.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from build_fap3_trd import sha
from bulk_frame_stream import read_packet, WINDOW
from probe_motion_entropy import Reader, codes_for
from probe_spatial_contexts import read_header
from test_cached_huffman_lookahead import primitive, call

ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'cached_huffman_lookahead_cases.json')
    args = parser.parse_args()
    reference = ROOT/'compact_cursor_cpu.json'
    baseline = json.loads(reference.read_bytes())
    if not baseline['complete']: raise ValueError('incomplete baseline')
    report = dict(scope=__doc__, complete=False, release=False,
        baseline_sha256=sha(reference.read_bytes()),
        source_sha256={name: sha((ROOT/name).read_bytes()) for name in
                       ('audit_cached_huffman_lookahead.py', 'cached_huffman_lookahead.py',
                        'test_cached_huffman_lookahead.py', 'prefix_huffman_z80.py',
                        'bulk_frame_stream.py')},
        required_readable_lookahead_bytes=2, guard_bytes_hex='a53c',
        proposed_packet_maximum=WINDOW-2, integrated_parser_changed=False,
        actual_playback_measured=False, volumes=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    save()
    try:
        for volume in baseline['volumes']:
            part, start, end = (volume[k] for k in ('part', 'start', 'end'))
            raw = (args.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != volume['raw_sha256']: raise ValueError('raw source differs')
            reader = Reader(raw)
            _, _, count, mapping, tables = read_header(reader, magic=b'FAP3')
            lengths = []
            no_literals = empty_coded = 0
            for index in range(count):
                _, packet = read_packet(reader, stored_guards=False)
                if start <= index < end:
                    lengths.append(len(packet['payload']))
                    no_literals += not packet['literal_bytes']
                    empty_coded += not packet['coded_bytes']
            reader.end()
            if len(lengths) != end-start: raise ValueError('packet coverage differs')
            old, new = [primitive(tables, mapping, flag) for flag in (False, True)]
            costs = Counter()
            contexts = []
            for context, table in enumerate(tables):
                lengths_seen = Counter()
                for value, (code, length) in enumerate(codes_for(255, table)):
                    if not length: continue
                    for offset in range(8):
                        encoded = (code << ((-offset-length)%8)).to_bytes((offset+length+7)//8, 'big')
                        before = call(old, context, encoded, offset)
                        after = call(new, context, encoded, offset)
                        kind = 'long' if length > 8 else 'cross' if offset+length >= 8 else 'inside'
                        expected = {'long': 18, 'cross': -7, 'inside': -11}[kind]
                        if (before[:2] != (value, offset+length) or after[:2] != before[:2]
                                or after[2]-before[2] != expected
                                or (new.cpu.b, new.cpu.e) != (new.cpu.read8(new.cpu.ix), new.cpu.read8(new.cpu.ix+1))):
                            raise AssertionError(('primitive result/cursor/cache/cycles', part, context, value, offset, before, after))
                        costs[kind, before[2], after[2]] += 1
                    lengths_seen[length] += 1
                contexts.append(dict(context=context, code_length_histogram=dict(sorted(lengths_seen.items())),
                                     code_count=sum(lengths_seen.values()), offsets_checked=list(range(8))))
            entry = dict(part=part, start=start, end=end, raw_sha256=sha(raw),
                tables_sha256=sha(b''.join(tables)), mapping_sha256=sha(mapping), contexts=contexts,
                paired_cases=sum(costs.values()),
                costs=[dict(kind=kind, baseline_tstates=before, tstates=after,
                            delta_tstates=after-before, cases=n) for (kind, before, after), n in sorted(costs.items())],
                checked_packets=len(lengths), max_payload_bytes=max(lengths),
                packets_without_literals=no_literals, packets_without_coded_values=empty_coded,
                packets_exceeding_two_guard_capacity=sum(n > WINDOW-2 for n in lengths),
                spare_packet_window_bytes_after_two_guards=WINDOW-max(lengths)-2)
            report['volumes'].append(entry)
            save()
            print(json.dumps({k:entry[k] for k in ('part','paired_cases','checked_packets','max_payload_bytes',
                                                   'packets_exceeding_two_guard_capacity')}), flush=True)
        report.update(complete=True, paired_cases=sum(v['paired_cases'] for v in report['volumes']),
            checked_packets=sum(v['checked_packets'] for v in report['volumes']),
            all_current_packets_fit_two_readable_guards=all(not v['packets_exceeding_two_guard_capacity']
                                                          for v in report['volumes']))
    except Exception as exc:
        report['failure'] = repr(exc)
        save()
        raise
    save()


if __name__ == '__main__':
    main()
