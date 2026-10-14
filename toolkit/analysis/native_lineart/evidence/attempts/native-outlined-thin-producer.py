"""True native-pixel source lines and matched solid Spectrum fills.

The source active area is256x144; the serialized frame is a standard6912-byte
Spectrum screen, including24-pixel black top/bottom bands. No radix-five
samples or2x2 expansion participate in tracing, palette fitting or storage.
"""
import cv2
import numpy as np
from cell_palette_quality import ATTRS, PAIRS
from stable_colour import hue_valid
from build_zxv_trd import spectrum_bitmap_offset
from lineart_colour import COLOURS

PARAMETERS = dict(active_rgb_size=[256, 144], native_screen_size=[256, 192],
    paper_rgb=[205, 205, 205], fine_sigma=.8, fine_kernel=5,
    fine_canny_low=12, fine_canny_high=24, coarse_sigma=1.8, coarse_kernel=9,
    coarse_canny_low=20, coarse_canny_high=40, minimum_line_samples=4,
    fill_rgb_rms_max=60., fill_max_component_delta=100., fill_hue_degrees=30.,
    black_max_component=64., minimum_colour_region_samples=16,
    minimum_black_region_samples=8, source_colour_fill_priority=6., empty_paper_priority=1.)
OFFSETS = np.array([spectrum_bitmap_offset(0, y) for y in range(192)])[:, None]+np.arange(32)


def validate(image):
    image = np.asarray(image)
    if image.shape != (192, 256, 3) or image.dtype != np.uint8:
        raise ValueError('expected uint8 native256x192 RGB')
    return image


def cells(values):
    return values.reshape(24, 8, 32, 8, *values.shape[2:]).transpose(0, 2, 1, 3, *range(4, values.ndim+2)).reshape(768, 64, *values.shape[2:])


def unpack(frame):
    frame = np.frombuffer(bytes(frame), np.uint8)
    if frame.shape != (6912,):raise ValueError('expected standard6912-byte native screen')
    return np.unpackbits(frame[:6144][OFFSETS], axis=1), frame[6144:]


def pixels(frame):
    bits, attrs = unpack(frame);attrs = attrs.reshape(24, 32).repeat(8, 0).repeat(8, 1)
    bright = (attrs >> 3) & 8
    ink = (attrs & 7) | bright;paper = ((attrs >> 3) & 7) | bright
    return COLOURS[np.where(bits, ink, paper)]


def source_lines(image):
    active = np.ascontiguousarray(validate(image)[24:168]);mask = np.zeros((192, 256), bool)
    edges = np.zeros(active.shape[:2], np.uint8)
    for name in ('fine', 'coarse'):
        size = PARAMETERS[name+'_kernel']
        blurred = cv2.GaussianBlur(active, (size, size), PARAMETERS[name+'_sigma'], borderType=cv2.BORDER_REPLICATE)
        edges |= cv2.Canny(blurred, PARAMETERS[name+'_canny_low'], PARAMETERS[name+'_canny_high'], L2gradient=True)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    keep = np.zeros(count, bool);keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= PARAMETERS['minimum_line_samples']
    mask[24:168] = keep[labels];return mask


def source_fills(image, *, dark_fills=False):
    source = validate(image)[24:168].astype(np.float32)
    delta = source[:, :, None]-COLOURS[None, None]
    distance = np.mean(delta**2, -1)
    eligible = (distance <= PARAMETERS['fill_rgb_rms_max']**2)
    eligible &= np.max(np.abs(delta), -1) <= PARAMETERS['fill_max_component_delta']
    eligible &= hue_valid(source[:, :, None], COLOURS[None, None], PARAMETERS['fill_hue_degrees'])
    eligible[:, :, 0] &= source.max(-1) <= (100 if dark_fills else PARAMETERS['black_max_component'])
    eligible[:, :, 7] = eligible[:, :, 15] = eligible[:, :, 8] = False
    chosen = np.where(eligible, distance, np.inf).argmin(-1)
    full = np.full((192, 256), 7, np.uint8)
    for colour in (*range(7), *range(9, 15)):
        proposed = (eligible[:, :, colour] & (chosen == colour)).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(proposed, connectivity=8)
        minimum = PARAMETERS['minimum_black_region_samples'] if colour == 0 else PARAMETERS['minimum_colour_region_samples']
        keep = np.zeros(count, bool);keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= minimum
        full[24:168][keep[labels]] = colour
    return full


def render_fills(fills, lines):
    desired = fills.copy();desired[lines] = 0;desired[:24] = desired[168:] = 0
    labels = cells(desired[..., None])[..., 0];target = COLOURS[labels]
    distance = np.mean((target[:, :, None, None]-PAIRS[None, None])**2, -1)
    optional = (labels != 0) & (labels != 7)
    allowed = distance == 0
    allowed |= optional[:, :, None, None] & np.all(PAIRS == COLOURS[7], -1)[None, None]
    score = np.where(allowed, distance, np.inf);nearest = score.argmin(-1)
    valid = allowed.any(-1).all(1)
    weights = np.where(optional, PARAMETERS['source_colour_fill_priority'], PARAMETERS['empty_paper_priority'])
    cost = (score.min(-1)*weights[:, :, None]).mean(1)
    selected = np.where(valid, cost, np.inf).argmin(1)
    if not np.isfinite(cost[np.arange(768), selected]).all():raise AssertionError('missing black/white fallback')
    bits = nearest[np.arange(768), :, selected].astype(np.uint8).reshape(24, 32, 8, 8).transpose(0, 2, 1, 3).reshape(192, 256)
    attrs = ATTRS[selected].copy();attrs[:96] = attrs[672:] = 1;bits[:24] = bits[168:] = 0
    bitmap = np.empty(6144, np.uint8);bitmap[OFFSETS] = np.packbits(bits, axis=1)
    return bitmap.tobytes()+attrs.tobytes()


def encode(image, *, dark_fills=True):
    """Keep exact contours/paper and old colours; reject whole regressing regions."""
    image = validate(image);lines = source_lines(image);old_fills = source_fills(image)
    original_state = render_fills(old_fills, lines)
    if not dark_fills:return original_state
    proposed = source_fills(image, dark_fills=True);added = (proposed == 0) & (old_fills != 0)
    count, labels = cv2.connectedComponents(added.astype(np.uint8), connectivity=8)
    if count == 1:return original_state
    original = pixels(original_state);old_error = np.mean((original-image)**2, -1)
    retained = np.ones(count, bool);retained[0] = False
    for _ in range(count):
        fills = np.where(retained[labels], proposed, old_fills).astype(np.uint8)
        state = render_fills(fills, lines);output = pixels(state);changed = np.any(output != original, -1)
        bad = changed & (np.mean((output-image)**2, -1) >= old_error)
        bad |= changed & (np.ptp(original, axis=-1) > 0)
        if not bad.any():return state
        bad_cells = cells(bad[..., None])[..., 0].any(1).reshape(24, 32)
        rejected = np.unique(labels[bad_cells.repeat(8, 0).repeat(8, 1) & retained[labels]])
        if not len(rejected):raise AssertionError('regression outside new dark regions')
        retained[rejected] = False
    raise AssertionError('non-monotonic native dark fill selection')
