"""Source-bounded colour selection with temporal error feedback on the host.

Search every canonical Spectrum colour pair and five fixed-phase coverages.
Compare against the actual source, not a frame-adaptive palette or histogram.
Temporal history can choose only among close current-source candidates.
Each logical sample's averaged and actual 2x2 RGB error is bounded by the
source's monochrome reference; this excludes misleading saturated mixtures.
No native format, dither phase or player instruction changes are required.
"""
import numpy as np

import five_level_dither as five
import monochrome_five_level as mono
from cell_palette_quality import ATTRS, PAIRS, PALETTES, averaged

PARAMETERS = dict(chroma_weight=.5, chroma_grain_weight=.05,
                  close_score_allowance=256., temporal_weight=.75,
                  attribute_change_cost=24., quiet_max_component_delta=4.,
                  source_rgb_allowance=64., source_chroma_allowance=16.,
                  source_chroma_ratio=2., boundary_weight=4., spatial_passes=3,
                  palette_seam_weight=.1)
COVERAGE = np.arange(5)/4
CHROMA = np.array([[1., 0.], [-1., -1.], [0., 1.]])
CHROMA_GRAIN = (COVERAGE*(1-COVERAGE))[None] * np.mean(
    ((PAIRS[:, 1]-PAIRS[:, 0]) @ CHROMA)**2, axis=1)[:, None]
RGB_GRAIN = (COVERAGE*(1-COVERAGE))[None] * np.mean(
    (PAIRS[:, 1]-PAIRS[:, 0])**2, axis=1)[:, None]


def boundary_cost(candidate_residual, selected_residual, source, selected_attrs):
    """Penalize cell-border steps absent from the current source picture.

    Compare matching samples on both sides of every attribute boundary.
    Residual differences and source-contrast weights protect real contours.
    """
    count = candidate_residual.shape[2]
    proposed = candidate_residual.reshape(24, 32, 4, 4, count, 3)
    current = selected_residual.reshape(24, 32, 4, 4, 3)
    original = source.reshape(24, 32, 4, 4, 3)
    score = np.zeros((24, 32, count))
    pair_ids = (selected_attrs[:, None] == ATTRS[None]).argmax(axis=1).reshape(24, 32)
    current_pairs = PAIRS[pair_ids]
    delta = original[:, 1:, :, 0]-original[:, :-1, :, -1]
    weight = np.exp(-np.mean(delta**2, axis=-1)/256)
    score[:, 1:] += (np.mean((proposed[:, 1:, :, 0]-current[:, :-1, :, -1, None])**2,
                            axis=-1)*weight[:, :, :, None]).mean(axis=2)
    score[:, :-1] += (np.mean((proposed[:, :-1, :, -1]-current[:, 1:, :, 0, None])**2,
                             axis=-1)*weight[:, :, :, None]).mean(axis=2)
    score[:, 1:] += PARAMETERS['palette_seam_weight']*np.mean(
        (PAIRS[None, None]-current_pairs[:, :-1, None])**2, axis=(3, 4))*weight.mean(axis=2)[:, :, None]
    score[:, :-1] += PARAMETERS['palette_seam_weight']*np.mean(
        (PAIRS[None, None]-current_pairs[:, 1:, None])**2, axis=(3, 4))*weight.mean(axis=2)[:, :, None]
    delta = original[1:, :, 0]-original[:-1, :, -1]
    weight = np.exp(-np.mean(delta**2, axis=-1)/256)
    score[1:] += (np.mean((proposed[1:, :, 0]-current[:-1, :, -1, :, None])**2,
                         axis=-1)*weight[:, :, :, None]).mean(axis=2)
    score[:-1] += (np.mean((proposed[:-1, :, -1]-current[1:, :, 0, :, None])**2,
                          axis=-1)*weight[:, :, :, None]).mean(axis=2)
    score[1:] += PARAMETERS['palette_seam_weight']*np.mean(
        (PAIRS[None, None]-current_pairs[:-1, :, None])**2, axis=(3, 4))*weight.mean(axis=2)[:, :, None]
    score[:-1] += PARAMETERS['palette_seam_weight']*np.mean(
        (PAIRS[None, None]-current_pairs[1:, :, None])**2, axis=(3, 4))*weight.mean(axis=2)[:, :, None]
    return score.reshape(768, count)/4


