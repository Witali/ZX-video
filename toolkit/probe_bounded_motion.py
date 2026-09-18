"""Pixel-bounded correction suppression during motion-vector search.

FMR1 format/decoder are unchanged. The PC can omit an entire packed-byte
correction only when its quarter-coverage errors fit the per-cell limits.
Each native 8x8 cell may be inexact for at most --max-inexact consecutive
frames; all errors are checked against the current original frame. A global
logical-pixel budget further limits each frame. For permitted quarter-step
changes each logical change alters one native dither pixel. Attribute bytes
remain exact. This is an offline experiment, not a playable release.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_bounded_dictionary import (COVERAGE, accept_pattern, bitmap_cells,
                                      compact_states, contrast_squared, quality)
from probe_exact_dictionary import STATES_SHA256
import probe_fine_motion as motion
from probe_lossless_layouts import measure, sha


def error_tables():
    levels = COVERAGE[(np.arange(256)[:, None] >> np.array([6, 4, 2, 0])) & 3]
    delta = levels[:, None, :] - levels[None, :, :]
    return (np.count_nonzero(delta, axis=2).astype(np.uint8),
            np.abs(delta).max(axis=2).astype(np.uint8),
            (delta * delta).sum(axis=2).astype(np.uint16))


CHANGES, MAX_DELTA, SQUARED = error_tables()


def choose_omissions(original, candidates, attrs, ages, maximum_changed, rmse, max_inexact):
    """Greedily remove profitable whole-byte corrections within each 8x8 cell."""
    changed = CHANGES[original, candidates]
    squared = SQUARED[original, candidates]
    difference = original ^ candidates
    gain = 8 + motion.POPCOUNT[difference].astype(np.int16)
    allowed = (changed > 0) & (MAX_DELTA[original, candidates] <= 1)
    allowed &= (ages < max_inexact)[None, :, None]
    selected = np.zeros(candidates.shape, dtype=bool)
    used = np.zeros(candidates.shape[:2], dtype=np.int16)
    error = np.zeros(candidates.shape[:2], dtype=np.int16)
    contrast = contrast_squared(attrs)
    for _ in range(4):
        eligible = allowed & ~selected & (used[..., None] + changed <= maximum_changed)
        eligible &= (error[..., None] + squared) * contrast[None, :, None] <= rmse**2 * 256
        score = np.where(eligible, gain / np.maximum(changed, 1), -1)
        row = score.argmax(axis=2)
        take = np.take_along_axis(score, row[..., None], axis=2)[..., 0] >= 0
        if not take.any():
            break
        chosen = np.eye(4, dtype=bool)[row] & take[..., None]
        selected |= chosen
        used += (changed * chosen).sum(axis=2, dtype=np.int16)
        error += (squared * chosen).sum(axis=2, dtype=np.int16)
    return selected, changed


def predict(states, offsets, maximum_changed=2, budget=128, max_inexact=1, rmse=24):
    size = 8
    reference = bitmap_cells(states)
    cells_y, cells_x = np.divmod(np.arange(768), 32)
    tile_for_cell = (cells_y // 2) * 16 + cells_x // 2
    vectors = np.empty((len(states), 192), dtype=np.uint8)
    residual = np.empty_like(states)
    filtered = np.empty_like(states)
    previous = np.zeros(3840, dtype=np.uint8)
    ages = np.zeros(768, dtype=np.int16)
    maximum_age = 0
    errors_per_frame = []
    for frame, current in enumerate(states):
        raster = motion.shifted_candidates(previous[:3072], offsets)
        candidates = raster.reshape(-1, 24, 4, 32).transpose(0, 1, 3, 2).reshape(-1, 768, 4)
        original = reference[frame][None]
        omit, changed = choose_omissions(original, candidates, current[3072:], ages,
                                          maximum_changed, rmse, max_inexact)
        delta = np.where(omit, 0, original ^ candidates)
        cost = 8 * np.count_nonzero(delta, axis=2) + motion.POPCOUNT[delta].sum(axis=2)
        cost = cost.reshape(-1, 12, 2, 16, 2).sum(axis=(2, 4)).reshape(-1, 192)
        cost[1:] += 8
        distortion = (changed * omit).sum(axis=2).reshape(-1, 12, 2, 16, 2).sum(axis=(2, 4)).reshape(-1, 192)
        chosen = (cost * 257 + distortion).argmin(axis=0)
        vectors[frame] = chosen
        selected = chosen[tile_for_cell]
        predicted = candidates[selected, np.arange(768)]
        pending = omit[selected, np.arange(768)]
        changes = changed[selected, np.arange(768)]
        # The search uses local costs. Apply the independent global budget
        # afterwards; corrections restored here make the stream exact there.
        pending_ids = np.flatnonzero(pending)
        gain = 8 + motion.POPCOUNT[reference[frame] ^ predicted]
        ratios = gain.ravel()[pending_ids] / changes.ravel()[pending_ids]
        order = pending_ids[np.argsort(-ratios, kind='stable')]
        keep = np.zeros(3072, dtype=bool)
        used = 0
        for index in order:
            count = int(changes.ravel()[index])
            if used + count <= budget:
                keep[index] = True
                used += count
        keep = keep.reshape(768, 4)
        result = np.where(keep, predicted, reference[frame])
        if not accept_pattern(reference[frame], result, current[3072:], rmse, maximum_changed).all():
            raise AssertionError('per-cell reference error exceeded')
        inexact = np.any(result != reference[frame], axis=1)
        ages = np.where(inexact, ages + 1, 0)
        maximum_age = max(maximum_age, int(ages.max()))
        if maximum_age > max_inexact or used > budget:
            raise AssertionError('temporal/global limit exceeded')
        errors_per_frame.append(used)
        filtered[frame] = compact_states(result[None], current[None, 3072:])[0]
        predicted_raster = compact_states(predicted[None], previous[None, 3072:])[0]
        residual[frame] = filtered[frame] ^ predicted_raster
        previous = filtered[frame]
        if frame % 500 == 0:
            print(f'Bounded motion p{maximum_changed} b{budget}: {frame}/{len(states)}', flush=True)
    return vectors, residual, filtered, dict(maximum_consecutive_inexact_frames=maximum_age,
                                            logical_changes_per_frame=errors_per_frame,
                                            max_logical_changes_per_frame=max(errors_per_frame, default=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--budgets', type=int, nargs='+', default=[64, 128, 256])
    parser.add_argument('--maximum-changed', type=int, default=2)
    parser.add_argument('--max-inexact', type=int, default=1)
    parser.add_argument('--rmse', type=float, default=24)
    parser.add_argument('--groups', type=int, nargs='+', default=[8, 16])
    args = parser.parse_args()
    if (any(n < 0 for n in args.budgets) or not 0 <= args.maximum_changed <= 16
            or args.max_inexact < 1 or not np.isfinite(args.rmse) or args.rmse < 0
            or any(not 1 <= n <= 65535 for n in args.groups)):
        parser.error('invalid bounds')
    with np.load(args.checkpoint) as saved:
        states = saved['states'].astype(np.uint8)
    if states.shape != (4971, 3840) or sha(states.tobytes()) != STATES_SHA256:
        raise ValueError('unexpected full movie')
    offsets = [(0, 0)] + [(x, y) for y in range(-4, 5) for x in range(-4, 5) if x or y]
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(scope=__doc__, baseline_commit='66257b4', reference_sha256=STATES_SHA256,
                  frames=len(states), resolution=[256, 192], logical_resolution=[128, 96], fps='25/3',
                  maximum_changed_pixels_per_cell=args.maximum_changed, max_inexact_frames=args.max_inexact,
                  rmse_limit=args.rmse, offsets=offsets, vector_penalty=8,
                  audio='unchanged; excluded from size', player_changed=False, hot_path_delta_tstates=0,
                  complete=False, rows=[])
    for budget in args.budgets:
        name = f'bounded_motion_p{args.maximum_changed}_b{budget}_a{args.max_inexact}_e{args.rmse:g}'
        vectors, residual, filtered, stats = predict(states, offsets, args.maximum_changed,
                                                    budget, args.max_inexact, args.rmse)
        np.savez_compressed(args.cache / (name + '.npz'), states=filtered, vectors=vectors, residual=residual)
        row = dict(name=name, frame_change_budget=budget, states_sha256=sha(filtered.tobytes()),
                   temporal=stats, quality=quality(states, filtered), layouts=[])
        report['rows'].append(row)
        for group in args.groups:
            data = motion.encode(vectors, residual, 8, offsets, group)
            raw_name = f'{name}_g{group}'
            (args.cache / (raw_name + '.raw')).write_bytes(data)
            if not np.array_equal(motion.decode(data), filtered):
                raise AssertionError('independent FMR1 decode differs from chosen frames')
            item = dict(name=raw_name, group_frames=group, vector_mask_ram_bytes=672 * group,
                        raw_bytes=len(data), stream_sha256=sha(data), exact_to_filtered=True,
                        deflate={str(n): measure(data, n) for n in (8192, len(data))})
            row['layouts'].append(item)
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(item), flush=True)
        print(json.dumps(dict(name=name, quality=row['quality'])), flush=True)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
