"""Favor readable shapes and quiet color ramps in the pixel-art renderer."""

import numpy as np

from .objective import COLOR_WEIGHT, TARGET_TEMPERATURE
from .screen import COLS, ROWS, pack, to_cells
from .smooth import SmoothCandidates
from .subject import box_mean, color_accents, pool4, screen_pixels


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
    channels = source.astype(np.float32).transpose(2, 0, 1)
    residual = np.stack([channel - box_mean(channel, 5) for channel in channels], axis=-1)
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


def cluster_pixels(source, current, locked):
    """Join small dither marks by swapping colors between nearby pixels."""
    screen, preview = current
    attrs, bits, _, _ = screen_pixels(screen, preview)
    color = preview.copy()
    source = source.astype(np.float32)
    locked = locked | (source == preview).all(axis=-1)
    height, width = bits.shape
    changed = False
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        rows = np.arange(max(1, 1 - dy), min(height - 1, height - dy - 1))
        cols = np.arange(max(1, 1 - dx), min(width - 1, width - dx - 1))
        a = np.s_[rows[:, None], cols]
        b = np.s_[rows[:, None] + dy, cols + dx]
        same_tile = ((rows[:, None] // 2 == (rows[:, None] + dy) // 2)
                     & (cols // 2 == (cols + dx) // 2))
        period = abs(dx) + dy + 2
        phase_index = (rows[:, None] if dy else cols) % period
        # In each phase, trades are disjoint and separated by enough
        # space that their immediate neighbors cannot also be traded.
        for phase in range(period):
            eligible = (phase_index == phase) & same_tile & ~locked[a] & ~locked[b] & (bits[a] != bits[b])
            yy, xx = np.nonzero(eligible)
            y, x = rows[yy], cols[xx]
            # Filter the other dimension so neighbor comparisons in a
            # phase use the current state rather than contested pixels.
            for offset in range(2):
                allowed = ((x if dy else y) % 2) == offset
                ay, ax = y[allowed], x[allowed]
                by, bx = ay + dy, ax + dx
                before_a, before_b = color[ay, ax], color[by, bx]
                delta = before_b.astype(np.float32) - before_a
                # Preserve genuine source contrast between trade sites.
                source_delta = source[by, bx] - source[ay, ax]
                eligible_swap = (source_delta ** 2 @ COLOR_WEIGHT) <= 28 ** 2
                trade_cost = 2 * ((delta * source_delta) @ COLOR_WEIGHT)
                gain = np.zeros(len(ay), dtype=np.int8)
                for oy, ox in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    neighbor_a = color[ay + oy, ax + ox]
                    neighbor_b = color[by + oy, bx + ox]
                    gain += (neighbor_a == before_b).all(axis=-1)
                    gain -= (neighbor_a == before_a).all(axis=-1)
                    gain += (neighbor_b == before_a).all(axis=-1)
                    gain -= (neighbor_b == before_b).all(axis=-1)
                if abs(dx) + dy == 1:
                    gain -= 2  # The edge joining the two pixels is unchanged.
                swap = eligible_swap & (gain >= 3) & (trade_cost <= 560. * gain)
                if swap.any():
                    changed = True
                    color[ay[swap], ax[swap]] = before_b[swap]
                    color[by[swap], bx[swap]] = before_a[swap]
                    bits[ay[swap], ax[swap]] ^= True
                    bits[by[swap], bx[swap]] ^= True

    return (pack(bits, attrs), color) if changed else current
