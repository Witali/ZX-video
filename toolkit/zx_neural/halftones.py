"""Restore shading where a saturated source region rendered as a flat color."""

import numpy as np

from .objective import COLOR_WEIGHT
from .screen import PALETTE, from_cells, pack, to_cells
from .smooth import diffuse_coverage
from .subject import LUMA, color_accents, screen_pixels, subject_scores


def restore_halftones(source, current):
    screen, preview = current
    original = to_cells(source).astype(np.float32)
    prior = to_cells(preview)
    accents = to_cells(color_accents(source, preview))
    # Detect flat primary-color areas, and require the source itself to
    # have the same dominant channel and a meaningful range of tones.
    channel = original.argmax(axis=-1)
    old_channel = prior.argmax(axis=-1)
    dominant = (original.max(axis=-1) - np.sort(original, axis=-1)[..., 1] > 38)
    primary = (prior > 0).sum(axis=-1) == 1
    light = original @ LUMA
    attrs, bits, _, _ = screen_pixels(screen, preview)
    attrs, bits = attrs.copy(), to_cells(bits).copy()
    output = prior.copy()
    changed = False
    for component, hue in enumerate((2, 4, 1)):
        region = dominant & (channel == component)
        flat = primary & region & (old_channel == component)
        cells = flat.mean(axis=(2, 3)) >= .48
        base = PALETTE[hue | ((attrs >> 3) & 8)].astype(np.float32)
        count = region.sum(axis=(2, 3)).clip(1)
        light_mean = (light * region).sum(axis=(2, 3)) / count
        light_spread = np.sqrt((((light - light_mean[..., None, None]) ** 2) * region).sum(axis=(2, 3)) / count)
        cells &= (light_mean > base @ LUMA + 18) & (light_spread >= 7)
        if not cells.any():
            continue

        rgb, old, mask = original[cells], prior[cells], region[cells]
        paper = base[cells][:, None, None, :]
        choices = [candidate for candidate in range(1, 8) if candidate != hue and candidate & hue]
        best_cost = np.inf
        for other in choices:
            ink = PALETTE[other | ((attrs[cells] >> 3) & 8)].astype(np.float32)[:, None, None, :]
            delta = ink - paper
            projection = ((rgb - paper) * delta * COLOR_WEIGHT).sum(axis=-1) / (delta ** 2 @ COLOR_WEIGHT)
            level = ((rgb - paper) @ LUMA) / (delta @ LUMA)
            coverage = (.55 * projection + .45 * level).clip(0, 1)
            expected = paper + coverage[..., None] * delta
            cost = np.mean(((expected - rgb) ** 2 @ COLOR_WEIGHT)[mask])
            if cost < best_cost:
                best_cost = cost
                best = other, ink, delta, projection, coverage
        other, ink, delta, projection, coverage = best
        # Map neighboring pixels directly, keeping exact colors wherever
        # possible. Zero diffusion strength outside the source region.
        background_bits = (old == ink).all(axis=-1) | (~(old == paper).all(axis=-1) & (projection > .5))
        fit = np.zeros_like(light, dtype=np.float32)
        fit[cells] = np.where(mask, coverage, background_bits)
        vectors = np.ones_like(original)
        vectors[cells] = delta
        new_bits = to_cells(diffuse_coverage(from_cells(fit), from_cells(region & cells[..., None, None]).astype(np.float32),
                                             from_cells(vectors)))
        new_colors = np.where(new_bits[cells][..., None], ink, paper)
        # Mixed cells can border a different object. Only retain the new
        # pair if its full-cell pooled error improves, including that border.
        old_error = (old - rgb).reshape(-1, 2, 4, 2, 4, 3).mean(axis=(2, 4))
        new_error = (new_colors - rgb).reshape(-1, 2, 4, 2, 4, 3).mean(axis=(2, 4))
        gain = ((old_error ** 2 - new_error ** 2) @ COLOR_WEIGHT).mean(axis=(1, 2))
        lost_accent = accents[cells] & ~mask & np.any(new_colors != old, axis=-1)
        keep = (gain > 16) & ~lost_accent.any(axis=(1, 2))
        if not keep.any():
            continue
        changed = True
        cells[cells] = keep
        bits[cells] = new_bits[cells]
        # Every candidate adds one or two channels, so its hue code is
        # greater than the base hue and can be used directly as ink.
        attrs[cells] = (attrs[cells] & 64) | (hue << 3) | other
        output[cells] = new_colors[keep]

    if not changed:
        return current
    result = from_cells(output)
    # Reject a shading gain bought with too much new 8×8 grid contrast.
    mask = np.zeros(source.shape[:2], dtype=np.float32)
    before = subject_scores(source, preview, mask)["seam_rmse"]
    after = subject_scores(source, result, mask)["seam_rmse"]
    if after - before > min(1.5, .075 * before):
        return current
    return pack(from_cells(bits), attrs), result
