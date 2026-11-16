"""Recover faint source edges along a detected subject's silhouette."""

import numpy as np

from .alignment import frame_errors
from .dark_ramps import quiet_seam_error, safe_ramp_tiles
from .dither import tiles
from .inner_contours import TRACE_DIRECTIONS
from .objective import COLOR_WEIGHT
from .screen import HEIGHT, WIDTH, from_cells, pack, to_cells
from .subject import LUMA, box_mean, color_accents, pool4, screen_pixels

DIRECTIONS = TRACE_DIRECTIONS + tuple((-y, -x) for y, x in TRACE_DIRECTIONS)


def silhouette_edges(rgb, preview, probability, direction):
    """Locate a weak signed RGB transition along the mask's outward normal."""
    h, w = probability.shape
    p = box_mean(probability, 3)
    light = rgb @ LUMA
    light = .55 * light + .45 * box_mean(light, 3)
    rendered = box_mean(preview @ LUMA, 3)
    smooth = np.stack([box_mean(channel, 3) for channel in np.moveaxis(rgb, -1, 0)], axis=-1)
    chroma = direction - direction.mean(axis=-1, keepdims=True)
    chroma /= np.linalg.norm(chroma, axis=-1, keepdims=True).clip(1)

    def offset(values):
        padded = np.pad(values, ((2, 2), (2, 2)) + ((0, 0),) * (values.ndim - 2), mode="edge")
        return lambda y, x: padded[2 + y:2 + y + h, 2 + x:2 + x + w]

    mask, tone, shown, color = map(offset, (p, light, rendered, smooth))
    near = (probability >= .30) & (p < .94)
    merit = np.zeros_like(light)
    bias = np.zeros_like(light)
    normals = np.zeros(p.shape, dtype=np.intp)
    for normal, (dy, dx) in enumerate(DIRECTIONS):
        outside = mask(2 * dy, 2 * dx)
        inside = mask(-2 * dy, -2 * dx)
        across = inside - outside
        follows_mask = near & (inside > .53) & (outside < .53) & (across >= .18)
        step = tone(-dy, -dx) - tone(2 * dy, 2 * dx)
        tint = (color(-dy, -dx) - color(2 * dy, 2 * dx)) * chroma
        step += .25 * tint.sum(axis=-1)
        sign = np.sign(step)
        missing = sign * (shown(-dy, -dx) - shown(2 * dy, 2 * dx)) < .95 * abs(step)
        # Demand a source slope at the pixel so mask boundaries alone
        # cannot add a line in a flat region or cross a real edge.
        local = sign * (light - tone(dy, dx))
        slope = sign * (tone(-dy, -dx) - tone(dy, dx))
        supported = ((abs(step) >= 9) & (abs(step) <= 68)
                     & (slope >= .35 * abs(step)) & (local >= -3))
        strength = np.where(follows_mask & missing & supported, across * abs(step), 0)
        bias = np.where(strength > merit, sign * np.minimum(2.3 * strength, 64), bias)
        normals = np.where(strength > merit, normal, normals)
        np.maximum(merit, strength, out=merit)
    return np.where(box_mean(merit > 0, 3) >= 2 / 9, bias, 0), normals


def improves_silhouette(rgb, before, after, marked, normals):
    """Compare the same source-supported transitions before and after an edit."""
    y, x = np.nonzero(marked)
    dy, dx = np.asarray(DIRECTIONS)[normals[y, x]].T
    h, w = marked.shape
    inside = (np.clip(y - dy, 0, h - 1), np.clip(x - dx, 0, w - 1))
    outside = (np.clip(y + 2 * dy, 0, h - 1), np.clip(x + 2 * dx, 0, w - 1))
    levels = (box_mean(image @ LUMA, 3) for image in (rgb, before, after))
    reference, old, new = (tone[inside] - tone[outside] for tone in levels)
    return (np.square(new - reference).sum() < np.square(old - reference).sum()
            and np.square(after - rgb).sum() <= np.square(before - rgb).sum())


