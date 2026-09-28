"""Measure optional phase-aligned Z80 output; this is not a TRD release gate."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import numpy as np

from audit_dither_phase import compress, sha
from benchmark_cell_screen import Harness
from bulk_frame_stream import read_packet
import cell_screen_z80 as machine
import dither_phase as phase
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('states', 'raw', 'output', 'zx0', 'cache'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--starts', type=int, nargs='+', default=[629, 2857, 3855])
    p.add_argument('--window', type=int, default=32)
    a = p.parse_args()
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    if a.window < 1 or any(start < 2 or start+a.window > len(states) for start in a.starts):
        p.error('invalid window')
    raw = a.raw.read_bytes(); reader = Reader(raw)
    _, _, count, _, _ = read_header(reader, magic=b'FAP3')
    if count != len(states): raise ValueError('frame count mismatch')
    _, exact = phase.dirty_maps(states, aligned=True)
    _, old_exact = phase.dirty_maps(states)
    old_maps, new_maps, offsets = [], [], [reader.pos]
    patched = bytearray(raw)
    for index in range(count):
        packet_start = reader.pos
        _, packet = read_packet(reader, stored_guards=False)
        at = packet_start+2+packet['coded_offset']-80
        old = raw[at:at+80]
        before = np.unpackbits(np.frombuffer(old, dtype=np.uint8)).reshape(20, 32).astype(bool)
        if np.any(old_exact[index] & ~before): raise AssertionError('input map omits legacy pixels')
        after = before | exact[index]
        after[after.sum(axis=1) >= 18] = True
        new = np.packbits(after).tobytes()
        patched[at:at+80] = new
        old_maps.append(old); new_maps.append(new); offsets.append(reader.pos)
    reader.end()
    opts = dict(fast_mask_dispatch=True, gray_cells=True,
                constant_attribute_borders=True, skip_black_borders=True)
    baseline = [machine.expected_tstates(mask, **opts) for mask in old_maps]
    candidate = [machine.expected_tstates(mask, phase_aligned=True, **opts) for mask in new_maps]
    old_code = machine.build(**opts, attribute_groups=True, preloaded_mask=True, page_entry=0x9780)
    code, labels, listing, regions = machine.build(**opts, phase_aligned=True,
        attribute_groups=True, preloaded_mask=True, page_entry=0x9780)
    cache = a.cache.resolve()/sha(a.zx0.read_bytes()); cache.mkdir(parents=True, exist_ok=True)
    windows = []
    for start in a.starts:
        h = Harness(fast_mask_dispatch=True, gray_cells=True, phase_aligned=True)
        native = []
        for index in range(start-2, start+a.window):
            mask = b'\xff'*80 if index < start else new_maps[index]
            result = h.run(states[index].tobytes(), mask, index-start+2)
            if index >= start: native.append(dict(frame=index, tstates=result['tstates'],
                output_sha256=result['output_sha256']))
        sizes = {}
        for name, source in (('baseline', raw), ('aligned_maps', patched)):
            blob = bytes(source[offsets[start]:offsets[start+a.window]])
            chunks = [blob[pos:pos+15872] for pos in range(0, len(blob), 15872)]
            with ThreadPoolExecutor(max_workers=3) as pool:
                blocks = list(pool.map(lambda chunk: compress(chunk, a.zx0.resolve(), cache), chunks))
            sizes[name] = dict(bytes=sum(b['zx0_bytes']+4 for b in blocks), blocks=blocks)
        windows.append(dict(start=start, end_exclusive=start+a.window, native=native, compression=sizes))
        print(f'Native phase window verified: {start}..{start+a.window}', flush=True)
    report = dict(scope=__doc__, complete=True, release=False, states_sha256=sha(states.tobytes()),
        raw_sha256=sha(raw), aligned_raw_sha256=sha(patched), packet_lengths_unchanged=True,
        frame_maps_changed=sum(x != y for x,y in zip(old_maps,new_maps)),
        changed_raw_bytes=sum(x != y for x,y in zip(raw,patched)),
        native_window_frames=len(windows)*a.window, native_seed_frames=2*len(windows),
        isolated_18_band_full_attribute_formula=dict(frames=count,
            baseline_tstates=sum(baseline), aligned_tstates=sum(candidate), delta_tstates=sum(candidate)-sum(baseline),
            baseline_max=max(baseline), aligned_max=max(candidate),
            excludes='Attribute-group optimization, atomic-page helper, wrapper CALL, AY/IRQ, ULA contention, TR-DOS and drive latency.'),
        same_map_delta_formula='395 + 43*bands + 61*sparse_cells + 3068*dense_bands',
        integrated_options_main_bytes=dict(before=len(old_code[0]), after=len(code), delta=len(code)-len(old_code[0])),
        regions=[dict(address=at, bytes=len(blob), sha256=sha(blob)) for at,blob in regions],
        phase_helper_conflicts_with='Optional resumable packet helper at F900',
        integrated_ram_placement_verified=False, native_formula_checked_per_instruction=True,
        default_renderer_changed=False, disk_delivery_measured=False, windows=windows,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        source_sha256_lf={name:sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n', b'\n'))
            for name in ('audit_phase_renderer.py', 'cell_screen_z80.py', 'benchmark_cell_screen.py',
                         'test_phase_renderer.py', 'test_cell_screen.py', 'dither_phase.py')})
    a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('windows', 'source_sha256_lf')}))


if __name__ == '__main__': main()
