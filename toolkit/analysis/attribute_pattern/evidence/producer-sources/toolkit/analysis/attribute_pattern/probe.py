"""Inspect source-smooth solid/pattern seams on the previous native release."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'toolkit'))
import build_long_video_trd as video
import five_level_dither as five
import texture_colour as texture
from cell_palette_quality import averaged
from stable_colour import cells, RGB_GRAIN, ATTRS, boundary_error


def metrics(source, state):
    """Measure both mean residuals and physical texture across source-smooth edges.

    Grain is the exact RGB variance of a logical sample's four native pixels.
    Solid/pattern counts compare matching samples on either side of an 8x8
    attribute edge where source RMS contrast <= 8. This is a diagnostic,
    not a perceptual grade. Real source edges receive exponentially less weight.
    """
    output = averaged(state)[12:84]
    original = source[12:84].astype(float)
    levels = five.unpack_levels(state[:3840])[12:84]
    attrs = np.frombuffer(state[3840:], np.uint8)
    pair = (attrs[:, None] == ATTRS).argmax(1).reshape(24, 32).repeat(4, 0).repeat(4, 1)[12:84]
    grain = np.sqrt(RGB_GRAIN[pair, levels])
    total = weight_sum = 0.;solid = smooth = 0
    for a, b, src in ((grain[:, 4::4], grain[:, 3:-1:4], original[:, 4::4]-original[:, 3:-1:4]),
                      (grain[4::4], grain[3:-1:4], original[4::4]-original[3:-1:4])):
        contrast = np.mean(src**2, axis=-1)
        weight = np.exp(-contrast/256)
        total += float((weight*(a-b)**2).sum());weight_sum += float(weight.sum())
        valid = contrast <= 64
        smooth += int(valid.sum())
        solid += int((valid & ((a == 0) != (b == 0))).sum())
    residual = cells(averaged(state)-source.astype(float))[96:672]
    local = residual.reshape(576, 2, 2, 2, 2, 3).mean(axis=(2, 4))
    cell_grain = cells(np.pad((grain**2)[:, :, None], ((12, 12), (0, 0), (0, 0))))[96:672, :, 0].mean(1).reshape(18, 32)
    cell_source = cells(source.astype(float))[96:672].mean(1).reshape(18, 32, 3)
    cell_total = cell_weights = 0.;solid_cells = smooth_cells = 0
    for a, b, src in ((cell_grain[:, 1:], cell_grain[:, :-1], cell_source[:, 1:]-cell_source[:, :-1]),
                      (cell_grain[1:], cell_grain[:-1], cell_source[1:]-cell_source[:-1])):
        contrast = np.mean(src**2, axis=-1);weight = np.exp(-contrast/256)
        cell_total += float((weight*(np.sqrt(a)-np.sqrt(b))**2).sum());cell_weights += float(weight.sum())
        valid = contrast <= 64;smooth_cells += int(valid.sum())
        solid_cells += int((valid & ((a == 0) != (b == 0))).sum())
    return dict(sample_mean_rgb_mse=float(np.mean(residual**2)),
        native_rgb_mse=float(np.mean(residual**2)+np.mean(grain**2)),
        mean_4x4_native_rgb_mse=float(np.mean(local**2)),
        mean_8x8_native_rgb_mse=float(np.mean(residual.mean(1)**2)),
        boundary_residual_mse=boundary_error(original, output),
        texture_seam_mse=total/max(weight_sum, 1e-12),
        source_smooth_boundary_samples=smooth, solid_pattern_boundary_samples=solid,
        cell_texture_seam_mse=cell_total/max(cell_weights, 1e-12),
        source_smooth_cell_edges=smooth_cells, solid_pattern_cell_edges=solid_cells)


def contact_sheet(rows, path):
    canvas = Image.new('RGB', (1536, len(rows)*320), 'white')
    draw = ImageDraw.Draw(canvas)
    for row, (label, source, before, after) in enumerate(rows):
        images = [source.repeat(2, 0).repeat(2, 1),
                  video.base.render_spectrum_screen(*five.expand(before)),
                  video.base.render_spectrum_screen(*five.expand(after))]
        for col, pixels in enumerate(images):
            draw.text((col*512+8, row*320+4), f'{label}: '+('Source', 'Previous release', 'Texture-aware')[col], fill='black')
            view = Image.fromarray(pixels[24:168]).resize((512, 288), Image.Resampling.NEAREST)
            canvas.paste(view, (col*512, row*320+24))
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args();args.output.mkdir(parents=True, exist_ok=True)
    source = np.fromfile(args.baseline/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3)
    old = np.load(args.baseline/'work/five-states.npy')
    rows = [];report = dict(parameters=texture.PARAMETERS, frames={})
    for index in (98, 100, 154, 259, 300, 506):
        image = np.zeros((96, 128, 3), np.uint8);image[12:84] = source[index]
        before = old[index].tobytes()
        new = texture.encode(image, before)
        report['frames'][str(index)] = dict(previous=metrics(image, before), candidate=metrics(image, new))
        rows.append((str(index), image, before, new))
    contact_sheet(rows, args.output/'probe.png')
    (args.output/'probe.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
