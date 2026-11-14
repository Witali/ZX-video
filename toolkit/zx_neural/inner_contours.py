"""Restore narrow dark contours inside saturated objects."""

import numpy as np

from .dither import tiles
from .screen import from_cells, pack, to_cells
from .subject import LUMA, box_mean, screen_pixels

TRACE_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


def dark_ridges(light):
    """Find dark lines with lighter pixels on opposing sides."""
    smooth = .55 * light + .45 * box_mean(light, 3)
    height, width = light.shape
    padded = np.pad(smooth, 3, mode="edge")
    response = np.zeros_like(smooth)
    for dy, dx in TRACE_DIRECTIONS:
        for distance in (2, 3):
            dy_offset, dx_offset = dy * distance, dx * distance
            first = padded[3 - dy_offset:3 - dy_offset + height, 3 - dx_offset:3 - dx_offset + width]
            second = padded[3 + dy_offset:3 + dy_offset + height, 3 + dx_offset:3 + dx_offset + width]
            np.maximum(response, np.minimum(first, second) - smooth, out=response)
    return .7 * response + .3 * np.maximum(box_mean(light, 7) - smooth, 0)


def dark_edge_response(tone, rendered):
    """Find the darker lip of a sharp transition in four orientations."""
    smooth = .55 * tone + .45 * box_mean(tone, 3)
    height, width = tone.shape
    padded = np.pad(smooth, 2, mode="edge")
    preview = np.pad(box_mean(rendered, 3), 2, mode="edge")

    def offset(values, y, x):
        return values[2 + y:2 + y + height, 2 + x:2 + x + width]

    response = np.zeros_like(smooth)
    for dy, dx in TRACE_DIRECTIONS + tuple((-y, -x) for y, x in TRACE_DIRECTIONS):
        forward = offset(padded, dy, dx)
        slope = forward - offset(padded, -dy, -dx)
        neighboring_slopes = np.maximum(smooth - offset(padded, -2 * dy, -2 * dx),
                                        offset(padded, 2 * dy, 2 * dx) - smooth)
        peak = (forward - smooth > 2.5) & (slope > neighboring_slopes)
        # The outline is a fallback for a transition that did not survive
        # quantization. Measure the tone on each side after averaging dots.
        rendered_slope = offset(preview, dy, dx) - offset(preview, -dy, -dx)
        weak = rendered_slope < .8 * slope
        np.maximum(response, np.where(peak & weak, slope, 0), out=response)
    return response


def restore_inner_contours(source, current, probability=None):
    """Keep narrow shadows and separate neighboring parts of saturated subjects."""
    current = restore_ridges(source, current, probability)
    return trace_dark_edges(source, current, probability)


def restore_ridges(source, current, probability):
    screen, preview = current
    light = source @ LUMA
    ridges = dark_ridges(light)
    strong = ridges >= 10
    if not strong.any():
        return current

    ordered = np.sort(source, axis=-1).astype(np.int16)
    saturated = ordered[..., 2] - ordered[..., 1] > 30
    hue = source.argmax(axis=-1)
    interior = np.zeros_like(strong)
    for channel in range(3):
        region = saturated & (hue == channel)
        interior |= region & (box_mean(region.astype(np.float32), 5) >= .6)
    if probability is not None:
        interior &= probability >= .5
    contour = strong & interior & (box_mean(strong.astype(np.float32), 3) >= .22)
    if not contour.any():
        return current

    attrs, bits, paper, ink = screen_pixels(screen, preview)
    paper_light, ink_light = paper @ LUMA, ink @ LUMA
    # A matching lower endpoint preserves the local hue and keeps this
    # pass away from contours already using a neutral or black shadow.
    light_ink = ink_light > paper_light
    darker = np.where(light_ink[..., None], paper, ink)
    dark_sorted = np.sort(darker, axis=-1).astype(np.int16)
    same_hue = (darker.argmax(axis=-1) == hue) & (dark_sorted[..., 2] > dark_sorted[..., 1])
    interior &= same_hue & (abs(ink_light - paper_light) >= 27) & np.any(source != preview, axis=-1)
    # If even the darker endpoint is too bright for the source, there is
    # no useful shadow to place here and swapping would just shift accents.
    contour &= interior & (light >= np.minimum(paper_light, ink_light) + 4)
    high = bits == light_ink
    # Keep the light/dark balance in each 4×4 tile. Move a highlight off
    # a dark contour only when it has a brighter same-hue destination.
    high_tiles = tiles(to_cells(high)).copy()
    contour_tiles = tiles(to_cells(contour))
    interior_tiles = tiles(to_cells(interior))
    light_tiles = tiles(to_cells(light))
    level = tiles(to_cells(light - 2.5 * ridges * contour))
    active = (high_tiles & contour_tiles).any(axis=(4, 5))
    changed = False
    for cell in zip(*np.nonzero(active), strict=True):
        state = high_tiles[cell].reshape(-1)
        line = contour_tiles[cell].reshape(-1)
        values = level[cell].reshape(-1)
        darken = np.flatnonzero(state & line)
        brighten = np.flatnonzero(~state & ~line & interior_tiles[cell].reshape(-1))
        count = min(len(darken), len(brighten))
        darken = darken[np.argsort(values[darken], kind="stable")[:count]]
        brighten = brighten[np.argsort(-values[brighten], kind="stable")[:count]]
        native = light_tiles[cell].reshape(-1)
        gain = (values[brighten] - values[darken] >= 8) & (native[brighten] >= native[darken] + 1)
        state[darken[gain]], state[brighten[gain]] = False, True
        changed |= gain.any()
    if not changed:
        return current
    high = from_cells(high_tiles.swapaxes(3, 4).reshape(*attrs.shape, 8, 8))
    bits = high == light_ink
    return pack(bits, attrs), np.where(bits[..., None], ink, paper)


