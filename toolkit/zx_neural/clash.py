"""Learn which legal pair repairs a false boundary on a completed screen."""

from pathlib import Path

import numpy as np

from .dark_ramps import false_border_steps, false_contrast_cost
from .dither import BAYER, tiles
from .model import load_weights, predict
from .objective import COLOR_WEIGHT, edge_weight
from .screen import ATTRIBUTES, COLS, INK, PAIR_COUNT, PAPER, PALETTE, ROWS, from_cells, pack, to_cells
from .smooth import diffuse_coverage
from .subject import color_accents, pool4, screen_pixels

CLASH_WEIGHTS = Path(__file__).with_name("weights64-clash.npz")
SHORTLIST = 5
PROFILES = np.array([.45, 1.4, 3., 6.], dtype=np.float32)
QUADRANT_Y, QUADRANT_X = np.indices((2, 2)).reshape(2, 4)
COLORS = PALETTE.astype(np.float32)


def clash_layout(channels):
    if channels != 64:
        raise ValueError("the clash model uses 64 channels")
    return ((34, channels, 3), (channels, channels, 3), (channels, PAIR_COUNT, 1))


def load_clash_weights(path=CLASH_WEIGHTS):
    return load_weights(path, layout=clash_layout)


class ClashCells:
    """Score candidate bit counts against the actual surrounding screen."""

    def __init__(self, source):
        rgb = source.astype(np.float32)
        self.source = to_cells(rgb)
        self.target = pool4(rgb)
        strong = np.zeros(source.shape[:2], dtype=bool)
        for axis in (0, 1):
            pixels = np.moveaxis(rgb, axis, 0)
            mask = np.moveaxis(strong, axis, 0)
            edge = np.abs(np.diff(pixels, axis=0)).max(axis=-1) >= 76.5
            mask[1:] |= edge
            mask[:-1] |= edge
        self.strong = strong

    def active(self, preview):
        severe_y, severe_x = false_border_steps(self.target, pool4(preview.astype(np.float32)))
        vertical = severe_y.reshape(ROWS - 1, COLS, 2).any(axis=-1)
        horizontal = severe_x.reshape(ROWS, 2, COLS - 1).any(axis=1)
        hit = np.zeros((ROWS, COLS), dtype=bool)
        hit[:-1] |= vertical
        hit[1:] |= vertical
        hit[:, :-1] |= horizontal
        hit[:, 1:] |= horizontal
        return hit

    def features(self, attrs, preview):
        residual = tiles(to_cells(preview.astype(np.float32)) - self.source).mean(axis=(4, 5))
        target = tiles(self.source).mean(axis=(4, 5))
        bright = (attrs >> 3) & 8
        color = np.concatenate((COLORS[((attrs >> 3) & 7) | bright], COLORS[(attrs & 7) | bright]), axis=-1)
        strength = tiles(to_cells(self.strong)).mean(axis=(4, 5), dtype=np.float32)
        return np.concatenate((target.reshape(ROWS, COLS, 12) / 255,
                               residual.reshape(ROWS, COLS, 12) / 255, color / 255,
                               strength.reshape(ROWS, COLS, 4)), axis=-1)

    def locks(self, preview, probability):
        raster = from_cells(self.source)
        locked = self.strong | color_accents(raster, preview) | (preview == raster).all(axis=-1)
        if probability is not None:
            # Keep already shaded subject boundaries, including open gaps.
            for axis in (0, 1):
                mask = np.moveaxis(locked, axis, 0)
                saliency = np.moveaxis(probability, axis, 0)
                boundary = (saliency[1:] >= .5) != (saliency[:-1] >= .5)
                mask[1:] |= boundary
                mask[:-1] |= boundary
        return to_cells(locked)

    def shortlist(self, preview, locked, attrs, bitmap, y, x, layers):
        bright = (attrs[y, x] >> 3) & 8
        old_paper = COLORS[((attrs[y, x] >> 3) & 7) | bright][:, None, :]
        old_ink = COLORS[(attrs[y, x] & 7) | bright][:, None, :]
        paper, ink = COLORS[PAPER], COLORS[INK]
        frozen, phase = locked[y, x], bitmap[y, x]
        keep_paper = (frozen & ~phase).any(axis=(1, 2))
        keep_ink = (frozen & phase).any(axis=(1, 2))
        allowed = (~keep_paper[:, None] | (old_paper == paper).all(axis=-1)
                   | (old_paper == ink).all(axis=-1))
        allowed &= (~keep_ink[:, None] | (old_ink == paper).all(axis=-1) | (old_ink == ink).all(axis=-1))
        if layers is not None:
            score = -predict(self.features(attrs, preview), layers)[y, x]
        else:
            direction = ink - paper
            weighted = direction * COLOR_WEIGHT
            rgb = self.target[2 * y[:, None] + QUADRANT_Y, 2 * x[:, None] + QUADRANT_X]
            delta = rgb[:, None] - paper[:, None]
            coverage = ((delta * weighted[:, None]).sum(axis=-1) / (direction * weighted).sum(axis=-1)[:, None]).clip(0, 1)
            score = np.square(delta - coverage[..., None] * direction[:, None]).sum(axis=(2, 3))
        return np.argsort(np.where(allowed, score, np.inf), axis=-1, kind="stable")[:, :SHORTLIST]

    def candidates(self, preview, locked, y, x, pairs, *, contrast=False):
        """Return the best verified four dot counts for each proposed pair."""
        paper, ink = COLORS[PAPER[pairs]], COLORS[INK[pairs]]
        direction = ink - paper
        painted = to_cells(preview)[y, x].astype(np.float32)
        old = pool4(preview.astype(np.float32))
        target = self.target
        cy, cx = 2 * y[:, None] + QUADRANT_Y, 2 * x[:, None] + QUADRANT_X
        ny = 2 * y[:, None] + np.where(QUADRANT_Y, 2, -1)
        nx = 2 * x[:, None] + np.where(QUADRANT_X, 2, -1)
        valid = np.stack(((ny >= 0) & (ny < 2 * ROWS), (nx >= 0) & (nx < 2 * COLS)), axis=-1)
        ny, nx = ny.clip(0, 2 * ROWS - 1), nx.clip(0, 2 * COLS - 1)
        source_tile = target[cy, cx]
        old_error = old[cy, cx] - source_tile
        neighbor = np.stack((old[ny, cx] - target[ny, cx], old[cy, nx] - target[cy, nx]), axis=-2)
        source_step = source_tile[..., None, :] - np.stack((target[ny, cx], target[cy, nx]), axis=-2)
        weight = edge_weight(source_step / 255) * valid
        quiet = (np.abs(source_step).max(axis=-1) <= 12) & valid
        old_seam = old_error[..., None, :] - neighbor
        old_large = quiet & (np.abs(old_seam).max(axis=-1) >= 48)

        frozen = locked[y, x].reshape(-1, 2, 4, 2, 4).swapaxes(2, 3).reshape(-1, 4, 16)
        pixels = painted.reshape(-1, 2, 4, 2, 4, 3).swapaxes(2, 3).reshape(-1, 4, 16, 3)
        force_ink = frozen[:, None] & (pixels[:, None] == ink[:, :, None, None, :]).all(axis=-1)
        force_paper = frozen[:, None] & (pixels[:, None] == paper[:, :, None, None, :]).all(axis=-1)
        legal = (force_ink | force_paper | ~frozen[:, None]).all(axis=(2, 3))
        minimum, maximum = force_ink.sum(axis=-1), 16 - force_paper.sum(axis=-1)

        # Fit a density along the candidate's RGB line. The surrounding
        # residuals tell us how to smooth a join without erasing source edges.
        denom = 1 + weight.sum(axis=-1)[..., None] * PROFILES
        shift = (neighbor * weight[..., None]).sum(axis=-2)
        aim = source_tile[:, None] + shift[:, None] * PROFILES[None, :, None, None] / denom.swapaxes(1, 2)[..., None]
        weighted = direction * COLOR_WEIGHT
        norm = (direction * weighted).sum(axis=-1)
        fraction = ((aim[:, None] - paper[:, :, None, None]) * weighted[:, :, None, None]).sum(axis=-1)
        count = np.rint(16 * fraction / norm[:, :, None, None]).clip(minimum[:, :, None], maximum[:, :, None])
        new_error = paper[:, :, None, None] + count[..., None] * (direction[:, :, None, None] / 16)
        new_error -= source_tile[:, None, None]
        seam = new_error[..., None, :] - neighbor[:, None, None]
        level = np.abs(seam).max(axis=-1)
        large = quiet[:, None, None] & (level >= 48)
        no_new = ~(large & ~old_large[:, None, None]).any(axis=(3, 4))
        removed = old_large.sum(axis=(1, 2))[:, None, None] - large.sum(axis=(3, 4))
        color_error = np.square(new_error).sum(axis=(3, 4))
        old_color_error = np.square(old_error).sum(axis=(1, 2))
        seam_error = (np.square(seam).sum(axis=-1) * weight[:, None, None]).sum(axis=(3, 4))
        old_seam_error = (np.square(old_seam).sum(axis=-1) * weight).sum(axis=(1, 2))
        accept = (legal[..., None] & no_new & (removed > 0)
                  & (color_error <= old_color_error[:, None, None])
                  & (seam_error < old_seam_error[:, None, None]))
        score = (color_error + 2 * seam_error) / (255 ** 2) - .15 * removed
        if contrast:
            penalty = (false_contrast_cost(level) * quiet[:, None, None]).sum(axis=(3, 4))
            prior_penalty = (false_contrast_cost(np.abs(old_seam).max(axis=-1)) * quiet).sum(axis=(1, 2))
            accept &= penalty <= prior_penalty[:, None, None]
            score += penalty / 255 ** 2
        score = np.where(accept, score, np.inf)
        best = score.argmin(axis=2)
        scalar = np.take_along_axis(score, best[..., None], axis=2)[..., 0]
        counts = np.take_along_axis(count, best[..., None, None], axis=2)[:, :, 0]
        return scalar, counts.astype(np.uint8)

    def fit(self, source, old, locked, pair, counts, *, keep_balanced=False):
        """Place the selected number of dots without altering protected pixels."""
        paper, ink = COLORS[PAPER[pair]], COLORS[INK[pair]]
        direction = ink - paper
        weight = direction * COLOR_WEIGHT
        projection = ((source - paper) @ weight) / (direction @ weight)
        projected = projection.clip(0, 1).reshape(2, 4, 2, 4).swapaxes(1, 2).reshape(4, 16)
        density = projected + (counts / 16 - projected.mean(axis=-1))[:, None]
        coverage = density.reshape(2, 2, 4, 4).swapaxes(1, 2).reshape(8, 8)
        force_ink = locked & (old == ink).all(axis=-1)
        floyd = diffuse_coverage(coverage, (~locked).astype(np.float32),
                                 np.broadcast_to(direction, (8, 8, 3)))
        priority = coverage + .45 * floyd - .002 * np.tile(BAYER, (2, 2))
        priority = np.where(locked, np.where(force_ink, 10., -10.), priority)
        priority = priority.reshape(2, 4, 2, 4).swapaxes(1, 2).reshape(4, 16)
        rank = np.argsort(np.argsort(-priority, axis=-1), axis=-1)
        bits = (rank < counts[:, None]).reshape(2, 2, 4, 4).swapaxes(1, 2).reshape(8, 8)
        if keep_balanced:
            # Preserve interior detail when the new pair already represents
            # the old tile with exactly the desired number of ink pixels.
            old_ink = (old == ink).all(axis=-1)
            representable = old_ink | (old == paper).all(axis=-1)
            retain = ((pool4(old_ink) * 16 == counts.reshape(2, 2)) & (pool4(representable) == 1))
            bits = np.where(retain.repeat(4, axis=0).repeat(4, axis=1), old_ink, bits)
        return bits, np.where(bits[..., None], ink, paper).astype(np.uint8)