def boundary_error(source, output):
    residual = output-source
    differences = [(residual[:, 4::4]-residual[:, 3:-1:4], source[:, 4::4]-source[:, 3:-1:4]),
                   (residual[4::4]-residual[3:-1:4], source[4::4]-source[3:-1:4])]
    numerator = denominator = 0.
    for error, contrast in differences:
        weight = np.exp(-np.mean(contrast**2, axis=-1)/256)
        numerator += float((np.mean(error**2, axis=-1)*weight).sum())
        denominator += float(weight.sum())
    return numerator/max(denominator, 1e-12)


def coherent_neutral_regions(source, levels, attrs, feasible, choices, spatial, retained):
    """Use one gray pair across connected smooth gray output regions.

    Independent cell minima can alternate normal/BRIGHT white and create
    rectangular texture boundaries. A shared, source-valid pair removes that
    mechanism without blurring pixels or object edges. Connectivity follows
    smooth CURRENT source samples, never the old output or frame history.
    """
    grid = source.reshape(24, 32, 4, 4, 3)
    smooth = (np.max(source, axis=1)-np.min(source, axis=1)).max(axis=1) <= 24
    smooth &= (attrs == 7) | (attrs == 71)
    smooth[:96] = smooth[672:] = False
    seen = np.zeros(768, dtype=bool)
    level_cells = cells(levels[:, :, None])[:, :, 0].copy()
    for first in np.flatnonzero(smooth):
        if seen[first]:
            continue
        component = [int(first)];seen[first] = True
        for index in component:
            row, col = divmod(index, 32)
            for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nr, nc = row+dr, col+dc
                if not 0 <= nr < 24 or not 0 <= nc < 32:
                    continue
                neighbor = nr*32+nc
                if seen[neighbor] or not smooth[neighbor]:
                    continue
                if dc == -1: delta = grid[row, col, :, 0]-grid[nr, nc, :, -1]
                elif dc == 1: delta = grid[row, col, :, -1]-grid[nr, nc, :, 0]
                elif dr == -1: delta = grid[row, col, 0]-grid[nr, nc, -1]
                else: delta = grid[row, col, -1]-grid[nr, nc, 0]
                if np.max(np.abs(delta)) <= 8:
                    component.append(neighbor);seen[neighbor] = True
        if len(component) < 4 or len(np.unique(attrs[component])) == 1:
            continue
        # Spatial grouping must not undo temporal stability in quiet cells.
        # Optimize changing cells around their already source-valid neighbors;
        # do not flash an entire old region when component connectivity changes.
        component = np.asarray(component)
        fixed = component[retained[component]]
        mutable = component[~retained[component]]
        if not len(mutable):
            continue
        candidates = [int(np.flatnonzero(ATTRS == a)[0]) for a in (7, 71)]
        candidates = [p for p in candidates if feasible[mutable, p].all()]
        if not candidates:
            continue
        pair = min(candidates, key=lambda p: float(spatial[mutable, p].sum()))
        if len(fixed) and len(np.unique(attrs[fixed])) == 1:
            prior = int(np.flatnonzero(ATTRS == attrs[fixed[0]])[0])
            if prior in candidates:
                pair = prior
        current_pair = (attrs[mutable, None] == ATTRS[None]).argmax(axis=1)
        old_score = spatial[mutable, current_pair].mean()
        if spatial[mutable, pair].mean() > old_score+1024:
            continue
        attrs[mutable] = ATTRS[pair]
        level_cells[mutable] = choices[mutable, :, pair]
    return level_cells.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128), attrs


def cells(values):
    """Arrange 4x4 logical samples in each native 8x8 attribute cell."""
    return values.reshape(24, 4, 32, 4, *values.shape[2:]).transpose(
        0, 2, 1, 3, *range(4, values.ndim+2)).reshape(768, 16, *values.shape[2:])


