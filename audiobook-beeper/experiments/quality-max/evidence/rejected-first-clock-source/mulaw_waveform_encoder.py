"""Offline G.711 search against the existing eight-pulse PDM player.

The stream remains standard one-byte mu-law. Only the PC searches: the Z80
still inverse-compands each byte and runs its unchanged exact accumulator.
The saved clock is a proposal, never a substitute for executing the result.
"""
import gzip
import time
from pathlib import Path

import numpy as np
from g711_codec import decode_table
from ima_waveform_encoder import WaveformModel, _best_unique
from waveform_kernel import workspace


def prepare(pcm, timeline):
    count = len(pcm) - 128
    holds = np.diff(timeline[:count * 8 + 1]).reshape(count, 8)
    unique, ids = np.unique(holds, axis=0, return_inverse=True)
    model = WaveformModel()
    # Split each physical hold into two equal integration intervals. This
    # reuses the tested 16-term kernel without inventing extra output edges.
    patterns = (((np.arange(256)[:, None] >> np.arange(8)) & 1) * 2 - 1)
    signed = np.repeat(patterns, 2, axis=1)
    features = []
    for row in unique:
        halves = np.repeat(row / 2, 2)
        a, b, l, r = model.packet(halves)
        features.append((a, l, signed @ r.T, signed @ b.T, halves / (3546900 / 8000)))
    starts = timeline[:count * 8].reshape(count, 8)
    queries = np.stack((starts + holds / 4, starts + holds * .75), axis=-1).reshape(count, 16)
    desired = model.reference(pcm.astype(float) / 256 + 128, queries)
    return desired, features, ids


def close_guard(chosen, error, levels):
    """Return the accumulator to its seed using only the silent guard.

    All mu-law levels are multiples of four. Eight pulses per sample make
    the residual a multiple of32; correcting the signed decoded sum modulo
    8192 therefore closes the exact16-bit state. Small +/-132,120,8 levels
    suffice in fewer than40 samples, below0.41% of DAC full-scale.
    """
    needed = ((32768-error)//8 + 4096) % 8192 - 4096
    lookup = {int(value)-32768:code for code,value in enumerate(levels)}
    values=[]
    if needed % 8:
        value = 132 if needed > 0 else -132
        values.append(value); needed-=value
    while needed:
        value = min(120,abs(needed)) * (1 if needed > 0 else -1)
        values.append(value);needed-=value
    assert len(values) <= 64
    for offset,value in enumerate(values):chosen[len(chosen)-64+offset]=lookup[value]
    assert (32768+8*sum(int(levels[code]) for code in chosen)) & 65535 == 32768


def encode(pcm, timeline, width=8, horizon=16, commit=8, regularization=.03,
           backend='auto', statistics=None):
    if not 1 <= commit <= horizon or width < 1 or regularization < 0:
        raise ValueError('invalid bounded mu-law search')
    desired, features, ids = prepare(pcm, timeline)
    levels = decode_table('mulaw').astype(np.int64) + 32768
    kernel = workspace(width, 256, backend)
    chosen = np.full(len(pcm), 255, dtype='u1')
    error = 32768
    state = np.zeros(6)
    tick = np.arange(9)
    shifts = 1 << np.arange(8)
    started = time.perf_counter()
    for start in range(0, len(ids), commit):
        stop = min(start + horizon, len(ids))
        errors = np.array([error]); states = state[None].copy(); costs = np.zeros(1)
        parents = np.empty((stop-start, width), dtype=np.intp)
        codes = np.empty((stop-start, width), dtype='u1')
        for sample in range(start, stop):
            a, l, response, endpoint, weights = features[ids[sample]]
            area = errors[:, None, None] + levels[None, :, None] * tick
            word = (np.diff(area // 65536, axis=2) @ shifts).ravel()
            next_error = (area[:, :, -1] & 65535).ravel()
            parent = np.repeat(np.arange(len(errors)), 256)
            base = states @ l.T
            if kernel is None:
                terms = (base[parent] + response[word] - desired[sample]) ** 2 * weights
            else:
                terms = kernel.errors(base, response, word, desired[sample], weights)
            score = costs[parent] + np.sum(terms, axis=1)
            score += regularization * np.tile(((levels-32768-pcm[sample]) / 32768) ** 2, len(errors))
            candidates = np.arange(len(score))
            best = (_best_unique(candidates, score, next_error, width) if kernel is None else
                    kernel.select(candidates, score, next_error))
            states = (states @ a.T)[parent[best]] + endpoint[word[best]]
            errors = next_error[best]; costs = score[best]
            parents[sample-start, :len(best)] = parent[best]
            codes[sample-start, :len(best)] = best % 256
        path = np.empty(stop-start, dtype='u1'); winner = 0
        for j in range(stop-start-1, -1, -1):
            path[j] = codes[j, winner]; winner = parents[j, winner]
        # Carry only the committed prefix. Speculative filter/accumulator
        # states beyond it must not leak into the next overlapping window.
        for sample, code in zip(range(start, min(start+commit, stop)), path):
            a, _, _, endpoint, _ = features[ids[sample]]
            area = error + levels[code] * tick
            word = int(np.diff(area // 65536) @ shifts)
            error = int(area[-1] & 65535)
            state = a @ state + endpoint[word]
            chosen[sample] = code
    close_guard(chosen,error,levels)
    if statistics is not None:
        statistics.update(width=width, horizon=horizon, commit=commit,
            regularization=regularization, seconds=time.perf_counter()-started,
            backend='native' if kernel else 'numpy', clock_patterns=len(features),
            z80_tstate_delta=0, spectrum_expanded_audio_bytes=0)
    return chosen.tobytes()


def saved_timeline(folder):
    return np.frombuffer(gzip.decompress((Path(folder)/'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)
