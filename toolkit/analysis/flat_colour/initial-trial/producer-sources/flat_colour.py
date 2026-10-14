"""Optional host encoder: solid Spectrum colours with source-aware cell seams.

Every logical sample normally selects one actual PAPER/INK endpoint. Search
all 56 canonical normal/BRIGHT pairs, then coordinate neighbouring cells only
within a bounded current-source error allowance. No temporal blending, error
diffusion, frame-dependent dither phase or native player changes are used.
"""
import numpy as np

import five_level_dither as five
from cell_palette_quality import ATTRS, PAIRS, PALETTES, averaged
from stable_colour import CHROMA, cells

Y = np.array([.2126, .7152, .0722], dtype=np.float32)
PARAMETERS = dict(chroma_weight=.35, luma_weight=.25, detail_weight=.75, seam_weight=2.,
    seam_source_rms=20., source_score_allowance=768., spatial_passes=3,
    quiet_max_component_delta=4., temporal_score_allowance=64.,
    minimal_samples_per_cell=1, minimal_grain_weight=.25,
    minimal_required_gain=512., contour_drop=24, contour_samples_per_cell=2,
    region_spatial_radius=3., region_colour_radius=24., region_join_rms=8.,
    region_minimum_samples=8, region_max_component_pull=12.)


def colour_error(delta):
    """Encoded-RGB error, including opponent colour and Rec.709 luma terms."""
    return (np.mean(delta**2, axis=-1)
        + PARAMETERS['chroma_weight']*np.mean((delta @ CHROMA)**2, axis=-1)
        + PARAMETERS['luma_weight']*(delta @ Y)**2)


def seam_cost(residuals, selected, source):
    """Charge artificial jumps at cell borders; actual source edges relax it.

    Compare output-minus-source on both sides. Red/black coordinate updates
    below never update adjacent cells simultaneously. This is a bounded local
    optimization, not a claim of a globally optimal segmentation.
    """
    candidate = residuals.reshape(24, 32, 4, 4, len(ATTRS), 3)
    current = residuals[np.arange(768), :, selected].reshape(24, 32, 4, 4, 3)
    original = source.reshape(24, 32, 4, 4, 3)
    score = np.zeros((24, 32, len(ATTRS)), np.float32)
    for a, b, ca, cb in (
        (np.s_[:, 1:, :, 0], np.s_[:, :-1, :, -1], np.s_[:, 1:], np.s_[:, :-1]),
        (np.s_[1:, :, 0], np.s_[:-1, :, -1], np.s_[1:], np.s_[:-1])):
        weight = np.exp(-np.mean((original[a]-original[b])**2, axis=-1)
            / PARAMETERS['seam_source_rms']**2)
        score[ca] += (np.mean((candidate[a]-current[b][..., None, :])**2,
            axis=-1)*weight[..., None]).mean(axis=-2)
        score[cb] += (np.mean((candidate[b]-current[a][..., None, :])**2,
            axis=-1)*weight[..., None]).mean(axis=-2)
    return score.reshape(768, -1)/4


def detail_cost(residuals, source):
    """Preserve source-defined internal shape/face edges, including hue edges.

    Charge lost or distorted gradients inside a cell rather than drawing a
    generic rectangle or sharpening native dither. Weak texture receives less
    weight. This measures image structure; it cannot recognize a person.
    """
    proposed = residuals.reshape(768, 4, 4, len(ATTRS), 3)
    original = source.reshape(768, 4, 4, 3)
    result = np.zeros((768, len(ATTRS)), np.float32)
    for a, b in ((np.s_[:, :, 1:], np.s_[:, :, :-1]),
                 (np.s_[:, 1:], np.s_[:, :-1])):
        contrast = np.mean((original[a]-original[b])**2, axis=-1)
        weight = np.minimum(1., contrast/32**2)
        result += (np.mean((proposed[a]-proposed[b])**2, axis=-1)
            *weight[..., None]).mean(axis=(1, 2))
    return result/2


def validate_state(state):
    if len(state) != five.STATE_BYTES:
        raise ValueError('expected 4608-byte five-level state')
    attrs = np.frombuffer(bytes(state[3840:]), np.uint8)
    if np.any(attrs & 128):
        raise ValueError('FLASH is not supported')
    five.unpack_levels(bytes(state[:3840]))
    return attrs


