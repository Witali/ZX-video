"""Refit the two palettes and all eight tile densities along a residual seam."""

from dataclasses import dataclass

import numpy as np

from .clash import COLORS, QUADRANT_X, QUADRANT_Y, ClashCells
from .dark_ramps import false_border_steps
from .objective import edge_weight
from .screen import ATTRIBUTES, COLS, INK, PAPER, ROWS, from_cells, pack, to_cells
from .subject import pool4, screen_pixels

COUNTS = np.arange(17, dtype=np.intp)
PALETTE_LIMIT = 12
SEAM_WEIGHTS = (.5, 2., 6.)


def seam_runs(target, residual, minimum):
    """Find runs as (tile length, axis, border, first tile, past-last tile)."""
    horizontal, vertical = false_border_steps(target, target + residual)
    for axis, lines in enumerate((horizontal, vertical.T)):
        for border, line in enumerate(lines):
            runs = np.flatnonzero(np.diff(np.r_[False, line, False]))
            for start, end in zip(runs[::2], runs[1::2], strict=True):
                if end - start >= minimum:
                    yield end - start, axis, border, start, end


def seam_pairs(target, residual):
    """Order cell pairs by the length of the visible run on their border."""
    pairs = {}
    for length, axis, border, start, end in seam_runs(target, residual, 2):
        for tile in range(start // 2, (end + 1) // 2):
            pair = ((border, tile), (border + 1, tile)) if axis == 0 else (
                (tile, border), (tile, border + 1))
            pairs[pair] = max(pairs.get(pair, 0), length)
    return sorted(pairs, key=lambda pair: (-pairs[pair], pair))


@dataclass(frozen=True)
class EdgeFit:
    pairs: np.ndarray
    current: np.ndarray
    errors: np.ndarray
    color: np.ndarray
    seam: np.ndarray
    large: np.ndarray
    allowed: np.ndarray
    old_seam: float
    old_large: int


def edge_fit(target, residual, coords, shared, paint, locked, attr):
    """Score a cell's count options against fixed outer neighbors."""
    y, x = coords
    ty, tx = 2 * y + QUADRANT_Y, 2 * x + QUADRANT_X
    desired = target[ty, tx]
    current = residual[ty, tx]
    colors = np.unique(paint[locked], axis=0)
    paper, ink = COLORS[PAPER], COLORS[INK]
    known = ((paper[:, None] == colors).all(axis=-1) | (ink[:, None] == colors).all(axis=-1)).all(axis=-1)
    pairs = np.flatnonzero(known)
    if not len(pairs):
        return None
    paper, ink = paper[pairs], ink[pairs]
    means = paper[:, None, :] + COUNTS[:, None] * (ink - paper)[:, None, :] / 16
    errors = means[:, None] - desired[:, None, :]
    color = np.square(errors).sum(axis=-1)
    pixels = paint.reshape(2, 4, 2, 4, 3).swapaxes(1, 2).reshape(4, 16, 3)
    frozen = locked.reshape(2, 4, 2, 4).swapaxes(1, 2).reshape(4, 16)
    force_ink = ((pixels[None] == ink[:, None, None]).all(axis=-1) & frozen).sum(axis=-1)
    force_paper = ((pixels[None] == paper[:, None, None]).all(axis=-1) & frozen).sum(axis=-1)
    allowed = (COUNTS >= force_ink[..., None]) & (COUNTS <= 16 - force_paper[..., None])
    seam = np.zeros_like(color)
    large = np.zeros_like(allowed, dtype=np.int8)
    old_seam = 0.
    old_large = 0
    shared_axis, inner_tiles = shared
    for axis, (along_y, along_x, limit) in enumerate(((ty, tx, ROWS), (tx, ty, COLS))):
        for tile, along in enumerate(along_y):
            neighbor = along + (1 if along % 2 else -1)
            if not 0 <= neighbor < 2 * limit or (axis == shared_axis and tile in inner_tiles):
                continue
            point = (neighbor, along_x[tile]) if axis == 0 else (along_x[tile], neighbor)
            step = desired[tile] - target[point]
            weight = edge_weight(step / 255)
            diff = errors[:, tile] - residual[point]
            prior = current[tile] - residual[point]
            seam[:, tile] += weight * np.square(diff).sum(axis=-1)
            old_seam += weight * np.square(prior).sum()
            if np.abs(step).max() <= 12:
                severe = np.abs(diff).max(axis=-1) >= 48
                was_severe = np.abs(prior).max() >= 48
                if was_severe:
                    large[:, tile] += severe
                    old_large += 1
                else:
                    allowed[:, tile] &= ~severe
    viable = np.flatnonzero(allowed.any(axis=-1).all(axis=-1))
    if not len(viable):
        return None
    # Preserve distinct endpoints from the previous screen when possible.
    # Rank the others by their independent color and fixed-border fit.
    prior = (attr & 64) | (min(attr & 7, (attr >> 3) & 7) << 3) | max(attr & 7, (attr >> 3) & 7)
    approx = np.where(allowed, color + 2 * seam, np.inf).min(axis=-1).sum(axis=-1)
    approx[ATTRIBUTES[pairs] == prior] = -np.inf
    chosen = viable[np.argsort(approx[viable], kind="stable")[:PALETTE_LIMIT]]
    return EdgeFit(pairs[chosen], current, errors[chosen], color[chosen], seam[chosen], large[chosen],
                   allowed[chosen], old_seam, old_large)


def fit_pair(target, residual, cells, output, locks, attrs):
    """Solve the two shared tile edges for each retained palette combination."""
    (y0, x0), (y1, x1) = cells
    axis = 0 if x0 == x1 else 1
    inner = ((2, 3), (0, 1)) if axis == 0 else ((1, 3), (0, 2))
    left, right = (edge_fit(target, residual, (y, x), (axis, inside), output[y, x], locks[y, x], attrs[y, x])
                   for (y, x), inside in zip(cells, inner, strict=True))
    if left is None or right is None:
        return None
    crosses = []
    before_color = np.square(left.current).sum() + np.square(right.current).sum()
    old_seam = left.old_seam + right.old_seam
    old_large = left.old_large + right.old_large
    old_inner = 0
    for a, b in zip(*inner, strict=True):
        step = (target[2*y0 + QUADRANT_Y[a], 2*x0 + QUADRANT_X[a]]
                - target[2*y1 + QUADRANT_Y[b], 2*x1 + QUADRANT_X[b]])
        w = edge_weight(step / 255)
        gap = left.errors[:, a, None, :, None] - right.errors[None, :, b, None, :]
        best_seam = w * np.square(gap).sum(axis=-1)
        quiet = np.abs(step).max() <= 12
        severe = quiet & (np.abs(gap).max(axis=-1) >= 48)
        old = left.current[a] - right.current[b]
        was_severe = quiet & (np.abs(old).max() >= 48)
        old_seam += w * np.square(old).sum()
        old_inner += int(was_severe)
        available = left.allowed[:, a, None, :, None] & right.allowed[None, :, b, None, :]
        crosses.append((a, b, best_seam, severe, available & (was_severe | ~severe)))
    if not old_inner:
        return None
    old_large += old_inner
    dimensions = (len(left.pairs), len(right.pairs))
    fy, fx = np.indices(dimensions)
    best = None
    for seam_weight in SEAM_WEIGHTS:
        lc = left.color + seam_weight * left.seam + (255 ** 2 * .20) * left.large
        rc = right.color + seam_weight * right.seam + (255 ** 2 * .20) * right.large
        counts_l = np.broadcast_to(np.where(left.allowed, lc, np.inf).argmin(axis=-1)[:, None], (*dimensions, 4)).copy()
        counts_r = np.broadcast_to(np.where(right.allowed, rc, np.inf).argmin(axis=-1)[None], (*dimensions, 4)).copy()
        shared_seam = np.zeros(dimensions)
        shared_large = np.zeros(dimensions, dtype=np.intp)
        legal = np.ones(dimensions, dtype=bool)
        for a, b, pressure, severe, valid in crosses:
            cost = lc[:, a, None, :, None] + rc[None, :, b, None, :] + seam_weight * pressure + (255 ** 2 * .35) * severe
            cost = np.where(valid, cost, np.inf).reshape(*dimensions, 17 ** 2)
            pick = cost.argmin(axis=-1)
            p, q = np.divmod(pick, 17)
            counts_l[..., a], counts_r[..., b] = p, q
            shared_seam += pressure[fy, fx, p, q]
            shared_large += severe[fy, fx, p, q]
            legal &= np.isfinite(cost[fy, fx, pick])
        def selected(l, r):
            return (l[fy[..., None], np.arange(4), counts_l].sum(axis=-1)
                    + r[fx[..., None], np.arange(4), counts_r].sum(axis=-1))

        color = selected(left.color, right.color)
        seam = selected(left.seam, right.seam) + shared_seam
        large = selected(left.large, right.large) + shared_large
        allow = (legal & (shared_large < old_inner) & (large < old_large)
                 & (color <= before_color) & (seam < old_seam))
        value = np.where(allow, (color + 2 * seam) / 255 ** 2 + .20 * large, np.inf)
        i, j = np.unravel_index(value.argmin(), dimensions)
        score = float(value[i, j])
        if np.isfinite(score) and (best is None or score < best[0]):
            best = score, (left.pairs[i], right.pairs[j]), (counts_l[i, j], counts_r[i, j])
    return None if best is None else best[1:]


def reduce_joint_clash(source, current, probability=None):
    """Try whole-cell changes across groups of residual 4×4 steps."""
    screen, preview = current
    geometry = ClashCells(source)
    residual = pool4(preview.astype(np.float32)) - geometry.target
    pairs = seam_pairs(geometry.target, residual)
    if not pairs:
        return current
    attrs, bits, _, _ = screen_pixels(screen, preview)
    attrs = attrs.copy()
    bitmap = to_cells(bits).copy()
    output = to_cells(preview).copy()
    locks = geometry.locks(preview, probability)
    changed = False
    for cells in pairs:
        result = fit_pair(geometry.target, residual, cells, output, locks, attrs)
        if result is None:
            continue
        labels, counts = result
        for (y, x), label, count in zip(cells, labels, counts, strict=True):
            bitmap[y, x], output[y, x] = geometry.fit(
                geometry.source[y, x], output[y, x], locks[y, x], label, count, keep_balanced=True)
            attrs[y, x] = ATTRIBUTES[label]
            block = np.s_[2*y:2*y+2, 2*x:2*x+2]
            residual[block] = pool4(output[y, x].astype(np.float32)) - geometry.target[block]
        changed = True
    return (pack(from_cells(bitmap), attrs), from_cells(output)) if changed else current
