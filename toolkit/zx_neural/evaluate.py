"""Compare conversion modes on sources held out from training and selection."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw

from .__main__ import choose, render
from .corpus import EVALUATION, read_source
from .model import DEFAULT_WEIGHTS, load_weights
from .objective import Candidates, COLOR_BUDGET, edge_weight
from .screen import HEIGHT, WIDTH, prepare

MODES = ("baseline", "spatial", "spatial-full", "neural", "hybrid")
PANEL_MODES = ("source", "baseline", "spatial", "hybrid")


def independent_decode(screen):
    """Decode with explicit thirds and scanline divisions, independent of pack()."""
    if len(screen) != 6912:
        raise ValueError("wrong SCR size")
    if any(attr & 128 for attr in screen[6144:]):
        raise ValueError("unexpected FLASH")
    out = bytearray()
    for y in range(192):
        row_offset = (y // 64) * 2048 + (y % 8) * 256 + ((y // 8) % 8) * 32
        attr_offset = 6144 + (y // 8) * 32
        for column in range(32):
            attr = screen[attr_offset + column]
            level = 255 if attr & 64 else 205
            paper, ink = (attr >> 3) & 7, attr & 7
            byte = screen[row_offset + column]
            for bit in range(7, -1, -1):
                color = ink if byte & (1 << bit) else paper
                out.extend(level if color & mask else 0 for mask in (2, 4, 1))
    return np.frombuffer(out, np.uint8).reshape(192, 256, 3)


def quality(source, output):
    """Measure false seam steps separately from RGB error and real edge errors."""
    source = source.astype(np.float32) / 255
    residual = output.astype(np.float32) / 255 - source
    # Four-pixel block averages suppress the ordered dot pattern while
    # retaining the location and size of each Spectrum attribute boundary.
    pooled = residual.reshape(HEIGHT // 4, 4, WIDTH // 4, 4, 3).mean(axis=(1, 3))
    pooled_source = source.reshape(HEIGHT // 4, 4, WIDTH // 4, 4, 3).mean(axis=(1, 3))
    seam_error = seam_weight = 0.
    pooled_error = pooled_weight = 0.
    strong_edge_sum = strong_edge_count = 0
    for axis in (0, 1):
        source_step = np.diff(source, axis=axis)
        error = np.mean(np.diff(residual, axis=axis) ** 2, axis=-1)
        seams = np.s_[7::8, :] if axis == 0 else np.s_[:, 7::8]
        weights = edge_weight(source_step[seams])
        seam_error += float((error[seams] * weights).sum())
        seam_weight += float(weights.sum())
        coarse_seams = np.s_[1::2, :] if axis == 0 else np.s_[:, 1::2]
        coarse_weights = edge_weight(np.diff(pooled_source, axis=axis)[coarse_seams])
        coarse_error = np.mean(np.diff(pooled, axis=axis)[coarse_seams] ** 2, axis=-1)
        pooled_error += float((coarse_error * coarse_weights).sum())
        pooled_weight += float(coarse_weights.sum())
        strong = np.max(np.abs(source_step), axis=-1) >= .30
        strong_edge_count += int(strong.sum())
        strong_edge_sum += float(error[strong].sum())
    return dict(rgb_rmse=float(np.sqrt(np.mean(residual ** 2))) * 255,
                pooled_rgb_rmse=float(np.sqrt(np.mean(pooled ** 2))) * 255,
                seam_rmse=np.sqrt(seam_error / seam_weight) * 255,
                pooled_seam_rmse=np.sqrt(pooled_error / pooled_weight) * 255,
                strong_edge_rmse=np.sqrt(strong_edge_sum / strong_edge_count) * 255
                if strong_edge_count else None)


def evaluate(weights, destination):
    destination.mkdir(parents=True, exist_ok=True)
    layers = load_weights(weights)
    row_height = HEIGHT + 20
    panel = Image.new("RGB", (WIDTH * len(PANEL_MODES), row_height * len(EVALUATION)), "#161819")
    draw = ImageDraw.Draw(panel)
    report = dict(weights_sha256=sha256(weights.read_bytes()).hexdigest(), sources=[])
    for row, (kind, name) in enumerate(EVALUATION):
        image = read_source(kind, name)
        source = prepare(image)
        label = Path(name).stem
        entry = dict(source=name, kind=kind, prepared_pixel_sha256=sha256(source.tobytes()).hexdigest(),
                     results={})
        images = {"source": source}
        for mode in MODES:
            samples = []
            for _ in range(3):
                start = perf_counter()
                candidates = Candidates(source)
                labels = choose(source, candidates, mode, layers)
                screen, preview = render(candidates, labels)
                samples.append((perf_counter() - start) * 1000)
            decoded = independent_decode(screen)
            np.testing.assert_array_equal(decoded, preview)
            regret = np.take_along_axis(candidates.regret, labels[..., None], axis=-1)
            if float(regret.max()) > COLOR_BUDGET:
                raise ValueError(f"{label} {mode} exceeded the per-cell color budget")
            entry["results"][mode] = dict(
                **quality(source, decoded), median_cpu_wall_ms=median(samples),
                scr_sha256=sha256(screen).hexdigest(), max_cell_regret=float(regret.max()))
            (destination / f"{label}-{mode}.scr").write_bytes(screen)
            Image.fromarray(decoded).save(destination / f"{label}-{mode}.png")
            images[mode] = decoded
        report["sources"].append(entry)
        for column, mode in enumerate(PANEL_MODES):
            x, y = column * WIDTH, row * row_height
            draw.text((x + 5, y + 3), f"{label} / {mode}", fill="white")
            panel.paste(Image.fromarray(images[mode]), (x, y + 20))
        print(label, " ".join(f"{m}={entry['results'][m]['seam_rmse']:.2f}" for m in MODES), flush=True)
    keys = ("rgb_rmse", "seam_rmse", "strong_edge_rmse", "median_cpu_wall_ms")
    report["means"] = {mode: {
        key: float(np.mean([entry["results"][mode][key] for entry in report["sources"]
                            if entry["results"][mode][key] is not None]))
        for key in keys} for mode in MODES}
    panel.save(destination / "comparison.png")
    (destination / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(json.dumps(report["means"], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    args = parser.parse_args()
    evaluate(args.weights, args.directory)


if __name__ == "__main__":
    main()