def region_guidance(image):
    """OpenCV mean-shift regions guide smooth fills; source features stay fixed.

    Connect adjacent similar filtered colours, never attribute-cell rectangles.
    Average sufficiently large regions using ORIGINAL source RGB, limiting each
    component's pull to 12 codes. Protect a one-sample neighbourhood of strong
    original colour edges so eyes, mouths and silhouettes are not smoothed.
    This is unsupervised colour segmentation, not semantic person detection.
    """
    import cv2
    active = np.ascontiguousarray(image[12:84])
    filtered = cv2.pyrMeanShiftFiltering(active,
        PARAMETERS['region_spatial_radius'], PARAMETERS['region_colour_radius'], maxLevel=0)
    height, width = active.shape[:2]
    ids = np.arange(height*width).reshape(height, width)
    parent = np.arange(height*width)
    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]];index = parent[index]
        return index
    filtered = filtered.astype(np.float32)
    for a, b in ((np.s_[:, 1:], np.s_[:, :-1]), (np.s_[1:], np.s_[:-1])):
        join = np.mean((filtered[a]-filtered[b])**2, axis=-1) <= PARAMETERS['region_join_rms']**2
        for first, second in zip(ids[a][join], ids[b][join]):
            x, y = root(first), root(second)
            if x != y:parent[max(x, y)] = min(x, y)
    labels = np.array([root(i) for i in range(height*width)]).reshape(height, width)
    _, labels = np.unique(labels, return_inverse=True);labels = labels.reshape(height, width)
    count = np.bincount(labels.ravel())
    original = active.astype(np.float32)
    means = np.stack([np.bincount(labels.ravel(), weights=original[..., c].ravel())/count
        for c in range(3)], axis=-1)[labels]
    protected = np.zeros((height, width), np.uint8)
    for a, b in ((np.s_[:, 1:], np.s_[:, :-1]), (np.s_[1:], np.s_[:-1])):
        edge = np.mean((original[a]-original[b])**2, axis=-1) > 24**2
        protected[a] |= edge;protected[b] |= edge
    protected = cv2.dilate(protected, np.ones((3, 3), np.uint8)) != 0
    eligible = (count[labels] >= PARAMETERS['region_minimum_samples']) & ~protected
    target = original+np.where(eligible[..., None], np.clip(means-original,
        -PARAMETERS['region_max_component_pull'], PARAMETERS['region_max_component_pull']), 0)
    full = image.astype(np.float32);full[12:84] = target
    return cells(full)


def contour_target(image, target):
    """Reuse source-RGB soft edges, limiting treatment to two samples per cell.

    Edges are image gradients, not recognized object outlines. Darken the
    fitting target by at most 24 codes before endpoint quantization. No black
    line is forcibly painted across already accurate output colours.
    """
    from monochrome_contours import edge_mask
    mask = cells(edge_mask(image)[..., None])[..., 0]
    # A fixed raster order makes crowded cells deterministic and bounded.
    mask &= np.cumsum(mask, axis=1) <= PARAMETERS['contour_samples_per_cell']
    return np.maximum(0, target-mask[..., None]*PARAMETERS['contour_drop'])


def minimal_levels(source, levels, selected):
    """Allow one quarter-level sample per cell only for a substantial gain.

    The native fixed 2x2 table creates the actual dots. Endpoint variance is
    charged explicitly, and the hard count prevents a textured whole-image
    fallback. There is no error propagation into other cells or frames.
    """
    palette = PALETTES[selected].astype(np.float32)
    delta = source[:, :, None]-palette[:, None]
    distance = colour_error(delta)
    variance = (np.arange(5)/4*(1-np.arange(5)/4))[None]
    variance = variance*np.mean((PAIRS[selected, 1]-PAIRS[selected, 0])**2, axis=-1)[:, None]
    penalized = distance+PARAMETERS['minimal_grain_weight']*variance[:, None]
    shades = penalized.argmin(axis=2)
    gain = penalized[np.arange(768)[:, None], np.arange(16), levels]
    gain -= penalized.min(axis=2)
    gain = np.where((shades > 0) & (shades < 4), gain, -np.inf)
    best = gain.argmax(axis=1)
    take = gain[np.arange(768), best] >= PARAMETERS['minimal_required_gain']
    result = levels.copy()
    result[np.flatnonzero(take), best[take]] = shades[np.flatnonzero(take), best[take]]
    return result


