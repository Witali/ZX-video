"""Keep highlights, warm shadows, and flattened subject tones readable."""

import numpy as np

from .alignment import frame_errors
from .dark_ramps import quiet_seam_error, safe_ramp_tiles
from .line_art import strong_edge_errors
from .screen import HEIGHT, PALETTE, WIDTH, pack, to_cells
from .smooth import balance_coverage, diffuse_coverage
from .subject import LUMA, box_mean, color_accents, pool4, screen_pixels
from .subject_continuity import connected_pixels


def restore_pale_highlights(source, current):
    """Smooth neighboring white cells whose BRIGHT contrast is absent in the source."""
    screen, preview = current
    rgb = source.astype(np.float32)
    light = rgb @ LUMA
    attrs, bits, _, _ = screen_pixels(screen, preview)
    low = preview.min(axis=-1)
    high = preview.max(axis=-1)
    white = (low >= 205) & (low == high)
    colored = (high > 0) & ~white
    mean = to_cells(light).mean(axis=(2, 3))
    eligible = ((to_cells(white).mean(axis=(2, 3)) >= .75)
                & (to_cells(colored).sum(axis=(2, 3)) <= 2) & (mean >= 152))
    bright = (attrs & 64) != 0
    selected = np.zeros_like(eligible)
    similar_x = (np.abs(np.diff(mean, axis=1)) <= 25) & (bright[:, 1:] != bright[:, :-1])
    similar_y = (np.abs(np.diff(mean, axis=0)) <= 25) & (bright[1:] != bright[:-1])
    for rows, cols in connected_pixels(eligible):
        part = np.zeros_like(eligible)
        part[rows, cols] = True
        if ((part[:, 1:] & part[:, :-1] & similar_x).any()
                or (part[1:] & part[:-1] & similar_y).any()):
            selected |= part
    if not selected.any():
        return current

    # A shared normal white endpoint removes hard BRIGHT switches. A
    # highlight lift avoids peppering the brightest areas with black dots.
    level = (.73 * light + .27 * rgb.max(axis=-1) + 18) / 205
    active = selected.repeat(8, axis=0).repeat(8, axis=1)
    shade = diffuse_coverage(level, active.astype(np.float32), np.ones_like(rgb))
    shade = balance_coverage(level, shade)
    output = np.where(active[..., None], shade[..., None] * 205, preview).astype(np.uint8)
    if quiet_seam_error(rgb, output, selected) >= quiet_seam_error(rgb, preview, selected):
        return current
    ref = pool4(rgb)
    if np.mean((pool4(output) - ref) ** 2) > np.mean((pool4(preview) - ref) ** 2):
        return current
    old_edges, new_edges = strong_edge_errors(rgb, (preview, output))
    if new_edges > old_edges + .5:
        return current
    return pack(np.where(active, shade, bits), np.where(selected, 7, attrs)), output


def restore_warm_shadows(source, current):
    """Recover dark details when black and yellow hide a warm source tone."""
    screen, preview = current
    rgb = source.astype(np.float32)
    red, green, blue = np.moveaxis(rgb, -1, 0)
    light = rgb @ LUMA
    warm = ((red - green >= 13) & (green - blue >= 8) & (red >= 1.27 * green)
            & (red <= 174) & (light >= 27) & (light <= 125))
    attrs, bits, _, _ = screen_pixels(screen, preview)
    count = to_cells(warm).sum(axis=(2, 3))
    missing_light = to_cells((light - preview @ LUMA) * warm).sum(axis=(2, 3))
    needs_tone = (count >= 29) & (missing_light >= 12 * count)
    if not needs_tone.any():
        return current
    yellow = (attrs & 63) == 6
    # A dark warm shape can span cells that the palette search dithered
    # using cool ink or white. Let nearby yellow cells supply the hue
    # where that ink had no matching source detail outside the shape.
    unsupported = np.isin(attrs & 63, (1, 3, 5, 7))
    unrelated = bits & ~warm & ((rgb.max(axis=-1) >= 160) | color_accents(source, preview))
    replaceable = unsupported & ~to_cells(unrelated).any(axis=(2, 3))
    eligible = (yellow | replaceable) & needs_tone
    nearby_yellow = box_mean(yellow, 3) > 0
    cells = np.zeros_like(eligible)
    for rows, cols in connected_pixels(eligible):
        if nearby_yellow[rows, cols].any():
            cells[rows, cols] = True
    if not cells.any():
        return current

    active = cells.repeat(8, axis=0).repeat(8, axis=1) & warm
    replaced = (cells & ~yellow).repeat(8, axis=0).repeat(8, axis=1)
    attrs = np.where(cells, (attrs & 64) | 6, attrs)
    ink = PALETTE[((attrs >> 3) & 8) | (attrs & 7)].repeat(8, axis=0).repeat(8, axis=1)
    # Follow the local folds and small dark features of the source. Stop
    # diffusion where the warm region ends.
    tone = light + .95 * (light - box_mean(light, 5))
    level = .80 * tone / (ink @ LUMA).clip(1)
    dots = diffuse_coverage(level, active.astype(np.float32), np.where(active[..., None], ink, 1))
    output = np.where(active[..., None], dots[..., None] * ink, np.where(replaced[..., None], 0, preview))
    if quiet_seam_error(rgb, output, cells) > quiet_seam_error(rgb, preview, cells):
        return current
    ref = pool4(rgb) @ LUMA
    if np.mean((pool4(output) @ LUMA - ref) ** 2) >= np.mean((pool4(preview) @ LUMA - ref) ** 2):
        return current
    old_edges, new_edges = strong_edge_errors(rgb, (preview, output))
    if new_edges > old_edges + .5:
        return current
    return pack(np.where(active, dots, bits & ~replaced), attrs), output


