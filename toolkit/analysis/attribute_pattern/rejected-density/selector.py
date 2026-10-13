"""Joint palette/coverage fitting with a screen-anchored density pattern.

Fit the source at several spatial scales. Compare texture as well as mean
colour across attribute boundaries. The five-level native format and its 2x2
phase are unchanged; fractional coverages are distributed over logical samples
using global coordinates, never restarted at an 8x8 character boundary.
"""
import numpy as np
import five_level_dither as five
from cell_palette_quality import ATTRS, PAIRS, PALETTES, averaged
from stable_colour import cells, RGB_GRAIN, CHROMA_GRAIN, CHROMA

PARAMETERS = dict(mean_weight=4., local_mean_weight=2., sample_weight=.15,
    chroma_weight=.75, physical_chroma_weight=.02, texture_seam_weight=.5,
    edge_weight=2., spatial_passes=3, projection_allowance=64.,
    physical_chroma_ratio=2., physical_chroma_allowance=16.,
    quiet_delta=4., keep_mean_allowance=16.)
Y = np.array([.2126, .7152, .0722])
yy, xx = np.indices((96, 128))
PHASE = np.mod((xx+.5)*.7548776662466927+(yy+.5)*.5698402909980532, 1.)


def comparison_report(comparison, *, active=True):
    """Reuse measured errors without claiming the older quantizer's guards."""
    report = comparison.report()
    for key in ('rgb_sample_bound', 'chroma_sample_bound', 'parameters'):
        report.pop(key)
    report.update(selector='texture_colour' if active else 'explicit legacy/monochrome',
        parameters=PARAMETERS.copy() if active else {},
        projection_guard='Continuous pair projection RGB <= continuous monochrome RGB +64 MSE/component',
        chroma_guard='Ideal fractional physical opponent error <= 2*neutral opponent error +16 MSE/component',
        actual_pixel_error_bounded_by_old_quantizer=False,
        fractional_density_phase='Screen-anchored R2 sequence, constant in time; not restarted per cell',
        quality_tradeoff='Distributed fractional levels may increase sample/physical pixel MSE while reducing low-pass error and cell texture seams')
    return report


def local_mean_error(residual):
    blocks = residual.reshape(768, 2, 2, 2, 2, *residual.shape[2:]).mean(axis=(2, 4))
    return np.mean(blocks**2, axis=(1, 2, blocks.ndim-1))


def edge_cost(residual, texture, current, current_texture, source):
    """Current-source mean/texture steps on both sides of each cell edge."""
    n = residual.shape[2]
    candidate = residual.reshape(24, 32, 4, 4, n, 3)
    grain = texture.reshape(24, 32, 4, 4, n)
    selected = current.reshape(24, 32, 4, 4, 3)
    selected_grain = current_texture.reshape(24, 32, 4, 4)
    original = source.reshape(24, 32, 4, 4, 3)
    result = np.zeros((24, 32, n))
    pairs = [((slice(None), slice(1, None), slice(None), 0),
              (slice(None), slice(None, -1), slice(None), -1)),
             ((slice(1, None), slice(None), 0, slice(None)),
              (slice(None, -1), slice(None), -1, slice(None)))]
    for right, left in pairs:
        weight = np.exp(-np.mean((original[right]-original[left])**2, axis=-1)/256)
        for target, neighbor in ((right, left), (left, right)):
            colour = np.mean((candidate[target]-selected[neighbor][..., None, :])**2, axis=-1)
            pattern = (grain[target]-selected_grain[neighbor][..., None])**2
            cost = ((colour+PARAMETERS['texture_seam_weight']*pattern)*weight[..., None]).mean(axis=2)
            result[target[:2]] += cost
    return result.reshape(768, n)/4


def shared_neutral_palette(source, selected, feasible, spatial, previous, quiet):
    """Join gray cells using source edges; internal highlights do not split it.

    A white highlight within one cell can require BRIGHT white. Neighboring
    gray cells then share that palette and distribute the requested density,
    instead of forming solid normal-white rectangles against textured cells.
    """
    gray = (ATTRS[selected] == 7) | (ATTRS[selected] == 71)
    gray[:96] = gray[672:] = False
    grid = source.reshape(24, 32, 4, 4, 3)
    seen = np.zeros(768, bool)
    for start in np.flatnonzero(gray):
        if seen[start]:
            continue
        region = [int(start)];seen[start] = True
        for index in region:
            row, col = divmod(index, 32)
            for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nr, nc = row+dr, col+dc
                if not 0 <= nr < 24 or not 0 <= nc < 32:
                    continue
                at = nr*32+nc
                if seen[at] or not gray[at]:
                    continue
                if dc == -1: delta = grid[row, col, :, 0]-grid[nr, nc, :, -1]
                elif dc == 1: delta = grid[row, col, :, -1]-grid[nr, nc, :, 0]
                elif dr == -1: delta = grid[row, col, 0]-grid[nr, nc, -1]
                else: delta = grid[row, col, -1]-grid[nr, nc, 0]
                if np.mean(delta**2) <= 256 and np.max(np.abs(delta)) <= 32:
                    seen[at] = True;region.append(at)
        if len(region) < 2 or len(np.unique(selected[region])) == 1:
            continue
        choices = [int(np.flatnonzero(ATTRS == a)[0]) for a in (7, 71)]
        choices = [i for i in choices if feasible[region, i].all()]
        if not choices:
            continue
        chosen = min(choices, key=lambda i: float(spatial[region, i].sum()))
        if previous is not None and quiet[region].all():
            prior_attrs = np.frombuffer(bytes(previous[3840:]), np.uint8)[region]
            if len(np.unique(prior_attrs)) == 1:
                prior = np.flatnonzero(ATTRS == prior_attrs[0])
                if len(prior) and int(prior[0]) in choices:
                    prior = int(prior[0])
                    if spatial[region, prior].mean() <= spatial[region, chosen].mean()+16:
                        chosen = prior
        selected[region] = chosen
    return selected


