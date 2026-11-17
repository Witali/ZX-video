"""Render connected dark gradients without arbitrary changes of ink hue."""

import numpy as np

from .alignment import frame_errors
from .line_art import strong_edge_errors
from .objective import COLOR_WEIGHT
from .screen import HEIGHT, PALETTE, WIDTH, from_cells, pack, to_cells
from .smooth import balance_coverage, diffuse_coverage
from .subject import LUMA, box_mean, pool4, screen_pixels
from .subject_continuity import connected_pixels

HUE_BITS = np.array([2, 4, 1])


def false_seam_count(source, preview):
    """Count large spurious steps along 8×8 borders with quiet source color."""
    return sum(int(border.sum()) for border in false_border_steps(pool4(source), pool4(preview)))


def false_border_steps(target, preview):
    """Locate large spurious 8×8 border steps in 4×4 RGB averages."""
    return (strength >= 48 for strength in false_border_contrast(target, preview))


def false_border_contrast(target, preview):
    """Measure RGB contrast added at a border where the source is quiet."""
    residual = preview - target
    for axis, borders in ((0, np.s_[1::2, :]), (1, np.s_[:, 1::2])):
        quiet = np.abs(np.diff(target, axis=axis)[borders]).max(axis=-1) <= 12
        error = np.abs(np.diff(residual, axis=axis)[borders]).max(axis=-1)
        yield np.where(quiet, error, 0)


def false_contrast_cost(level):
    """A doubled false step incurs sixteen times the contrast penalty."""
    return np.square(np.square(np.asarray(level, dtype=np.float32)) / 48)


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


def fit_ramp_coverage(level, rgb, preview, cells, ink, *, paper=None, seam_strength=1.):
    """Fit each 4×4 mean to the ramp and to the render outside its boundary."""
    initial = pool4(level.clip(0, 1))
    coverage = initial.copy()
    axis = pool4(ink if paper is None else ink - paper)
    base = 0. if paper is None else pool4(paper)
    source = pool4(rgb)
    fixed = pool4(preview)
    active = cells.repeat(2, axis=0).repeat(2, axis=1)
    source_x = np.abs(np.diff(source, axis=1)).max(axis=-1)
    source_y = np.abs(np.diff(source, axis=0)).max(axis=-1)
    # Real source edges limit how much adjacent targets can influence one
    # another. Give additional weight to quiet seams against fixed cells.
    reach = 24 if paper is None else 35
    horizontal = np.exp(-(source_x / reach) ** 2)
    vertical = np.exp(-(source_y / reach) ** 2)
    if paper is None:
        horizontal *= np.where(active[:, 1:] & active[:, :-1], .9, 1.8)
        vertical *= np.where(active[1:] & active[:-1], .9, 1.8)
    else:
        horizontal *= seam_strength
        vertical *= seam_strength
    neighbor_weight = np.zeros_like(initial)
    neighbor_weight[:, 1:] += horizontal
    neighbor_weight[:, :-1] += horizontal
    neighbor_weight[1:] += vertical
    neighbor_weight[:-1] += vertical
    residual = base + axis * initial[..., None] - source
    norm = (axis ** 2 @ COLOR_WEIGHT).clip(1) * (1 + neighbor_weight)
    for _ in range(8 if paper is None else 18):
        error = np.where(active[..., None], base + axis * coverage[..., None], fixed) - source
        neighbors = np.zeros_like(error)
        neighbors[:, 1:] += horizontal[..., None] * error[:, :-1]
        neighbors[:, :-1] += horizontal[..., None] * error[:, 1:]
        neighbors[1:] += vertical[..., None] * error[:-1]
        neighbors[:-1] += vertical[..., None] * error[1:]
        projected = ((neighbors - neighbor_weight[..., None] * residual) * axis) @ COLOR_WEIGHT
        coverage = .4 * coverage + .6 * (initial + projected / norm).clip(0, 1)
    return level + (coverage - initial).repeat(4, axis=0).repeat(4, axis=1)


