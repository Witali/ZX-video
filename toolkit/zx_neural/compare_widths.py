"""Compare the original, retrained, wide and distilled models on fresh photos."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw

from .__main__ import choose, render
from .dither import DITHER_COLOR_BUDGET, DitherCandidates
from .evaluate import independent_decode, quality
from .model import CLIC_WIDE_WEIGHTS, DEFAULT_WEIGHTS, load_weights
from .objective import COLOR_BUDGET, Candidates
from .photo_corpus import REVISION, clic_split, read_clic, read_evaluation_photos
from .screen import HEIGHT, WIDTH, prepare


def comparison_sheet(destination, photos, results, title, modes, metric="seam_rmse"):
    height = HEIGHT + 22
    sheet = Image.new("RGB", (WIDTH * (1 + len(modes)), height * len(photos)), "#161819")
    draw = ImageDraw.Draw(sheet)
    for row, ((name, source), entry) in enumerate(zip(photos, results, strict=True)):
        y = row * height
        draw.text((5, y + 4), f"Source  /  {Path(name).stem}", fill="white")
        sheet.paste(Image.fromarray(source), (0, y + 22))
        for column, (mode, label) in enumerate(modes, 1):
            x = column * WIDTH
            score = entry["results"][mode][metric]
            suffix = "seam" if metric == "seam_rmse" else "pooled seam"
            draw.text((x + 5, y + 4), f"{label}  /  {suffix} {score:.2f}", fill="white")
            with Image.open(destination / f"{Path(name).stem}-{mode}.png") as image:
                sheet.paste(image, (x, y + 22))
    sheet.save(destination / f"{title}.png")


def compare(photos, corpus, destination, weights, training_reports):
    destination.mkdir(parents=True, exist_ok=True)
    models = {mode: load_weights(path) for mode, path in weights.items()}
    paths = dict(weights)
    report = dict(corpus=corpus, weights={
        mode: dict(sha256=sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size,
                   channels=models[mode][0][0].shape[0]) for mode, path in paths.items()
    }, sources=[])
    excluded = set()
    documented = set()
    for path in training_reports:
        saved = json.loads(path.read_text(encoding="utf8"))
        documented.add(saved["weights_sha256"])
        excluded.update(saved["source_pixel_sha256"].values())
        excluded.update(saved.get("validation_pixel_sha256", {}).values())
    for model in report["weights"].values():
        if model["sha256"] not in documented:
            raise ValueError("missing training report for one of the model hashes")
    examples = []
    variants = [("baseline", "baseline", None), ("spatial", "spatial", None)]
    variants.extend((f"{mode}-{model}", mode, weights) for model, weights in models.items()
                    for mode in ("neural", "hybrid"))
    variants.append(("dither-wide64", "hybrid", models["wide64"]))
    for name, image in photos:
        digest = sha256(image.tobytes()).hexdigest()
        if digest in excluded:
            raise ValueError(f"evaluation photo {name} is in a training or validation split")
        source = prepare(image)
        entry = dict(source=name, pixel_sha256=digest,
                     prepared_sha256=sha256(source.tobytes()).hexdigest(), results={})
        outputs = {}
        for tag, mode, layers in variants:
            timings = []
            for _ in range(3):
                start = perf_counter()
                candidates = Candidates(source)
                labels = choose(source, candidates, mode, layers)
                dither = tag == "dither-wide64"
                if dither:
                    candidates = DitherCandidates(candidates)
                    labels = candidates.select(labels)
                screen, preview = render(candidates, labels)
                timings.append((perf_counter() - start) * 1000)
            decoded = independent_decode(screen)
            np.testing.assert_array_equal(decoded, preview)
            max_regret = float(np.take_along_axis(candidates.regret, labels[..., None], axis=-1).max())
            if max_regret > (DITHER_COLOR_BUDGET if dither else COLOR_BUDGET):
                raise ValueError(f"{name} {tag} exceeded the color budget")
            output = destination / f"{Path(name).stem}-{tag}"
            output.with_suffix(".scr").write_bytes(screen)
            Image.fromarray(decoded).save(output.with_suffix(".png"))
            entry["results"][tag] = dict(**quality(source, decoded), max_cell_regret=max_regret,
                                          median_cpu_wall_ms=median(timings),
                                          scr_sha256=sha256(screen).hexdigest())
            outputs[tag] = decoded
        reference = outputs["hybrid-original32"]
        entry["changed_pixels_from_original32"] = {
            tag: int(np.count_nonzero(np.any(outputs[tag] != reference, axis=-1)))
            for tag, mode, _ in variants if mode == "hybrid"
        }
        entry["dither_changed_pixels"] = int(np.count_nonzero(
            np.any(outputs["dither-wide64"] != outputs["hybrid-wide64"], axis=-1)))
        report["sources"].append(entry)
        examples.append((name, source))
        print(f"{name}: " + ", ".join(
            f"{tag} {entry['results'][tag]['seam_rmse']:.2f}" for tag, mode, _ in variants
            if mode == "hybrid"), flush=True)

    keys = ("rgb_rmse", "pooled_rgb_rmse", "seam_rmse", "pooled_seam_rmse",
            "strong_edge_rmse", "median_cpu_wall_ms")
    report["means"] = {
        tag: {key: mean(entry["results"][tag][key] for entry in report["sources"]
                        if entry["results"][tag][key] is not None) for key in keys}
        for tag, _, _ in variants
    }
    (destination / "comparison.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    views = [(f"hybrid-{tag}", label) for tag, label in (
        ("original32", "Original 32"), ("retrained32", "Retrained 32"), ("wide64", "FP32 / 64"),
        ("distilled32", "Distilled 32")) if tag in weights]
    for offset in range(0, len(examples), 4):
        comparison_sheet(destination, examples[offset:offset + 4], report["sources"][offset:offset + 4],
                         f"comparison-{1 + offset // 4}", views)
        comparison_sheet(destination, examples[offset:offset + 4], report["sources"][offset:offset + 4],
                         f"dither-{1 + offset // 4}", [
                             ("hybrid-wide64", "FP32 / 64"), ("dither-wide64", "FP32 / 64 + dither")],
                         metric="pooled_seam_rmse")
    print(json.dumps(report["means"], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--bsds-archive", type=Path)
    inputs.add_argument("--clic-root", type=Path)
    parser.add_argument("--retrained", type=Path, required=True)
    parser.add_argument("--wide", type=Path, default=CLIC_WIDE_WEIGHTS)
    parser.add_argument("--distilled", type=Path)
    parser.add_argument("--training-report", type=Path, action="append", required=True)
    args = parser.parse_args()
    weights = dict(original32=DEFAULT_WEIGHTS, retrained32=args.retrained, wide64=args.wide)
    if args.distilled:
        weights["distilled32"] = args.distilled
    if args.clic_root:
        photos = read_clic(clic_split(args.clic_root)[2])
        corpus = dict(name="CLIC 2020 Professional Validation", split="holdout")
    else:
        photos = read_evaluation_photos(args.bsds_archive)
        corpus = dict(name="BSDS500", split="test", mirror_revision=REVISION)
    compare(photos, corpus, args.directory, weights, args.training_report)


if __name__ == "__main__":
    main()
