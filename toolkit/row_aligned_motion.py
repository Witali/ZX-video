"""Bounded row-symbol motion experiment; existing phase-zero Z80 vectors.

Each bitmap byte is one opaque dictionary symbol for four logical pixels.
Horizontal displacement must be a multiple of four logical pixels; vertical
displacement is one logical row. Preserve the legacy vector identifiers so
the independent scalar decoder and current native cache/handler can verify
the stream unchanged. No claim of cycle-optimal host selection.
"""
import numpy as np
from probe_fine_motion import tile_bytes, raster_bytes
from probe_hybrid_tiles import OFFSETS

ALIGNED = [(i, dx // 4, dy) for i, (dx, dy) in enumerate(OFFSETS) if dx % 4 == 0]


def shifted_rows(previous):
    source = previous.reshape(96, 32)
    candidates = np.zeros((len(ALIGNED), 96, 32), dtype=np.uint8)
    for i, (_, dx, dy) in enumerate(ALIGNED):
        candidates[i, max(0, dy):min(96, 96 + dy), max(0, dx):min(32, 32 + dx)] = source[
            max(0, -dy):min(96, 96 - dy), max(0, -dx):min(32, 32 - dx)]
    return candidates.reshape(len(ALIGNED), 3072)


def predict_rows(states):
    if states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840:
        raise ValueError('expected uint8 compact row-index frames')
    target = tile_bytes(states[:, :3072], 8)
    vectors = np.empty(target.shape[:2], dtype=np.uint8)
    residual = np.empty_like(states)
    previous = np.zeros(3840, dtype=np.uint8)
    identifiers = np.array([i for i, _, _ in ALIGNED], dtype=np.uint8)
    for frame, current in enumerate(states):
        candidates = tile_bytes(shifted_rows(previous[:3072]), 8)
        delta = candidates ^ target[frame]
        # One byte per changed symbol, plus one byte penalty for motion.
        # Dictionary index bit patterns have no brightness/distance meaning.
        cost = np.count_nonzero(delta, axis=2)
        cost[1:] += 1
        chosen = cost.argmin(axis=0)  # Temporal retention wins ties.
        vectors[frame] = identifiers[chosen]
        residual[frame, :3072] = raster_bytes(delta[chosen, np.arange(192)][None], 8)[0]
        residual[frame, 3072:] = current[3072:] ^ previous[3072:]
        previous = current
    return vectors, residual
