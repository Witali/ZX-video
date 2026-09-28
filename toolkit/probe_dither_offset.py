"""Measure a shared per-cell offset for four consecutive 2x2 coverages.

The two palettes are 0/1/2/3 and 1/2/3/4 bright dots out of four.
Reuse INK/PAPER orientation as the selector, so this host prototype stores
no extra bit. It is not the existing player format and is not a TRD builder.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from audit_dither_phase import compress, sha
import build_long_video_trd as video
import dither_phase as phase
import five_level_dither as five


def canonical(state):
    state = np.frombuffer(bytes(state), dtype=np.uint8)
    if state.shape != (3840,) or np.any(state[3072:] & 128):
        raise ValueError('expected compact frame without FLASH')
    attrs = state[3072:].reshape(24, 32).copy()
    reverse = phase.reversed_phase(attrs)
    values = ((state[:3072].reshape(96, 32)[..., None] >> np.array([6, 4, 2, 0])) & 3).reshape(96, 128)
    values = np.array([0, 1, 2, 4], dtype=np.uint8)[values]
    values = np.where(reverse.repeat(4, 0).repeat(4, 1), 4-values, values)
    attrs = np.where(reverse, (attrs & 0xc0) | ((attrs & 7) << 3) | ((attrs >> 3) & 7), attrs)
    # Identical endpoints have no visible coverage; give them a unique zero
    # representation instead of treating arbitrary hidden bits as quality.
    equal = (attrs & 7) == ((attrs >> 3) & 7)
    values = np.where(equal.repeat(4, 0).repeat(4, 1), 0, values)
    return values, attrs


def shift(state, previous_offsets=None):
    """Minimize squared coverage error per cell; retain ties over time.

    Each out-of-range sample moves by one coverage step. The squared RGB
    cost shares the same colour-pair factor throughout its attribute cell,
    so choosing the less common extreme is also RGB-MSE optimal here.
    """
    wanted, attrs = canonical(state)
    cells = wanted.reshape(24, 4, 32, 4).transpose(0, 2, 1, 3)
    black, white = (cells == 0).sum((2, 3)), (cells == 4).sum((2, 3))
    offsets = white > black
    if previous_offsets is not None:
        previous_offsets = np.asarray(previous_offsets)
        if previous_offsets.shape != (24, 32):
            raise ValueError('expected a 32x24 offset map')
        offsets = np.where(black == white, previous_offsets.astype(bool), offsets)
    # Cells with equal endpoints have no visible difference. Avoid arbitrary
    # inverse encoding there, since INK/PAPER cannot signal an equal-pair bit.
    offsets &= (attrs & 7) != ((attrs >> 3) & 7)
    per_pixel = offsets.repeat(4, 0).repeat(4, 1)
    actual = np.clip(wanted, per_pixel.astype(np.uint8), per_pixel.astype(np.uint8)+3)
    codes = np.where(per_pixel, 4-actual, actual)
    encoded_attrs = np.where(offsets, (attrs & 0xc0) | ((attrs & 7) << 3) | ((attrs >> 3) & 7), attrs)
    packed = (codes[:, 0::4] << 6) | (codes[:, 1::4] << 4) | (codes[:, 2::4] << 2) | codes[:, 3::4]
    return packed.tobytes()+encoded_attrs.tobytes(), offsets, wanted, actual, attrs, black, white


def decode(state):
    """Independent coverage decoder for the shifted four-code prototype."""
    data = np.frombuffer(bytes(state), dtype=np.uint8)
    if data.shape != (3840,) or np.any(data[3072:] & 128):
        raise ValueError('expected shifted compact frame without FLASH')
    attrs = data[3072:].reshape(24, 32)
    reversed_cells = phase.reversed_phase(attrs)
    code = ((data[:3072].reshape(96, 32)[..., None] >> np.array([6, 4, 2, 0])) & 3).reshape(96, 128)
    values = np.where(reversed_cells.repeat(4, 0).repeat(4, 1), 4-code, code).astype(np.uint8)
    attrs = np.where(reversed_cells, (attrs & 0xc0) | ((attrs & 7) << 3) | ((attrs >> 3) & 7), attrs)
    return values, attrs


def picture(state, *, shifted=False):
    if not shifted:
        return video.base.render_spectrum_screen(*phase.expand(state, aligned=True))
    values, attrs = decode(state)
    return video.base.render_spectrum_screen(*five.expand(five.pack_levels(values)+attrs.tobytes()))


def sheet(states, candidates, indices, path):
    result = Image.new('RGB', (1024, 432*len(indices)), (24, 24, 24))
    draw = ImageDraw.Draw(result)
    for row, index in enumerate(indices):
        for column, source in enumerate((states, candidates)):
            rendered = Image.fromarray(picture(source[index], shifted=bool(column)))
            result.paste(rendered.resize((512, 384), Image.Resampling.NEAREST), (column*512, row*432+28))
            draw.text((column*512+8, row*432+8), f'Frame {index}: '+
                ('shifted quartet (host only)' if column else 'phase-aligned baseline'), fill='white')
    path.parent.mkdir(parents=True, exist_ok=True)
    result.save(path)


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
    if (states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840
            or args.window < 1 or any(i < 1 or i+args.window > len(states) for i in args.starts)):
        parser.error('invalid states/window')
    previous = None
    candidates, frames = np.empty_like(states), []
    palette = np.array([video.base.zx_rgb(colour, bright) for bright in (0, 1) for colour in range(8)], dtype=float)
    for index, state in enumerate(states):
        encoded, previous, wanted, actual, attrs, black, white = shift(state, previous)
        values, check_attrs = decode(encoded)
        if not np.array_equal(values, actual) or not np.array_equal(check_attrs, attrs):
            raise AssertionError('shifted coverage roundtrip differs')
        candidates[index] = np.frombuffer(encoded, dtype=np.uint8)
        bright = (attrs >> 6)*8
        difference = palette[(attrs & 7)+bright]-palette[((attrs >> 3) & 7)+bright]
        # Average colour per logical pixel, not a perceptual percentage.
        factor = np.mean(difference**2, axis=2).repeat(4, 0).repeat(4, 1)/16
        moved = wanted != actual
        active = moved[12:84]
        overlap = (black[3:21] > 0) & (white[3:21] > 0)
        contrast = np.any(difference[3:21] != 0, axis=2)
        visible_overlap = overlap & contrast
        visible_moved = active & (factor[12:84] > 0)
        if int(active.sum()) != int(np.minimum(black[3:21], white[3:21]).sum()):
            raise AssertionError('nonminimal shifted coverage error')
        frames.append(dict(frame=index, cells_with_both_endpoints=int(visible_overlap.sum()),
            logical_pixels_changed=int(visible_moved.sum()),
            logical_pixel_fraction=float(visible_moved.mean()),
            native_pixel_fraction=float(visible_moved.mean()/4),
            mean_rgb_mse=float((active*factor[12:84]).mean()),
            maximum_coverage_error=float(np.max(np.abs(wanted.astype(int)-actual.astype(int)))/4)))
    print(f'Checked optimal per-cell offsets and roundtrips: {len(states)} frames', flush=True)
    indices = [row['frame'] for row in sorted(frames, key=lambda r: (-r['mean_rgb_mse'], r['frame']))[:3]]
    sheet(states, candidates, indices, args.preview)
    encoder = args.zx0.resolve()
    cache = args.cache.resolve()/sha(encoder.read_bytes())
    cache.mkdir(parents=True, exist_ok=True)
    windows = []
    for start in args.starts:
        record = dict(start=start, end_exclusive=start+args.window, carried_predictor_frame=start-1, layouts={})
        for name, matrix in (('current_2bit', states), ('shifted_2bit_reused_orientation', candidates)):
            raw = np.bitwise_xor(matrix[start:start+args.window], matrix[start-1:start+args.window-1]).tobytes()
            chunks = [raw[i:i+15872] for i in range(0, len(raw), 15872)]
            unique = {sha(chunk): chunk for chunk in chunks}
            with ThreadPoolExecutor(max_workers=2) as executor:
                items = list(executor.map(lambda data: compress(data, encoder, cache), unique.values()))
            lookup = {r['decoded_sha256']: r for r in items}
            blocks = [lookup[sha(chunk)] for chunk in chunks]
            record['layouts'][name] = dict(bytes=len(raw), sha256=sha(raw), blocks=blocks,
                zx0_with_headers_bytes=sum(r['zx0_bytes']+4 for r in blocks))
        before = record['layouts']['current_2bit']['zx0_with_headers_bytes']
        after = record['layouts']['shifted_2bit_reused_orientation']['zx0_with_headers_bytes']
        record.update(delta_bytes=after-before, delta_percent=100*(after/before-1))
        windows.append(record)
        print(f'Window {start}..{start+args.window}: {before} -> {after} bytes', flush=True)
    summary = dict(active_cells_per_frame=576, active_logical_pixels_per_frame=9216,
        cells_with_both_endpoints=sum(r['cells_with_both_endpoints'] for r in frames),
        frames_with_both_endpoints=sum(r['cells_with_both_endpoints'] > 0 for r in frames),
        changed_logical_pixels=sum(r['logical_pixels_changed'] for r in frames),
        mean_logical_pixel_fraction=float(np.mean([r['logical_pixel_fraction'] for r in frames])),
        mean_native_pixel_fraction=float(np.mean([r['native_pixel_fraction'] for r in frames])),
        maximum_frame_logical_pixel_fraction=max(r['logical_pixel_fraction'] for r in frames),
        mean_rgb_mse=float(np.mean([r['mean_rgb_mse'] for r in frames])),
        maximum_frame_rgb_mse=max(r['mean_rgb_mse'] for r in frames),
        separate_flag_bytes=96, reused_orientation_flag_bytes=0, shifted_frame_bytes=3840)
    sources = ('probe_dither_offset.py', 'test_dither_offset.py', 'dither_phase.py',
               'five_level_dither.py', 'audit_dither_phase.py', 'build_long_video_trd.py')
    report = dict(complete=True, release=False, frames=len(states), states_sha256=sha(states.tobytes()),
        candidate_sha256=sha(candidates.tobytes()), source_file_sha256=sha(args.states.read_bytes()),
        scope='Host shifted-quartet quality audit and bounded XOR/ZX0 controls; no production change',
        source_sha256_lf={name: sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')) for name in sources},
        every_frame_roundtrip_exact=True, per_cell_minimum_coverage_error_verified=True,
        original_rgb_requantized=False, production_runtime_delta_tstates=0,
        new_native_cost_tstates=None, full_playback_verified=False, trds_built=0,
        compression_scope='XOR n-1 with carried predictor; 15872-byte independent ZX0 blocks, 4-byte headers; excludes FAP3/AY/startup/sector padding',
        encoder_sha256=sha(encoder.read_bytes()), encoder_mode='ZX0 v2 optimal',
        preview_frames=indices, preview_sha256=sha(args.preview.read_bytes()),
        summary=summary, windows=windows, frames_detail=frames)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
