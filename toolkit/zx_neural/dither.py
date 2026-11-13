"""Select Spectrum pairs while accounting for ordered dithering and cell seams."""

import numpy as np

from .objective import COLOR_WEIGHT, Candidates, edge_weight
from .screen import COLS, ROWS, INK, PAPER, PALETTE, from_cells, to_cells

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                  [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32)
THRESHOLDS = (np.tile(BAYER, (2, 2)) + .5) / 16
DITHER_COLOR_BUDGET = .022
DITHER_SWEEPS = 6


def tiles(values):
    """Split each 8x8 cell into four 4x4 tiles."""
    return values.reshape(ROWS, COLS, 2, 4, 2, 4, *values.shape[4:]).swapaxes(3, 4)


def tile_pixels(values):
    return values.repeat(4, axis=2).repeat(4, axis=3)


class DitherCandidates(Candidates):
    """Use the actual dithered colors when comparing neighboring pairs."""

    seam_weight = 5.

    def __init__(self, original):
        source = original.source
        palette = PALETTE.astype(np.float32) / 255
        paper, ink = palette[PAPER], palette[INK]
        direction = ink - paper
        nearest = original.distances[..., INK] < original.distances[..., PAPER]
        projection = (source @ (direction * COLOR_WEIGHT).T - (paper * direction) @ COLOR_WEIGHT)
        projection /= direction ** 2 @ COLOR_WEIGHT
        padded = np.pad(from_cells(source), ((1, 1), (1, 1), (0, 0)), mode="edge")
        windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3), axis=(0, 1))
        protected = to_cells(np.max(np.ptp(windows, axis=(-2, -1)), axis=-1) > 34 / 255)
        smooth = np.ptp(tiles(source), axis=(4, 5)).max(axis=-1) <= 44 / 255
        proposed = np.where(protected[..., None], nearest, projection > THRESHOLDS[..., None])
        pooled_source = tiles(source).mean(axis=(4, 5))
        before = paper + tiles(nearest).mean(axis=(4, 5), dtype=np.float32)[..., None] * direction
        after = paper + tiles(proposed).mean(axis=(4, 5), dtype=np.float32)[..., None] * direction
        improvement = ((before - pooled_source[..., None, :]) ** 2
                       - (after - pooled_source[..., None, :]) ** 2) @ COLOR_WEIGHT
        self.patterns = np.where(tile_pixels(smooth[..., None] & (improvement > (4 / 255) ** 2)),
                                 proposed, nearest)
        coverage = tiles(self.patterns).mean(axis=(4, 5), dtype=np.float32)[..., None]
        residual = paper + coverage * direction - pooled_source[..., None, :]
        pixel_cost = np.where(self.patterns, original.distances[..., INK], original.distances[..., PAPER])
        self.unary = .8 * (residual ** 2 @ COLOR_WEIGHT).mean(axis=(2, 3)) + .2 * pixel_cost.mean(axis=(2, 3))
        self.regret = self.unary - self.unary.min(axis=-1, keepdims=True)
        self.allowed = self.regret <= DITHER_COLOR_BUDGET

        # Compare both the tile average and the dot-pattern contrast. The
        # second term discourages sudden texture changes on the 8x8 grid.
        texture = np.sqrt(coverage * (1 - coverage)) * np.abs(direction)
        sides = np.concatenate([residual, .75 * texture], axis=-1) * np.sqrt(np.float32(2))
        self.residuals = np.moveaxis(np.asarray([
            sides[:, :, 0], sides[:, :, -1], sides[:, :, :, 0], sides[:, :, :, -1],
        ]), -2, 3)
        self.horizontal = edge_weight(pooled_source[:, 1:, :, 0] - pooled_source[:, :-1, :, -1])
        self.vertical = edge_weight(pooled_source[1:, :, 0] - pooled_source[:-1, :, -1])

    def bitmap(self, labels):
        return np.take_along_axis(self.patterns, labels[..., None, None, None], axis=-1)[..., 0]

    def select(self, initial):
        best = self.unary.argmin(axis=-1)
        allowed = np.take_along_axis(self.allowed, initial[..., None], axis=-1)[..., 0]
        return self.refine(np.where(allowed, initial, best), DITHER_SWEEPS)
