"""Compare two outline palette models on fixed image holdouts."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean

import numpy as np

from .__main__ import convert
from .evaluate import independent_decode, quality
from .line_art import outline_subjects
from .model import CLIC_WIDE_WEIGHTS, OUTLINE_WEIGHTS, PIXEL_ART_WEIGHTS, load_weights, predict
from .objective import Candidates, features
from .photo_corpus import clic_split, read_clic, read_evaluation_photos
from .screen import prepare
from .subject import SubjectDetector
from .texture_corpus import read_textures, texture_splits


def compare(groups, previous, candidate, detector, training_report=None):
    photo_layers = load_weights(CLIC_WIDE_WEIGHTS)
    pixel_layers = load_weights(PIXEL_ART_WEIGHTS)
    layers = {"previous": load_weights(previous), "candidate": load_weights(candidate)}
    trained_on = set()
    if training_report is not None:
        for key in ("source_pixel_sha256", "validation_pixel_sha256"):
            trained_on.update(training_report[key].values())

    results = {}
    for group, sources in groups.items():
        scenes = []
        for name, image in sources:
            if sha256(image.tobytes()).hexdigest() in trained_on:
                raise ValueError(f"{group} holdout overlaps training or validation")
            crop = group in ("dtd", "kylberg")
            source = prepare(image, crop=crop)
            probability = detector.predict(image, crop) if detector else None
            base = convert(source, "hybrid", pixel_layers, pixel_art=True, photo_layers=photo_layers,
                           probability=probability, floyd=True, repair=True, automatic_outline=False)
            inputs = features(source, Candidates(source))
            outputs = {}
            scene = {"source": name}
            for label, weights in layers.items():
                preference = -.003 * np.tanh(predict(inputs, weights))
                screen, preview = outline_subjects(source, base, probability, preference=preference)
                np.testing.assert_array_equal(independent_decode(screen), preview)
                outputs[label] = preview
                metrics = quality(source, preview)
                scene[label] = {key: metrics[key] for key in ("pooled_rgb_rmse", "pooled_seam_rmse")}
                scene[label]["screen_sha256"] = sha256(screen).hexdigest()
                scene[label]["outlined_pixels"] = int(np.any(preview != base[1], axis=-1).sum())
            scene["changed_pixels"] = int(np.any(outputs["previous"] != outputs["candidate"], axis=-1).sum())
            scenes.append(scene)
        results[group] = dict(
            images=len(scenes), changed=sum(scene["changed_pixels"] > 0 for scene in scenes),
            means={label: {key: mean(scene[label][key] for scene in scenes)
                           for key in ("pooled_rgb_rmse", "pooled_seam_rmse", "outlined_pixels")}
                   for label in layers},
            scenes=scenes,
        )
        print(f"{group}: {len(scenes)} images, {results[group]['changed']} changed", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--previous", type=Path, default=OUTLINE_WEIGHTS)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--bsds-archive", type=Path, required=True)
    parser.add_argument("--clic-root", type=Path, required=True)
    parser.add_argument("--texture-root", type=Path, required=True)
    parser.add_argument("--subject-model", type=Path)
    parser.add_argument("--training-report", type=Path)
    args = parser.parse_args()
    inputs = (args.previous, args.candidate, args.bsds_archive, args.subject_model, args.training_report,
              CLIC_WIDE_WEIGHTS, PIXEL_ART_WEIGHTS, OUTLINE_WEIGHTS)
    if args.report.resolve() in {path.resolve() for path in inputs if path is not None}:
        parser.error("the report must use a separate path from the inputs")
    training = json.loads(args.training_report.read_text(encoding="utf8")) if args.training_report else None
    previous_hash = sha256(args.previous.read_bytes()).hexdigest()
    candidate_hash = sha256(args.candidate.read_bytes()).hexdigest()
    if training is not None and training["weights_sha256"] != candidate_hash:
        parser.error("the training report does not match the candidate weights")
    detector = SubjectDetector(args.subject_model) if args.subject_model else None
    groups = {"bsds": read_evaluation_photos(args.bsds_archive), "clic": read_clic(clic_split(args.clic_root)[2])}
    groups.update({name: read_textures(partition[2]) for name, partition in texture_splits(args.texture_root)})
    results = compare(groups, args.previous, args.candidate, detector, training)
    report = dict(previous_sha256=previous_hash, candidate_sha256=candidate_hash, groups=results)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
