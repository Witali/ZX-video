"""Fit connected, low-contrast subject details across ZX attribute cells."""

import numpy as np

from .dither import THRESHOLDS
from .objective import COLOR_WEIGHT
from .screen import ATTRIBUTES, INK, PAPER, PALETTE, from_cells, pack, to_cells
from .subject import (
    LUMA, box_mean, color_accents, narrow_regions, preserves_colors, screen_pixels, subject_scores,
)


def elongated_parts(mask):
    """Find long components with 8-connected native pixels."""
    pending = set(zip(*np.nonzero(mask), strict=True))
    for seed in sorted(pending):
        if seed not in pending:
            continue
        pending.remove(seed)
        component = [seed]
        for y, x in component:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    neighbor = y + dy, x + dx
                    if neighbor in pending:
                        pending.remove(neighbor)
                        component.append(neighbor)
        if len(component) < 48:
            continue
        coords = np.asarray(component)
        variance = np.linalg.eigvalsh(np.cov(coords.T))
        if variance[1] >= 3 * max(variance[0], 1) and np.ptp(coords, axis=0).max() >= 16:
            yield coords.T


def fit_part(source, current, part, cells, edge, sign):
    """Rank legal shared pairs by local RGB fit and the part's own mean tone."""
    _, preview = current
    palette = PALETTE.astype(np.float32)
    paper = palette[PAPER]
    direction = palette[INK] - paper
    axis = direction * COLOR_WEIGHT
    norm = (direction * axis).sum(axis=-1)
    original = to_cells(source)[cells].astype(np.float32)
    prior = to_cells(preview)[cells].astype(np.float32)
    foreground = to_cells(part)[cells]
    outline = to_cells(edge)[cells]
    # Nudge the detail by only 10 levels, plus a 16-level stroke on its
    # inside edge. Retain the source shading throughout the rest of it.
    target = np.where(foreground[..., None], original + sign * (10 + 16 * outline)[..., None],
                      .48 * original + .52 * prior)
    target = target.clip(0, 255)
    coverage = (target @ axis.T - (paper * axis).sum(axis=-1)) / norm
    patterns = coverage > THRESHOLDS[..., None]
    rendered = paper + patterns[..., None] * direction
    residual = rendered - target[..., None, :]
    pooled = residual.reshape(-1, 2, 4, 2, 4, len(ATTRIBUTES), 3).mean(axis=(2, 4))
    fit = (pooled ** 2 @ COLOR_WEIGHT).mean(axis=(0, 1, 2))
    tone = ((residual[foreground].mean(axis=0)) ** 2) @ COLOR_WEIGHT
    chroma = direction - (direction @ LUMA)[:, None]
    grain = (chroma ** 2 @ COLOR_WEIGHT).astype(np.float32)
    ranking = np.argsort(fit + 1.1 * tone + .05 * grain, kind="stable")
    return patterns, rendered, ranking[:3], np.sqrt(grain)


def replace_cells(current, cells, pair, patterns, rendered):
    screen, preview = current
    attrs, bits, _, _ = screen_pixels(screen, preview)
    attrs = attrs.copy()
    attrs[cells] = ATTRIBUTES[pair]
    bitmap = to_cells(bits).copy()
    bitmap[cells] = patterns[..., pair]
    output = to_cells(preview).copy()
    output[cells] = rendered[..., pair, :].astype(np.uint8)
    return pack(from_cells(bitmap), attrs), from_cells(output)


def part_scores(light, source_light, part, outside, normalizer, sign):
    smooth = box_mean(light, 3)
    background = box_mean(light * outside, 15) / normalizer
    contrast = sign * (smooth - background)
    weak_contrast = np.percentile(contrast[part], 20)
    tone_error = np.sqrt(np.mean((smooth[part] - source_light[part]) ** 2))
    return weak_contrast, tone_error


def continue_thin_parts(source, baseline, current, probability, mask):
    """Reduce missing contrast and false color jumps along source-supported details."""
    foreground = probability >= .50
    thin = narrow_regions(foreground)
    if not thin.any():
        return current
    outside = ~foreground
    count = box_mean(outside.astype(np.float32), 15)
    normalizer = np.maximum(count, .01)
    source_light = source @ LUMA
    source_smoothed = box_mean(source_light, 3)
    step = box_mean(source_light, 5) - box_mean(source_light * outside, 15) / normalizer
    inside_edge = box_mean(foreground.astype(np.float32), 3) < .85
    protected = to_cells(color_accents(source, baseline[1])).any(axis=(2, 3))
    starting = subject_scores(source, current[1], mask)
    for sign in (-1, 1):
        supported = thin & (sign * step > 8) & (count >= .12)
        for ys, xs in elongated_parts(supported):
            part = np.zeros_like(thin)
            part[ys, xs] = True
            cells = to_cells(part).any(axis=(2, 3))
            if (cells & protected).any() or cells.sum() > 20:
                continue
            previous = part_scores(current[1] @ LUMA, source_smoothed, part, outside, normalizer, sign)
            patterns, rendered, pairs, grain = fit_part(source, current, part, cells, inside_edge, sign)
            best = current
            lowest = np.inf
            for pair in pairs:
                proposal = replace_cells(current, cells, pair, patterns, rendered)
                contrast, error = part_scores(proposal[1] @ LUMA, source_smoothed, part, outside, normalizer, sign)
                # Prefer a smooth tone over a similarly light mixture of
                # strongly contrasting hues, which can obscure the detail.
                cost = error + .15 * grain[pair]
                if (contrast < max(16, min(previous[0] + 5, 32), .75 * previous[0])
                        or error > previous[1] - 4 or cost >= lowest):
                    continue
                scores = subject_scores(source, proposal[1], mask)
                if (scores["luma_contrast"] >= .90 * starting["luma_contrast"]
                        and scores["seam_rmse"] <= starting["seam_rmse"] + .45
                        and preserves_colors(source, baseline[1], proposal[1], toned_detail=part)):
                    best, lowest = proposal, cost
            current = best
    return current
