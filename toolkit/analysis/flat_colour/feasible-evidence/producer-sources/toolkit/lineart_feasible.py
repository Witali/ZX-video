"""Source-close NORMAL/BRIGHT fill alternatives with unchanged line geometry.

The existing line selector fixes a fill endpoint before imposing the shared
BRIGHT bit. Here optional fills may use the other brightness of the *same*
accepted source hue, if it passes the original RGB limits and improves on
paper. Contours, black regions and unmatched paper remain mandatory.
"""
import numpy as np

import five_level_dither as five
import lineart_colour as line
from cell_palette_quality import ATTRS, PAIRS, averaged
from stable_colour import cells, hue_valid


def encode(image, previous=None, previous_image=None):
    image = line.validate(image)
    if (previous is None) != (previous_image is None):
        raise ValueError('temporal inputs must be supplied together')
    if previous_image is not None:line.validate(previous_image)
    fills = line.source_fills(image)
    desired = fills.copy();desired[line.source_lines(image)] = 0
    desired[:12] = desired[84:] = 0
    labels = cells(desired[..., None])[..., 0]
    source = cells(image).astype(np.float32)
    target = line.COLOURS[labels]
    original_delta = source[:, :, None, None]-PAIRS[None, None]
    original_error = np.mean(original_delta**2, axis=-1)
    target_error = np.mean((target[:, :, None, None]-PAIRS[None, None])**2, axis=-1)
    optional = (labels != 0) & (labels != 7)
    paper = np.all(PAIRS == line.COLOURS[7], axis=-1)
    # Pair endpoints are uniquely identified by the native RGB table, except
    # duplicate black. Neither duplicate can be used by an optional fill.
    endpoint_hue = np.argmin(np.mean((PAIRS[:, :, None]-line.COLOURS[None, None])**2, axis=-1), axis=-1) & 7
    same_hue = endpoint_hue[None, None] == (labels[:, :, None, None] & 7)
    within_bounds = (original_error <= line.PARAMETERS['fill_rgb_rms_max']**2)
    within_bounds &= np.max(np.abs(original_delta), axis=-1) <= line.PARAMETERS['fill_max_component_delta']
    within_bounds &= hue_valid(source[:, :, None, None], PAIRS[None, None], line.PARAMETERS['fill_hue_degrees'])
    paper_error = np.mean((source-line.COLOURS[7])**2, axis=-1)
    alternate = same_hue & within_bounds & (original_error < paper_error[:, :, None, None])
    allowed = target_error == 0
    allowed |= optional[:, :, None, None] & (paper[None, None] | alternate)
    baseline = cells(averaged(line.encode(image)))
    baseline_error = np.mean((source-baseline)**2, axis=-1)
    allowed &= ~optional[:, :, None, None] | (original_error <= baseline_error[:, :, None, None])
    # Optional source error picks the closest feasible endpoint; mandatory
    # black/paper use zero cost, since their source overrides are intentional.
    score = np.where(allowed, np.where(optional[:, :, None, None], original_error, 0), np.inf)
    nearest = score.argmin(axis=-1)
    valid = allowed.any(axis=-1).all(axis=1)
    cost = score.min(axis=-1).sum(axis=1)
    selected = np.where(valid, cost, np.inf).argmin(axis=1)
    if not np.isfinite(cost[np.arange(768), selected]).all():
        raise AssertionError('missing exact black/white fallback')
    levels = nearest[np.arange(768), :, selected].astype(np.uint8)*4
    levels = levels.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128)
    attrs = ATTRS[selected].copy()
    levels[:12] = levels[84:] = 0;attrs[:96] = attrs[672:] = 1
    return five.pack_levels(levels)+attrs.tobytes()
