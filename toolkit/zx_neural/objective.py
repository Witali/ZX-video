"""Palette candidates and an edge-aware cost for visible attribute clashes."""

from functools import cached_property

import numpy as np

from .screen import COLS, ROWS, INK, PAPER, PALETTE, PAIR_COUNT, to_cells

COLOR_WEIGHT = np.array([.25, .60, .15], np.float32)
SEAM_WEIGHT = .65
COLOR_BUDGET = .006
TEMPERATURE = .0025
TARGET_TEMPERATURE = .0008
TRAIN_SWEEPS = 5
REFINE_SWEEPS = 2
SHORTLIST = 8
# Edge samples are in raster order along each side, with opposite edges aligned.
TOP, BOTTOM, LEFT, RIGHT = range(4)
GRID_Y, GRID_X = np.indices((ROWS, COLS))


def edge_weight(delta):
    """Weight quiet regions most strongly and give real edges room to remain."""
    return np.exp(-np.mean(delta ** 2, axis=-1) / .012)


def features(rgb, candidates):
    """Summarize four quadrants and four edges of each cell for the CNN."""
    cells = to_cells(rgb.astype(np.float32) * (2 / 255) - 1)
    quadrants = cells.reshape(ROWS, COLS, 2, 4, 2, 4, 3).mean(axis=(3, 5))
    sides = np.concatenate([
        cells[:, :, 0, :].mean(axis=2), cells[:, :, -1, :].mean(axis=2),
        cells[:, :, :, 0].mean(axis=2), cells[:, :, :, -1].mean(axis=2),
    ], axis=-1)
    # The CNN can compare actual color fits in its neighborhood. A logarithm
    # expands the small differences among the plausible choices in each cell.
    hint = candidates.contextual_cost(candidates.unary.argmin(axis=-1), average_edges=True)
    hint -= hint.min(axis=-1, keepdims=True)
    return np.concatenate([quadrants.reshape(ROWS, COLS, 12), sides,
                           np.log1p(candidates.regret * 64), np.log1p(hint * 64)], axis=-1)


def pixel_distances(rgb):
    source = rgb.astype(np.float32) / 255
    palette = PALETTE.astype(np.float32) / 255
    # Penalize errors at thin lines and high-contrast details in the source.
    strength = np.zeros(source.shape[:2], np.float32)
    horizontal = np.max(np.abs(np.diff(source, axis=1)), axis=-1)
    vertical = np.max(np.abs(np.diff(source, axis=0)), axis=-1)
    for target, contrast in ((strength[:, 1:], horizontal), (strength[:, :-1], horizontal),
                             (strength[1:], vertical), (strength[:-1], vertical)):
        np.maximum(target, contrast, out=target)
    importance = 1 + .75 * np.minimum(strength * 3, 1)
    distances = ((source[:, :, None] - palette) ** 2) @ COLOR_WEIGHT
    return to_cells(distances * importance[:, :, None])


