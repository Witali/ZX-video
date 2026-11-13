"""Convert PNG/JPEG and other Pillow-readable images to ZX Spectrum .scr."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from .brightness import repair_brightness
from .dither import DitherCandidates
from .model import DEFAULT_WEIGHTS, load_weights, predict
from .objective import Candidates, REFINE_SWEEPS, SHORTLIST, TEMPERATURE, features
from .screen import ATTRIBUTES, PALETTE, from_cells, pack, prepare


def choose(rgb, candidates, mode, layers=None):
    baseline = candidates.unary.argmin(axis=-1)
    scores = -candidates.regret / TEMPERATURE
    if mode in ("neural", "hybrid"):
        scores += predict(features(rgb, candidates), layers)
        if mode == "neural":
            return np.where(candidates.allowed, scores, -np.inf).argmax(axis=-1)
    if mode in ("hybrid", "spatial"):
        # The baseline always stays available. Rank the remaining candidates
        # before the expensive eight-pixel boundary comparisons.
        scores = np.where(candidates.allowed, scores, -np.inf)
        np.put_along_axis(scores, baseline[..., None], np.inf, axis=-1)
        choices = np.argsort(-scores, axis=-1, kind="stable")[..., :SHORTLIST]
        return candidates.refine(baseline, REFINE_SWEEPS, choices=choices)
    if mode == "spatial-full":
        return candidates.refine(baseline, REFINE_SWEEPS)
    return baseline


def render(candidates, labels, *, dither=False, repair=False):
    source = candidates.source
    if dither:
        candidates = DitherCandidates(candidates)
        labels = candidates.select(labels)
    bits = candidates.bitmap(labels)
    attrs = ATTRIBUTES[labels]
    if repair:
        attrs, bits = repair_brightness(source, labels, bits)
    screen = pack(from_cells(bits), attrs)
    bright = (attrs >> 3) & 8
    paper = (((attrs >> 3) & 7) | bright)[..., None, None]
    ink = ((attrs & 7) | bright)[..., None, None]
    return screen, from_cells(PALETTE[np.where(bits, ink, paper)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("screen", type=Path, help="output 6912-byte .scr")
    parser.add_argument("--preview", type=Path, help="optional native RGB preview PNG")
    parser.add_argument("--crop", action="store_true", help="center crop to fill the 4:3 screen")
    parser.add_argument("--dither", action="store_true", help="apply ordered dithering in smooth regions")
    parser.add_argument("--mode", choices=("spatial", "hybrid", "neural", "spatial-full", "baseline"),
                        default="spatial")
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    args = parser.parse_args()
    use_model = args.mode in ("neural", "hybrid")
    outputs = [path.resolve() for path in (args.screen, args.preview) if path is not None]
    inputs = {args.image.resolve()}
    if use_model:
        inputs.add(args.weights.resolve())
    if inputs.intersection(outputs) or len(set(outputs)) != len(outputs):
        parser.error("outputs must use separate paths from each other and from the inputs")
    try:
        layers = load_weights(args.weights) if use_model else None
        with Image.open(args.image) as image:
            rgb = prepare(image, args.crop)
        candidates = Candidates(rgb)
        repair = args.dither or args.mode in ("spatial", "spatial-full", "hybrid")
        screen, preview = render(candidates, choose(rgb, candidates, args.mode, layers),
                                 dither=args.dither, repair=repair)
        args.screen.write_bytes(screen)
        if args.preview:
            Image.fromarray(preview).save(args.preview, format="PNG")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"zx_neural: {error}\n")


if __name__ == "__main__":
    main()
