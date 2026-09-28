"""Reproduce dither seams and measure a five-level host prototype in windows.

No TRDs are generated or replaced. Compression compares XOR-of-frame-byte
layouts, not the full FAP3 motion/Huffman/AY stream; it cannot predict disk
count or playback cadence. Existing renderer opcodes are also checked.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw

from benchmark_cell_screen import Harness
import build_long_video_trd as video
import dither_phase as phase
import five_level_dither as five
import zx0_codec


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compress(chunk, executable, cache):
    key = sha(chunk)
    path = cache/(key+'.zx0')
    if path.exists():
        data = path.read_bytes()
    else:
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            source, target = Path(folder)/'input.raw', Path(folder)/'output.zx0'
            source.write_bytes(chunk)
            subprocess.run([str(executable), '-f', str(source.resolve()), str(target.resolve())],
                           check=True, capture_output=True)
            data = target.read_bytes()
        if zx0_codec.decompress(data, limit=len(chunk)) != chunk:
            raise AssertionError('ZX0 roundtrip differs')
        path.write_bytes(data)
    if zx0_codec.decompress(data, limit=len(chunk)) != chunk:
        raise AssertionError('cached ZX0 roundtrip differs')
    return dict(decoded_bytes=len(chunk), zx0_bytes=len(data), decoded_sha256=key, zx0_sha256=sha(data))


def contact_sheet(states, indices, path):
    sheet = Image.new('RGB', (1024, 440*len(indices)), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for row, index in enumerate(indices):
        for column, aligned in enumerate((False, True)):
            native = Image.fromarray(video.base.render_spectrum_screen(*phase.expand(states[index], aligned=aligned)))
            sheet.paste(native.resize((512, 384), Image.Resampling.NEAREST), (512*column, 440*row+30))
            draw.text((512*column+8, 440*row+10),
                      f'Frame {index}: '+('aligned host reference' if aligned else 'existing player phase'), fill='white')
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--states', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview', type=Path, required=True)
    parser.add_argument('--zx0', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--starts', type=int, nargs='+', default=[629, 2857, 3855])
    parser.add_argument('--window', type=int, default=32)
    args = parser.parse_args()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    if (states.ndim != 2 or states.shape[1] != 3840 or states.dtype != np.uint8
            or args.window < 1 or any(start < 1 or start+args.window > len(states) for start in args.starts)):
        parser.error('invalid states or temporal window')
    rows, transformed = [], np.empty((len(states), five.STATE_BYTES), dtype=np.uint8)
    new_top, new_bottom = np.frombuffer(five.TOP, dtype=np.uint8), np.frombuffer(five.BOTTOM, dtype=np.uint8)
    for index, state in enumerate(states):
        row = phase.phase_seams(state, states[index-1] if index else None)
        row.update(frame=index, spatial_samples=row['horizontal_samples']+row['vertical_samples'])
        rows.append(row)
        encoded = five.from_compact(state)
        transformed[index] = np.frombuffer(encoded, dtype=np.uint8)
        words = five.unpack_words(encoded[:3840])
        top, bottom = phase.scanlines(state, aligned=True)
        reverse = phase.reversed_phase(state[3072:].reshape(24, 32)).repeat(4, axis=0)
        # Canonical endpoints swap bitmap bits, keeping the displayed colours.
        for wanted, actual in ((top, new_top[words]), (bottom, new_bottom[words])):
            if not np.array_equal(np.where(reverse, wanted ^ 255, wanted), actual):
                raise AssertionError(f'five-level reference differs at frame {index}')
    print(f'Host phase/colour equivalence checked: {len(states)} frames', flush=True)
    old_maps, old_cells = phase.dirty_maps(states)
    new_maps, new_cells = phase.dirty_maps(states, aligned=True)
    extra_exact = new_cells & ~old_cells
    # Dense-band promotion may already cover an otherwise unchanged cell.
    # Count actual omissions by the old transmitted map separately.
    extra = new_cells & ~np.unpackbits(old_maps, axis=2).astype(bool)
    missing_by_frame = extra.sum(axis=(1, 2))
    indices = [r['frame'] for r in sorted(rows, key=lambda r: (-r['spatial_samples'], r['frame']))[:3]]
    contact_sheet(states, indices, args.preview)
    # Execute the unchanged actual Z80 renderer, not just a Python preview.
    native = Harness(fast_mask_dispatch=True, gray_cells=True)
    native_results = []
    for count, index in enumerate(indices):
        result = native.run(states[index].tobytes(), bytes([255])*80, count)
        native_results.append(dict(frame=index, **result))
    encoder = args.zx0.resolve()
    cache = args.cache.resolve()/sha(encoder.read_bytes())
    cache.mkdir(parents=True, exist_ok=True)
    windows = []
    for start in args.starts:
        record = dict(start=start, end_exclusive=start+args.window, frames=args.window,
                      carried_predictor_frame=start-1, decoded_block_limit=15872, layouts={})
        for name, matrix in (('current_2bit', states), ('canonical_5level_10bit', transformed)):
            delta = np.bitwise_xor(matrix[start:start+args.window], matrix[start-1:start+args.window-1]).tobytes()
            chunks = [delta[i:i+15872] for i in range(0, len(delta), 15872)]
            # Independent bounded blocks, two workers; identical chunks share a cache.
            unique = {sha(chunk): chunk for chunk in chunks}
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda chunk: compress(chunk, encoder, cache), unique.values()))
            by_hash = {row['decoded_sha256']: row for row in results}
            blocks = [by_hash[sha(chunk)] for chunk in chunks]
            record['layouts'][name] = dict(input_bytes=len(delta), input_sha256=sha(delta), blocks=blocks,
                zx0_bytes=sum(b['zx0_bytes'] for b in blocks),
                zx0_with_u16_length_headers_bytes=sum(b['zx0_bytes']+4 for b in blocks))
        before = record['layouts']['current_2bit']['zx0_with_u16_length_headers_bytes']
        after = record['layouts']['canonical_5level_10bit']['zx0_with_u16_length_headers_bytes']
        record.update(delta_bytes=after-before, delta_percent=100*(after/before-1))
        windows.append(record)
        print(f'Window {start}..{start+args.window}: {before} -> {after} bytes', flush=True)
    files = ['dither_phase.py', 'five_level_dither.py', 'audit_dither_phase.py',
             'test_dither_phase.py', 'test_five_level_dither.py',
             'build_long_video_trd.py', 'cell_screen_z80.py', 'benchmark_cell_screen.py']
    summary = dict(
        frames_with_spatial_half_phase_seams=sum(r['spatial_samples'] > 0 for r in rows),
        spatial_half_phase_samples=sum(r['spatial_samples'] for r in rows),
        temporal_half_phase_samples=sum(r['temporal_half_samples'] for r in rows),
        frames_with_temporal_half_phase_flips=sum(r['temporal_half_samples'] > 0 for r in rows),
        maximum_spatial_samples=max(r['spatial_samples'] for r in rows),
        newly_required_native_cells=int(extra.sum()),
        additional_exact_bitmap_changes=int(extra_exact.sum()),
        frames_requiring_additional_cells=int((missing_by_frame > 0).sum()),
        changed_80byte_native_maps=int(np.any(old_maps != new_maps, axis=(1, 2)).sum()),
        existing_compact_frame_bytes=3840, five_level_frame_bytes=4608,
        existing_pattern_bytes=3072, five_level_pattern_bytes=3840,
        existing_table_bytes=512, proposed_table_bytes=2048)
    report = dict(complete=True, release=False, frames=len(states), states_sha256=sha(states.tobytes()),
        input_file_sha256=sha(args.states.read_bytes()),
        scope='Full host phase audit plus three bounded compression windows and isolated existing renderer checks',
        player_changed=False, integrated_player_delta_tstates=0, trds_built=0, full_playback_verified=False,
        new_format_player_implemented=False, new_format_native_tstates=None,
        corrected_reference_matches_five_level_display_all_frames=True,
        mean_2x2_colour_preserved=True, original_video_requantized=False,
        compression_scope='XOR n-1 frame bytes, carried preceding frame, independent ZX0 blocks; excludes FAP3/AY/startup/sector padding',
        encoder_sha256=sha(encoder.read_bytes()), encoder_mode='ZX0 v2 optimal',
        source_sha256_lf={name: sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')) for name in files},
        summary=summary, frames_with_extra_cells=[dict(frame=i, cells=int(n)) for i, n in enumerate(missing_by_frame) if n],
        preview_frames=indices, preview_sha256=sha(args.preview.read_bytes()),
        existing_renderer_code_sha256=sha(native.code), existing_renderer_checks=native_results,
        windows=windows, frame_diagnostics=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
