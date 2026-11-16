"""Prepare sources for the stronger subject contrast rendering mode."""

import numpy as np
from PIL import Image, ImageFilter

from .alignment import frame_errors
from .dark_ramps import false_border_steps, false_seam_count, fit_ramp_coverage, quiet_seam_error, safe_ramp_tiles
from .dither import tiles
from .inner_contours import dark_ridges
from .line_art import strong_edge_errors, thin_edges
from .objective import COLOR_WEIGHT
from .screen import COLS, HEIGHT, PALETTE, ROWS, WIDTH, from_cells, pack, to_cells
from .smooth import balance_coverage, diffuse_coverage
from .subject import LUMA, box_mean, color_accents, pool4, screen_pixels
from .subject_continuity import connected_pixels


def emphasize_subject(source, probability):
    """Separate the figure using source-supported outlines and tone changes."""
    if probability is None or not (probability >= .5).any():
        return source
    rgb = source.astype(np.float32)
    light = rgb @ LUMA
    mask = np.clip((probability - .16) / .64, 0, 1)
    eroded = Image.fromarray(np.rint(mask * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
    boundary = mask - np.asarray(eroded, dtype=np.float32) / 255
    nearby = np.clip(box_mean(mask, 13) * 3, 0, 1) * (1 - mask)
    local = box_mean(light, 5)
    base = box_mean(light, 11)
    outline = np.clip((box_mean(thin_edges(light), 3) - .08) / .25, 0, 1)
    folds = np.clip((dark_ridges(light) - 12) / 24, 0, 1)
    # Follow the outline only where a source edge supports it. At the
    # same time keep shallow shading inside the figure and reduce fine
    # background contrast in the narrow band around it.
    tone = .4 * mask * ((light - base) + .38 * (light - 148))
    tone -= 93 * boundary * outline + 56 * folds * mask
    tone += .2 * nearby * (.55 * local + .45 * base - light)
    chroma = .1 * (nearby + .27 * mask) * np.clip((80 - np.ptp(rgb, axis=-1)) / 60, 0, 1)
    return np.rint(np.clip(rgb + tone[..., None] - chroma[..., None] * (rgb - light[..., None]), 0, 255)).astype(np.uint8)


def protect_dim_details(source, current, probability, render_reference):
    """Recover warm midtones that the stronger rendering crushed into shadow."""
    if probability is None:
        return current
    screen, preview = current
    rgb = source.astype(np.float32)
    red, green, blue = np.moveaxis(rgb, -1, 0)
    light = rgb @ LUMA
    detail = ((red > 1.13 * green) & (green - blue >= 5) & (light >= 32) & (light <= 124)
              & (probability >= .47))
    original = box_mean(light, 3)
    missing = original - box_mean(preview @ LUMA, 3)
    darkened = to_cells(detail & (missing >= 23)).sum(axis=(2, 3)) >= 14
    possible = to_cells(detail).sum(axis=(2, 3)) >= 14
    components = [(y, x) for y, x in connected_pixels(possible) if darkened[y, x].sum() >= 3]
    if not components:
        return current

    ordinary_screen, ordinary = render_reference()
    if ordinary_screen == screen:
        return current
    old_attrs, old_bits, _, _ = screen_pixels(ordinary_screen, ordinary)
    attrs, bits, _, _ = screen_pixels(screen, preview)
    output = preview
    bounds = (0, 0, WIDTH, HEIGHT)
    for y, x in components:
        cells = np.zeros_like(possible)
        cells[y, x] = True
        area = cells.repeat(8, axis=0).repeat(8, axis=1)
        trial = np.where(area[..., None], ordinary, output)
        selected = detail & area
        before = box_mean(output @ LUMA, 3)
        after = box_mean(trial @ LUMA, 3)
        loss = np.square((before - original)[selected]).sum()
        recovered = np.square((after - original)[selected]).sum()
        if recovered >= .93 * loss:
            continue
        if quiet_seam_error(rgb, trial, cells) > quiet_seam_error(rgb, output, cells):
            continue
        old, new = (frame_errors(rgb, image, bounds) for image in (output, trial))
        seam_allowance = .08 if recovered <= .75 * loss else 0.
        if new[0] > old[0] + seam_allowance or new[1] > old[1] or new[2] > old[2]:
            continue
        if false_seam_count(rgb, trial) > false_seam_count(rgb, output):
            continue
        attrs = np.where(cells, old_attrs, attrs)
        bits = np.where(area, old_bits, bits)
        output = trial
    if output is preview:
        return current
    return pack(bits, attrs), output


def shade_bright_whites(source, current):
    """Fit dark-dot density to the original shadows around bright whites."""
    screen, preview = current
    attrs, bits, _, _ = screen_pixels(screen, preview)
    white_is_ink = (attrs & 7) == 7
    grayscale = ((attrs & 63) == 7) | ((attrs & 63) == 56)
    bright_white = grayscale & ((attrs & 64) != 0)
    if not bright_white.any():
        return current
    rgb = source.astype(np.float32)
    light = rgb @ LUMA
    white = (preview == 255).all(axis=-1)
    highlights = (light >= 228) & (rgb.min(axis=-1) >= 202)
    shadows = (light < 211) & white
    eligible = (bright_white & (to_cells(highlights).sum(axis=(2, 3)) >= 12)
                & (to_cells(shadows).sum(axis=(2, 3)) >= 5))
    if not eligible.any():
        return current

    colors = np.full_like(rgb, 255)
    level = light / 255
    output = preview
    pattern = bits.copy()
    target = pool4(rgb)
    for y, x in connected_pixels(eligible):
        cells = np.zeros_like(eligible)
        cells[y, x] = True
        area = cells.repeat(8, axis=0).repeat(8, axis=1)
        fitted = fit_ramp_coverage(level, rgb, output, cells, colors)
        # Preserve the brightest part of the detail. Dark pixels receive
        # the density needed to represent their average luminance.
        fitted = np.where(highlights, np.maximum(fitted, level), fitted)
        halftone = diffuse_coverage(fitted, area.astype(np.float32), colors)
        dots = balance_coverage(fitted, halftone)
        candidate = np.where(area[..., None], (255 * dots[..., None]), output).astype(np.uint8)
        if not safe_ramp_tiles(rgb, output, candidate)[area].all():
            continue
        if quiet_seam_error(rgb, candidate, cells) > quiet_seam_error(rgb, output, cells):
            continue
        if np.square(pool4(candidate) - target).sum() >= np.square(pool4(output) - target).sum():
            continue
        old_edge, new_edge = strong_edge_errors(rgb, (output, candidate))
        if new_edge > old_edge:
            continue
        polarity = white_is_ink.repeat(8, axis=0).repeat(8, axis=1)
        pattern[area] = (dots == polarity)[area]
        output = candidate
    if output is preview:
        return current
    return pack(pattern, attrs), output


def promote_white_details(source, current, probability):
    """Use BRIGHT on source-white details and shade the transition in adjoining cells."""
    if probability is None:
        return current
    screen, preview = current
    attrs, bits, _, _ = screen_pixels(screen, preview)
    rgb = source.astype(np.float32)
    light = rgb @ LUMA
    chroma = np.ptp(rgb, axis=-1)
    pale = (rgb.min(axis=-1) >= 184) & (light >= 211) & (chroma <= 52) & (probability >= .38)
    white = np.zeros_like(pale)
    for y, x in connected_pixels(pale):
        if len(y) >= 100 and np.count_nonzero(light[y, x] >= 236) >= 35:
            white[y, x] = True
    if not white.any():
        return current

    ink, paper = attrs & 7, (attrs >> 3) & 7
    has_white = (ink == 7) | (paper == 7)
    low = np.where(ink == 7, paper, ink)
    count = to_cells(white).sum(axis=(2, 3))
    highlights = to_cells(white & (light >= 229)).sum(axis=(2, 3))
    accent = ((rgb.min(axis=-1) <= .43 * rgb.max(axis=-1)) & (chroma >= 80)
              & color_accents(source, preview))
    accent_cells = to_cells(accent).sum(axis=(2, 3))
    shade = to_cells(rgb.min(axis=-1) >= .46 * rgb.max(axis=-1)).sum(axis=(2, 3)) >= 32
    foreground = to_cells(probability).mean(axis=(2, 3)) >= .28
    strong = np.zeros_like(white)
    for axis in (0, 1):
        along = np.moveaxis(strong, axis, 0)
        edge = np.abs(np.diff(np.moveaxis(rgb, axis, 0), axis=0)).max(axis=-1) >= 76.5
        along[1:] |= edge
        along[:-1] |= edge

    region = has_white & (highlights >= 6)
    # Use the same white endpoint on both sides where real white fabric
    # crosses a cell border. The narrowest layout remains available when
    # the surrounding pairs cannot express a smooth continuation.
    across_x = (white[:, 7:-1:8] & white[:, 8::8]).reshape(ROWS, 8, COLS - 1).sum(axis=1) >= 2
    across_y = (white[7:-1:8] & white[8::8]).reshape(ROWS - 1, COLS, 8).sum(axis=2) >= 2
    bounds = (0, 0, WIDTH, HEIGHT)
    original = frame_errors(rgb, preview, bounds)
    original_steps = false_seam_count(rgb, preview)
    bright_before = ((preview == 255).all(axis=-1) & white).sum()
    for minimum, strength, grow in ((36, 6., True), (38, 7., True), (26, 5., False), (36, 7., False)):
        promote = region & (count >= minimum)
        if grow:
            adjacent = np.zeros_like(promote)
            adjacent[:, 1:] |= promote[:, :-1] & across_x
            adjacent[:, :-1] |= promote[:, 1:] & across_x
            adjacent[1:] |= promote[:-1] & across_y
            adjacent[:-1] |= promote[1:] & across_y
            promote |= adjacent & has_white & (count >= 5)
        if not np.any(promote & ((attrs & 64) == 0)):
            continue
        core = promote.repeat(8, axis=0).repeat(8, axis=1)
        nearby = to_cells(box_mean(core, 11)).mean(axis=(2, 3)) > .04
        cells = promote | (nearby & foreground & has_white)
        affected = cells.repeat(8, axis=0).repeat(8, axis=1)
        neutral = promote & shade & (accent_cells == 0)
        dark = np.where(neutral, 0, low)
        intensity = np.where(promote | ((attrs & 64) != 0), 8, 0)
        lo = PALETTE[dark + intensity].repeat(8, axis=0).repeat(8, axis=1).astype(np.float32)
        hi = PALETTE[7 + intensity].repeat(8, axis=0).repeat(8, axis=1).astype(np.float32)
        span = hi - lo
        luminance = (light - lo @ LUMA) / (span @ LUMA).clip(1)
        color = ((rgb - lo) * (span * COLOR_WEIGHT)).sum(axis=-1) / (span ** 2 @ COLOR_WEIGHT).clip(1)
        level = np.clip(.8 * luminance + .2 * color + .02 * white * ((light - 209) / 48).clip(0, 1), 0, 1)
        level = fit_ramp_coverage(level, rgb, preview, cells, hi, paper=lo, seam_strength=strength).clip(0, 1)
        floyd = diffuse_coverage(level, affected.astype(np.float32), np.where(affected[..., None], span, 1))
        dots = pin_white_edges(
            level, floyd, strong & affected, (preview.min(axis=-1) >= 205) & (light >= 217),
            (preview.max(axis=-1) == 0) & (lo.max(axis=-1) == 0) & (light <= 126),
        )
        dots = correct_white_border_density(rgb, preview, lo, hi, affected, dots, level, accent)
        if dots is None:
            continue
        dots = refine_white_dots(rgb, preview, lo, hi, affected, dots, accent)
        output = np.where(affected[..., None], np.where(dots[..., None], hi, lo), preview).astype(np.uint8)
        if ((output == 255).all(axis=-1) & white).sum() < bright_before + 12:
            continue
        if quiet_seam_error(rgb, output, cells) > quiet_seam_error(rgb, preview, cells):
            continue
        fitted = frame_errors(rgb, output, bounds)
        if fitted[0] > original[0] or fitted[1] >= original[1] or fitted[2] > original[2]:
            continue
        if false_seam_count(rgb, output) > original_steps:
            continue
        promoted = np.where(promote, (dark << 3) | 71, attrs).astype(np.uint8)
        white_is_ink = ((promoted & 7) == 7).repeat(8, axis=0).repeat(8, axis=1)
        return pack(np.where(affected, dots == white_is_ink, bits), promoted), output
    return current


def pin_white_edges(level, floyd, strong, white, black):
    """Put shade dots on the source side of strong edges within each 4×4 count."""
    def split(raster):
        return tiles(to_cells(raster)).reshape(ROWS, COLS, 2, 2, 16)

    locked = strong & (white | black)
    priority = split(np.where(locked, np.where(white, 5., -5.), level + .25 * floyd))
    order = np.argsort(np.argsort(-priority, axis=-1), axis=-1)
    count = np.rint(split(level).sum(axis=-1, keepdims=True))
    low = split(locked & white).sum(axis=-1, keepdims=True)
    high = 16 - split(locked & black).sum(axis=-1, keepdims=True)
    pattern = (order < np.clip(count, low, high)).reshape(ROWS, COLS, 2, 2, 4, 4)
    return from_cells(pattern.swapaxes(3, 4).reshape(ROWS, COLS, 8, 8))


def correct_white_border_density(source, prior, low, high, area, dots, level, accents):
    """Adjust the two densities together where BRIGHT exposes a quiet border."""
    target = pool4(source)
    old = tuple(false_border_steps(target, pool4(prior)))
    output = np.where(area[..., None], np.where(dots[..., None], high, low), prior)
    means = pool4(output)
    ramp = pool4(high - low) / 16
    blocked = ~area | accents

    def new_steps():
        return tuple(found & ~known for known, found in zip(old, false_border_steps(target, means), strict=True))

    remaining = new_steps()
    for _ in range(8):
        count = sum(int(steps.sum()) for steps in remaining)
        if count == 0:
            return dots
        neighbors = set()
        for y, x in np.argwhere(remaining[0]):
            neighbors.update(((2 * y + 1, x), (2 * y + 2, x)))
        for y, x in np.argwhere(remaining[1]):
            neighbors.update(((y, 2 * x + 1), (y, 2 * x + 2)))
        best = None
        for y, x in sorted(neighbors):
            patch = np.s_[4 * y:4 * y + 4, 4 * x:4 * x + 4]
            for direction in (-1, 1):
                eligible = ~blocked[patch] & (dots[patch] == (direction == -1))
                if not eligible.any():
                    continue
                rank = np.where(eligible, direction * level[patch], -np.inf).ravel()
                positions = np.argsort(-rank, kind="stable")[:min(3, int(eligible.sum()))]
                color = means[y, x].copy()
                for amount in range(1, len(positions) + 1):
                    means[y, x] = color + amount * direction * ramp[y, x]
                    steps = sum(int(item.sum()) for item in new_steps())
                    if steps < count:
                        error = np.square(means[y, x] - target[y, x]).sum()
                        score = steps, error, amount, -rank[positions[:amount]].sum()
                        if best is None or score < best[0]:
                            best = score, y, x, positions[:amount], direction
                means[y, x] = color
        if best is None:
            return None
        _, y, x, positions, direction = best
        row, col = np.unravel_index(positions, (4, 4))
        dots[4 * y + row, 4 * x + col] = direction > 0
        means[y, x] += len(positions) * direction * ramp[y, x]
        remaining = new_steps()
    return dots if not any(steps.any() for steps in remaining) else None


def refine_white_dots(source, prior, low, high, active, dots, accents):
    """Keep the shade density and place individual dots along actual source edges."""
    result = dots.copy()
    residual = np.where(active[..., None], np.where(result[..., None], high, low), prior) - source
    positions = list(zip(*np.nonzero(pool4(active) > 0), strict=True))
    for _ in range(2):
        for row, col in positions:
            y, x = 4 * row, 4 * col
            area = np.s_[y:y + 4, x:x + 4]
            state = result[area].ravel()
            mutable = ~accents[area].ravel()
            ink, paper = np.meshgrid(np.flatnonzero(state & mutable), np.flatnonzero(~state & mutable), indexing="ij")
            if not ink.size:
                continue
            variants = np.broadcast_to(state, (ink.size, 16)).copy()
            indices = np.arange(ink.size)
            variants[indices, ink.ravel()] = False
            variants[indices, paper.ravel()] = True
            previous = residual[area]
            prepared = variants.reshape(-1, 4, 4)
            candidate = np.where(prepared[..., None], high[area], low[area]) - source[area]
            scores = .17 * (candidate ** 2 - previous ** 2).sum(axis=(1, 2, 3))
            for axis, origin in enumerate((y, x)):
                reference = np.moveaxis(source[area], axis, 0)
                old = np.moveaxis(previous, axis, 0)
                new = np.moveaxis(candidate, axis + 1, 1)
                important = np.abs(np.diff(reference, axis=0)).max(axis=-1) >= 76.5
                cost = np.diff(new, axis=1) ** 2 - np.diff(old, axis=0) ** 2
                scores += (cost * important[..., None]).sum(axis=(1, 2, 3))
                for pole, neighbor in ((0, origin - 1), (3, origin + 4)):
                    if not 0 <= neighbor < source.shape[axis]:
                        continue
                    across = (neighbor, slice(x, x + 4)) if axis == 0 else (slice(y, y + 4), neighbor)
                    gradient = np.abs(source[across] - reference[pole]).max(axis=-1)
                    old_step = old[pole] - residual[across]
                    new_step = new[:, pole] - residual[across]
                    scores += ((new_step ** 2 - old_step ** 2) * (gradient >= 76.5)[..., None]).sum(axis=(1, 2))
                    if (origin + (4 if pole else 0)) % 8 == 0 and gradient.mean() <= 20:
                        # Four-pixel averages reflect the brightness of this
                        # dithered border better than any individual dot does.
                        scores += .45 * (new_step.mean(axis=1) ** 2 - old_step.mean(axis=0) ** 2).sum(axis=1)
            chosen = int(scores.argmin())
            if scores[chosen] < 0:
                result[area] = prepared[chosen]
                residual[area] = candidate[chosen]
    return result
