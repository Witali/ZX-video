"""Verify direct alternate-HL target loads on all saved movie frames.

CPU-stage experiment only: exact compact bytes, both screens, input, paging
and instruction timings. Excludes ZX0, queues, IRQ cadence, ULA and disks.
Baseline frame totals are the saved complete two-byte-cache CPU run.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
from benchmark_cached_huffman_lookahead import (Harness, OPTIONS, Reader, display_screen,
    frames, install_hl_masks, read_header, read_packet, serialized_masks,
    unpack, unpack_audio, unpack_bulk, unpack_cache)
from build_fap3_trd import sha
import cached_huffman_lookahead as lookahead
import compact_cursor
import direct_motion_target as direct
import inline_huffman_patches as inline
import uncontended_frame as relocation

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-directory', type=Path, default=ROOT.parent/'.worktree/volume-huffman/.tmp/probe')
    p.add_argument('--states', type=Path, default=ROOT.parent/'.worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz')
    p.add_argument('--output', type=Path, default=ROOT/'direct_motion_target_cpu.json')
    p.add_argument('--limit', type=int)
    args = p.parse_args()
    if args.limit is not None and args.limit < 1: p.error('positive limit required')
    if args.output.exists(): p.error('output already exists')
    reference = ROOT/'cached_huffman_lookahead_cpu.json'
    baseline = json.loads(reference.read_bytes())
    if not baseline['complete'] or not baseline['full_compact_and_both_native_exact']:
        raise ValueError('incomplete baseline')
    sources = baseline['baseline_source_sha256'] | baseline['source_sha256']
    for name, expected in sources.items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError(('source differs', name))
    with np.load(args.states, allow_pickle=False) as saved: states = saved['states']
    if len(states) != 4221 or sha(states.tobytes()) != baseline['states_sha256']:
        raise ValueError('different states')
    report = dict(complete=False, release=False, scope=__doc__,
        baseline_commit='5856133', reference_sha256=sha(reference.read_bytes()),
        baseline_sources=sources, states_sha256=baseline['states_sha256'],
        source_sha256={name:sha((ROOT/name).read_bytes()) for name in
            ('direct_motion_target.py','benchmark_direct_motion_target.py','test_direct_motion_target.py')},
        new_trds_built=False, actual_playback_measured=False,
        compressed_movie_stream_delta_bytes=0, bootstrap_compressed_delta_bytes=None, volumes=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save(): args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    keys = ('baseline_tstates','tstates','delta_tstates','nonzero_motion_entries')
    save()
    try:
        for volume in baseline['volumes']:
            part, start, end = (volume[k] for k in ('part','start','end'))
            raw = (args.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != volume['raw_sha256']: raise ValueError('raw stream differs')
            cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
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
            for bank, index in ((7,start-2),(5,start-1)):
                if index >= 0:
                    screen = display_screen(states[index].tobytes(), black_borders=True)
                    screen = bytes(6144)+screen[6144:]
                    c.banks[bank][:6912] = screen
                    h.expected_screens[bank] = screen
            relocation.install_stage(h)
            lookahead.install_frame(h)
            change = direct.install_stage(h)
            generated = inline.install_stage(h, tables, mapping)
            compact_cursor.install_stage(h)
            entries = {h.recon[f'predict_{phase}']:str(phase) for phase in (0,2,4,6)}
            entries[h.recon['clear_tile']] = 'clear'
            saved = dict(part=part, start=start, end=end, raw_sha256=sha(raw),
                         implementation=change, inline_code_bytes=generated['code_bytes'], frames=[])
            report['volumes'].append(saved)
            previous = Counter()
            for index in range(start, min(end,start+args.limit) if args.limit else end):
                local = index-start
                group, native = packets[index]
                if start and local < 2: native = bytes([255])*80
                actual = relocation.run_stage(h, group, native, states[index].tobytes(), local,
                                              masks[index], details[index]['cache'])
                counts = Counter()
                for (pc, _), n in h.histogram.items():
                    if pc in entries: counts[entries[pc]] += n
                used, previous = counts-previous, counts
                nonzero = sum(used[str(phase)] for phase in (2,4,6))
                before, after = volume['frames'][local]['tstates'], actual['total_tstates']
                if after-before != -21*nonzero:
                    raise AssertionError(('whole-frame delta',part,index,before,after,nonzero))
                saved['frames'].append(dict(frame=index, baseline_tstates=before, tstates=after,
                    delta_tstates=after-before, nonzero_motion_entries=nonzero, phase_entries=dict(used)))
                if local % 100 == 0:
                    save()
                    print(f'part {part}: {local+1}/{end-start} exact compact/screens/cycles', flush=True)
            saved['checked_frames'] = len(saved['frames'])
            saved.update({key:sum(f[key] for f in saved['frames']) for key in keys})
            save()
            print(json.dumps({k:saved[k] for k in ('part','checked_frames',*keys)}), flush=True)
        report.update(complete=args.limit is None, full_compact_and_both_native_exact=True,
            checked_frames=sum(v['checked_frames'] for v in report['volumes']),
            slower_frames=sum(f['delta_tstates']>0 for v in report['volumes'] for f in v['frames']))
        report.update({key:sum(v[key] for v in report['volumes']) for key in keys})
    except Exception as exc:
        report['failure'] = repr(exc)
        save()
        raise
    save()
    print(json.dumps({key:report[key] for key in ('complete','checked_frames',*keys)}), flush=True)


if __name__ == '__main__': main()
