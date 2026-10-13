"""Compare exact source RGB, old native screens and new native screens."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'toolkit'))
import build_long_video_trd as video
import five_level_dither as five
import stable_colour


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--baseline', type=Path, default=HERE/'evidence')
    parser.add_argument('--ffmpeg', required=True)
    args = parser.parse_args()
    current = json.loads((args.build/'conversion.json').read_bytes())
    assert current['complete'] and current['timing_verified']
    count = current['frames']
    old = np.load(args.baseline/'work/five-states.npy', mmap_mode='r')
    new = np.load(args.build/'work/five-states.npy', mmap_mode='r')
    assert old.shape == new.shape == (count, five.STATE_BYTES)
    rgb_path = args.build/'work/frames.rgb'
    assert digest(rgb_path) == digest(args.baseline/'work/frames.rgb')
    assert digest(args.build/'work/ay.bin') == digest(args.baseline/'work/ay.bin')
    assert digest(args.build/'work/audio-preview.wav') == digest(args.baseline/'work/audio-preview.wav')
    source = np.memmap(rgb_path, dtype=np.uint8, mode='r', shape=(count, 72, 128, 3))
    comparison = stable_colour.Comparison()
    image = np.zeros((96, 128, 3), dtype=np.uint8)
    for index in range(count):
        image[12:84] = source[index]
        comparison.add(image, old[index].tobytes(), new[index].tobytes())
    measured = comparison.report()
    measured.update(complete=True, source_rgb_sha256=digest(rgb_path),
        baseline_states_sha256=digest(args.baseline/'work/five-states.npy'),
        selected_states_sha256=digest(args.build/'work/five-states.npy'),
        exact_source_and_ay_unchanged=True, baseline_commit='fe3bb2cf',
        output_scope='Source/old/new native-reference preview; actual new TRD fully verified independently in Fuse.')
    quality = json.loads((args.build/'video-quality.json').read_bytes())
    assert measured['frames'] == quality['colour_comparison']['frames']
    (args.build/'colour-comparison.json').write_text(
        json.dumps(measured, indent=2)+'\n', encoding='utf-8', newline='\n')
    # Include hard old scenes and the largest remaining new-source RGB error.
    indices = sorted({98, 99, 100, 154, count-1,
        int(np.argmax([row['stable']['rgb_mse'] for row in measured['frames']]))})
    sheet = Image.new('RGB', (768, len(indices)*216), (24, 24, 24))
    labels = ImageDraw.Draw(sheet)
    for row, index in enumerate(indices):
        image[12:84] = source[index]
        views = [Image.fromarray(image).resize((256, 192), Image.Resampling.NEAREST)]
        views.extend(Image.fromarray(video.base.render_spectrum_screen(*five.expand(states[index].tobytes())))
                     for states in (old, new))
        for column, (label, view) in enumerate(zip(('Source', 'Previous', 'Stable colours'), views)):
            sheet.paste(view, (column*256, row*216+24))
            labels.text((column*256+4, row*216+4), f'{index}: {label}', fill='white')
    sheet.save(args.build/'colour-comparison.png')
    command = [args.ffmpeg, '-v', 'error', '-nostdin', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '768x216', '-framerate', '10', '-i', 'pipe:0',
        '-i', str(args.build/'work/audio-preview.wav'), '-map', '0:v:0', '-map', '1:a:0',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '128k', '-t', str(current['duration_seconds']),
        '-movflags', '+faststart', str(args.build/'colour-comparison.mp4')]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for index in range(count):
            image[12:84] = source[index]
            panel = Image.new('RGB', (768, 216), (24, 24, 24))
            labels = ImageDraw.Draw(panel)
            views = [Image.fromarray(image).resize((256, 192), Image.Resampling.NEAREST)]
            views.extend(Image.fromarray(video.base.render_spectrum_screen(*five.expand(states[index].tobytes())))
                         for states in (old, new))
            for column, (label, view) in enumerate(zip(('Source', 'Previous', 'Stable colours'), views)):
                panel.paste(view, (column*256, 24))
                labels.text((column*256+4, 4), label, fill='white')
            process.stdin.write(np.asarray(panel, np.uint8).tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError('comparison preview encoding failed')
    print(json.dumps({key: measured[key] for key in ('legacy', 'stable', 'exact_source_and_ay_unchanged')}))


if __name__ == '__main__':
    main()