def encode(image, reference, previous=None, previous_image=None):
    image = np.asarray(image)
    if image.shape != (96, 128, 3) or image.dtype != np.uint8:
        raise ValueError('expected uint8 RGB 128x96')
    if (previous is None) != (previous_image is None):
        raise ValueError('temporal feedback needs both previous source and output')
    # averaged() also validates the packed level words. FLASH is disallowed.
    if len(reference) != five.STATE_BYTES or np.any(
            np.frombuffer(bytes(reference[3840:]), dtype=np.uint8) & 128):
        raise ValueError('expected non-FLASH five-level reference')
    source = cells(image.astype(float))
    reference_error = np.mean((cells(averaged(reference))-source)**2, axis=(1, 2))
    colours, inverse = np.unique(image.reshape(-1, 3), axis=0, return_inverse=True)
    choices = np.empty((len(colours), len(ATTRS)), dtype=np.uint8)
    available = np.empty(choices.shape, dtype=bool)
    mono_state = mono.encode(image)
    mono_output = averaged(mono_state)
    mono_levels = five.unpack_levels(mono_state[:3840])
    mono_rgb = np.mean((mono_output-image.astype(float))**2, axis=2)
    mono_physical = mono_rgb+(mono_levels/4)*(1-mono_levels/4)*255**2
    for start in range(0, len(colours), 512):
        values = colours[start:start+512].astype(float)
        numerator = colours[start:start+512].astype(np.uint32) @ np.array([2126, 7152, 722], np.uint32)
        coverage = ((8*numerator+2550000)//5100000).astype(float)/4
        baseline_rgb = np.mean((values-coverage[:, None]*255)**2, axis=1)
        baseline_physical = baseline_rgb+coverage*(1-coverage)*255**2
        distance = np.mean((values[:, None, None]
                            - PALETTES[None])**2, axis=3)
        chroma_distance = np.mean(((values[:, None, None]-PALETTES[None]) @ CHROMA)**2, axis=3)
        neutral_chroma = np.mean((values @ CHROMA)**2, axis=1)
        valid = ((distance <= baseline_rgb[:, None, None]+PARAMETERS['source_rgb_allowance'])
            & (distance+RGB_GRAIN[None] <= baseline_physical[:, None, None]
                + PARAMETERS['source_rgb_allowance'])
            & (chroma_distance+CHROMA_GRAIN[None] <= PARAMETERS['source_chroma_ratio']*neutral_chroma[:, None, None]
                + PARAMETERS['source_chroma_allowance']))
        guarded = np.where(valid, distance, np.inf)
        choices[start:start+512] = guarded.argmin(axis=2)
        available[start:start+512] = valid.any(axis=2)
    levels = cells(choices[inverse].reshape(96, 128, len(ATTRS)))
    candidates = PALETTES[np.arange(len(ATTRS))[None, None], levels]
    residual = candidates-source[:, :, None]
    rgb_error = np.mean(residual**2, axis=(1, 3))
    chroma_error = np.mean((residual @ CHROMA)**2, axis=(1, 3))
    grain = CHROMA_GRAIN[np.arange(len(ATTRS))[None, None], levels].mean(axis=1)
    spatial = (rgb_error+PARAMETERS['chroma_weight']*chroma_error
               + PARAMETERS['chroma_grain_weight']*grain)
    # The monochrome fallback always satisfies these sample-level guards.
    # Do not independently cap each cell at its old RGB minimum: that would
    # block a close shared palette which removes an artificial cell border.
    # Any averaged-error tradeoffs are measured explicitly in the report.
    feasible = cells(available[inverse].reshape(96, 128, len(ATTRS))).all(axis=1)
    best = np.where(feasible, spatial, np.inf).min(axis=1)
    if not np.all(np.isfinite(best)):
        raise AssertionError('source guard has no feasible monochrome fallback')
    close = feasible & (spatial <= best[:, None]+PARAMETERS['close_score_allowance'])
    score = spatial.copy()
    if previous is not None:
        previous_image = np.asarray(previous_image)
        if previous_image.shape != image.shape or previous_image.dtype != np.uint8:
            raise ValueError('invalid previous source RGB')
        old_source = cells(previous_image.astype(float))
        old_residual = cells(averaged(previous))-old_source
        # User requirement: colour must not trail picture changes. Disable
        # history entirely if ANY sample/component changes by more than four
        # source codes. This only stabilizes near-static quantization noise;
        # it never blends output frames or delays a changing cell's palette.
        confidence = (np.max(np.abs(source-old_source), axis=(1, 2))
                      <= PARAMETERS['quiet_max_component_delta']).astype(float)
        transition = np.mean(((residual-old_residual[:, :, None]) @ CHROMA)**2,
                             axis=(1, 3))
        old_attrs = np.frombuffer(bytes(previous[3840:]), dtype=np.uint8)
        score += confidence[:, None]*(PARAMETERS['temporal_weight']*transition
            + PARAMETERS['attribute_change_cost']*(ATTRS[None] != old_attrs[:, None]))
    selected = np.where(close, score, np.inf).argmin(axis=1)
    output_levels = levels[np.arange(768), :, selected].reshape(24, 32, 4, 4).transpose(
        0, 2, 1, 3).reshape(96, 128)
    output_levels[:12] = 0
    output_levels[84:] = 0
    attrs = ATTRS[selected].copy()
    retain = np.zeros(768, dtype=bool)
    if previous is not None:
        # For near-static input, also evaluate the actual previous cell, not
        # only its pair with freshly thresholded levels. This avoids a 2x2
        # dither/attribute jump when source noise crosses a quantizer boundary.
        # It is retained only if close to today's optimum AND no worse than
        # today's legacy RGB bound. All changing cells bypass this branch.
        old_output = cells(averaged(previous))
        old_error = old_output-source
        old_rgb = np.mean(old_error**2, axis=(1, 2))
        old_chroma = np.mean((old_error @ CHROMA)**2, axis=(1, 2))
        old_levels = cells(five.unpack_levels(bytes(previous[:3840]))[:, :, None])[:, :, 0]
        old_pair = (old_attrs[:, None] == ATTRS[None]).argmax(axis=1)
        old_grain = CHROMA_GRAIN[old_pair[:, None], old_levels].mean(axis=1)
        old_spatial = (old_rgb+PARAMETERS['chroma_weight']*old_chroma
            + PARAMETERS['chroma_grain_weight']*old_grain)
        old_sample_rgb = np.mean(old_error**2, axis=2)
        old_physical = old_sample_rgb+RGB_GRAIN[old_pair[:, None], old_levels]
        old_physical_chroma = np.mean((old_error @ CHROMA)**2, axis=2)+CHROMA_GRAIN[old_pair[:, None], old_levels]
        neutral_chroma = np.mean((source @ CHROMA)**2, axis=2)
        old_close = ((old_sample_rgb <= cells(mono_rgb[:, :, None])[:, :, 0]+PARAMETERS['source_rgb_allowance']+1e-8)
            & (old_physical <= cells(mono_physical[:, :, None])[:, :, 0]+PARAMETERS['source_rgb_allowance']+1e-8)
            & (old_physical_chroma <= PARAMETERS['source_chroma_ratio']*neutral_chroma+PARAMETERS['source_chroma_allowance']+1e-8)).all(axis=1)
        retain = (confidence.astype(bool) & old_close
            & (old_rgb <= np.maximum(reference_error, cells(mono_rgb[:, :, None])[:, :, 0].mean(axis=1))+PARAMETERS['source_rgb_allowance']+1e-8)
            & (old_spatial <= best+PARAMETERS['close_score_allowance']))
        chosen_cells = cells(output_levels[:, :, None])[:, :, 0].copy()
        chosen_cells[retain] = old_levels[retain]
        output_levels = chosen_cells.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128)
        attrs[retain] = old_attrs[retain]
    # Alternate checkerboard parity to avoid a directional scan bias. Only
    # close current-source candidates are eligible. Retained near-static cells
    # are fixed, with their source-validated pixels supplying edge references.
    held_levels, held_attrs = output_levels.copy(), attrs.copy()
    held_output = cells(averaged(five.pack_levels(output_levels)+attrs.tobytes()))
    current = held_output-source
    parity = (np.indices((24, 32)).sum(axis=0)%2).ravel()
    active = np.zeros(768, dtype=bool);active[96:672] = True
    for _ in range(PARAMETERS['spatial_passes']):
        for group in (0, 1):
            current_attrs = ATTRS[selected].copy();current_attrs[retain] = held_attrs[retain]
            spatial_score = score+PARAMETERS['boundary_weight']*boundary_cost(residual, current, source, current_attrs)
            proposed = np.where(close, spatial_score, np.inf).argmin(axis=1)
            mutable = active & ~retain & (parity == group)
            selected[mutable] = proposed[mutable]
            current = candidates[np.arange(768), :, selected]-source
            current[retain] = held_output[retain]-source[retain]
    output_cells = levels[np.arange(768), :, selected].copy()
    output_cells[retain] = cells(held_levels[:, :, None])[retain, :, 0]
    output_levels = output_cells.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128)
    output_levels[:12] = output_levels[84:] = 0
    attrs = ATTRS[selected].copy();attrs[retain] = held_attrs[retain]
    output_levels, attrs = coherent_neutral_regions(source, output_levels, attrs, feasible, levels, spatial, retain)
    attrs[:96] = 1
    attrs[672:] = 1
    state = five.pack_levels(output_levels)+attrs.tobytes()
    actual = cells(averaged(state))-source
    rgb = np.mean(actual**2, axis=2)
    state_levels = cells(five.unpack_levels(state[:3840])[:, :, None])[:, :, 0]
    state_pairs = (attrs[:, None] == ATTRS[None]).argmax(axis=1)
    physical = rgb+RGB_GRAIN[state_pairs[:, None], state_levels]
    physical_chroma = np.mean((actual @ CHROMA)**2, axis=2)+CHROMA_GRAIN[state_pairs[:, None], state_levels]
    if (np.any(rgb[96:672] > cells(mono_rgb[:, :, None])[96:672, :, 0]+PARAMETERS['source_rgb_allowance']+1e-8)
            or np.any(physical[96:672] > cells(mono_physical[:, :, None])[96:672, :, 0]+PARAMETERS['source_rgb_allowance']+1e-8)
            or np.any(physical_chroma[96:672] > PARAMETERS['source_chroma_ratio']*np.mean((source[96:672] @ CHROMA)**2, axis=2)+PARAMETERS['source_chroma_allowance']+1e-8)):
        raise AssertionError('output violates current source/physical RGB guard')
    return state


