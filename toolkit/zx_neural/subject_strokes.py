"""Place dark strokes on narrow source details near a detected subject."""

import numpy as np

from .alignment import frame_errors
from .dark_ramps import quiet_seam_error, safe_ramp_tiles
from .dither import tiles
from .inner_contours import TRACE_DIRECTIONS, dark_edge_response, dark_ridges
from .line_art import strong_edge_errors
from .objective import COLOR_WEIGHT, edge_weight
from .screen import HEIGHT, WIDTH, from_cells, pack, to_cells
from .subject import LUMA, box_mean, color_accents, pool4, screen_pixels


def stroke_guide(light, shown, probability):
    """Find the dark center of a narrow line and its brighter shoulders."""
    ridge = dark_ridges(light)
    edge = dark_edge_response(light, shown)
    smooth = .55 * light + .45 * box_mean(light, 3)
    near_subject = (probability >= .20) & (box_mean(probability, 7) >= .38)
    local_detail = box_mean(light, 5) - light
    rendered = box_mean(shown, 3)
    trace = near_subject & (rendered > smooth) & ((ridge >= 8) | ((edge >= 17) & (local_detail >= 5)))
    trace &= box_mean(trace, 3) >= 2 / 9
    if not trace.any():
        return np.zeros_like(light)

    # Require a local minimum across a ridge, or a missing transition
    # with enough support along the line to survive the native resolution.
    h, w = light.shape
    padded = np.pad(smooth, 2, mode="edge")
    thin = np.zeros_like(trace)
    for dy, dx in TRACE_DIRECTIONS:
        left, left_near, right_near, right = [
            padded[2 + d * dy:2 + d * dy + h, 2 + d * dx:2 + d * dx + w] for d in (-2, -1, 1, 2)
        ]
        thin |= ((smooth <= left_near + 2) & (smooth <= right_near + 2)
                 & (smooth + 4 <= np.minimum(left, right)))
    trace &= (box_mean(thin & trace, 3) > 0) | (edge >= 18)
    strength = np.maximum(ridge, .55 * edge)
    # A line can already have the right dark dots. In that case recover
    # its lighter side where the source shows a bright lip next to it.
    shoulder = (box_mean(trace, 5) > 0) & (local_detail <= -5) & (rendered < light)
    return np.where(trace, -np.minimum(3.5 * strength, 80), np.where(shoulder, np.minimum(-3.5 * local_detail, 80), 0))


def place_stroke_dots(state, allowed, guide, native, light):
    """Move existing dark dots towards the line without changing the tile mean."""
    fit = native + guide
    gain = fit[None, :] - fit[:, None]
    hits_line = (guide[:, None] < 0) | (guide[None, :] > 0)
    valid = (hits_line & (gain >= 4) & (guide[None, :] >= guide[:, None] + 3)
             & (native[None, :] >= native[:, None] - 35) & (light[None, :] >= light[:, None] + 3))
    for _ in range(3):
        pairs = valid & (state & allowed)[:, None] & (~state & allowed)[None, :]
        if not pairs.any():
            break
        shadow, highlight = np.unravel_index(np.argmax(np.where(pairs, gain, -np.inf)), pairs.shape)
        state[shadow], state[highlight] = False, True


def improves_stroke_render(source, before, after, guide):
    """Keep native color, real edges and individual grid lines from regressing."""
    prior = before - source
    candidate = after - source
    gain = np.sum(((candidate - prior) @ LUMA) * guide)
    if gain <= 0 or np.square(candidate).sum() > np.square(prior).sum():
        return False
    old_edges, new_edges = strong_edge_errors(source, (before, after))
    if new_edges > old_edges:
        return False
    old_seams = new_seams = 0.
    for axis in (0, 1):
        grid = np.s_[7::8, :] if axis == 0 else np.s_[:, 7::8]
        weight = edge_weight(np.diff(source, axis=axis)[grid] / 255)
        old_seams += (np.square(np.diff(prior, axis=axis)[grid]).sum(axis=-1) * weight).sum(dtype=np.float64)
        new_seams += (np.square(np.diff(candidate, axis=axis)[grid]).sum(axis=-1) * weight).sum(dtype=np.float64)
    return new_seams <= old_seams


