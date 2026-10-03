"""Offline bounded trellis encoder for the unchanged four-bit IMA decoder.

Keep distinct (predictor, index) states, minimize PCM16 squared error over
64-sample blocks, and retain the exact state across blocks. Saturating
transitions are forbidden, as required by the existing guarded Z80 decoder.
The output is still ordinary low-nibble-first headerless IMA ADPCM.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time
import wave

import numpy as np

from ima_codec import STEPS, INDEX, decode, require_unclipped


def code_alphabet(allowed_codes=None):
    """Use actual IMA nibbles; a restricted alphabet keeps the same decoder."""
    codes = np.arange(16) if allowed_codes is None else np.asarray(allowed_codes)
    if (codes.ndim != 1 or not len(codes) or not np.issubdtype(codes.dtype, np.integer)
            or np.any(codes < 0) or np.any(codes > 15) or len(np.unique(codes)) != len(codes)):
        raise ValueError('allowed codes must be unique IMA nibbles')
    return codes.astype(np.int64)


def encode(pcm8, width=32, block_samples=64, predictor=0, index=0, allowed_codes=None):
    if len(pcm8) % 2 or width < 1 or block_samples < 2 or block_samples % 2:
        raise ValueError('need even samples/block length and a positive beam width')
    steps = np.asarray(STEPS, dtype=np.int64)[:, None]
    codes = code_alphabet(allowed_codes)
    branches = len(codes)
    delta = ((steps >> 3) + (steps * ((codes & 4) != 0)) +
             ((steps >> 1) * ((codes & 2) != 0)) + ((steps >> 2) * ((codes & 1) != 0)))
    delta *= np.where(codes & 8, -1, 1)
    successor = np.clip(np.arange(89)[:, None] + np.asarray(INDEX)[codes & 7], 0, 88)
    chosen = np.empty(len(pcm8), dtype='u1')
    target = (np.asarray(pcm8, dtype=np.int64) - 128) * 256
    for start in range(0, len(target), block_samples):
        block = target[start:start + block_samples]
        preds = np.array([predictor], dtype=np.int64)
        indices = np.array([index], dtype=np.int64)
        costs = np.zeros(1, dtype=np.int64)
        paths = np.zeros((1, len(block)), dtype='u1')
        for position, sample in enumerate(block):
            predicted = (preds[:, None] + delta[indices]).reshape(-1)
            next_indices = successor[indices].reshape(-1)
            score = (costs[:, None] + (predicted.reshape(-1, branches) - sample) ** 2).reshape(-1)
            valid = (predicted >= -32768) & (predicted <= 32767)
            ids = np.flatnonzero(valid)
            # Merge equivalent decoder states before beam pruning. Otherwise
            # duplicate code paths can consume the entire beam without looking ahead.
            key = (predicted[ids] + 32768) * 89 + next_indices[ids]
            order = np.lexsort((ids, score[ids], key))
            ordered = ids[order]
            unique = np.r_[True, key[order][1:] != key[order][:-1]]
            ordered = ordered[unique]
            best = ordered[np.lexsort((ordered, score[ordered]))[:width]]
            paths = paths[best // branches].copy()
            paths[:, position] = codes[best % branches]
            preds, indices, costs = predicted[best], next_indices[best], score[best]
        chosen[start:start + len(block)] = paths[0]
        predictor, index = int(preds[0]), int(indices[0])
    return bytes((chosen[::2] | (chosen[1::2] << 4)).tolist())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--width', type=int, default=32)
    args = p.parse_args()
    with wave.open(str(args.source), 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 1, 8000)
        source = np.frombuffer(w.readframes(w.getnframes()), 'u1')
    started = time.monotonic()
    packed = encode(source, args.width)
    guard = require_unclipped(packed)
    pcm, _ = decode(packed)
    original = (source.astype(np.int64) - 128) * 256
    snr = float(10 * np.log10(np.mean(original ** 2) / np.mean((pcm - original) ** 2)))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
    report = dict(scope='Offline encoder only; no new native player', samples=len(source),
                  beam_width=args.width, block_samples=64, seconds=time.monotonic()-started,
                  source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                  packed_sha256=hashlib.sha256(packed).hexdigest(), packed_bytes=len(packed),
                  raw_pcm16_snr_db=snr, saturation_guard=guard)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