def restore_weak_subject_edges(source, current, probability):
    """Move legal shade pixels towards the original silhouette, preserving strong edges."""
    if probability is None or not (probability >= .53).any():
        return current
    screen, preview = current
    attrs, bits, paper, ink = screen_pixels(screen, preview)
    light_ink = (ink @ LUMA) > (paper @ LUMA)
    shade = np.where(light_ink[..., None], paper, ink)
    lit = np.where(light_ink[..., None], ink, paper)
    direction = lit.astype(np.float32) - shade
    rgb = source.astype(np.float32)
    bias, normals = silhouette_edges(rgb, preview, probability, direction)
    if not bias.any():
        return current

    span = direction @ LUMA
    normal = direction * COLOR_WEIGHT
    projection = ((rgb - shade) * normal).sum(axis=-1) / (direction * normal).sum(axis=-1).clip(1)
    native = projection * span
    # Keep the rendered primary when it matches the dominant source
    # channel, including tinted pixels where another channel is close.
    primary = (((preview > 0).sum(axis=-1) == 1) & (source.argmax(axis=-1) == preview.argmax(axis=-1))
               & (np.ptp(rgb, axis=-1) >= 32))
    usable = ((probability >= .12) & (span >= 25) & np.any(source != preview, axis=-1)
              & ~primary & ~color_accents(source, preview))
    for axis in (0, 1):
        locked = np.moveaxis(usable, axis, 0)
        strong = np.abs(np.diff(np.moveaxis(rgb, axis, 0), axis=0)).max(axis=-1) >= 76.5
        locked[1:] &= ~strong
        locked[:-1] &= ~strong

    def quadrants(raster):
        return tiles(to_cells(raster)).reshape(*attrs.shape, 2, 2, 16)

    def rasterize(quadrants):
        parts = quadrants.reshape(*attrs.shape, 2, 2, 4, 4)
        return from_cells(parts.swapaxes(3, 4).reshape(*attrs.shape, 8, 8))

    state = quadrants(bits == light_ink).copy()
    eligible = quadrants(usable)
    edges = quadrants(bias)
    levels = quadrants(native)
    active = (eligible & (edges != 0) & (state != (edges > 0))).any(axis=-1)
    for tile in zip(*np.nonzero(active), strict=True):
        swap_edge_dots(state[tile], eligible[tile], edges[tile], levels[tile])
    swapped = rasterize(state) == light_ink
    shifted = np.where(swapped[..., None], ink, paper)

    # If no nearby dot suits the line, let one additional pixel carry
    # the edge in a tile whose average also gets closer to the source.
    improve = (bias != 0) & (swapped != ((bias > 0) == light_ink)) & usable
    rank = quadrants(np.where(improve, abs(bias), -1))
    strokes = (rank.argmax(axis=-1, keepdims=True) == np.arange(16)) & (rank > 0)
    strokes = rasterize(strokes)
    amended = swapped ^ strokes
    candidate = np.where(amended[..., None], ink, paper)
    ref = pool4(rgb)
    before, after = pool4(preview) - ref, pool4(candidate) - ref
    better = ((after ** 2).sum(axis=-1) < (before ** 2).sum(axis=-1)) & (abs(after @ LUMA) < abs(before @ LUMA))
    safe = better.repeat(4, axis=0).repeat(4, axis=1) & safe_ramp_tiles(rgb, shifted, candidate)
    amended = np.where(safe, amended, swapped)
    result = np.where(amended[..., None], ink, paper)
    changed = to_cells(amended != swapped).any(axis=(2, 3))
    bounds = (0, 0, WIDTH, HEIGHT)
    if (changed.any() and quiet_seam_error(rgb, result, changed) <= quiet_seam_error(rgb, shifted, changed)
            and frame_errors(rgb, result, bounds)[0] <= frame_errors(rgb, shifted, bounds)[0]
            and improves_silhouette(rgb, preview, result, bias != 0, normals)):
        return pack(amended, attrs), result
    if not np.array_equal(swapped, bits) and improves_silhouette(rgb, preview, shifted, bias != 0, normals):
        return pack(swapped, attrs), shifted
    return current


def swap_edge_dots(state, allowed, bias, native):
    """Shift shade within a 4×4 tile without changing its mean color."""
    tuned = native + bias
    difference = tuned[None, :] - tuned[:, None]
    source_fit = native[None, :] >= native[:, None] - 12
    on_edge = (bias[:, None] < 0) | (bias[None, :] > 0)
    worth_moving = source_fit & on_edge & (difference >= 6)
    for _ in range(3):
        pairs = worth_moving & (state & allowed)[:, None] & (~state & allowed)[None, :]
        if not pairs.any():
            break
        shadow, highlight = np.unravel_index(np.argmax(np.where(pairs, difference, -np.inf)), pairs.shape)
        state[shadow], state[highlight] = False, True
