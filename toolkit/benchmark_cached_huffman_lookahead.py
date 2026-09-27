"""Execute two-byte lookahead caching against the complete compact-cursor baseline.

The stage fixture has two guards after coded input when literals are empty.
The integrated FAP3 parser currently guarantees only one final guard; this
benchmark does not establish that changed input contract for disk playback.
ZX0, queues, AY/IRQ cadence, ULA, ROM and disk delivery are excluded.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from benchmark_static_cache_borders import OPTIONS
from build_fap3_trd import sha
from bulk_frame_stream import unpack as unpack_bulk, read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks, display_screen
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from profile_frame_hotspots import install_hl_masks
import compact_cursor
import cached_huffman_lookahead as lookahead
import inline_huffman_patches as inline
import uncontended_frame as relocation

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-directory', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT/'cached_huffman_lookahead_cpu.json')
    p.add_argument('--limit', type=int, help='Per-volume smoke, never complete')
    a = p.parse_args()
    if a.limit is not None and a.limit < 1: p.error('--limit must be positive')
    names = ('compact_cursor_cpu.json', 'cached_huffman_byte_cpu.json', 'frame_hotspot_profile.json')
    baseline, symbols, profile = [json.loads((ROOT/name).read_bytes()) for name in names]
    if not all(r['complete'] and r['full_compact_and_both_native_exact'] for r in (baseline, symbols, profile)):
        raise ValueError('incomplete reference')
    for name, expected in profile['source_sha256'].items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError(('baseline source differs', name))
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    if (len(states) != baseline['checked_frames']
            or any(sha(states.tobytes()) != r['states_sha256'] for r in (baseline, symbols, profile))):
        raise ValueError('different frame states')
    report = dict(complete=False, release=False, scope=__doc__, baseline_commit='cb94632',
        reference_sha256={name: sha((ROOT/name).read_bytes()) for name in names},
        source_sha256={name: sha((ROOT/name).read_bytes()) for name in
            ('benchmark_cached_huffman_lookahead.py', 'cached_huffman_lookahead.py',
             'test_cached_huffman_lookahead.py', 'compact_cursor.py')},
        baseline_source_sha256=profile['source_sha256'], states_sha256=sha(states.tobytes()),
        compressed_stream_delta_bytes=0, new_playback_measured=False,
        integrated_guard_contract_verified=False, physical_drive_verified=False, volumes=[])
    a.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    save()
    try:
        for volume, refs in zip(baseline['volumes'], symbols['volumes'], strict=True):
            part, start, end = (volume[k] for k in ('part', 'start', 'end'))
            if (part, start, end) != tuple(refs[k] for k in ('part', 'start', 'end')):
                raise ValueError('volume ranges differ')
            raw = (a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != volume['raw_sha256'] or sha(raw) != refs['raw_sha256']:
                raise ValueError('different raw input')
            cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)), 32, 4))[0]
            tables, mapping, packets = frames(cells)
            masks = serialized_masks(cells)
            reader = Reader(raw)
            _, _, count, _, _ = read_header(reader, magic=b'FAP3')
            details = [read_packet(reader, stored_guards=False)[1] for _ in range(count)]
            reader.end()
            h = Harness(tables, mapping, static_cache_borders=True, carry_huffman=True,
                register_fragments=True, cached_huffman_byte=True, metadata_mode='compiled', **OPTIONS)
            install_hl_masks(h)
            c = h.cpu
            c.guarding = False
            if start: c.banks[5][0x2400:0x3300] = states[start-1].tobytes()
            for bank, index in ((7, start-2), (5, start-1)):
                if index >= 0:
                    screen = display_screen(states[index].tobytes(), black_borders=True)
                    screen = bytes(6144)+screen[6144:]
                    c.banks[bank][:6912] = screen
                    h.expected_screens[bank] = screen
            relocation.install_stage(h)
            patch = lookahead.install_frame(h)
            inlined = inline.install_stage(h, tables, mapping)
            # Keep the inline bank-aware instruction mapping while applying
            # cursor patches; compact_cursor itself does not replace it.
            compact_cursor.install_stage(h)
            instruction_map = h.instructions
            counts = Counter()
            count_names = {"EX AF,AF' (return symbol)": 'short',
                           'LD B,E (advance cache)': 'cross', "EX AF,AF' (recover rank)": 'long',
                           'CALL lookahead refresh': 'setup'}

            class Counted(dict):
                def __getitem__(self, pc):
                    row = instruction_map[pc]
                    key = count_names.get(row['instruction'])
                    if key: counts[key] += 1
                    return row

            h.instructions = Counted(instruction_map)
            saved = dict(part=part, start=start, end=end, raw_sha256=sha(raw),
                implementation=patch, inline_code_bytes=inlined['code_bytes'],
                inline_end=inlined['end'], frames=[])
            report['volumes'].append(saved)
            previous = Counter()
            for index in range(start, min(end, start+a.limit) if a.limit else end):
                local = index-start
                group, native = packets[index]
                if start and local < 2: native = bytes([255])*80
                actual = relocation.run_stage(h, group, native, states[index].tobytes(), local,
                                             masks[index], details[index]['cache'])
                used = counts-previous
                previous = counts.copy()
                expected = refs['frames'][local]
                inside, cross, long = used['short']-used['cross'], used['cross'], used['long']
                if (inside, cross, long, used['setup']) != tuple(expected[k] for k in
                                                                ('short_inside', 'short_cross', 'long'))+(1,):
                    raise AssertionError(('symbol execution counts differ', part, index, used, expected))
                before, after = volume['frames'][local]['tstates'], actual['total_tstates']
                wanted = lookahead.delta(inside, cross, long)
                if after-before != wanted:
                    raise AssertionError(('whole-frame cycle delta differs', part, index, before, after, wanted))
                saved['frames'].append(dict(frame=index, baseline_tstates=before, tstates=after,
                    delta_tstates=wanted, short_inside=inside, short_cross=cross, long=long))
                if local % 100 == 0:
                    save()
                    print(f'part {part}: {local+1}/{end-start} exact compact/screens/cycles', flush=True)
            saved['checked_frames'] = len(saved['frames'])
            for key in ('baseline_tstates', 'tstates', 'delta_tstates', 'short_inside', 'short_cross', 'long'):
                saved[key] = sum(row[key] for row in saved['frames'])
            save()
            print(json.dumps({k:v for k,v in saved.items() if k not in ('frames','implementation')}), flush=True)
        report.update(complete=a.limit is None, full_compact_and_both_native_exact=True,
            checked_frames=sum(v['checked_frames'] for v in report['volumes']),
            slower_frames=sum(f['delta_tstates'] > 0 for v in report['volumes'] for f in v['frames']))
        for key in ('baseline_tstates', 'tstates', 'delta_tstates', 'short_inside', 'short_cross', 'long'):
            report[key] = sum(v[key] for v in report['volumes'])
    except Exception as exc:
        report['failure'] = repr(exc)
        save()
        raise
    save()
    print(json.dumps({k:report[k] for k in ('complete','checked_frames','baseline_tstates','tstates','delta_tstates')}), flush=True)


if __name__ == '__main__':
    main()
