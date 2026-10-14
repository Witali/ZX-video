"""Source-RGB line drawing, with only well-matched solid Spectrum fills.

Keep a uniform NORMAL-white paper. Draw current-source contours in black,
then fill sufficiently coherent near-native black/colour regions. Hardware
cells with three required colours lose optional colour fill before losing
black detail or tinting the paper. No artificial cell outline or dither.
"""
import cv2
import numpy as np

import five_level_dither as five
from cell_palette_quality import ATTRS, PAIRS, averaged
from stable_colour import cells, hue_valid

COLOURS = np.array([[(255 if c & 8 else 205) if c & mask else 0
    for mask in (2, 4, 1)] for c in range(16)], np.float32)
PARAMETERS = dict(paper_rgb=[205, 205, 205], fine_sigma=.4,
    fine_canny_low=24, fine_canny_high=48, coarse_sigma=.9,
    coarse_canny_low=40, coarse_canny_high=80, minimum_line_samples=2,
    fill_rgb_rms_max=60., fill_max_component_delta=100.,
    fill_hue_degrees=30., black_max_component=64.,
    minimum_colour_region_samples=4, minimum_black_region_samples=2,
    source_colour_fill_priority=6., empty_paper_priority=1.)


def validate(image):
    image = np.asarray(image)
    if image.shape != (96, 128, 3) or image.dtype != np.uint8:
        raise ValueError('expected uint8 RGB 128x96')
    return image


def source_lines(image):
    """Trace fine RGB detail and larger silhouettes before palette quantizing.

    Both scales use current-source multichannel Canny and fixed thresholds.
    The detector never sees output pixels, dither or the attribute-cell grid.
    Short-component filtering removes isolated specks without discarding small
    connected eye/mouth lines. This is image tracing, not semantic detection.
    """
    image = validate(image)
    active = np.ascontiguousarray(image[12:84])
    fine = cv2.GaussianBlur(active, (3, 3), PARAMETERS['fine_sigma'], borderType=cv2.BORDER_REPLICATE)
    coarse = cv2.GaussianBlur(active, (5, 5), PARAMETERS['coarse_sigma'], borderType=cv2.BORDER_REPLICATE)
    lines = cv2.Canny(fine, PARAMETERS['fine_canny_low'], PARAMETERS['fine_canny_high'], L2gradient=True)
    lines |= cv2.Canny(coarse, PARAMETERS['coarse_canny_low'], PARAMETERS['coarse_canny_high'], L2gradient=True)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(lines, connectivity=8)
    keep = np.zeros(count, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= PARAMETERS['minimum_line_samples']
    mask = np.zeros((96, 128), bool);mask[12:84] = keep[labels]
    return mask


def source_fills(image, *, dark_fills=False):
    """Accept only original RGB sufficiently close to an actual chip colour.

    Strong colour labels must form a small connected region, independently of
    cell borders. Every other area remains white paper, not a guessed saturated
    substitute for source brown/gray. Black has an additional component bound.
    """
    image = validate(image);original = image[12:84].astype(np.float32)
    delta = original[:, :, None]-COLOURS[None, None]
    distance = np.mean(delta**2, axis=-1)
    eligible = (distance <= PARAMETERS['fill_rgb_rms_max']**2)
    eligible &= np.max(np.abs(delta), axis=-1) <= PARAMETERS['fill_max_component_delta']
    eligible &= hue_valid(original[:, :, None], COLOURS[None, None], PARAMETERS['fill_hue_degrees'])
    black_limit = PARAMETERS['fill_max_component_delta'] if dark_fills else PARAMETERS['black_max_component']
    eligible[:, :, 0] &= original.max(axis=-1) <= black_limit
    # White is the fixed paper, not an extra coloured label.
    eligible[:, :, 7] = eligible[:, :, 15] = eligible[:, :, 8] = False
    selected = np.where(eligible, distance, np.inf).argmin(axis=-1)
    result = np.full((72, 128), 7, np.uint8)
    for colour in (*range(7), *range(9, 15)):
        proposed = eligible[:, :, colour] & (selected == colour)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(proposed.astype(np.uint8), connectivity=8)
        keep = np.zeros(count, bool)
        minimum = PARAMETERS['minimum_black_region_samples'] if colour == 0 else PARAMETERS['minimum_colour_region_samples']
        keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= minimum
        result[keep[labels]] = colour
    full = np.full((96, 128), 7, np.uint8);full[12:84] = result
    return full


def render_fills(fills, line_mask):
    """Prioritize contours and black regions over optional third-colour fills.

    Every selected endpoint must be either the exact classified source colour
    or white. Required black and white samples must remain exact. This gives
    a valid black/white fallback in every cell, and prevents colour rectangular
    spills where the Spectrum cannot fit contour/paper/fill simultaneously.
    History is intentionally unused: every mask follows the current source.
    """
    desired = fills.copy();desired[line_mask] = 0
    desired[:12] = desired[84:] = 0
    labels = cells(desired[..., None])[..., 0]
    target = COLOURS[labels]
    delta = target[:, :, None, None]-PAIRS[None, None]
    distance = np.mean(delta**2, axis=-1)
    allowed = distance == 0
    optional_colour = (labels != 0) & (labels != 7)
    paper = np.all(PAIRS == COLOURS[7], axis=-1)
    allowed |= optional_colour[:, :, None, None] & paper[None, None]
    score = np.where(allowed, distance, np.inf)
    nearest = score.argmin(axis=-1)
    valid = allowed.any(axis=-1).all(axis=1)
    weight = np.where(optional_colour, PARAMETERS['source_colour_fill_priority'], PARAMETERS['empty_paper_priority'])
    cost = (score.min(axis=-1)*weight[:, :, None]).mean(axis=1)
    selected = np.where(valid, cost, np.inf).argmin(axis=1)
    if not np.isfinite(cost[np.arange(768), selected]).all():
        raise AssertionError('missing exact black/white fallback')
    levels = nearest[np.arange(768), :, selected].astype(np.uint8)*4
    levels = levels.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128)
    attrs = ATTRS[selected].copy()
    levels[:12] = levels[84:] = 0;attrs[:96] = attrs[672:] = 1
    return five.pack_levels(levels)+attrs.tobytes()


