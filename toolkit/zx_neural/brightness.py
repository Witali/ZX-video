"""Suppress artificial BRIGHT steps between solid cells of the same hue."""

import numpy as np

from .objective import COLOR_WEIGHT
from .screen import ATTRIBUTES, COLS, INK, PAPER, PALETTE, ROWS

SMOOTH_RANGE = 32 / 255
SMOOTH_BORDER = 24 / 255
MAX_REGRET = .017


def repair_brightness(source, labels, bits):
    """Unify BRIGHT on connected, smooth solid-color cells within an RGB budget.

    A real RGB discontinuity in the source cuts the component. Mixed cells
    (including dither patterns) retain their actual pixels and attributes.
    """
    filled = bits.all(axis=(2, 3))
    solid = filled | ~bits.any(axis=(2, 3))
    color = np.where(filled, INK[labels], PAPER[labels])
    hue = color & 7
    eligible = solid & (hue != 0) & (np.ptp(source, axis=(2, 3)).max(axis=-1) <= SMOOTH_RANGE)
    horizontal = np.abs(source[:, 1:, :, 0] - source[:, :-1, :, -1]).max(axis=(2, 3))
    vertical = np.abs(source[1:, :, 0] - source[:-1, :, -1]).max(axis=(2, 3))
    horizontal = (horizontal <= SMOOTH_BORDER) & (hue[:, 1:] == hue[:, :-1])
    vertical = (vertical <= SMOOTH_BORDER) & (hue[1:] == hue[:-1])
    visited = ~eligible
    result = ATTRIBUTES[labels].copy()
    bitmap = bits.copy()
    palette = PALETTE.astype(np.float32) / 255
    mean = source.mean(axis=(2, 3))
    # Variance is identical for both solid endpoints and cancels in the
    # per-cell regret and component comparison.
    costs = ((mean[..., None, :] - palette[hue[..., None] + [0, 8]]) ** 2) @ COLOR_WEIGHT
    # Only a component touching an artificial BRIGHT seam needs a search.
    bright = color >> 3
    horizontal_flip = horizontal & eligible[:, 1:] & eligible[:, :-1] & (bright[:, 1:] != bright[:, :-1])
    vertical_flip = vertical & eligible[1:] & eligible[:-1] & (bright[1:] != bright[:-1])
    seeds = np.zeros_like(eligible)
    seeds[:, 1:] |= horizontal_flip
    seeds[1:] |= vertical_flip
    for y, x in zip(*np.nonzero(seeds), strict=True):
        if visited[y, x]:
            continue
        component = [(y, x)]
        visited[y, x] = True
        for cy, cx in component:
            neighbors = (
                (cy, cx - 1, cx > 0 and horizontal[cy, cx - 1]),
                (cy, cx + 1, cx + 1 < COLS and horizontal[cy, cx]),
                (cy - 1, cx, cy > 0 and vertical[cy - 1, cx]),
                (cy + 1, cx, cy + 1 < ROWS and vertical[cy, cx]),
            )
            for ny, nx, joined in neighbors:
                if joined and not visited[ny, nx]:
                    visited[ny, nx] = True
                    component.append((ny, nx))
        rows, cols = zip(*component, strict=True)
        current = color[rows, cols] >> 3
        local = costs[rows, cols]
        original = local[np.arange(len(component)), current]
        allowed = ((local - original[:, None]) <= MAX_REGRET).all(axis=0)
        if not allowed.any():
            continue
        bright = np.where(allowed, local.sum(axis=0), np.inf).argmin()
        change = current != bright
        rows, cols = np.asarray(rows)[change], np.asarray(cols)[change]
        result[rows, cols] = (bright << 6) | hue[rows, cols]
        bitmap[rows, cols] = True
    return result, bitmap
