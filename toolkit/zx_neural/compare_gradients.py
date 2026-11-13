"""Compare palette seams and gradient rendering on the fixed photo splits."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw

from .__main__ import choose, render
from .evaluate import independent_decode, quality
from .model import CLIC_WIDE_WEIGHTS, load_weights
from .objective import Candidates
from .photo_corpus import clic_split, read_clic, read_evaluation_photos
from .screen import HEIGHT, WIDTH, prepare

MODES = {"plain": {}, "ordered": {"dither": True}, "smooth": {"smooth": True}, "floyd": {"floyd": True}}
TITLES = {"source": "Source", "plain": "Previous (solid)", "ordered": "Previous (ordered)",
          "smooth": "Joint color search", "floyd": "Joint search + Floyd-Steinberg"}


def sheet(path, rows, columns):
    row_height = HEIGHT + 22
    panel = Image.new("RGB", (len(columns) * WIDTH, len(rows) * row_height), "#161819")
    draw = ImageDraw.Draw(panel)
    for row, (name, images) in enumerate(rows):
        y = row * row_height
        for col, mode in enumerate(columns):
            x = col * WIDTH
            title = f"Source / {name}" if mode == "source" else TITLES[mode]
            draw.text((x + 5, y + 4), title, fill="white")
            panel.paste(Image.fromarray(images[mode]), (x, y + 22))
    panel.save(path)


def compare(sources, destination, weights):
    destination.mkdir(parents=True, exist_ok=True)
    layers = load_weights(weights)
    rows, entries = [], []
    for name, image in sources:
        source = prepare(image)
        candidates = Candidates(source)
        labels = choose(source, candidates, "hybrid", layers)
        images = {"source": source}
        entry = dict(source=name, prepared_sha256=sha256(source.tobytes()).hexdigest(), results={})
        for mode, options in MODES.items():
            start = perf_counter()
            screen, preview = render(candidates, labels, **options, repair=True)
            elapsed = (perf_counter() - start) * 1000
            decoded = independent_decode(screen)
            np.testing.assert_array_equal(preview, decoded)
            images[mode] = decoded
            entry["results"][mode] = dict(**quality(source, decoded), render_ms=elapsed,
                                          scr_sha256=sha256(screen).hexdigest())
            if mode in ("smooth", "floyd"):
                (destination / f"{Path(name).stem}-{mode}.scr").write_bytes(screen)
        rows.append((Path(name).stem, images))
        entries.append(entry)
    for offset in range(0, len(rows), 4):
        sheet(destination / f"comparison-{offset // 4 + 1}.png", rows[offset:offset + 4],
              ("source", "plain", "ordered", "smooth", "floyd"))
    means = {
        mode: {key: mean(entry["results"][mode][key] for entry in entries
                         if entry["results"][mode][key] is not None)
               for key in entries[0]["results"][mode] if key != "scr_sha256"}
        for mode in MODES
    }
    report = dict(weights_sha256=sha256(weights.read_bytes()).hexdigest(), sources=entries, means=means)
    (destination / "comparison.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(json.dumps(means, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--clic-root", type=Path)
    source.add_argument("--bsds-archive", type=Path)
    parser.add_argument("--validation", action="store_true", help="use the CLIC validation split")
    parser.add_argument("--weights", type=Path, default=CLIC_WIDE_WEIGHTS)
    args = parser.parse_args()
    if args.validation and args.clic_root is None:
        parser.error("--validation requires --clic-root")
    sources = (read_clic(clic_split(args.clic_root)[1 if args.validation else 2])
               if args.clic_root else read_evaluation_photos(args.bsds_archive))
    compare(sources, args.destination, args.weights)


if __name__ == "__main__":
    main()
