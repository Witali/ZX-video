"""Restore narrow dark contours inside saturated objects."""

import numpy as np

from .dither import tiles
from .screen import from_cells, pack, to_cells
from .subject import LUMA, box_mean, screen_pixels


def dark_ridges(light):
    """Find dark lines with lighter pixels on opposing sides."""
    smooth = .55 * light + .45 * box_mean(light, 3)
    height, width = light.shape
    padded = np.pad(smooth, 3, mode="edge")
    response = np.zeros_like(smooth)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        for distance in (2, 3):
            dy_offset, dx_offset = dy * distance, dx * distance
            first = padded[3 - dy_offset:3 - dy_offset + height, 3 - dx_offset:3 - dx_offset + width]
            second = padded[3 + dy_offset:3 + dy_offset + height, 3 + dx_offset:3 + dx_offset + width]
            np.maximum(response, np.minimum(first, second) - smooth, out=response)
    return .7 * response + .3 * np.maximum(box_mean(light, 7) - smooth, 0)


def restore_inner_contours(source, current, probability=None):
    """Move highlights away from supported dark lines without changing their local density."""
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
