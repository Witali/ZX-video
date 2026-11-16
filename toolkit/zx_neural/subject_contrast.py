"""Prepare sources for the stronger subject contrast rendering mode."""

import numpy as np
from PIL import Image, ImageFilter

from .dark_ramps import fit_ramp_coverage, quiet_seam_error, safe_ramp_tiles
from .inner_contours import dark_ridges
from .line_art import strong_edge_errors, thin_edges
from .screen import pack, to_cells
from .smooth import balance_coverage, diffuse_coverage
from .subject import LUMA, box_mean, pool4, screen_pixels
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
