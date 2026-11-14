"""Compare the photo renderer and pixel-art variants on held-out photos."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean

import numpy as np

from .__main__ import convert
from .evaluate import independent_decode, quality
from .model import CLIC_WIDE_WEIGHTS, PIXEL_ART_WEIGHTS, load_weights
from .photo_corpus import clic_split, read_clic, read_evaluation_photos
from .screen import prepare
from .subject import SubjectDetector


def compare(photos, old_layers, new_layers, detector):
    variants = (
        ("before", False, "hybrid", old_layers),
        ("search", True, "spatial", None),
        ("previous_net", True, "hybrid", old_layers),
        ("after", True, "hybrid", new_layers),
    )
    scenes = []
    for name, image in photos:
        source = prepare(image)
        probability = detector.predict(image) if detector else None
        results = {}
        for label, style, mode, layers in variants:
            screen, preview = convert(source, mode, layers, pixel_art=style, photo_layers=old_layers,
                                      probability=probability, floyd=True, repair=True)
            np.testing.assert_array_equal(independent_decode(screen), preview)
            transitions = sum((np.diff(preview, axis=axis) != 0).any(axis=-1).sum() for axis in (0, 1))
            metrics = quality(source, preview)
            results[label] = dict(pooled_rgb_rmse=metrics["pooled_rgb_rmse"],
                                  pooled_seam_rmse=metrics["pooled_seam_rmse"],
                                  transitions=int(transitions), screen_sha256=sha256(screen).hexdigest())
        scenes.append(dict(source=Path(name).stem, results=results))
    means = {label: {key: mean(scene["results"][label][key] for scene in scenes)
                     for key in ("pooled_rgb_rmse", "pooled_seam_rmse", "transitions")}
             for label, *_ in variants}
    return dict(means=means, scenes=scenes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--bsds-archive", type=Path, required=True)
    parser.add_argument("--clic-root", type=Path, required=True)
    parser.add_argument("--subject-model", type=Path)
    parser.add_argument("--weights", type=Path, default=PIXEL_ART_WEIGHTS)
    args = parser.parse_args()
    paths = [args.bsds_archive, args.weights, CLIC_WIDE_WEIGHTS, args.subject_model]
    if args.report.resolve() in {path.resolve() for path in paths if path is not None}:
        parser.error("the report must use a separate path from the inputs")
    old_layers, new_layers = load_weights(CLIC_WIDE_WEIGHTS), load_weights(args.weights)
    detector = SubjectDetector(args.subject_model) if args.subject_model else None
    groups = {"bsds": read_evaluation_photos(args.bsds_archive),
              "clic": read_clic(clic_split(args.clic_root)[2])}
    results = {name: compare(photos, old_layers, new_layers, detector) for name, photos in groups.items()}
    args.report.write_text(json.dumps(results, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