class Comparison:
    """Stream source/legacy/selected measurements; no perceptual grade."""
    def __init__(self):
        self.rows = []
        self.previous = None

    def add(self, image, legacy, selected):
        source = image[12:84].astype(float)
        outputs = [averaged(state)[12:84] for state in (legacy, selected)]
        attrs = [np.frombuffer(bytes(state[3936:4512]), dtype=np.uint8)
                 for state in (legacy, selected)]
        row = {}
        for name, output, attribute in zip(('legacy', 'stable'), outputs, attrs):
            residual = output-source
            values = dict(rgb_mse=float(np.mean(residual**2)),
                          chroma_mse=float(np.mean((residual @ CHROMA)**2)),
                          boundary_residual_mse=boundary_error(source, output))
            full_attrs = np.frombuffer(bytes((legacy, selected)[0 if name == 'legacy' else 1][3840:]), np.uint8)
            pair_index = (full_attrs[:, None] == ATTRS[None]).argmax(axis=1).reshape(24, 32).repeat(4, 0).repeat(4, 1)[12:84]
            lev = five.unpack_levels(bytes((legacy, selected)[0 if name == 'legacy' else 1][:3840]))[12:84]
            values['physical_rgb_mse'] = float(np.mean(residual**2)+np.mean(RGB_GRAIN[pair_index, lev]))
            values['physical_chroma_mse'] = float(np.mean((residual @ CHROMA)**2)+np.mean(CHROMA_GRAIN[pair_index, lev]))
            if self.previous is not None:
                old_source, old_outputs, old_attrs = self.previous
                at = 0 if name == 'legacy' else 1
                values['temporal_chroma_residual_mse'] = float(np.mean(
                    ((residual-(old_outputs[at]-old_source)) @ CHROMA)**2))
                change = np.max(np.abs(cells(image.astype(float))[96:672]
                    - cells(self.previous_full_source.astype(float))[96:672]), axis=(1, 2))
                quiet = change <= PARAMETERS['quiet_max_component_delta']
                if quiet.any():
                    temporal = ((residual-(old_outputs[at]-old_source)) @ CHROMA)**2
                    by_cell = temporal.reshape(18, 4, 32, 4, 2).transpose(
                        0, 2, 1, 3, 4).reshape(576, 16, 2).mean(axis=(1, 2))
                    values['quiet_temporal_chroma_residual_mse'] = float(by_cell[quiet].mean())
                values['quiet_cells'] = int(quiet.sum())
                values['quiet_attribute_changes'] = int(((attribute != old_attrs[at]) & quiet).sum())
                values['attribute_changes'] = int((attribute != old_attrs[at]).sum())
            row[name] = values
        self.rows.append(row)
        self.previous = source.copy(), [o.copy() for o in outputs], [a.copy() for a in attrs]
        self.previous_full_source = image.copy()

    def report(self):
        result = dict(parameters=PARAMETERS.copy(), frames=self.rows,
            rgb_sample_bound='Each averaged and physical 2x2 RGB error <= source monochrome reference +64 MSE/component',
            chroma_sample_bound='Each physical 2x2 opponent-colour error <= 2*neutral reference +16 MSE/component',
            chroma_metric='Squared R-G and B-G differences; not a perceptual grade',
            quiet_source_cell_max_component_delta=4, fixed_dither_phase=True,
            player_instruction_delta_tstates=0)
        for name in ('legacy', 'stable'):
            result[name] = {}
            for key in ('rgb_mse', 'physical_rgb_mse', 'chroma_mse', 'physical_chroma_mse', 'boundary_residual_mse', 'temporal_chroma_residual_mse', 'quiet_temporal_chroma_residual_mse'):
                values = [row[name][key] for row in self.rows if key in row[name]]
                result[name][key] = float(np.mean(values)) if values else 0.
            for key in ('quiet_cells', 'quiet_attribute_changes', 'attribute_changes'):
                result[name][key] = sum(row[name].get(key, 0) for row in self.rows)
        return result