def safe_ramp_tiles(source, before, after):
    """Protect quiet 8×8 borders when substituting individual 4×4 dot counts."""
    target, previous, candidate = map(pool4, (source, before, after))
    safe = np.ones(target.shape[:2], dtype=bool)
    for axis in (0, 1):
        ref, old, new = (np.moveaxis(values, axis, 0) for values in (target, previous, candidate))
        step = ref[2::2] - ref[1:-1:2]
        old_error = np.abs(old[2::2] - old[1:-1:2] - step).max(axis=-1)
        quiet = np.abs(step).max(axis=-1) <= 12

        def sharper(head, tail):
            error = np.abs(tail - head - step).max(axis=-1)
            return quiet & (error >= 48) & ((old_error < 48) | (error > old_error))

        # Check both edits together and either edit alone so the result
        # stays safe if a neighbor is kept for a different border.
        both = sharper(new[1:-1:2], new[2::2])
        keep = np.moveaxis(safe, axis, 0)
        keep[1:-1:2] &= ~(both | sharper(new[1:-1:2], old[2::2]))
        keep[2::2] &= ~(both | sharper(old[1:-1:2], new[2::2]))
    return safe.repeat(4, axis=0).repeat(4, axis=1)


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

    if new_seam < .97 * old_seam:
        # Keep the accepted ink and brightness ramp. Correct local dot
        # counts only where Floyd's dot placement adds visible steps.
        balanced = balance_coverage(level, shaded)
        candidate = np.where(active[..., None], np.where(balanced[..., None], ink, 0), preview).astype(np.uint8)
        safe = safe_ramp_tiles(rgb, result, candidate)
        balanced = np.where(safe, balanced, shaded)
        candidate = np.where(safe[..., None], candidate, result)
        candidate_seam = quiet_seam_error(rgb, candidate, cells)
        if candidate_seam < new_seam - max(.25, .06 * new_seam):
            target = pool4(rgb)
            color_error = np.mean((pool4(result) - target) ** 2)
            balanced_error = np.mean((pool4(candidate) - target) ** 2)
            if balanced_error <= color_error:
                candidate_edges, = strong_edge_errors(rgb, (candidate,))
                if candidate_edges <= min(new_edges + .1, old_edges + .5):
                    shaded, result = balanced, candidate

    attrs, bits, _, _ = screen_pixels(screen, preview)
    return pack(np.where(active, shaded, bits), np.where(cells, selected, attrs)), result


def restore_neutral_shadow_blocks(source, current):
    """Remove compact runs of unsupported saturated ink from muted shadows."""
    screen, preview = current
    attrs, bits, _, _ = screen_pixels(screen, preview)
    paper, ink = (attrs >> 3) & 7, attrs & 7
    hue = np.where(paper == 0, ink, paper)
    colored = ((ink == 0) | (paper == 0)) & (hue > 0) & (hue < 7)
    if not colored.any():
        return current

    rgb = source.astype(np.float32)
    light = rgb @ LUMA
    peak = rgb.max(axis=-1)
    # Leave padding black while still fitting the visible part of a cell
    # that straddles the edge of a letterboxed photo.
    content = peak > 14
    count = to_cells(content).sum(axis=(2, 3))
    divisor = count.clip(1)
    mean = to_cells(rgb * content[..., None]).sum(axis=(2, 3)) / divisor[..., None]
    tone = mean @ LUMA
    offset = np.abs(light - tone.repeat(8, axis=0).repeat(8, axis=1))
    uniform = to_cells((offset <= 17) | ~content).mean(axis=(2, 3)) >= .77
    chroma = to_cells(np.ptp(rgb, axis=-1) * content).sum(axis=(2, 3)) / divisor
    muted = ((count >= 26) & (tone >= 30) & (tone <= 110) & (chroma <= 32) & uniform
             & (to_cells(peak).max(axis=(2, 3)) <= 146))
    ink_axis = PALETTE[hue].astype(np.float32) / 205
    density = (mean * ink_axis).sum(axis=-1) / (ink_axis ** 2).sum(axis=-1).clip(1)
    color_fit = np.mean((mean - density[..., None] * ink_axis) ** 2, axis=-1)
    neutral_fit = np.mean((mean - mean.mean(axis=-1, keepdims=True)) ** 2, axis=-1)
    tint = np.ptp(to_cells(preview).mean(axis=(2, 3)), axis=-1)
    seeds = muted & colored & (tint >= 10) & (color_fit > neutral_fit + 70)
    if not seeds.any():
        return current

    # Keep a small region together so its new halftone can follow the
    # original brightness across adjacent cells.
    shades = (.75 * light + .25 * rgb.mean(axis=-1)) / 205
    neutral = np.full_like(rgb, 205)
    bounds = (0, 0, WIDTH, HEIGHT)
    output = preview
    for y, x in connected_pixels(seeds):
        if len(y) < 3:
            continue
        cells = np.zeros_like(seeds)
        cells[y, x] = True
        area = cells.repeat(8, axis=0).repeat(8, axis=1)
        fitted = np.where(content, fit_ramp_coverage(shades, rgb, output, cells, neutral), 0)
        dots = balance_coverage(fitted, diffuse_coverage(fitted, area.astype(np.float32), neutral))
        trial = np.where(area[..., None], (205 * dots)[..., None], output).astype(np.uint8)
        if quiet_seam_error(rgb, trial, cells) >= quiet_seam_error(rgb, output, cells) - .5:
            continue
        old, new = (frame_errors(rgb, image, bounds) for image in (output, trial))
        if new[0] > old[0] or new[1] >= old[1] or new[2] > old[2] + .15:
            continue
        if false_seam_count(rgb, trial) > false_seam_count(rgb, output):
            continue
        attrs = np.where(cells, 7, attrs)
        bits = np.where(area, dots, bits)
        output = trial
    if output is preview:
        return current
    return pack(bits, attrs), output
