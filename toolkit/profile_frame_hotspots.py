"""Execute every baseline frame and profile bank-aware Z80 instruction costs.

The HL-reader / inline-Huffman reconstruction and native output are unchanged.
Packets are supplied by the host; ZX0, packet copies, queue, AY, IRQ, ULA,
TR-DOS and physical disk latency are excluded. Both complete screens and
compact bytes are checked, as is every frame's earlier CPU total minus the
independently verified 499-T HL metadata saving. This is not a playback run.
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
import compiled_masks_z80 as masks
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks, display_screen
import inline_huffman_patches as inline
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
import uncontended_frame as relocation

ROOT = Path(__file__).parent


def install_hl_masks(h):
    c = h.cpu
    page = c.port_7ffd
    c.guarding = False
    c.port_7ffd = 0x17
    regions, labels, rows, generated = masks.build(hl_flags=True)
    for at, data in regions + generated:
        for i, value in enumerate(data):
            c.write8(at + i, value)
    h.instructions.update({r['address']: dict(r, phase='metadata') for r in rows})
    h.metadata_entry = labels['decode']
    h.metadata_formula = lambda data: masks.expected_tstates(data, hl_flags=True)
    c.port_7ffd = page


def instrument(h, generated):
    """Count each executed instruction once, without re-reading side-effecting listings."""
    c = h.cpu
    fixed = dict(h.instructions)
    bank6 = {r['address']: r for r in generated['listing']}
    histogram = Counter()
    stages = Counter()
    original_step = c.step

    def step():
        pc, before = c.pc, c.tstates
        bank = c.port_7ffd & 7 if pc >= 0xc000 else -1
        row = bank6[pc] if bank == 6 and pc in bank6 else fixed[pc]
        original_step()
        elapsed = c.tstates - before
        allowed = row['tstates'] if isinstance(row['tstates'], list) else [row['tstates']]
        if elapsed not in allowed:
            raise AssertionError(('profile instruction timing', bank, pc, elapsed, allowed))
        histogram[bank, pc, elapsed] += 1
        stages[row['phase'] + '/' + row['stage']] += elapsed

    c.step = step
    return histogram, stages, fixed, bank6


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-directory', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT / 'frame_hotspot_profile.json')
    p.add_argument('--limit', type=int, help='Per-volume smoke only; never a complete profile')
    a = p.parse_args()
    model_path = ROOT / 'inline_huffman_patches_cpu.json'
    model = json.loads(model_path.read_bytes())
    with np.load(a.states, allow_pickle=False) as saved:
        states = saved['states']
    if (not model['complete'] or not model['full_compact_and_both_native_exact'] or
            len(states) != model['checked_frames'] or sha(states.tobytes()) != model['states_sha256']):
        raise ValueError('different or incomplete baseline')
    sources = ('profile_frame_hotspots.py', 'frame_output_pipeline.py', 'causal_tile_z80.py',
               'cell_screen_z80.py', 'compiled_masks_z80.py', 'uncontended_frame.py',
               'inline_huffman_patches.py', 'prefix_huffman_z80.py', 'benchmark_static_cache_borders.py',
               'validate_fast_sparse.py', 'benchmark_compact_screen.py', 'attribute_groups_z80.py')
    report = dict(complete=False, release=False, scope=__doc__, baseline_commit='074e1e7',
        baseline_report_sha256=sha(model_path.read_bytes()), states_sha256=model['states_sha256'],
        source_sha256={name: sha((ROOT / name).read_bytes()) for name in sources},
        implemented_optimization=False, player_cpu_delta_tstates=0, stream_delta_bytes=0,
        physical_drive_verified=False, actual_new_playback_measured=False, volumes=[])
    a.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')

    save()
    try:
        for v in model['volumes']:
            part, start, end = v['part'], v['start'], v['end']
            raw = (a.raw_directory / f'volume-{part}.raw').read_bytes()
            if sha(raw) != v['raw_sha256']:
                raise ValueError('raw input differs')
            cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)), 32, 4))[0]
            tables, mapping, packets = frames(cells)
            encoded_masks = serialized_masks(cells)
            reader = Reader(raw)
            _, _, count, _, _ = read_header(reader, magic=b'FAP3')
            details = [read_packet(reader, stored_guards=False)[1] for _ in range(count)]
            reader.end()
            h = Harness(tables, mapping, static_cache_borders=True, carry_huffman=True,
                        register_fragments=True, cached_huffman_byte=True, metadata_mode='compiled', **OPTIONS)
            install_hl_masks(h)
            c = h.cpu
            c.guarding = False
            if start:
                c.banks[5][0x2400:0x3300] = states[start - 1].tobytes()
            for bank, index in ((7, start - 2), (5, start - 1)):
                if index >= 0:
                    screen = display_screen(states[index].tobytes(), black_borders=True)
                    screen = bytes(6144) + screen[6144:]
                    c.banks[bank][:6912] = screen
                    h.expected_screens[bank] = screen
            relocation.install_stage(h)
            generated = inline.install_stage(h, tables, mapping)
            hist, stages, fixed, bank6 = instrument(h, generated)
            volume = dict(part=part, start=start, end=end, raw_sha256=sha(raw), frames=[])
            report['volumes'].append(volume)
            previous = Counter()
            for index in range(start, min(end, start + a.limit) if a.limit else end):
                local = index - start
                group, native = packets[index]
                if start and local < 2:
                    native = b'\xff' * 80
                actual = relocation.run_stage(h, group, native, states[index].tobytes(), local,
                                              encoded_masks[index], details[index]['cache'])
                wanted = v['frames'][local]['tstates'] - 499
                frame_stages = stages - previous
                previous = stages.copy()
                if actual['total_tstates'] != wanted or sum(frame_stages.values()) != wanted:
                    raise AssertionError(('full frame count differs', part, index, actual['total_tstates'], wanted))
                volume['frames'].append(dict(frame=index, tstates=wanted, stages=dict(frame_stages)))
                if local % 200 == 0:
                    save()
                    print(f'part {part}: {local + 1}/{end - start} exact compact/screens/CPU', flush=True)
            rows = []
            for (bank, pc, ticks), n in sorted(hist.items()):
                row = bank6[pc] if bank == 6 and pc in bank6 else fixed[pc]
                rows.append(dict(bank=bank, address=pc, instruction=row['instruction'],
                                 stage=row['phase'] + '/' + row['stage'], tstates=ticks, count=n, total=ticks * n))
            total = sum(r['tstates'] for r in volume['frames'])
            if sum(r['total'] for r in rows) != total:
                raise AssertionError('histogram total differs')
            volume.update(checked_frames=len(volume['frames']), tstates=total, stages=dict(stages),
                          instruction_histogram=rows, hottest_instructions=sorted(rows, key=lambda r: r['total'], reverse=True)[:30])
            save()
            print(json.dumps(dict(part=part, tstates=total, stages=dict(stages))), flush=True)
        report.update(complete=a.limit is None, checked_frames=sum(v['checked_frames'] for v in report['volumes']),
                      tstates=sum(v['tstates'] for v in report['volumes']), full_compact_and_both_native_exact=True)
    except Exception as exc:
        report['failure'] = repr(exc)
        save()
        raise
    save()


if __name__ == '__main__':
    main()
