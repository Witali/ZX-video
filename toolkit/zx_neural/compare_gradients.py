"""Compare palette seams and gradient rendering on the fixed photo splits."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw

from .__main__ import add_subject, choose, render
from .evaluate import independent_decode, quality
from .halftones import restore_halftones
from .inner_contours import restore_inner_contours
from .model import CLIC_WIDE_WEIGHTS, load_weights
from .objective import Candidates
from .photo_corpus import clic_split, read_clic, read_evaluation_photos
from .screen import HEIGHT, WIDTH, prepare
from .subject import SubjectDetector, subject_scores

MODES = {"plain": {}, "ordered": {"dither": True}, "smooth": {"smooth": True}, "floyd": {"floyd": True}}
TITLES = {"source": "Source", "plain": "Previous (solid)", "ordered": "Previous (ordered)",
          "smooth": "Joint color search", "floyd": "Floyd-Steinberg", "subject": "Automatic silhouette"}


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


def compare(sources, destination, weights, subject_model=None):
    destination.mkdir(parents=True, exist_ok=True)
    layers = load_weights(weights)
    detector = SubjectDetector(subject_model) if subject_model else None
    rows, entries = [], []
    for name, image in sources:
        source = prepare(image)
        candidates = Candidates(source)
        labels = choose(source, candidates, "hybrid", layers)
        images = {"source": source}
        entry = dict(source=name, prepared_sha256=sha256(source.tobytes()).hexdigest(), results={})
        for mode, options in MODES.items():
            if detector and mode != "floyd":
                continue
            start = perf_counter()
            screen, preview = render(candidates, labels, **options, repair=True)
            if mode == "floyd":
                baseline = screen, preview
                screen, preview = restore_halftones(source, (screen, preview))
                screen, preview = restore_inner_contours(source, (screen, preview))
            elapsed = (perf_counter() - start) * 1000
            decoded = independent_decode(screen)
            np.testing.assert_array_equal(preview, decoded)
            images[mode] = decoded
            entry["results"][mode] = dict(**quality(source, decoded), render_ms=elapsed,
                                          scr_sha256=sha256(screen).hexdigest())
            if mode in ("smooth", "floyd"):
                (destination / f"{Path(name).stem}-{mode}.scr").write_bytes(screen)
        if detector:
            start = perf_counter()
            probability = detector.predict(image)
            before = images["floyd"]
            after_screen, after_preview = add_subject(source, "hybrid", layers, baseline,
                                                      probability, floyd=True, repair=True)
            after_screen, after_preview = restore_halftones(source, (after_screen, after_preview))
            after_screen, after_preview = restore_inner_contours(source, (after_screen, after_preview), probability)
            elapsed = (perf_counter() - start) * 1000
            decoded = independent_decode(after_screen)
            np.testing.assert_array_equal(after_preview, decoded)
            images["subject"] = decoded
            mask = np.clip((probability - .38) / .52, 0, 1)
            entry["silhouette"] = dict(before=subject_scores(source, before, mask),
                                       after=subject_scores(source, decoded, mask),
                                       changed_pixels=int(np.any(before != decoded, axis=-1).sum()))
            entry["results"]["subject"] = dict(**quality(source, decoded), render_ms=elapsed,
                                               scr_sha256=sha256(after_screen).hexdigest())
            (destination / f"{Path(name).stem}-subject.scr").write_bytes(after_screen)
        rows.append((Path(name).stem, images))
        entries.append(entry)
    columns = ("source", "floyd", "subject") if detector else ("source", "plain", "ordered", "smooth", "floyd")
    for offset in range(0, len(rows), 4):
        sheet(destination / f"comparison-{offset // 4 + 1}.png", rows[offset:offset + 4],
              columns)
    means = {
        mode: {key: mean(entry["results"][mode][key] for entry in entries
                         if entry["results"][mode][key] is not None)
               for key in entries[0]["results"][mode] if key != "scr_sha256"}
        for mode in entries[0]["results"]
    }
    report = dict(weights_sha256=sha256(weights.read_bytes()).hexdigest(), sources=entries, means=means)
    if subject_model:
        report["subject_model_sha256"] = sha256(subject_model.read_bytes()).hexdigest()
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
    parser.add_argument("--subject-model", type=Path, help="compare baseline with automatic silhouette restoration")
    args = parser.parse_args()
    if args.validation and args.clic_root is None:
        parser.error("--validation requires --clic-root")
    sources = (read_clic(clic_split(args.clic_root)[1 if args.validation else 2])
               if args.clic_root else read_evaluation_photos(args.bsds_archive))
    compare(sources, args.destination, args.weights, args.subject_model)


if __name__ == "__main__":
    main()
