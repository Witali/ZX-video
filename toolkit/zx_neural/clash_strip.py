"""Fit a band of neighboring palettes when separate cell pairs are insufficient."""

import numpy as np

from .clash import COLORS, QUADRANT_X, QUADRANT_Y, ClashCells
from .clash_joint import COUNTS, PALETTE_LIMIT, seam_runs
from .dark_ramps import false_border_steps
from .objective import edge_weight
from .screen import ATTRIBUTES, COLS, INK, PAPER, ROWS, from_cells, pack, to_cells
from .subject import pool4, screen_pixels

RAMP = COLORS[PAPER, None] + (COUNTS.astype(np.float32) / 16)[None, :, None] * (
    COLORS[INK, None] - COLORS[PAPER, None])


def strip_score(target, residual, original):
    masks = tuple(false_border_steps(target, target + residual))
    added = sum(int((b & ~a).sum()) for a, b in zip(original, masks, strict=True))
    severe = sum(int(mask.sum()) for mask in masks)
    color = np.square(residual).sum(dtype=np.float64)
    seam = 0.
    for axis in (0, 1):
        fit, source = (np.moveaxis(values, axis, 0) for values in (residual, target))
        weight = edge_weight((source[1:-1:2] - source[2::2]) / 255)
        seam += (np.square(fit[1:-1:2] - fit[2::2]).sum(axis=-1) * weight).sum(dtype=np.float64)
    return added, severe, color, seam


def fit_strip(geometry, prior, coords, painted, locked, incumbent, original_masks, original_score):
    """Select legal palettes for a strip using alternating non-touching cells."""
    y, x = coords
    ty, tx = 2 * y[:, None] + QUADRANT_Y, 2 * x[:, None] + QUADRANT_X
    ny = np.clip(ty + np.where(QUADRANT_Y, 1, -1), 0, 2 * ROWS - 1)
    nx = np.clip(tx + np.where(QUADRANT_X, 1, -1), 0, 2 * COLS - 1)
    target = geometry.target
    source = target[ty, tx]
    steps = np.stack((source - target[ny, tx], source - target[ty, nx]), axis=-2)
    weight = edge_weight(steps / 255) * np.stack((ny != ty, nx != tx), axis=-1)
    old = prior[ty, tx]
    old_step = np.stack((old - prior[ny, tx], old - prior[ty, nx]), axis=-2)
    protected_join = ((np.abs(steps).max(axis=-1) <= 12)
                      & (np.abs(old_step).max(axis=-1) < 48) & (weight > 0))
    pen = np.where(protected_join, np.float32(3e5), np.float32(4e4))

    pixels = painted.reshape(-1, 2, 4, 2, 4, 3).swapaxes(2, 3).reshape(-1, 4, 16, 3)
    frozen = locked.reshape(-1, 2, 4, 2, 4).swapaxes(2, 3).reshape(-1, 4, 16)
    paper = (pixels[:, None] == COLORS[PAPER][None, :, None, None]).all(axis=-1) & frozen[:, None]
    ink = (pixels[:, None] == COLORS[INK][None, :, None, None]).all(axis=-1) & frozen[:, None]
    legal = (paper | ink | ~frozen[:, None]).all(axis=(2, 3))
    legal = (legal[..., None, None] & (COUNTS >= ink.sum(axis=-1)[..., None])
             & (COUNTS <= 16 - paper.sum(axis=-1)[..., None]))
    residual = RAMP[None, :, None] - source[:, None, :, None]
    color = np.square(residual).sum(axis=-1)
    old_paper, old_ink = (incumbent >> 3) & 7, incumbent & 7
    canonical = ((incumbent & 64) | (np.minimum(old_paper, old_ink) << 3) | np.maximum(old_paper, old_ink))
    cheap = np.where(legal, color, np.inf).min(axis=-1).sum(axis=-1)
    cheap[canonical[:, None] == ATTRIBUTES] = -1
    shortlist = np.argsort(cheap, axis=-1, kind="stable")[:, :PALETTE_LIMIT]
    cells = np.arange(len(y))[:, None]
    residual, color, legal = (array[cells, shortlist] for array in (residual, color, legal))
    parity = (y + x) % 2
    phases = [np.flatnonzero(parity == phase) for phase in (0, 1)]
    for seam_weight in (1., 3., 8.):
        result = prior.copy()
        labels = np.empty(len(y), dtype=np.intp)
        dots = np.empty((len(y), 4), dtype=np.intp)
        for _ in range(8):
            previous = result[ty, tx]
            for phase in phases:
                vertical = residual[phase] - result[ny[phase], tx[phase]][:, None, :, None]
                horizontal = residual[phase] - result[ty[phase], nx[phase]][:, None, :, None]
                cost = color[phase].copy()
                for axis, difference in enumerate((vertical, horizontal)):
                    cost += (seam_weight * np.square(difference).sum(axis=-1) * weight[phase, None, :, None, axis]
                             + pen[phase, None, :, None, axis] * (np.abs(difference).max(axis=-1) >= 48))
                cost = np.where(legal[phase], cost, np.inf)
                labels[phase] = cost.min(axis=-1).sum(axis=-1).argmin(axis=-1)
                dots[phase] = cost[np.arange(len(phase)), labels[phase]].argmin(axis=-1)
                result[ty[phase], tx[phase]] = residual[phase[:, None], labels[phase, None], np.arange(4), dots[phase]]
            if np.array_equal(result[ty, tx], previous):
                break
        added, severe, rgb, seam = strip_score(target, result, original_masks)
        if not added and severe < original_score[1] and rgb <= original_score[2] and seam < original_score[3]:
            return shortlist[cells[:, 0], labels], dots
    return None


