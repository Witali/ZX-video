"""Favor readable shapes and quiet color ramps in the pixel-art renderer."""

import numpy as np

from .objective import COLOR_WEIGHT, TARGET_TEMPERATURE
from .screen import COLS, ROWS, pack, to_cells
from .smooth import SmoothCandidates
from .subject import box_mean, color_accents, pool4, screen_pixels

TILE_Y = np.array([0, 0, 1, 1])
TILE_X = np.array([0, 1, 0, 1])
WINDOW_Y, WINDOW_X = np.indices((4, 4)).reshape(2, -1) - 1
POOL_KERNEL = ((abs(WINDOW_Y[:, None] - TILE_Y) <= 1)
               & (abs(WINDOW_X[:, None] - TILE_X) <= 1)).astype(np.float32) / 9
PATTERNS = ((np.arange(16)[:, None] >> np.arange(4)) & 1).astype(np.float32)
POOLED_PATTERNS = PATTERNS @ POOL_KERNEL.T


def mean_rgb(rgb, size):
    return np.stack([box_mean(channel, size) for channel in rgb.transpose(2, 0, 1)], axis=-1)


class PixelArtCandidates(SmoothCandidates):
    """Charge more for pairs whose endpoints create chromatic grain."""

    chroma_grain_weight = .32

    def training_target(self, original):
        """Teach the network to rank legal pairs against joint row/column search."""
        initial = original.unary.argmin(axis=-1)
        labels = self.select(initial)
        score = np.where(original.allowed, self.contextual_cost(labels, average_edges=True), np.inf)
        minimum = score.min(axis=-1, keepdims=True)
        probabilities = np.exp(-(score - minimum) / TARGET_TEMPERATURE)
        opportunity = np.take_along_axis(score, initial[..., None], axis=-1)[..., 0] - minimum[..., 0]
        importance = 1 + 3 * np.minimum(opportunity / .04, 1)
        return probabilities / probabilities.sum(axis=-1, keepdims=True), importance


def preserve_photo_details(source, photo, styled, probability):
    """Keep subject details and smooth gradients from the photograph render."""
    old_screen, old = photo
    new_screen, new = styled
    accents = color_accents(source, old)
    lock = accents & (old != new).any(axis=-1)
    if probability is not None:
        foreground = probability >= .5
        lock |= box_mean(foreground.astype(np.float32), 5) >= .12
    cells = to_cells(lock).any(axis=(2, 3))
    # A local mean follows shallow ramps. Measure the remaining source
    # texture to protect gradients whose fine diffusion would otherwise
    # acquire visible clusters or bands. Lock both palette and bitmap.
    residual = source - mean_rgb(source, 5)
    texture = box_mean(residual ** 2 @ COLOR_WEIGHT, 7)
    cells |= (to_cells(texture) <= 3 ** 2).mean(axis=(2, 3)) >= .65
    # Reject large local color errors on the background as well. Compare
    # pooled colors to ignore shifts in the positions of individual dots.
    target = pool4(source)
    old_cost = (pool4(old) - target) ** 2 @ COLOR_WEIGHT
    new_cost = (pool4(new) - target) ** 2 @ COLOR_WEIGHT
    cells |= (new_cost - old_cost > 30 ** 2).reshape(ROWS, 2, COLS, 2).any(axis=(1, 3))
    old_attrs, old_bits, _, _ = screen_pixels(old_screen, old)
    new_attrs, new_bits, _, _ = screen_pixels(new_screen, new)
    pixels = cells.repeat(8, axis=0).repeat(8, axis=1)
    attrs = np.where(cells, old_attrs, new_attrs)
    bits = np.where(pixels, old_bits, new_bits)
    return (pack(bits, attrs), np.where(pixels[..., None], old, new)), pixels | accents


def refine_texture(source, current, locked):
    """Fit unlocked 2×2 patterns to source detail while keeping their mean colors."""
    screen, preview = current
    attrs, bits, paper, ink = screen_pixels(screen, preview)
    target = source.astype(np.float32)
    locked = locked | (source == preview).all(axis=-1)
    # Keep both sides of strong source edges in the current render.
    horizontal = np.abs(np.diff(target, axis=1)).max(axis=-1) >= 76.5
    vertical = np.abs(np.diff(target, axis=0)).max(axis=-1) >= 76.5
    locked[:, :-1] |= horizontal
    locked[:, 1:] |= horizontal
    locked[:-1] |= vertical
    locked[1:] |= vertical

    result = preview.copy()
    directions = ink.astype(np.float32) - paper
    height, width = bits.shape
    tiles = []
    for dy, dx in ((0, 0), (2, 2), (0, 2), (2, 0)):
        rows, cols = np.meshgrid(np.arange(4 + dy, height - 3, 4),
                                 np.arange(4 + dx, width - 3, 4), indexing="ij")
        y, x = rows.ravel(), cols.ravel()
        pixels = (y[:, None] + TILE_Y, x[:, None] + TILE_X)
        count = bits[pixels].sum(axis=-1)
        active = ~locked[pixels].all(axis=-1) & (count > 0) & (count < 4)
        y, x = y[active], x[active]
        if y.size:
            tiles.append((y, x))
    if not tiles:
        return current

    for _ in range(2):
        for y, x in tiles:
            pixels = (y[:, None] + TILE_Y, x[:, None] + TILE_X)
            window = (y[:, None] + WINDOW_Y, x[:, None] + WINDOW_X)
            weights = directions[y, x] * COLOR_WEIGHT
            norm = (directions[y, x] * weights).sum(axis=-1)
            state = bits[pixels].astype(np.float32)
            delta = PATTERNS - state[:, None, :]
            legal = (delta.sum(axis=-1) == 0) & ((delta == 0) | ~locked[pixels][:, None]).all(axis=-1)

            # Each phase has disjoint 4×4 windows of affected 3×3 averages.
            # Reject added error in those averages, then use the native
            # pixel error to favor fine details among the remaining patterns.
            residual = result - target
            pooled = (mean_rgb(residual, 3)[window] * weights[:, None]).sum(axis=-1)
            shift = POOLED_PATTERNS - (state @ POOL_KERNEL.T)[:, None, :]
            pooled_cost = (shift * (2 * pooled[:, None] + shift * norm[:, None, None])).sum(axis=-1)
            native = (residual[pixels] * weights[:, None]).sum(axis=-1)
            native_cost = (delta * (2 * native[:, None] + delta * norm[:, None, None])).sum(axis=-1)
            cost = np.where(legal & (pooled_cost <= 1e-3), pooled_cost + .26 * native_cost, np.inf)
            selected = cost.argmin(axis=-1)
            improved = cost[np.arange(len(y)), selected] < -1e-3
            state = np.where(improved[:, None], PATTERNS[selected], state).astype(bool)
            bits[pixels] = state
            result[pixels] = np.where(state[..., None], ink[pixels], paper[pixels])

    return pack(bits, attrs), result
