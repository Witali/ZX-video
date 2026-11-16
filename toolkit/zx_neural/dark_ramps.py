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


def mute_cool_shadows(rgb, current, selected, hue):
    """Try neutral ink for pale cool ramps that the Spectrum makes too saturated."""
    screen, preview = current
    resolved = np.zeros_like(selected, dtype=bool)
    source_cells = to_cells(rgb)
    hue_cells = to_cells(hue)
    for color in (1, 5):
        for rows, cols in connected_pixels(selected == color):
            own = hue_cells[rows, cols] == color
            region = source_cells[rows, cols][own]
            if region.size and region.min(axis=-1).sum() >= .35 * region.max(axis=-1).sum():
                resolved[rows, cols] = True
    if not resolved.any():
        return current

    active = resolved.repeat(8, axis=0).repeat(8, axis=1)
    # Neutral ink raises the missing channel levels. Use sparse dots to
    # retain contrast at the edge of the ramp.
    level = .65 * (rgb @ LUMA) / 205
    proposed = diffuse_coverage(level, active.astype(np.float32), np.ones_like(rgb))
    proposed = balance_coverage(level, proposed)
    result = np.where(active[..., None], proposed[..., None] * 205, preview).astype(np.uint8)
    if quiet_seam_error(rgb, result, resolved) >= quiet_seam_error(rgb, preview, resolved):
        return current
    target = pool4(rgb)
    region = resolved.repeat(2, axis=0).repeat(2, axis=1)
    old_error = np.mean((pool4(preview)[region] - target[region]) ** 2)
    new_error = np.mean((pool4(result)[region] - target[region]) ** 2)
    if new_error >= .9 * old_error:
        return current
    old_edges, new_edges = strong_edge_errors(rgb, (preview, result))
    if new_edges > old_edges + 2.5:
        return current

    attrs, bits, _, _ = screen_pixels(screen, preview)
    return pack(np.where(active, proposed, bits), np.where(resolved, 7, attrs)), result


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
        return current
    old_edges, new_edges = strong_edge_errors(rgb, (preview, result))
    if new_edges > old_edges + .5:
        return current

    attrs, bits, _, _ = screen_pixels(screen, preview)
    ramp_screen = pack(np.where(active, shaded, bits), np.where(cells, selected, attrs))
    return mute_cool_shadows(rgb, (ramp_screen, result), selected, hue)