def encode(image, previous=None, previous_image=None, *, dither='none', contours=False, vision='none'):
    image = np.asarray(image)
    if image.shape != (96, 128, 3) or image.dtype != np.uint8:
        raise ValueError('expected uint8 RGB 128x96')
    if dither not in ('none', 'minimal'):
        raise ValueError('dither must be none or minimal')
    if vision not in ('none', 'regions'):
        raise ValueError('vision must be none or regions')
    if (previous is None) != (previous_image is None):
        raise ValueError('temporal feedback needs both previous source and output')
    source = cells(image.astype(np.float32))
    target = region_guidance(image) if vision == 'regions' else source
    if contours:target = contour_target(image, target)
    pairs = PAIRS.astype(np.float32)
    distance = colour_error(target[:, :, None, None]-pairs[None, None])
    endpoints = distance.argmin(axis=3).astype(np.uint8)*4
    candidates = pairs[np.arange(len(ATTRS))[None, None], endpoints//4]
    residuals = candidates-source[:, :, None]
    spatial = colour_error(candidates-target[:, :, None]).mean(axis=1)
    best = spatial.min(axis=1)
    close = spatial <= best[:, None]+PARAMETERS['source_score_allowance']
    # Exact representable cells must not be sacrificed for neighbour harmony.
    exact = np.mean(residuals**2, axis=(1, 3)).min(axis=1) == 0
    close[exact] &= np.mean(residuals[exact]**2, axis=(1, 3)) == 0
    structural = PARAMETERS['detail_weight']*detail_cost(residuals, source)
    selected = np.where(close, spatial+structural, np.inf).argmin(axis=1)
    yy, xx = np.indices((24, 32));checker = ((yy+xx) % 2).ravel()
    for _ in range(PARAMETERS['spatial_passes']):
        for parity in (0, 1):
            score = spatial+structural+PARAMETERS['seam_weight']*seam_cost(residuals, selected, source)
            proposal = np.where(close, score, np.inf).argmin(axis=1)
            selected[checker == parity] = proposal[checker == parity]
    output_levels = endpoints[np.arange(768), :, selected].copy()
    if dither == 'minimal':
        output_levels = minimal_levels(target, output_levels, selected)
    attrs = ATTRS[selected].copy()
    if previous is not None:
        previous_image = np.asarray(previous_image)
        if previous_image.shape != image.shape or previous_image.dtype != np.uint8:
            raise ValueError('invalid previous source RGB')
        old_attrs = validate_state(previous)
        old_levels = cells(five.unpack_levels(bytes(previous[:3840]))[..., None])[..., 0]
        quiet = np.max(np.abs(source-cells(previous_image.astype(np.float32))), axis=(1, 2)) <= 4
        old_error = colour_error(cells(averaged(previous))-target).mean(axis=1)
        current_error = colour_error(PALETTES[selected[:, None], output_levels]-target).mean(axis=1)
        fractional = ((old_levels > 0) & (old_levels < 4)).sum(axis=1)
        valid = np.isin(old_attrs, ATTRS) & (fractional <= (1 if dither == 'minimal' else 0))
        retain = quiet & valid & (old_error <= current_error+PARAMETERS['temporal_score_allowance'])
        # Exact new source colours are not delayed by the history allowance.
        retain &= ~exact | (np.mean((cells(averaged(previous))-source)**2, axis=(1, 2)) == 0)
        output_levels[retain] = old_levels[retain];attrs[retain] = old_attrs[retain]
    levels = output_levels.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128)
    levels[:12] = levels[84:] = 0
    attrs[:96] = attrs[672:] = 1
    return five.pack_levels(levels)+attrs.tobytes()


def comparison_report(comparison, *, dither='none', contours=False, vision='none'):
    report = comparison.report()
    report.pop('rgb_sample_bound');report.pop('chroma_sample_bound');report.pop('parameters')
    report.update(selector='solid endpoints with source-aware cell coordination',
        parameters=PARAMETERS.copy(), dither=dither, contours=contours, vision=vision,
        source_guard_scope='Per-cell current-target score <= endpoint optimum + 768. Exact source cells remain exact. No bound against the older dithered quantizer is claimed.',
        actual_pixel_error_bounded_by_old_quantizer=False,
        minimal_dither_limit='At most one logical 2x2 sample per active 8x8 cell',
        contour_scope='Source RGB edges, not semantic objects; at most two logical samples darkened by 24 target codes per cell',
        vision_scope='Unsupervised mean-shift colour regions, source-bounded 12-code pull, strong source detail protected; no neural or semantic person detector')
    return report