def reduce_clash_strips(source, current, probability=None):
    """Search around the longest quiet seams left after the two-cell pass."""
    screen, preview = current
    geometry = ClashCells(source)
    target = geometry.target
    pooled = pool4(preview.astype(np.float32))
    prior = pooled - target
    runs = sorted(seam_runs(target, prior, 4), reverse=True)[:2]
    if not runs:
        return current
    attrs, bits, _, _ = screen_pixels(screen, preview)
    painted = to_cells(preview)
    locks = geometry.locks(preview, probability)
    cell_source = target.reshape(ROWS, 2, COLS, 2, 3).mean(axis=(1, 3))
    original_masks = tuple(false_border_steps(target, pooled))
    original_score = strip_score(target, prior, original_masks)
    for _, axis, border, start, stop in runs:
        oriented = target if axis == 0 else target.transpose(1, 0, 2)
        center = oriented[2 * border + 1:2 * border + 3, start:stop].mean(axis=(0, 1))
        cells = np.zeros(attrs.shape, dtype=bool)
        area = cells if axis == 0 else cells.T
        area[max(0, border - 3):border + 5, max(0, start // 2 - 3):(stop + 1) // 2 + 3] = True
        cells &= np.abs(cell_source - center).max(axis=-1) <= 42
        y, x = np.nonzero(cells)
        if len(y) < 4:
            continue
        result = fit_strip(geometry, prior, (y, x), painted[y, x], locks[y, x], attrs[y, x],
                           original_masks, original_score)
        if result is None:
            continue
        output = painted.copy()
        bitmap = to_cells(bits).copy()
        new_attrs = attrs.copy()
        labels, dots = result
        for cy, cx, label, count in zip(y, x, labels, dots, strict=True):
            bitmap[cy, cx], output[cy, cx] = geometry.fit(
                geometry.source[cy, cx], painted[cy, cx], locks[cy, cx], label, count, keep_balanced=True)
            new_attrs[cy, cx] = ATTRIBUTES[label]
        return pack(from_cells(bitmap), new_attrs), from_cells(output)
    return current
