"""Review source lines and matched fills before committing to a disk rebuild."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'toolkit'))
import lineart_colour as line
import five_level_dither as five
from cell_palette_quality import averaged
from build_zxv_trd import render_spectrum_screen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--flat-preview', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):parser.error('output must be new or empty')
    args.output.mkdir(parents=True, exist_ok=True)
    original = np.fromfile(args.baseline/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3)
    baseline = np.load(args.baseline/'work/five-states.npy')
    flat = np.load(args.flat_preview/'states.npz')
    indices = (98, 154, 259, 300, 506, 792)
    canvas = Image.new('RGB', (2048, len(indices)*312), '#181818');draw = ImageDraw.Draw(canvas)
    image = np.zeros((96, 128, 3), np.uint8);rows = [];selected = []
    for row, at in enumerate(indices):
        image[12:84] = original[at]
        state = line.encode(image);selected.append(np.frombuffer(state, np.uint8))
        lines = line.source_lines(image);fills = line.source_fills(image)
        before = flat['contours'][int(np.flatnonzero(flat['indices'] == at)[0])].tobytes()
        pictures = [image.repeat(2, 0).repeat(2, 1),
            render_spectrum_screen(*five.expand(baseline[at].tobytes())),
            render_spectrum_screen(*five.expand(before)), render_spectrum_screen(*five.expand(state))]
        for col, (label, pixels) in enumerate(zip(('Source', 'Existing', 'Rejected flat', 'Source lines + matched fills'), pictures)):
            draw.text((col*512+8, row*312+4), f'{at/10:.1f}s {label}', fill='white')
            canvas.paste(Image.fromarray(pixels[24:168]).resize((512, 288), Image.Resampling.NEAREST), (col*512, row*312+24))
        output = averaged(state)
        np.testing.assert_array_equal(output[lines], np.zeros((lines.sum(), 3)))
        rows.append(dict(frame=at, source_line_samples=int(lines.sum()),
            source_matched_colour_samples=int(((fills != 0) & (fills != 7))[12:84].sum()),
            source_matched_black_samples=int((fills[12:84] == 0).sum()),
            native_rgb_mse=float(np.mean((output[12:84]-image[12:84])**2)),
            patterned_samples=int(((five.unpack_levels(state[:3840]) > 0) & (five.unpack_levels(state[:3840]) < 4)).sum())))
    canvas.save(args.output/'lineart-comparison.png')
    np.savez_compressed(args.output/'states.npz', indices=np.array(indices), source=original[list(indices)], states=np.array(selected))
    (args.output/'report.json').write_text(json.dumps(dict(parameters=line.PARAMETERS,
        frames=rows, scope='Six-frame host review of source-line drawing; no semantic recognition or native disk timing.'), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':main()
