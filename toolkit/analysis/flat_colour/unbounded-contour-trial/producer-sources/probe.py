"""Compare fixed difficult cartoon windows; this produces host references only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'toolkit'))
import flat_colour as flat
import five_level_dither as five
from cell_palette_quality import averaged, ATTRS, PAIRS
from stable_colour import boundary_error, cells
from build_zxv_trd import render_spectrum_screen

WINDOWS = (90, 144, 252, 288, 496, 784)
COUNT = 16
VARIANTS = dict(flat={}, minimal=dict(dither='minimal'),
    contours=dict(contours=True), regions=dict(vision='regions'),
    regions_contours=dict(vision='regions', contours=True))


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream, 'sha256').hexdigest()


def metrics(source, state):
    output = averaged(state)[12:84];source = source[12:84].astype(float)
    levels = five.unpack_levels(state[:3840])[12:84]
    attrs = np.frombuffer(state[3840:], np.uint8)[96:672]
    pair = (attrs[:, None] == ATTRS).argmax(axis=1).reshape(18, 32).repeat(4, 0).repeat(4, 1)
    variance = np.mean((PAIRS[pair, 1]-PAIRS[pair, 0])**2, axis=-1)*(levels/4)*(1-levels/4)
    total = retained = 0;gradient_sum = 0.;gradient_count = 0
    for a, b in ((np.s_[:, 1:], np.s_[:, :-1]), (np.s_[1:], np.s_[:-1])):
        original = source[a]-source[b];new = output[a]-output[b]
        contrast = np.mean(original**2, axis=-1);strong = contrast >= 24**2
        product = (original*new).sum(axis=-1)
        norms = np.linalg.norm(original, axis=-1)*np.linalg.norm(new, axis=-1)
        good = (product >= .5*norms) & (np.mean(new**2, axis=-1) >= .35**2*contrast)
        total += int(strong.sum());retained += int((good & strong).sum())
        gradient_sum += float(np.mean((new-original)**2, axis=-1)[strong].sum())
        gradient_count += int(strong.sum())
    return dict(sample_rgb_mse=float(np.mean((output-source)**2)),
        native_rgb_mse=float(np.mean((output-source)**2)+variance.mean()),
        native_grain_variance=float(variance.mean()),
        patterned_sample_percent=float(100*np.mean((levels > 0) & (levels < 4))),
        maximum_patterned_samples_per_cell=int(cells(np.pad(((levels > 0) & (levels < 4))[..., None],
            ((12, 12), (0, 0), (0, 0)))).sum(axis=1).max()),
        boundary_residual_mse=boundary_error(source, output),
        strong_source_edges=total, retained_strong_edges=retained,
        strong_edge_gradient_mse=gradient_sum/max(gradient_count, 1))


def sheet(images, states, indices, columns, path):
    canvas = Image.new('RGB', (512*len(columns), 312*len(indices)), '#181818')
    draw = ImageDraw.Draw(canvas)
    for row, at in enumerate(indices):
        for col, name in enumerate(columns):
            pixels = (images[at].repeat(2, 0).repeat(2, 1) if name == 'source'
                else render_spectrum_screen(*five.expand(states[name][at].tobytes()))[24:168])
            draw.text((col*512+8, row*312+4), f"{int(at)/10:.1f}s  {name}", fill='white')
            canvas.paste(Image.fromarray(pixels).resize((512, 288), Image.Resampling.NEAREST),
                (col*512, row*312+24))
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path)
    parser.add_argument('--selected', choices=tuple(VARIANTS), default='regions')
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args()
    if not args.preview_only and args.output.exists() and any(args.output.iterdir()):
        parser.error('output must be new or empty')
    args.output.mkdir(parents=True, exist_ok=True)
    source_path = args.baseline/'work/frames.rgb';baseline_path = args.baseline/'work/five-states.npy'
    images = np.fromfile(source_path, np.uint8).reshape(-1, 72, 128, 3)
    baseline = np.load(baseline_path)
    indices = sorted(set([i for lo in WINDOWS for i in range(lo, lo+COUNT)]))
    image = np.zeros((96, 128, 3), np.uint8)
    if not args.preview_only:
        states = dict(baseline=baseline.copy());rows = []
        elapsed = {}
        for name, settings in VARIANTS.items():
            state_array = np.zeros_like(baseline);started = time.perf_counter()
            for lo in WINDOWS:
                previous = previous_image = None
                for at in range(lo-2, lo+COUNT):
                    image[12:84] = images[at]
                    state = flat.encode(image, previous, previous_image, **settings)
                    state_array[at] = np.frombuffer(state, np.uint8)
                    previous, previous_image = state, image.copy()
            states[name] = state_array
            elapsed[name] = time.perf_counter()-started
            print(f'{name}: {len(indices)} measured frames, {elapsed[name]:.3f}s including contexts', flush=True)
        quiet_error = {name: [0., 0] for name in states}
        for at in indices:
            image[12:84] = images[at]
            row = dict(frame=at, metrics={name: metrics(image, array[at].tobytes()) for name, array in states.items()})
            if at not in WINDOWS:
                source_delta = images[at].astype(float)-images[at-1].astype(float)
                quiet = np.max(np.abs(source_delta), axis=-1) <= 4
                for name, array in states.items():
                    residual = (averaged(array[at].tobytes())-averaged(array[at-1].tobytes()))[12:84]-source_delta
                    quiet_error[name][0] += float(((residual @ flat.Y)[quiet]**2).sum())
                    quiet_error[name][1] += int(quiet.sum())
            rows.append(row)
        summary = {}
        for name in states:
            summary[name] = {key: float(np.mean([row['metrics'][name][key] for row in rows]))
                for key in rows[0]['metrics']['baseline']}
            for key in ('strong_source_edges', 'retained_strong_edges'):
                summary[name][key] = sum(row['metrics'][name][key] for row in rows)
            summary[name]['strong_edge_retention_percent'] = 100*summary[name]['retained_strong_edges']/summary[name]['strong_source_edges']
            summary[name]['quiet_source_luma_residual_mse'] = quiet_error[name][0]/max(quiet_error[name][1], 1)
            summary[name]['maximum_patterned_samples_per_cell'] = max(row['metrics'][name]['maximum_patterned_samples_per_cell'] for row in rows)
        report = dict(date='2026-10-14', baseline_commit='3423807c', baseline_disk='df986063d6cc6e5ff9048cea074e642759fc6140ca911ecd86064b7fe1c399cb',
            source_sha256=digest(source_path), baseline_states_sha256=digest(baseline_path),
            measured_frames=len(indices), windows=[dict(start=lo, end=lo+COUNT, context_frames=2) for lo in WINDOWS],
            parameters=flat.PARAMETERS, variants=VARIANTS, elapsed_seconds=elapsed, summary=summary, frames=rows,
            scope='Host native-format references on 96 fixed frames. No new TRD, full-player timing or semantic person-recognition/subjective readability grade.',
            metric_scope='Edges use averaged 2x2 RGB, original adjacent RMS >=24, output >=35% source contrast and RGB gradient cosine >=0.5. Quiet measure is source-residual luma on max source component delta <=4; not motion compensation. Native MSE includes exact within-2x2 endpoint variance.')
        np.savez_compressed(args.output/'states.npz', indices=np.array(indices), source=images[indices],
            **{name: array[indices] for name, array in states.items()})
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(summary, indent=2), flush=True)
    else:
        saved = np.load(args.output/'states.npz')
        states = {name: np.zeros_like(baseline) for name in ('baseline', *VARIANTS)}
        for name in states:states[name][indices] = saved[name]
    snapshot_indices = (98, 154, 259, 300, 506, 792)
    sheet(images, states, snapshot_indices, ('source', 'baseline', 'flat', 'minimal', 'regions', 'regions_contours'), args.output/'all-variants.png')
    sheet(images, states, (154, 300, 506), ('source', 'baseline', args.selected), args.output/'characters.png')
    if args.ffmpeg:
        width, height = 768, 168
        command = [str(args.ffmpeg), '-v', 'error', '-nostdin', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
            '-video_size', f'{width}x{height}', '-framerate', '10', '-i', 'pipe:0', '-an',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(args.output/'comparison.mp4')]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        try:
            for at in indices:
                panel = Image.new('RGB', (width, height), '#181818');draw = ImageDraw.Draw(panel)
                for col, name in enumerate(('source', 'baseline', args.selected)):
                    pixels = (images[at].repeat(2, 0).repeat(2, 1) if name == 'source'
                        else render_spectrum_screen(*five.expand(states[name][at].tobytes()))[24:168])
                    panel.paste(Image.fromarray(pixels), (col*256, 24))
                    draw.text((col*256+4, 4), f'{at/10:.1f}s {name}', fill='white')
                process.stdin.write(np.asarray(panel, np.uint8).tobytes())
        finally:process.stdin.close()
        if process.wait() != 0:raise RuntimeError('preview failed')
    (args.output/'preview.json').write_text(json.dumps(dict(selected=args.selected, fps=10,
        frames=len(indices), duration=len(indices)/10, source_times=[i/10 for i in indices],
        scope='Silent host reference; six non-contiguous windows, no Fuse capture.'), indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':main()
