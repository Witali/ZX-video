"""Reduce grid-aligned color seams while retaining two legal colors per cell."""

import numpy as np

from .dither import DitherCandidates, THRESHOLDS
from .objective import COLOR_WEIGHT, GRID_X, GRID_Y, TOP, BOTTOM, LEFT, RIGHT
from .screen import COLS, ROWS, INK, PAPER, PALETTE, from_cells, to_cells


def floyd_bitmap(candidates, labels):
    """Diffuse projected color error in serpentine order over the whole raster."""
    source = candidates.source
    palette = PALETTE.astype(np.float32) / 255
    paper = palette[PAPER[labels]][:, :, None, None]
    direction = palette[INK[labels]][:, :, None, None] - paper
    normal = direction * COLOR_WEIGHT
    length = (direction * normal).sum(axis=-1)
    projection = ((source - paper) * normal).sum(axis=-1) / length
    strength = np.clip((34 / 255 - candidates.local_range(source)) / (22 / 255), 0, 1)
    vectors = np.broadcast_to(direction, source.shape)
    return to_cells(diffuse_coverage(from_cells(projection), from_cells(strength), from_cells(vectors)))


def diffuse_coverage(projection, strength, direction):
    """Dither raster coverage, with zero strength cutting diffusion across a boundary."""
    coverage = np.clip(projection, 0, 1).tolist()
    strength = strength.tolist()
    vectors = direction * np.sqrt(COLOR_WEIGHT)
    lengths = np.sqrt((direction * (direction * COLOR_WEIGHT)).sum(axis=-1))
    unit = vectors / lengths[..., None]
    # Transport only the part of the previous error the receiving pair can
    # express. The dot product vanishes for orthogonal color directions.
    length = lengths.tolist()
    horizontal = np.maximum(0, (unit[:, 1:] * unit[:, :-1]).sum(axis=-1)).tolist()
    vertical = np.maximum(0, (unit[1:] * unit[:-1]).sum(axis=-1)).tolist()
    down_right = np.maximum(0, (unit[1:, 1:] * unit[:-1, :-1]).sum(axis=-1)).tolist()
    down_left = np.maximum(0, (unit[1:, :-1] * unit[:-1, 1:]).sum(axis=-1)).tolist()
    height, width = unit.shape[:2]
    bits = np.empty((height, width), dtype=bool)
    for y in range(height):
        step = 1 if y % 2 == 0 else -1
        order = range(width) if step == 1 else range(width - 1, -1, -1)
        for x in order:
            level = min(1., max(0., coverage[y][x]))
            selected = level > .5
            bits[y, x] = selected
            error = (level - selected) * strength[y][x] * length[y][x] / 16
            if error == 0:
                continue
            ahead = x + step
            behind = x - step
            if 0 <= ahead < width:
                coverage[y][ahead] += 7 * error * horizontal[y][min(x, ahead)] * strength[y][ahead] / length[y][ahead]
            if y + 1 == height:
                continue
            coverage[y + 1][x] += 5 * error * vertical[y][x] * strength[y + 1][x] / length[y + 1][x]
            for target, weight in ((behind, 3), (ahead, 1)):
                if 0 <= target < width:
                    similarity = down_left[y][target] if target < x else down_right[y][x]
                    coverage[y + 1][target] += weight * error * similarity * strength[y + 1][target] / length[y + 1][target]
    return bits