def restore_subject_tones(source, current, probability):
    """Recover shadow detail where pale dots flattened the subject's midtones."""
    if probability is None or not (probability >= .45).any():
        return current

    screen, preview = current
    rgb = source.astype(np.float32)
    light = rgb @ LUMA
    shown = preview @ LUMA
    attrs, bits, paper, ink = screen_pixels(screen, preview)
    shadow = np.where(((ink @ LUMA) > (paper @ LUMA))[..., None], paper, ink)
    gap = shown - shadow @ LUMA
    pale = preview.min(axis=-1) >= 205

    # Existing dark colors can describe the lost tone if they are neutral
    # or point in the same chroma direction as the source.
    chroma = rgb - rgb.mean(axis=-1, keepdims=True)
    shadow_chroma = shadow - shadow.mean(axis=-1, keepdims=True)
    hue_support = (shadow_chroma * chroma).sum(axis=-1)
    required = np.linalg.norm(shadow_chroma, axis=-1) * np.maximum(12, .56 * np.linalg.norm(chroma, axis=-1))
    active = (pale & (box_mean(pale, 5) >= .48) & (probability >= .45)
              & (hue_support >= required) & (gap >= 45) & (light > 25) & (light < 192))
    # Leave both sides of strong source edges as rendered. In the remaining
    # areas, follow small dark features when deciding where to put the dots.
    horizontal = np.abs(np.diff(rgb, axis=1)).max(axis=-1) >= 76.5
    vertical = np.abs(np.diff(rgb, axis=0)).max(axis=-1) >= 76.5
    active[:, :-1] &= ~horizontal
    active[:, 1:] &= ~horizontal
    active[:-1] &= ~vertical
    active[1:] &= ~vertical
    tone = light + .55 * (light - box_mean(light, 5))
    coverage = np.clip(.9 * (box_mean(shown, 3) - tone - 5) / gap.clip(1), 0, .88) * active
    dots = balance_coverage(coverage, np.zeros_like(active))
    if not dots.any():
        return current

    candidate = np.where(dots[..., None], shadow, preview)
    # An edit must improve both average color and luminance in its tile.
    # Then protect the boundary against either possible decision next door.
    before_error = pool4(preview) - pool4(rgb)
    after_error = pool4(candidate) - pool4(rgb)
    improves = ((np.square(after_error).sum(axis=-1) < np.square(before_error).sum(axis=-1))
                & (np.abs(after_error @ LUMA) < np.abs(before_error @ LUMA)))
    dots &= improves.repeat(4, axis=0).repeat(4, axis=1)
    candidate = np.where(dots[..., None], shadow, preview)
    dots &= safe_ramp_tiles(rgb, preview, candidate)
    if not dots.any():
        return current
    output = np.where(dots[..., None], shadow, preview)
    changed = to_cells(dots).any(axis=(2, 3))
    if quiet_seam_error(rgb, output, changed) > quiet_seam_error(rgb, preview, changed):
        return current
    bounds = (0, 0, WIDTH, HEIGHT)
    if frame_errors(rgb, output, bounds)[0] > frame_errors(rgb, preview, bounds)[0]:
        return current
    return pack(bits ^ dots, attrs), output