class Candidates:
    """Compute exactly what each legal pair would paint, including its edges."""

    seam_weight = SEAM_WEIGHT

    def __init__(self, rgb):
        self.source = to_cells(rgb.astype(np.float32) / 255)
        self.distances = pixel_distances(rgb)
        paper_error = self.distances[..., PAPER]
        ink_error = self.distances[..., INK]
        self.unary = np.minimum(paper_error, ink_error).mean(axis=(2, 3))
        self.regret = self.unary - self.unary.min(axis=-1, keepdims=True)
        self.allowed = self.regret <= COLOR_BUDGET
        self.horizontal = edge_weight(self.source[:, 1:, :, 0] - self.source[:, :-1, :, -1])
        self.vertical = edge_weight(self.source[1:, :, 0] - self.source[:-1, :, -1])

    @cached_property
    def residuals(self):
        palette = PALETTE.astype(np.float32) / 255
        residuals = []
        for side in (np.s_[:, :, 0, :], np.s_[:, :, -1, :],
                     np.s_[:, :, :, 0], np.s_[:, :, :, -1]):
            distances = self.distances[side]
            ink = distances[..., INK] < distances[..., PAPER]
            rendered = palette[np.where(ink, INK, PAPER)]
            residuals.append(rendered - self.source[side][:, :, :, None])
        return np.moveaxis(np.asarray(residuals), -2, 3)

    def bitmap(self, labels):
        ink = INK[labels][..., None, None, None]
        paper = PAPER[labels][..., None, None, None]
        return (np.take_along_axis(self.distances, ink, axis=-1)
                < np.take_along_axis(self.distances, paper, axis=-1))[..., 0]

    def contextual_cost(self, labels, *, average_edges=False, choices=None):
        """Measure false color steps using candidate pixels and actual neighbors."""
        edge = self.residuals
        horizontal, vertical = self.horizontal, self.vertical
        if average_edges:
            # Give the CNN coarse evidence about seams at the baseline solution.
            # The optimizer and teacher still compare all eight aligned pixels.
            edge = edge.mean(axis=-2, keepdims=True)
            horizontal = horizontal.mean(axis=-1, keepdims=True)
            vertical = vertical.mean(axis=-1, keepdims=True)
        chosen = edge[:, GRID_Y, GRID_X, labels]
        unary = self.unary
        if choices is not None:
            edge = edge[:, GRID_Y[..., None], GRID_X[..., None], choices]
            unary = np.take_along_axis(unary, choices, axis=-1)
        cost = np.zeros_like(unary)

        def add(target, candidate, neighbor, weight):
            difference = candidate - neighbor[:, :, None]
            target += np.mean((difference ** 2).mean(axis=-1) * weight[:, :, None], axis=-1)

        add(cost[:, 1:], edge[LEFT, :, 1:], chosen[RIGHT, :, :-1], horizontal)
        add(cost[:, :-1], edge[RIGHT, :, :-1], chosen[LEFT, :, 1:], horizontal)
        add(cost[1:], edge[TOP, 1:], chosen[BOTTOM, :-1], vertical)
        add(cost[:-1], edge[BOTTOM, :-1], chosen[TOP, 1:], vertical)
        return unary + self.seam_weight * cost

    def refine(self, labels, sweeps, choices=None):
        """Optimize even/odd cells separately so no simultaneous edits share a seam."""
        labels = labels.copy()
        allowed = self.allowed if choices is None else np.take_along_axis(self.allowed, choices, axis=-1)
        even = (GRID_Y + GRID_X) % 2 == 0
        for _ in range(sweeps):
            changed = False
            for mask in (even, ~even):
                cost = np.where(allowed, self.contextual_cost(labels, choices=choices), np.inf)
                best = cost.argmin(axis=-1)
                current = labels
                if choices is not None:
                    current = (choices == labels[..., None]).argmax(axis=-1)
                # Keep ties stable, including pairs whose rendered pixels coincide.
                improve = mask & (cost[GRID_Y, GRID_X, best] < cost[GRID_Y, GRID_X, current] - 1e-8)
                next_labels = best if choices is None else choices[GRID_Y, GRID_X, best]
                labels[improve] = next_labels[improve]
                changed |= bool(improve.any())
            if not changed:
                break
        return labels

    def training_target(self):
        baseline = self.unary.argmin(axis=-1)
        labels = self.refine(baseline, TRAIN_SWEEPS)
        score = np.where(self.allowed, self.contextual_cost(labels), np.inf)
        minimum = score.min(axis=-1, keepdims=True)
        logits = -(score - minimum) / TARGET_TEMPERATURE
        probabilities = np.exp(logits)
        opportunity = score[GRID_Y, GRID_X, baseline] - minimum[..., 0]
        importance = 1 + 3 * np.minimum(opportunity / .025, 1)
        return probabilities / probabilities.sum(axis=-1, keepdims=True), importance
