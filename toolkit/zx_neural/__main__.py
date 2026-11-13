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
from .smooth import SmoothCandidates, floyd_bitmap


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


def render(candidates, labels, *, dither=False, smooth=False, floyd=False, repair=False):
    source = candidates.source
    if dither or smooth or floyd:
        strategy = SmoothCandidates if smooth or floyd else DitherCandidates
        candidates = strategy(candidates)
        labels = candidates.select(labels)
    bits = floyd_bitmap(candidates, labels) if floyd else candidates.bitmap(labels)
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
    gradients = parser.add_mutually_exclusive_group()
    gradients.add_argument("--solid", action="store_true", help="use the previous rendering without dithering")
    gradients.add_argument("--dither", action="store_true", help="apply ordered dithering in smooth regions")
    gradients.add_argument("--smooth", action="store_true", help="optimize gradient dithering across cells")
    gradients.add_argument("--floyd", action="store_true", help="diffuse color error across cell boundaries (default)")
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
        floyd = args.floyd or not (args.solid or args.dither or args.smooth)
        repair = args.dither or args.smooth or floyd or args.mode in ("spatial", "spatial-full", "hybrid")
        screen, preview = render(candidates, choose(rgb, candidates, args.mode, layers),
                                 dither=args.dither, smooth=args.smooth, floyd=floyd, repair=repair)
        args.screen.write_bytes(screen)
        if args.preview:
            Image.fromarray(preview).save(args.preview, format="PNG")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"zx_neural: {error}\n")


if __name__ == "__main__":
    main()
