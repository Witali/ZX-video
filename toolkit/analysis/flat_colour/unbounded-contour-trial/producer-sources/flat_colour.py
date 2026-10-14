"""Optional host encoder: solid Spectrum colours with source-aware cell seams.

Every logical sample normally selects one actual PAPER/INK endpoint. Search
all 56 canonical normal/BRIGHT pairs, then coordinate neighbouring cells only
within a bounded current-source error allowance. No temporal blending, error
diffusion, frame-dependent dither phase or native player changes are used.
"""
import numpy as np

import five_level_dither as five
from cell_palette_quality import ATTRS, PAIRS, PALETTES, averaged
from stable_colour import CHROMA, cells, hue_valid

Y = np.array([.2126, .7152, .0722], dtype=np.float32)
PARAMETERS = dict(chroma_weight=.35, luma_weight=.25, detail_weight=.75, seam_weight=2., hue_limit_degrees=35.,
    seam_source_rms=20., source_score_allowance=768., spatial_passes=3,
    quiet_max_component_delta=4., temporal_score_allowance=64.,
    minimal_samples_per_cell=1, minimal_grain_weight=.25,
    minimal_required_gain=512., minimal_source_detail_rms=24.,
    contour_canny_low=40, contour_canny_high=80, contour_minimum_component=4,
    contour_source_rms=24., contour_retained_contrast=.5,
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


def source_contours(image):
    """Thin original-RGB lines; reject isolated texture and shift to dark side.

    The initial 7x7 soft detector/24-code target pull lost small facial detail.
    A 3x3 blur preserves smaller features. Dark-side placement traces an eye or
    mouth with the darker colour already available in the cell; the detector
    never sees attribute rectangles or the output's dither.
    """
    import cv2
    active = np.ascontiguousarray(image[12:84])
    smooth = cv2.GaussianBlur(active, (3, 3), .65, borderType=cv2.BORDER_REPLICATE)
    edges = cv2.Canny(smooth, PARAMETERS['contour_canny_low'],
        PARAMETERS['contour_canny_high'], L2gradient=True)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    keep = np.zeros(count, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= PARAMETERS['contour_minimum_component']
    points = np.argwhere(keep[labels])
    result = np.zeros((96, 128), bool)
    y = active.astype(float) @ Y
    for row, col in points:
        neighbors = [(int(row), int(col))]+[(int(row)+dy, int(col)+dx)
            for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0))
            if 0 <= row+dy < 72 and 0 <= col+dx < 128]
        r, c = min(neighbors, key=lambda at: y[at])
        result[r+12, c] = True
    return result


def paint_lost_contours(source, levels, selected, mask):
    """Restore only strong source lines lacking contrast in the filled output.

    Use the existing darker endpoint. Already retained boundaries and exact
    source cells are untouched. This intentionally trades colour/RGB accuracy
    for visible outlines; it is neither semantic recognition nor a fidelity
    bound. All work is on the host, with no extra native drawing pass.
    """
    output = PALETTES[selected[:, None], levels].reshape(24, 32, 4, 4, 3).transpose(
        0, 2, 1, 3, 4).reshape(96, 128, 3)
    original = source.reshape(24, 32, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(96, 128, 3)
    source_edge = np.zeros((96, 128));output_edge = np.zeros_like(source_edge)
    for a, b in ((np.s_[:, 1:], np.s_[:, :-1]), (np.s_[1:], np.s_[:-1])):
        src = np.mean((original[a]-original[b])**2, axis=-1)
        out = np.mean((output[a]-output[b])**2, axis=-1)
        source_edge[a] = np.maximum(source_edge[a], src);source_edge[b] = np.maximum(source_edge[b], src)
        output_edge[a] = np.maximum(output_edge[a], out);output_edge[b] = np.maximum(output_edge[b], out)
    lost = mask & (source_edge >= PARAMETERS['contour_source_rms']**2)
    lost &= output_edge < PARAMETERS['contour_retained_contrast']**2*source_edge
    lost[:12] = lost[84:] = False
    darker = (PAIRS[selected] @ Y).argmin(axis=1).astype(np.uint8)*4
    result = levels.copy()
    selected_mask = cells(lost[..., None])[..., 0]
    result[selected_mask] = np.broadcast_to(darker[:, None], levels.shape)[selected_mask]
    return result


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
    # Sparse coloured dots in an otherwise uniform background are distracting.
    # Reserve the single optional patterned sample for actual source detail.
    detailed = np.mean(np.var(source, axis=1), axis=1) >= PARAMETERS['minimal_source_detail_rms']**2
    gain[~detailed] = -np.inf
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
    pairs = PAIRS.astype(np.float32)
    distance = colour_error(target[:, :, None, None]-pairs[None, None])
    endpoints = distance.argmin(axis=3).astype(np.uint8)*4
    candidates = pairs[np.arange(len(ATTRS))[None, None], endpoints//4]
    # A neutral endpoint is always a legal fallback. For chromatic output,
    # reject misleading hue directions such as muted brown -> bright red.
    valid = hue_valid(source[:, :, None], candidates, PARAMETERS['hue_limit_degrees']).all(axis=1)
    residuals = candidates-source[:, :, None]
    spatial = colour_error(candidates-target[:, :, None]).mean(axis=1)
    best = np.where(valid, spatial, np.inf).min(axis=1)
    close = valid & (spatial <= best[:, None]+PARAMETERS['source_score_allowance'])
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
    if contours:
        output_levels = paint_lost_contours(source, output_levels, selected, source_contours(image))
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
        valid &= hue_valid(source, cells(averaged(previous)), PARAMETERS['hue_limit_degrees']).all(axis=1)
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
        source_guard_scope='Before optional contour painting: per-cell target score <= hue-valid endpoint optimum + 768, quiet retention adds <=64. Exact source cells remain exact. No old-quantizer or contour RGB bound.',
        actual_pixel_error_bounded_by_old_quantizer=False,
        minimal_dither_limit='At most one logical 2x2 sample per active 8x8 cell',
        contour_scope='Thin source-RGB Canny edges placed on their dark side; use existing darker endpoint only where filled output lost contrast. No forced cell rectangles or semantic objects.',
        vision_scope='Unsupervised mean-shift colour regions, source-bounded 12-code pull, strong source detail protected; no neural or semantic person detector')
    return report