def trace_dark_edges(source, current, probability):
    screen, preview = current
    attrs, bits, paper, ink = screen_pixels(screen, preview)
    light = source @ LUMA
    ordered = np.sort(source, axis=-1).astype(np.int16)
    saturation = ordered[..., 2] - ordered[..., 1]
    response = dark_edge_response(light + .33 * saturation, preview @ LUMA)
    if not np.any(response >= 14):
        return current

    paper_light, ink_light = paper @ LUMA, ink @ LUMA
    light_ink = ink_light > paper_light
    darker = np.where(light_ink[..., None], paper, ink)
    lighter = np.where(light_ink[..., None], ink, paper)
    primary_shadow = (darker > 0).sum(axis=-1) == 1
    black_pair = (darker == 0).all(axis=-1) & ((lighter > 0).sum(axis=-1) == 1)
    rendered_hue = np.where(primary_shadow, darker.argmax(axis=-1), lighter.argmax(axis=-1))
    source_hue = source.argmax(axis=-1)
    same_hue = source_hue == rendered_hue

    color_support = np.zeros_like(light)
    for channel in range(3):
        saturated = (source_hue == channel) & (saturation >= 36)
        local = box_mean(saturated, 5)
        color_support = np.where(rendered_hue == channel, local, color_support)
    nearby = color_support >= .4
    inside = same_hue & (saturation >= 36) & (color_support >= .56)
    if probability is not None:
        nearby &= box_mean(probability, 5) >= .4
        inside &= probability >= .42
    at_edge = nearby & (response >= 17)
    at_edge &= box_mean(at_edge, 3) >= .22
    usable = np.any(source != preview, axis=-1)
    low, high = np.minimum(paper_light, ink_light), np.maximum(paper_light, ink_light)
    dark_line = at_edge & usable & same_hue & (saturation >= 13) & primary_shadow
    dark_line &= (high - low >= 25) & (light >= low + np.maximum(4, .12 * (high - low)))
    dark_line &= (preview == lighter).all(axis=-1)
    donor = inside & usable & primary_shadow & ~at_edge
    donor &= light >= low + np.maximum(24, .33 * (high - low))

    # Use black sparingly where it is already one endpoint. The small
    # budget prevents a change to a broad shadow or a solid tile.
    black_edge = nearby & black_pair & usable & (response >= 14) & (ordered[..., 2] < 155)
    black_edge &= (light < np.minimum(78, high + 32)) & (box_mean(black_edge, 3) >= .22)
    black_edge &= light <= .5 * high + 47
    state = tiles(to_cells(bits == light_ink)).copy(order="C")
    lines = tiles(to_cells(dark_line))
    donors = tiles(to_cells(donor))
    black = tiles(to_cells(black_edge))
    strength = tiles(to_cells(response))
    source_light = tiles(to_cells(light))
    black_neighbors = tiles(to_cells(box_mean((preview == 0).all(axis=-1), 3)))
    active = (state & (lines | black)).any(axis=(4, 5))
    for tile in zip(*np.nonzero(active), strict=True):
        high_bits = state[tile].reshape(-1)
        levels = source_light[tile].reshape(-1)
        scores = strength[tile].reshape(-1) - .45 * levels
        shadows = np.flatnonzero(high_bits & black[tile].reshape(-1))
        if shadows.size:
            # Avoid peppering a broad solid-color object. New black pixels
            # should extend a small existing break or a stronger source edge.
            neighbors = black_neighbors[tile].reshape(-1)
            shadows = shadows[(neighbors[shadows] >= 1 / 9) | (scores[shadows] >= 12)]
            high_bits[shadows[np.argsort(-scores[shadows], kind="stable")[:2]]] = False
            continue

        darken = np.flatnonzero(high_bits & lines[tile].reshape(-1))
        brighten = np.flatnonzero(~high_bits & donors[tile].reshape(-1))
        pairs = min(darken.size, brighten.size)
        darken = darken[np.argsort(-scores[darken], kind="stable")[:pairs]]
        brighten = brighten[np.argsort(-levels[brighten], kind="stable")[:pairs]]
        improves = levels[brighten] >= levels[darken] + 3
        high_bits[darken[improves]], high_bits[brighten[improves]] = False, True

    high_bits = from_cells(state.swapaxes(3, 4).reshape(*attrs.shape, 8, 8))
    new_bits = high_bits == light_ink
    if np.array_equal(bits, new_bits):
        return current
    return pack(new_bits, attrs), np.where(new_bits[..., None], ink, paper)