def select_fills(image, *, dark_fills=False):
    """Roll back source-connected new dark regions if a cell loses accuracy.

    Adding mandatory black to a white/colour cell can displace its old colour.
    Reject every added dark component touching such a cell, not just its cell
    fragment, then rerender. Rejection is monotonic and eventually reaches the
    original feasible image. Existing black/colour/line pixels remain exact;
    every changed pixel strictly reduces original RGB error. No old frame is
    involved and accepted dark-region geometry never follows the cell grid.
    """
    image = validate(image);lines = source_lines(image)
    original_fills = source_fills(image)
    original_state = render_fills(original_fills, lines)
    if not dark_fills:return original_state, original_fills
    proposed = source_fills(image, dark_fills=True)
    added = (proposed == 0) & (original_fills != 0)
    count, labels = cv2.connectedComponents(added.astype(np.uint8), connectivity=8)
    original = averaged(original_state)
    original_error = np.mean((original-image)**2, axis=-1)
    retained = np.ones(count, bool);retained[0] = False
    for _ in range(count):
        fills = np.where(retained[labels], proposed, original_fills).astype(np.uint8)
        state = render_fills(fills, lines);output = averaged(state)
        changed = np.any(output != original, axis=-1)
        bad = changed & (np.mean((output-image)**2, axis=-1) >= original_error)
        bad |= changed & (np.ptp(original, axis=-1) > 0)
        if not bad.any():return state, fills
        bad_cells = cells(bad[..., None])[..., 0].any(axis=1).reshape(24, 32)
        rejected = np.unique(labels[bad_cells.repeat(4, 0).repeat(4, 1) & retained[labels]])
        if not len(rejected):raise AssertionError('dark fill regression outside added regions')
        retained[rejected] = False
    raise AssertionError('non-monotonic dark fill selection')


def encode(image, previous=None, previous_image=None, *, dark_fills=False):
    image = validate(image)
    if (previous is None) != (previous_image is None):
        raise ValueError('temporal inputs must be supplied together')
    if previous_image is not None:validate(previous_image)
    return select_fills(image, dark_fills=dark_fills)[0]


def comparison_report(comparison, *, dark_fills=False):
    report = comparison.report()
    report.pop('rgb_sample_bound');report.pop('chroma_sample_bound');report.pop('parameters')
    report.update(selector='source-RGB line drawing with matched native solid fills',
        parameters=PARAMETERS.copy(), dither='none', contours=True,
        actual_pixel_error_bounded_by_old_quantizer=False,
        source_guard_scope='Stylistic line drawing. Fill labels are source-matched, but no photographic RGB error bound is claimed. Black contours and uniform white paper override unsupported optional third-colour fills.',
        available_fill_colours='Normal and BRIGHT Spectrum colours. Fixed white paper RGB205 must remain exact; cells with paper cannot select a BRIGHT colour.',
        semantic_person_model=False)
    report['dark_fills'] = dark_fills
    if dark_fills:
        report['parameters']['black_max_component'] = PARAMETERS['fill_max_component_delta']
        report['source_guard_scope'] += ' Dark fills admit black within the same RMS60/component100 source guard as coloured endpoints; isolated samples remain rejected.'
        report['dark_region_rollback'] = 'Reject whole source-connected added regions touching a cell with any pixel RGB regression or a changed old coloured pixel. Every accepted changed pixel strictly improves original RGB error.'
    return report
