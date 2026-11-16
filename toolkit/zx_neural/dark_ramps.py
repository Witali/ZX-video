"""Render connected dark gradients without arbitrary changes of ink hue."""

import numpy as np

from .line_art import strong_edge_errors
from .objective import COLOR_WEIGHT
from .screen import PALETTE, from_cells, pack, to_cells
from .smooth import balance_coverage, diffuse_coverage
from .subject import LUMA, box_mean, pool4, screen_pixels
from .subject_continuity import connected_pixels

HUE_BITS = np.array([2, 4, 1])


def quiet_seam_error(source, preview, changed):
    """Measure 8×8 steps where the source changes gradually across a border."""
    reference = pool4(source)
    output = pool4(preview)
    error = 0.
    count = 0
    adjacent = (changed[1:] | changed[:-1], changed[:, 1:] | changed[:, :-1])
    for axis, seams in ((0, np.s_[1::2, :]), (1, np.s_[:, 1::2])):
        original_step = np.diff(reference, axis=axis)[seams]
        output_step = np.diff(output, axis=axis)[seams]
        affected = adjacent[axis].repeat(2, axis=1 - axis)
        quiet = affected & (np.abs(original_step).max(axis=-1) <= 20)
        error += np.square((output_step - original_step)[quiet]).sum(dtype=np.float64)
        count += int(quiet.sum())
    return float(np.sqrt(error / max(1, 3 * count)))


def fit_ramp_coverage(level, rgb, preview, cells, ink):
    """Fit each 4×4 mean to the ramp and to the render outside its boundary."""
    initial = pool4(level.clip(0, 1))
    coverage = initial.copy()
    axis = pool4(ink)
    source = pool4(rgb)
    fixed = pool4(preview)
    active = cells.repeat(2, axis=0).repeat(2, axis=1)
    source_x = np.abs(np.diff(source, axis=1)).max(axis=-1)
    source_y = np.abs(np.diff(source, axis=0)).max(axis=-1)
    # Real source edges limit how much adjacent targets can influence one
    # another. Give additional weight to quiet seams against fixed cells.
    horizontal = np.exp(-(source_x / 24) ** 2) * np.where(active[:, 1:] & active[:, :-1], .9, 1.8)
    vertical = np.exp(-(source_y / 24) ** 2) * np.where(active[1:] & active[:-1], .9, 1.8)
    neighbor_weight = np.zeros_like(initial)
    neighbor_weight[:, 1:] += horizontal
    neighbor_weight[:, :-1] += horizontal
    neighbor_weight[1:] += vertical
    neighbor_weight[:-1] += vertical
    residual = axis * initial[..., None] - source
    norm = (axis ** 2 @ COLOR_WEIGHT).clip(1) * (1 + neighbor_weight)
    for _ in range(8):
        error = np.where(active[..., None], axis * coverage[..., None], fixed) - source
        neighbors = np.zeros_like(error)
        neighbors[:, 1:] += horizontal[..., None] * error[:, :-1]
        neighbors[:, :-1] += horizontal[..., None] * error[:, 1:]
        neighbors[1:] += vertical[..., None] * error[:-1]
        neighbors[:-1] += vertical[..., None] * error[1:]
        projected = ((neighbors - neighbor_weight[..., None] * residual) * axis) @ COLOR_WEIGHT
        coverage = .4 * coverage + .6 * (initial + projected / norm).clip(0, 1)
    return level + (coverage - initial).repeat(4, axis=0).repeat(4, axis=1)


def restore_dark_ramps(source, current):
    """Keep a common black/ink pair across a smooth, similarly tinted shadow."""
    screen, preview = current
    rgb = source.astype(np.float32)
    peak = rgb.max(axis=-1)
    floor = rgb.min(axis=-1)
    spread = peak - floor
    light = rgb @ LUMA
    dark = (peak >= 23) & (peak <= 156) & (light <= 118)
    if not dark.any():
        return current

    # Classify the source hue relative to its own brightness range. A sky
    # can retain the same hue as its intensity rises toward the horizon.
    hue = (rgb - floor[..., None] >= .67 * spread[..., None]) @ HUE_BITS
    hue = np.where(spread >= 11, hue, 7)
    local = np.stack([box_mean(channel, 3) for channel in np.moveaxis(rgb, -1, 0)], axis=-1)
    fine_detail = box_mean(np.max(np.abs(rgb - local), axis=-1), 3)
    allowed = ((to_cells(fine_detail <= 4).mean(axis=(2, 3)) >= .25)
               & (to_cells(peak).max(axis=(2, 3)) <= 167))
    if not allowed.any():
        return current

    old_hue = to_cells((preview > 0) @ HUE_BITS)
    selected = np.zeros(allowed.shape, dtype=np.uint8)
    for color in range(1, 8):
        matching = to_cells(dark & (hue == color))
        eligible = allowed & (matching.mean(axis=(2, 3)) >= .58)
        mismatched = matching & (old_hue != 0) & (old_hue != color)
        visible = mismatched.mean(axis=(2, 3)) >= .13
        for rows, cols in connected_pixels(eligible):
            size = len(rows)
            if size >= 12 and np.count_nonzero(visible[rows, cols]) >= max(4, .09 * size):
                selected[rows, cols] = color
    if not selected.any():
        return current

    # Normal-intensity ink gives smaller changes per dot than BRIGHT 1.
    # Fit the source to the ink axis, reducing density so saturated dots
    # do not dominate the shadows. Damp off-hue dark detail toward black.
    cells = selected != 0
    color = selected.repeat(8, axis=0).repeat(8, axis=1)
    active = color != 0
    ink = PALETTE[color].astype(np.float32)
    axis = ink * COLOR_WEIGHT
    level = (rgb * axis).sum(axis=-1) / (ink * axis).sum(axis=-1).clip(1)
    level -= .27 * light / 205
    shadow = np.clip((peak - 21) / 24, 0, 1)
    level *= np.where(hue == color, 1, shadow)
    directions = np.where(active[..., None], ink, 1)
    shaded = diffuse_coverage(level, active.astype(np.float32), directions)
    result = np.where(active[..., None], np.where(shaded[..., None], ink, 0), preview).astype(np.uint8)
    old_seam = quiet_seam_error(rgb, preview, cells)
    new_seam = quiet_seam_error(rgb, result, cells)
    if new_seam >= .97 * old_seam:
        # A uniform ink can remove a false hue boundary and still leave a
        # density step against nearby cells whose attributes must stay put.
        fitted = fit_ramp_coverage(level, rgb, preview, cells, ink)
        shaded = balance_coverage(fitted, diffuse_coverage(fitted, active.astype(np.float32), directions))
        result = np.where(active[..., None], np.where(shaded[..., None], ink, 0), preview).astype(np.uint8)
        if quiet_seam_error(rgb, result, cells) >= .90 * old_seam:
            return current
        target = pool4(rgb)
        initial_error = np.mean((pool4(preview) - target) ** 2)
        if np.mean((pool4(result) - target) ** 2) > 1.06 * initial_error:
            return current
    old_edges, new_edges = strong_edge_errors(rgb, (preview, result))
    if new_edges > old_edges + .5:
        return current

    attrs, bits, _, _ = screen_pixels(screen, preview)
    return pack(np.where(active, shaded, bits), np.where(cells, selected, attrs)), result