def restore_subject_strokes(source, current, probability):
    """Retain source-backed dark strokes with the two existing cell colors."""
    if probability is None or not (probability >= .38).any():
        return current
    screen, before = current
    source = source.astype(np.float32)
    light = source @ LUMA
    shown = before @ LUMA
    guide = stroke_guide(light, shown, probability)
    if not guide.any():
        return current

    attrs, bits, paper, ink = screen_pixels(screen, before)
    light_ink = ink @ LUMA > paper @ LUMA
    high = np.where(light_ink[..., None], ink, paper)
    low = np.where(light_ink[..., None], paper, ink)
    direction = high.astype(np.float32) - low
    span = direction @ LUMA
    projection = ((source - low) * (direction * COLOR_WEIGHT)).sum(axis=-1) / (direction ** 2 @ COLOR_WEIGHT).clip(1)
    native = projection * span
    chroma = np.ptp(source, axis=-1)
    accent = (chroma >= 112) & color_accents(source, before)
    # A rendered primary can already match a moderate source color.
    # In that case it should keep its position, even near a ridge.
    dominant = np.max(np.where(before > 0, source, 0), axis=-1)
    matched_primary = (((before > 0).sum(axis=-1) == 1) & (chroma >= 27)
                       & (source.max(axis=-1) - dominant <= 8) & (abs(shown - light) <= 55))
    accent |= matched_primary
    allowed = ((span >= 30) & (probability >= .12) & ~accent & np.any(source != before, axis=-1))

    def quadrants(image):
        return tiles(to_cells(image)).reshape(*attrs.shape, 2, 2, 16)

    def rasterize(dots):
        blocks = dots.reshape(*attrs.shape, 2, 2, 4, 4).swapaxes(3, 4)
        return from_cells(blocks.reshape(*attrs.shape, 8, 8))

    shifted = quadrants(bits == light_ink).copy()
    eligible, shape, fit, levels = map(quadrants, (allowed, guide, native, light))
    active = (eligible & (shape != 0) & ((shape > 0) != shifted)).any(axis=-1)
    for tile in zip(*np.nonzero(active), strict=True):
        place_stroke_dots(shifted[tile], eligible[tile], shape[tile], fit[tile], levels[tile])
    shifted = rasterize(shifted)
    shifted_image = np.where(shifted[..., None], high, low)

    # Use a single additional dark dot only where the tile also needs
    # more shade. Keep the density on quiet attribute borders stable.
    rank = quadrants(np.where((guide < 0) & shifted & allowed, -guide, -1))
    extra = rasterize((rank.argmax(axis=-1, keepdims=True) == np.arange(16)) & (rank > 0))
    trial = np.where(extra[..., None], low, shifted_image)
    reference = pool4(source)
    old_color = pool4(before) - reference
    new_color = pool4(trial) - reference
    better = ((new_color ** 2).sum(axis=-1) < (old_color ** 2).sum(axis=-1)) & (abs(new_color @ LUMA) < abs(old_color @ LUMA))
    extra &= better.repeat(4, axis=0).repeat(4, axis=1) & safe_ramp_tiles(source, shifted_image, trial)
    if extra.any():
        changed = to_cells(extra).any(axis=(2, 3))
        trial = np.where(extra[..., None], low, shifted_image)
        bounds = (0, 0, WIDTH, HEIGHT)
        if (quiet_seam_error(source, trial, changed) <= quiet_seam_error(source, before, changed)
                and frame_errors(source, trial, bounds)[0] <= frame_errors(source, before, bounds)[0]
                and improves_stroke_render(source, before, trial, guide)):
            return pack((shifted & ~extra) == light_ink, attrs), trial
    if np.array_equal(shifted, bits == light_ink) or not improves_stroke_render(source, before, shifted_image, guide):
        return current
    return pack(shifted == light_ink, attrs), shifted_image