def encode(image, reference=None, previous=None, previous_image=None):
    image = np.asarray(image)
    if image.shape != (96, 128, 3) or image.dtype != np.uint8:
        raise ValueError('expected uint8 RGB 128x96')
    if (previous is None) != (previous_image is None):
        raise ValueError('both previous source and output are required')
    if previous is not None:
        previous_image = np.asarray(previous_image)
        if previous_image.shape != image.shape or previous_image.dtype != np.uint8:
            raise ValueError('invalid previous source RGB')
        if len(previous) != five.STATE_BYTES or np.any(
                np.frombuffer(bytes(previous[3840:]), np.uint8) & 128):
            raise ValueError('expected non-FLASH five-level previous output')
    source = cells(image.astype(float))
    quiet = (np.max(np.abs(source-cells(previous_image.astype(float))), axis=(1, 2))
             <= PARAMETERS['quiet_delta']) if previous is not None else np.zeros(768, bool)
    colours, inverse = np.unique(image.reshape(-1, 3), axis=0, return_inverse=True)
    direction = PAIRS[:, 1]-PAIRS[:, 0]
    numerator = np.einsum('ucp,cp->uc', colours[:, None].astype(float)-PAIRS[None, :, 0], direction*Y)
    denominator = np.sum(direction**2*Y, axis=1)
    coverage = np.clip(numerator/denominator[None], 0, 1)
    projected = PAIRS[None, :, 0]+coverage[:, :, None]*direction[None]
    projection_error = np.mean((projected-colours[:, None])**2, axis=2)
    mono = (colours.astype(float) @ Y)[:, None]
    reference_error = np.mean((colours-mono)**2, axis=1)
    projected_chroma = np.mean(((projected-colours[:, None]) @ CHROMA)**2, axis=2)
    expected_grain = coverage*(1-coverage)*np.mean((direction @ CHROMA)**2, axis=1)[None]
    neutral_chroma = np.mean((colours.astype(float) @ CHROMA)**2, axis=1)
    available = ((projection_error <= reference_error[:, None]+PARAMETERS['projection_allowance'])
        & (projected_chroma+expected_grain <= PARAMETERS['physical_chroma_ratio']*neutral_chroma[:, None]
            +PARAMETERS['physical_chroma_allowance']))
    fractional = coverage[inverse].reshape(96, 128, len(ATTRS))*4
    quantized = np.minimum(4, np.floor(fractional+PHASE[:, :, None])).astype(np.uint8)
    levels = cells(quantized)
    output = PALETTES[np.arange(len(ATTRS))[None, None], levels]
    residual = output-source[:, :, None]
    mean = np.mean(residual.mean(axis=1)**2, axis=2)
    local = local_mean_error(residual)
    sample = np.mean(residual**2, axis=(1, 3))
    chroma = np.mean((residual.mean(axis=1) @ CHROMA)**2, axis=2)
    physical_chroma = np.mean((residual @ CHROMA)**2, axis=(1, 3))
    physical_chroma += CHROMA_GRAIN[np.arange(len(ATTRS))[None, None], levels].mean(axis=1)
    spatial = (PARAMETERS['mean_weight']*mean+PARAMETERS['local_mean_weight']*local
        +PARAMETERS['sample_weight']*sample+PARAMETERS['chroma_weight']*chroma
        +PARAMETERS['physical_chroma_weight']*physical_chroma)
    feasible = cells(available[inverse].reshape(96, 128, len(ATTRS))).all(axis=1)
    selected = np.where(feasible, spatial, np.inf).argmin(axis=1)
    if not np.all(feasible[np.arange(768), selected]):
        raise AssertionError('no source-valid palette')
    texture = np.sqrt(RGB_GRAIN[np.arange(len(ATTRS))[None, None], levels])
    parity = np.indices((24, 32)).sum(axis=0).ravel()%2
    for _ in range(PARAMETERS['spatial_passes']):
        for group in (0, 1):
            current = residual[np.arange(768), :, selected]
            current_texture = texture[np.arange(768), :, selected]
            cost = spatial+PARAMETERS['edge_weight']*edge_cost(residual, texture, current, current_texture, source)
            proposed = np.where(feasible, cost, np.inf).argmin(axis=1)
            selected[parity == group] = proposed[parity == group]
    selected = shared_neutral_palette(source, selected, feasible, spatial, previous, quiet)
    chosen_levels = levels[np.arange(768), :, selected].copy()
    attrs = ATTRS[selected].copy()
    if previous is not None:
        old_attrs = np.frombuffer(bytes(previous[3840:]), np.uint8)
        old_residual = cells(averaged(previous))-source
        new_residual = residual[np.arange(768), :, selected]
        old_cost = 4*np.mean(old_residual.mean(axis=1)**2, axis=1)+2*local_mean_error(old_residual)
        new_cost = 4*np.mean(new_residual.mean(axis=1)**2, axis=1)+2*local_mean_error(new_residual)
        retain = quiet & (old_attrs == attrs) & (old_cost <= new_cost+PARAMETERS['keep_mean_allowance'])
        old_levels = cells(five.unpack_levels(bytes(previous[:3840]))[:, :, None])[:, :, 0]
        chosen_levels[retain] = old_levels[retain]
    bitmap = chosen_levels.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128)
    bitmap[:12] = bitmap[84:] = 0
    attrs[:96] = 1;attrs[672:] = 1
    return five.pack_levels(bitmap)+attrs.tobytes()