def reduce_clash(source, current, layers, probability=None):
    """Rank plausible repairs, then enforce the exact decoded-screen score."""
    screen, preview = current
    geometry = ClashCells(source)
    eligible = geometry.active(preview)
    if not eligible.any():
        return current

    attrs, bits, _, _ = screen_pixels(screen, preview)
    attrs = attrs.copy()
    bitmap, output = to_cells(bits).copy(), to_cells(preview).copy()
    parity = np.indices((ROWS, COLS)).sum(axis=0) % 2
    changed = False
    # Cells of the same parity share no edge. Refresh the neighbors after
    # each color so the local checks also hold for the combined edits.
    for phase in (0, 1):
        y, x = np.nonzero(eligible & (parity == phase))
        if not len(y):
            continue
        locked = geometry.locks(preview, probability)
        pairs = geometry.shortlist(preview, locked, attrs, bitmap, y, x, layers)
        scores, counts = geometry.candidates(preview, locked, y, x, pairs)
        chosen = scores.argmin(axis=-1)
        accept = np.flatnonzero(np.isfinite(scores).any(axis=-1))
        for i in accept:
            cy, cx = y[i], x[i]
            label = pairs[i, chosen[i]]
            bitmap[cy, cx], output[cy, cx] = geometry.fit(geometry.source[cy, cx], output[cy, cx],
                                                       locked[cy, cx], label, counts[i, chosen[i]])
            attrs[cy, cx] = ATTRIBUTES[label]
        if len(accept):
            changed = True
            preview = from_cells(output)
            eligible = geometry.active(preview)
    if changed:
        return pack(from_cells(bitmap), attrs), preview
    return current
