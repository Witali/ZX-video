"""Reuse the sparse harmonic fit for extremely close spectral shapes.

The decomposition is homogeneous in amplitude: normalize by the spectral
peak, fit once, then restore each state's own intensity. Rounded fingerprints
are only a lookup; validate the full vector within 1e-7 before reusing it.
This is analysis caching, not an AY phase reset or a coarser output schedule.
"""
from collections import OrderedDict
import hashlib
import numpy as np

CAPACITY = 2048
_cache = OrderedDict()
_stats = dict(rows=0, reused=0, largest_shape_error=0.)


def reset():
    _cache.clear()
    _stats.update(rows=0, reused=0, largest_shape_error=0.)


def stats():
    return dict(_stats, entries=len(_cache), capacity=CAPACITY, full_shape_tolerance=1e-7)


def decompose(magnitude, sample_rate, iterations, fit):
    magnitude = np.asarray(magnitude, dtype=float)
    scale = np.max(magnitude, axis=1)
    normalized = magnitude/np.maximum(scale[:, None], 1e-30)
    keys, pending, representatives = [], {}, []
    for i, shape in enumerate(normalized):
        key = (sample_rate, iterations, len(shape), hashlib.sha256(np.round(shape, 6).astype('<f8').tobytes()).digest())
        keys.append(key)
        cached = _cache.get(key)
        if cached is not None and np.max(abs(cached[0]-shape)) <= 1e-7:
            _stats['reused'] += 1
            _stats['largest_shape_error'] = max(_stats['largest_shape_error'], float(np.max(abs(cached[0]-shape))))
            _cache.move_to_end(key)
        elif key in pending and np.max(abs(normalized[pending[key]]-shape)) <= 1e-7:
            _stats['reused'] += 1
        else:
            # A rare rounded-key collision must not reuse an unchecked vector.
            if key in pending or cached is not None:
                key = (*key, shape.tobytes())
                keys[-1] = key
            pending[key] = i
            representatives.append(i)
    if representatives:
        amplitudes, explained = fit(normalized[representatives], sample_rate, iterations)
        for j, i in enumerate(representatives):
            _cache[keys[i]] = (normalized[i].copy(), amplitudes[j].copy(), float(explained[j]))
    result = np.stack([_cache[key][1]*s for key, s in zip(keys, scale)])
    explained = np.array([_cache[key][2] for key in keys])
    while len(_cache) > CAPACITY:
        _cache.popitem(last=False)
    _stats['rows'] += len(magnitude)
    return result, explained