class SmoothCandidates(DitherCandidates):
    """Optimize whole rows and columns so adjacent pairs can change together."""

    seam_weight = 4.
    pair_weight = .025
    chroma_grain_weight = .12
    budget = .035
    shortlist = 12
    passes = 3

    def __init__(self, original):
        super().__init__(original)
        exact = original.unary <= 1e-8
        # A legal exact cell has no quantization error to diffuse. Keep all
        # its exact pairs in play, including those with an unused endpoint.
        within_budget = self.regret <= self.budget
        self.allowed = np.where(exact.any(axis=-1, keepdims=True), exact, within_budget)

    def select(self, initial, preference=None):
        legal_cost = np.where(self.allowed, self.unary, np.inf)
        if preference is not None:
            legal_cost = legal_cost + preference
        best = legal_cost.argmin(axis=-1)
        initial = np.where(self.allowed[GRID_Y, GRID_X, initial], initial, best)
        order = np.argsort(legal_cost, axis=-1, kind="stable")[..., :self.shortlist]
        # Retain the converter's original proposal as an additional option.
        choices = np.concatenate((initial[..., None], order), axis=-1)
        costs = np.take_along_axis(legal_cost, choices, axis=-1)
        edges = self.residuals[:, GRID_Y[..., None], GRID_X[..., None], choices]
        endpoints = PALETTE.astype(np.float32) / 255
        # Compare endpoint colors as well as the actual pooled edge color.
        # This avoids flipping between very different dot colors with
        # similar average RGB in a smooth area.
        pair = np.concatenate((endpoints[PAPER[choices]], endpoints[INK[choices]]), axis=-1)
        selected = np.zeros((ROWS, COLS), dtype=np.intp)
        for _ in range(self.passes):
            before = selected.copy()
            self._scan(selected, costs, edges, pair, self.horizontal, self.vertical)
            self._scan(selected.T, costs.swapaxes(0, 1), edges[[LEFT, RIGHT, TOP, BOTTOM]].swapaxes(1, 2),
                       pair.swapaxes(0, 1), self.vertical.swapaxes(0, 1), self.horizontal.swapaxes(0, 1))
            if np.array_equal(selected, before):
                break
        return choices[GRID_Y, GRID_X, selected]

    def _scan(self, selected, costs, edges, pair, horizontal, vertical):
        """Minimize each strip exactly with the neighboring strips held fixed."""
        height, width, count = costs.shape
        cols = np.arange(width)

        # Cost matrices for neighbors in each row; the DP reuses them.
        difference = edges[RIGHT, :, :-1, :, None] - edges[LEFT, :, 1:, None, :]
        transitions = self.seam_weight * (
            (difference ** 2).mean(axis=-1) * horizontal[:, :, None, None]).mean(axis=-1)
        difference = pair[:, :-1, :, None] - pair[:, 1:, None, :]
        transitions += self.pair_weight * (difference ** 2).mean(axis=-1) * horizontal.mean(axis=-1)[..., None, None]

        for row in range(height):
            local = costs[row].copy()
            for other, side, opposite, weights in (
                (row - 1, TOP, BOTTOM, vertical[row - 1] if row else None),
                (row + 1, BOTTOM, TOP, vertical[row] if row + 1 < height else None),
            ):
                if weights is None:
                    continue
                fixed = selected[other]
                delta = edges[side, row] - edges[opposite, other, cols, fixed][:, None]
                local += self.seam_weight * ((delta ** 2).mean(axis=-1) * weights[:, None]).mean(axis=-1)
                delta = pair[row] - pair[other, cols, fixed][:, None]
                local += self.pair_weight * (delta ** 2).mean(axis=-1) * weights.mean(axis=-1)[:, None]
            previous = np.empty((width, count), dtype=np.intp)
            cost = local[0]
            for col in range(1, width):
                path = cost[:, None] + transitions[row, col - 1]
                previous[col] = path.argmin(axis=0)
                cost = local[col] + path.min(axis=0)
            selected[row, -1] = cost.argmin()
            for col in range(width - 1, 0, -1):
                selected[row, col - 1] = previous[col, selected[row, col]]

    def patterns_for(self, source, pooled_source, nearest, projection, paper, direction, local_range):
        """Fade the dot pattern into the closest-color mask near real edges."""
        strength = np.clip((34 / 255 - local_range) / (22 / 255), 0, 1)
        coverage = np.clip(projection, 0, 1)
        coverage = nearest + strength[..., None] * (coverage - nearest)
        return coverage > THRESHOLDS[..., None]

    def color_cost(self, residual, pixel_cost, coverage, direction, local_range):
        """Charge chromatic grain from mixing distant, saturated endpoints."""
        coarse = (residual ** 2 @ COLOR_WEIGHT).mean(axis=(2, 3))
        fine = pixel_cost.mean(axis=(2, 3))
        chroma = direction - (direction @ COLOR_WEIGHT)[:, None]
        grain = (coverage * (1 - coverage)).mean(axis=(2, 3))[..., 0]
        chroma_grain = grain * (chroma ** 2 @ COLOR_WEIGHT)
        detail = (local_range > 48 / 255).mean(axis=(2, 3), dtype=np.float32)[..., None]
        fine_weight = .24 + .34 * detail
        return (1 - fine_weight) * coarse + fine_weight * fine + self.chroma_grain_weight * chroma_grain
