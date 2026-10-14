"""Check every selected line/fill against source and make a matched comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'toolkit'))
import lineart_colour as line
import five_level_dither as five
from cell_palette_quality import averaged
from build_zxv_trd import render_spectrum_screen


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path);p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--ffmpeg', type=Path, required=True)
    args = p.parse_args();build = args.build
    manifest = json.loads((build/'conversion.json').read_bytes())
    if not manifest['complete'] or not manifest['timing_verified']:
        raise ValueError('complete native-qualified build required')
    assert manifest['colour_policy'] == 'lineart' and len(manifest['volumes']) == 1
    states = np.load(build/'work/five-states.npy')
    volume = manifest['volumes'][0]
    native = np.load(build/'work'/Path(volume['file']).stem/'states.npz')['states']
    source = np.fromfile(build/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3)
    old = np.load(args.baseline/'work/five-states.npy')
    old_rgb = np.fromfile(args.baseline/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3)
    common = min(len(old), len(source))
    assert np.array_equal(source[:common], old_rgb[:common])
    assert states.shape == native.shape == (len(source), 4608)
    assert manifest['frames'] == len(source) and manifest['ay_ticks'] == len(source)*5
    with (build/'work/ay.bin').open('rb') as current, (args.baseline/'work/ay.bin').open('rb') as previous:
        assert current.read(common*5*12) == previous.read(common*5*12)
    with wave.open(str(build/'work/audio-preview.wav'), 'rb') as current, wave.open(str(args.baseline/'work/audio-preview.wav'), 'rb') as previous:
        assert current.getparams()[:3] == previous.getparams()[:3] == (1, 2, 22050)
        assert current.readframes(common*5*441) == previous.readframes(common*5*441)
    image = np.zeros((96, 128, 3), np.uint8);rows = []
    for at, active in enumerate(source):
        image[12:84] = active
        before = states[at].tobytes();actual = native[at].tobytes()
        output = averaged(actual)
        np.testing.assert_array_equal(output, averaged(before))
        levels = five.unpack_levels(actual[:3840])
        assert set(np.unique(levels)) <= {0, 4}
        lines = line.source_lines(image);fills = line.source_fills(image)
        np.testing.assert_array_equal(output[lines], np.zeros((lines.sum(), 3)))
        black = fills == 0;black[:12] = black[84:] = False
        np.testing.assert_array_equal(output[black], np.zeros((black.sum(), 3)))
        paper = (fills == 7) & ~lines;paper[:12] = paper[84:] = False
        np.testing.assert_array_equal(output[paper], np.full((paper.sum(), 3), 205))
        coloured = np.ptp(output, axis=-1) != 0
        np.testing.assert_array_equal(output[coloured], line.COLOURS[fills[coloured]])
        optional = (fills != 0) & (fills != 7) & ~lines
        rows.append(dict(frame=at, source_line_samples=int(lines.sum()),
            black_fill_samples=int(black.sum()), output_colour_samples=int(coloured.sum()),
            optional_matched_fill_samples=int(optional.sum()),
            optional_colour_falls_back_to_paper=int((optional & ~coloured).sum()),
            sample_and_native_rgb_mse=float(np.mean((output[12:84]-active)**2)),
            old_sample_rgb_mse=(float(np.mean((averaged(old[at].tobytes())[12:84]-active)**2)) if at < common else None)))
    result = dict(complete=True, full_native_qualified=True, frames=len(source), common_frames=common,
        exact_common_rgb_and_ay_and_model_wav=True, every_source_line_black=True,
        every_matched_black_fill_exact=True, every_paper_sample_exact=True,
        every_output_colour_source_matched=True, no_dither=True,
        parameters=line.PARAMETERS, source_sha256=digest(build/'work/frames.rgb'),
        states_sha256=digest(build/'work/five-states.npy'), frames_detail=rows,
        mean_native_rgb_mse=float(np.mean([row['sample_and_native_rgb_mse'] for row in rows])),
        scope='All selected source lines/fills and actual native-format references checked. Stylized source tracing, not a photographic-fidelity or semantic recognition grade. Old comparison covers its available leading frames only.')
    (build/'lineart-comparison.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    command = [str(args.ffmpeg), '-v', 'error', '-nostdin', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '768x168', '-framerate', '10', '-i', 'pipe:0',
        '-i', str(build/'work/audio-preview.wav'), '-map', '0:v:0', '-map', '1:a:0',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '128k', '-t', str(common/10), '-movflags', '+faststart', str(build/'lineart-comparison.mp4')]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for at in range(common):
            panel = Image.new('RGB', (768, 168), '#181818');draw = ImageDraw.Draw(panel)
            pictures = [source[at].repeat(2, 0).repeat(2, 1),
                render_spectrum_screen(*five.expand(old[at].tobytes()))[24:168],
                render_spectrum_screen(*five.expand(native[at].tobytes()))[24:168]]
            for col, (label, pixels) in enumerate(zip(('Source', 'Existing colour', 'Source lines + fills'), pictures)):
                panel.paste(Image.fromarray(pixels), (col*256, 24))
                draw.text((col*256+4, 4), f'{at/10:.1f}s {label}', fill='white')
            process.stdin.write(np.asarray(panel, np.uint8).tobytes())
    finally:process.stdin.close()
    if process.wait() != 0:raise RuntimeError('comparison preview failed')
    print(json.dumps({key:value for key,value in result.items() if key not in ('frames_detail', 'parameters')}, indent=2))


if __name__ == '__main__':main()
