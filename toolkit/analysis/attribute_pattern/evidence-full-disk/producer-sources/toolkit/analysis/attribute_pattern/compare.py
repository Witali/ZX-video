"""Compare every source/previous/new frame and render native-reference previews."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'toolkit'))
from probe import metrics, contact_sheet
import build_long_video_trd as video
import five_level_dither as five
import stable_colour
import texture_colour
from cell_palette_quality import averaged


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--skip-preview', action='store_true', help='refresh measurements without encoding previews again')
    args = parser.parse_args();build = args.build
    conversion = json.loads((build/'conversion.json').read_bytes())
    # Diagnostics can be saved after a failed/partial native run. They cannot
    # qualify a release; archive.py separately requires all full native proofs.
    native_count = conversion.get('frames') or conversion['input']['encoded_frames']
    old = np.load(args.baseline/'work/five-states.npy', mmap_mode='r')
    new = np.load(build/'work/five-states.npy', mmap_mode='r')
    count = min(len(old), native_count)
    assert new.shape == (native_count, 4608) and old.shape[1] == 4608
    for name, size in (('frames.rgb', count*72*128*3), ('ay.bin', count*5*12)):
        with (build/'work'/name).open('rb') as current, (args.baseline/'work'/name).open('rb') as prior:
            assert current.read(size) == prior.read(size)
    with wave.open(str(build/'work/audio-preview.wav'), 'rb') as current, wave.open(str(args.baseline/'work/audio-preview.wav'), 'rb') as prior:
        assert current.getframerate() == prior.getframerate() == 22050
        assert current.getnchannels() == prior.getnchannels() == 1
        assert current.getsampwidth() == prior.getsampwidth() == 2
        samples = count*5*441
        assert current.readframes(samples) == prior.readframes(samples)
    sources = np.memmap(build/'work/frames.rgb', np.uint8, mode='r', shape=(count, 72, 128, 3))
    image = np.zeros((96, 128, 3), np.uint8)
    comparison = stable_colour.Comparison();rows = [];previous = None
    quiet_sum = [0., 0.];quiet_count = 0
    for index, source in enumerate(sources):
        image[12:84] = source
        states = [old[index].tobytes(), new[index].tobytes()]
        comparison.add(image, *states)
        row = {name: metrics(image, state) for name, state in zip(('previous', 'selected'), states)}
        output = [averaged(state)[12:84] for state in states]
        if previous is not None:
            old_source, old_outputs = previous
            quiet = np.max(np.abs(source.astype(float)-old_source), axis=2) <= 4
            quiet_count += int(quiet.sum())
            for at in range(2):
                residual_delta = (output[at]-old_outputs[at])-(source.astype(float)-old_source)
                luma = residual_delta @ texture_colour.Y
                quiet_sum[at] += float((luma[quiet]**2).sum())
        previous = source.astype(float), output
        rows.append(row)
    report = dict(complete=True, full_native_qualified=bool(conversion.get('timing_verified')),
        frames=count, native_frames=native_count, baseline_commit='db07319e', exact_source_and_ay_unchanged=True,
        comparison_scope=f'Leading {count} frames against previously qualified disk. Full {native_count}-frame source errors are in video-quality.json and every native screen/AY/deadline is independently checked.',
        source_rgb_sha256=digest(build/'work/frames.rgb'),
        baseline_states_sha256=digest(args.baseline/'work/five-states.npy'),
        selected_states_sha256=digest(build/'work/five-states.npy'),
        parameters=texture_colour.PARAMETERS.copy(), frame_metrics=rows,
        colour=texture_colour.comparison_report(comparison),
        metric_scope='Cell texture: source-weighted jump of mean native RGB standard deviation across neighboring 8x8 cells. Solid/pattern edge: exactly zero versus nonzero within-sample grain, source cell-mean RMS contrast <=8. Sample seams include intentional fractional-density variation; report separately.',
        preview_scope='Source/previous/new native references; TRD qualification independently checks all actual Fuse screen bytes. AY preview uses the unchanged chip model WAV.')
    for at, name in enumerate(('previous', 'selected')):
        report[name] = {key: float(np.mean([row[name][key] for row in rows]))
                        for key in rows[0][name] if not key.endswith('_samples') and not key.endswith('_edges')}
        report[name].update({key: sum(row[name][key] for row in rows)
                            for key in rows[0][name] if key.endswith('_samples') or key.endswith('_edges')})
        report[name]['quiet_pooled_luma_residual_mse'] = quiet_sum[at]/max(quiet_count, 1)
    report['quiet_source_samples'] = quiet_count
    (build/'pattern-comparison.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if args.skip_preview:
        print(json.dumps({key:report[key] for key in ('previous', 'selected', 'quiet_source_samples', 'full_native_qualified')}, indent=2))
        return
    worst = int(np.argmax([r['selected']['cell_texture_seam_mse'] for r in rows]))
    indices = sorted({98, 100, 154, 259, 300, 506, worst})
    sheets = []
    for index in indices:
        image[12:84] = sources[index]
        sheets.append((str(index), image.copy(), old[index].tobytes(), new[index].tobytes()))
    contact_sheet(sheets, build/'pattern-comparison.png')
    command = [args.ffmpeg, '-v', 'error', '-nostdin', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '768x216', '-framerate', '10', '-i', 'pipe:0',
        '-i', str(build/'work/audio-preview.wav'), '-map', '0:v:0', '-map', '1:a:0',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '128k', '-t', str(count/10), '-movflags', '+faststart',
        str(build/'pattern-comparison.mp4')]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for index in range(count):
            image[12:84] = sources[index]
            panel = Image.new('RGB', (768, 216), (24, 24, 24));draw = ImageDraw.Draw(panel)
            views = [image.repeat(2, 0).repeat(2, 1),
                video.base.render_spectrum_screen(*five.expand(old[index].tobytes())),
                video.base.render_spectrum_screen(*five.expand(new[index].tobytes()))]
            for column, (label, pixels) in enumerate(zip(('Source', 'Previous', 'Texture-aware'), views)):
                panel.paste(Image.fromarray(pixels), (column*256, 24))
                draw.text((column*256+4, 4), label, fill='white')
            process.stdin.write(np.asarray(panel, np.uint8).tobytes())
    finally:process.stdin.close()
    if process.wait() != 0:raise RuntimeError('preview encoding failed')
    print(json.dumps({key:report[key] for key in ('previous', 'selected', 'quiet_source_samples', 'full_native_qualified')}, indent=2))


if __name__ == '__main__':main()
