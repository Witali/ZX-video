"""Improve weak detail inside a subject while keeping exact tile densities."""

import numpy as np

from .clash import ClashCells
from .objective import COLOR_WEIGHT
from .screen import HEIGHT, WIDTH, from_cells, pack
from .subject import LUMA, box_mean, screen_pixels

TILE_Y, TILE_X = np.indices((4, 4)).reshape(2, 16)
WINDOW_Y, WINDOW_X = np.indices((8, 8)) - 2

# Each swap removes one ink pixel and adds another. The sampled 3×3 box
# response fits inside this window, even for swaps on the tile's rim.
BOX = ((abs(WINDOW_Y - TILE_Y[:, None, None]) <= 1)
       & (abs(WINDOW_X - TILE_X[:, None, None]) <= 1)).astype(np.float32) / 9
SWAPS = (BOX[None] - BOX[:, None]).reshape(256, 8, 8)
BOX_SHIFT = SWAPS.reshape(256, 64)
EDGE_SHIFT = tuple(np.diff(SWAPS, axis=axis).reshape(256, 56) for axis in (1, 2))
BOX_ENERGY = np.square(BOX_SHIFT).sum(axis=-1)


def weak_edges(light, subject):
    """Weight source-supported steps in the 3×3 mean inside the silhouette."""
    averaged = box_mean(light, 3)
    edges = []
    for axis in (0, 1):
        luma = np.moveaxis(averaged, axis, 0)
        inside = np.moveaxis(subject, axis, 0)
        step = np.abs(np.diff(luma, axis=0))
        valid = inside[:-1] & inside[1:] & (step >= 5) & (step <= 32)
        strength = np.where(valid, np.minimum(step / 18, 1), 0)
        edges.append(np.moveaxis(strength.astype(np.float32), 0, axis))
    return tuple(edges)


def refine_clash_details(source, current, probability):
    """Move ink within each 4×4 tile to follow printable weak contours."""
    screen, preview = current
    if probability is None:
        return current
    subject = probability >= .65
    if not subject.any():
        return current
    target = source.astype(np.float32)
    edges = weak_edges(target @ LUMA, subject)
    if not any(edge.any() for edge in edges):
        return current
    attrs, bits, paper, ink = screen_pixels(screen, preview)
    locked = from_cells(ClashCells(source).locks(preview, probability)) | ~subject
    directions = ink.astype(np.float32) - paper
    result = preview.copy()
    changed = False

    # Tile origins eight pixels apart have disjoint windows. All accepted
    # moves in a phase therefore reduce the combined error as well.
    phases = []
    for oy, ox in ((4, 4), (4, 8), (8, 4), (8, 8)):
        y, x = np.meshgrid(np.arange(oy, HEIGHT - 5, 8), np.arange(ox, WIDTH - 5, 8), indexing="ij")
        y, x = y.ravel(), x.ravel()
        loc = (y[:, None] + TILE_Y, x[:, None] + TILE_X)
        eligible = ~locked[loc]
        mixed = (eligible & bits[loc]).any(axis=-1) & (eligible & ~bits[loc]).any(axis=-1)
        if not mixed.any():
            continue
        y, x = y[mixed], x[mixed]
        wy = y[:, None, None] + WINDOW_Y
        wx = x[:, None, None] + WINDOW_X
        edge_weights = (edges[0][wy[:, :-1], wx[:, :-1]].reshape(-1, 56),
                        edges[1][wy[:, :, :-1], wx[:, :, :-1]].reshape(-1, 56))
        use = (edge_weights[0].sum(axis=-1) + edge_weights[1].sum(axis=-1)) > 0
        if use.any():
            phases.append((y[use], x[use], wy[use], wx[use], tuple(item[use] for item in edge_weights)))

    for _ in range(2):
        for y, x, wy, wx, edge_weights in phases:
            loc = (y[:, None] + TILE_Y, x[:, None] + TILE_X)
            state = bits[loc]
            unlocked = ~locked[loc]
            legal = ((state & unlocked)[:, :, None] & (~state & unlocked)[:, None]).reshape(-1, 256)
            residual = result.astype(np.float32) - target
            mean = np.stack([box_mean(channel, 3) for channel in np.moveaxis(residual, -1, 0)], axis=-1)
            patch = mean[wy, wx].astype(np.float32)
            axis = directions[y, x]
            color_axis = axis * COLOR_WEIGHT
            squared = (axis * color_axis).sum(axis=-1)
            pooled = (patch * color_axis[:, None, None]).sum(axis=-1).reshape(-1, 64)
            color_cost = 2 * (pooled @ BOX_SHIFT.T) + squared[:, None] * BOX_ENERGY
            light = patch @ LUMA
            span = axis @ LUMA
            edge_cost = np.zeros_like(color_cost)
            for k, (weights, shift) in enumerate(zip(edge_weights, EDGE_SHIFT, strict=True)):
                step = np.diff(light, axis=k + 1).reshape(-1, 56)
                edge_cost += (2 * span[:, None] * ((weights * step) @ shift.T)
                              + np.square(span[:, None]) * (weights @ np.square(shift).T))
            native = (residual[loc] * color_axis[:, None]).sum(axis=-1)
            native_cost = (2 * (native[:, None] - native[:, :, None]) + 2 * squared[:, None, None]).reshape(-1, 256)
            feasible = legal & (edge_cost < -.01) & (color_cost <= 0) & (native_cost <= 0)
            cost = np.where(feasible, edge_cost + .12 * color_cost, np.inf)
            selected = cost.argmin(axis=-1)
            keep = np.isfinite(cost[np.arange(len(y)), selected])
            if not keep.any():
                continue
            remove, add = np.divmod(selected[keep], 16)
            for indices, value, colors in ((remove, False, paper), (add, True, ink)):
                yy = y[keep] + TILE_Y[indices]
                xx = x[keep] + TILE_X[indices]
                bits[yy, xx] = value
                result[yy, xx] = colors[yy, xx]
            changed = True
    return (pack(bits, attrs), result) if changed else current
