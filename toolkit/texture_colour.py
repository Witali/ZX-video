"""Preserve the crisp quantizer and feather only artificial solid/pattern seams.

The source-bounded selector remains the baseline. Reject false colour directions
before selecting its palette. A narrow, source-smooth band at gray attribute
boundaries may then distribute a fractional shade; the rest of the picture
keeps the established five-level fixed-phase pattern exactly.
"""
import numpy as np
import five_level_dither as five
import stable_colour as stable
from cell_palette_quality import averaged
from stable_colour import cells, ATTRS, RGB_GRAIN

PARAMETERS = dict(hue_limit_degrees=20., feather_width_logical=2,
    source_edge_rms_max=8., output_edge_rms_max=40., solid_pull_max=8.,
    solid_step_rms_max=56., solid_step_pull_max=24.)
Y = np.array([.2126, .7152, .0722])
yy, xx = np.indices((96, 128))
PHASE = np.mod((xx+.5)*.7548776662466927+(yy+.5)*.5698402909980532, 1.)


def feather(image, state):
    """Soften a false gray solid/pattern edge within four native pixels.

    Eligibility uses the current source on BOTH sides of the boundary. Strong
    source contours are never feathered. At a solid endpoint, a limited pull
    toward the neighbor introduces sparse dots before the attribute edge.
    At a patterned endpoint, use fractional source brightness in the same band.
    All other samples retain their old levels, including sharp source detail.
    The rare fractional samples use global phase, unchanged between frames.
    """
    source = image.astype(float)
    output = averaged(state)
    levels = five.unpack_levels(state[:3840]).copy()
    attrs = np.frombuffer(state[3840:], np.uint8)
    attr_pixels = attrs.reshape(24, 32).repeat(4, 0).repeat(4, 1)
    gray = (attr_pixels == 7) | (attr_pixels == 71)
    grain = (levels > 0) & (levels < 4)
    seeds = np.zeros((96, 128), bool)
    target = np.zeros((96, 128), float)
    counts = np.zeros((96, 128), np.uint8)
    luminance = output @ Y
    original = source @ Y
    edges = [(np.s_[:, 4::4], np.s_[:, 3:-1:4]),
             (np.s_[4::4, :], np.s_[3:-1:4, :])]
    for right, left in edges:
        contrast = np.mean((output[right]-output[left])**2, axis=2)
        # NORMAL white=205 versus BRIGHT white=255 can form a flat square
        # even when neither cell has dots. Seed the bright side gradually too.
        solid_step = (~grain[right] & ~grain[left] & (contrast >= 12**2)
            & (contrast <= PARAMETERS['solid_step_rms_max']**2))
        valid = (gray[right] & gray[left]
            & (np.mean((source[right]-source[left])**2, axis=2) <= PARAMETERS['source_edge_rms_max']**2)
            & (solid_step | ((grain[right] != grain[left]) & (contrast <= PARAMETERS['output_edge_rms_max']**2))))
        for at, neighbor in ((right, left), (left, right)):
            maximum_pull = np.where(solid_step, PARAMETERS['solid_step_pull_max'], PARAMETERS['solid_pull_max'])
            pulled = luminance[at]+np.clip((luminance[neighbor]-luminance[at])/2,
                -maximum_pull, maximum_pull)
            value = np.where(grain[at], original[at], pulled)
            target[at] += np.where(valid, value, 0)
            seeds[at] |= valid
            counts[at] += valid
    # A corner can be seeded by two edges. Average their target values.
    target /= np.maximum(counts, 1)
    target_delta = target-luminance
    weight = seeds.astype(float)
    # Extend one logical sample in all directions, only through a locally
    # smooth source with the same gray pair and the same solid/pattern class.
    extension_sum = np.zeros_like(target);extension_count = np.zeros_like(target)
    for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        near = np.roll(seeds, (dy, dx), axis=(0, 1))
        delta = np.roll(target_delta, (dy, dx), axis=(0, 1))
        eligible = (near & ~seeds & gray & (attr_pixels == np.roll(attr_pixels, (dy, dx), (0, 1)))
            & (grain == np.roll(grain, (dy, dx), (0, 1)))
            & (np.mean((source-np.roll(source, (dy, dx), (0, 1)))**2, axis=2) <= 64))
        eligible[0] = eligible[-1] = False;eligible[:, 0] = eligible[:, -1] = False
        extension_sum += np.where(eligible, delta, 0);extension_count += eligible
    expanded = extension_count > 0
    target_delta[expanded] = extension_sum[expanded]/extension_count[expanded]
    weight[expanded] = .5
    weight[:12] = weight[84:] = 0
    white = np.where(attr_pixels == 7, 205., 255.)
    desired = np.clip((luminance+weight*target_delta)*4/white, 0, 4)
    fractional = np.floor(desired+PHASE).astype(np.uint8)
    changed = weight > 0
    levels[changed] = fractional[changed]
    return five.pack_levels(levels)+attrs.tobytes()


def encode(image, reference, previous=None, previous_image=None):
    baseline = stable.encode(image, reference, previous, previous_image,
        hue_limit=PARAMETERS['hue_limit_degrees'])
    return feather(image, baseline)


def comparison_report(comparison, *, active=True):
    report = comparison.report()
    if active:
        report.pop('rgb_sample_bound');report.pop('chroma_sample_bound')
        report.update(selector='source-bounded palette + localized gray seam feathering',
            baseline_parameters=report.pop('parameters'), parameters=PARAMETERS.copy(),
            actual_pixel_error_bounded_by_old_quantizer=False,
            source_guard_scope='Baseline keeps original sample/physical bounds; a narrow gray seam band may introduce sparse fractional levels outside those bounds. Measure its actual errors explicitly.',
            fractional_density_phase='Screen-anchored R2 sequence only inside the seam band, constant in time',
            quality_tradeoff='Localized feathering may increase pixel MSE; no whole-image fractional retexturing')
    return report
