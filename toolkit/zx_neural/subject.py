"""Optional automatic subject separation for ZX Spectrum photographs."""

from hashlib import sha256

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .objective import edge_weight
from .screen import COLS, PALETTE, WIDTH, pack, prepare, to_cells

LUMA = np.array([.2126, .7152, .0722], dtype=np.float32)
_CONTOUR_BLUR = ImageFilter.GaussianBlur(2.4)
_THIN_DETAIL_BLUR = ImageFilter.GaussianBlur(.75)
_OPENING_ERODE = ImageFilter.MinFilter(13)
_OPENING_DILATE = ImageFilter.MaxFilter(13)
U2NETP_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
U2NETP_SHA256 = "309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8"


class SubjectDetector:
    """Run the small U²-NetP saliency model locally using ONNX Runtime."""

    def __init__(self, path):
        model = path.read_bytes()
        if sha256(model).hexdigest() != U2NETP_SHA256:
            raise ValueError("subject model must be the documented U²-NetP ONNX file")
        try:
            import onnxruntime as ort
        except ImportError as error:
            raise ValueError("--subject-model requires the optional onnxruntime package") from error
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(model, sess_options=options, providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name
        self.output = self.session.get_outputs()[0].name

    def predict(self, image, crop=False):
        source = ImageOps.exif_transpose(image).convert("RGB")
        pixels = np.asarray(source.resize((320, 320), Image.Resampling.LANCZOS), dtype=np.float32)
        pixels /= max(float(pixels.max()), 1)
        mean = np.array([.485, .456, .406], dtype=np.float32)
        scale = np.array([.229, .224, .225], dtype=np.float32)
        tensor = ((pixels - mean) / scale).transpose(2, 0, 1)[None].copy()
        prediction = self.session.run([self.output], {self.input: tensor})[0][0, 0]
        # Keep absolute confidence so an uncertain prediction does not
        # become a strong mask through per-image normalization.
        mask = Image.fromarray(prediction).resize(source.size, Image.Resampling.BILINEAR)
        mask = Image.fromarray(np.rint(np.clip(np.asarray(mask), 0, 1) * 255).astype(np.uint8))
        return prepare(mask, crop)[..., 0].astype(np.float32) / 255


def has_subject(source, probability):
    interior = probability > .85
    active = max(1, np.count_nonzero(source.max(axis=-1)))
    return .02 <= interior.sum() / active <= .62


def box_mean(values, size):
    pad = size // 2
    padded = np.pad(values, pad, mode="edge")
    total = np.pad(padded, ((1, 0), (1, 0))).cumsum(0, dtype=np.float64).cumsum(1)
    return (total[size:, size:] - total[:-size, size:] - total[size:, :-size] + total[:-size, :-size]) / size**2


def protect_thin_parts(source, preview, probability):
    """Reinforce narrow silhouette parts that lost their source contrast."""
    foreground = probability >= .50
    mask_image = Image.fromarray(foreground.astype(np.uint8) * 255)
    wide = np.asarray(mask_image.filter(_OPENING_ERODE).filter(_OPENING_DILATE)) != 0
    thin = foreground & ~wide
    if not thin.any():
        return None
    source = source.astype(np.float32)
    light = source @ LUMA
    rendered = preview.astype(np.float32) @ LUMA
    outside = ~foreground
    count = np.maximum(box_mean(outside.astype(np.float32), 15), .01)
    original_step = light - box_mean(light * outside, 15) / count
    rendered_step = box_mean(rendered, 3) - box_mean(rendered * outside, 15) / count
    direction = np.sign(original_step)
    chroma = np.linalg.norm(source - source.mean(axis=-1, keepdims=True), axis=-1)
    eligible = thin & (abs(original_step) > 12) & (direction * rendered_step < 28) & (chroma < 65)
    if not eligible.any():
        return None
    shift = np.where(eligible, direction * np.maximum(0., 115 - abs(original_step)), 0.)
    # Feather the correction by less than one native pixel. Scaling RGB
    # changes brightness while maintaining the original channel ratios.
    shifted = Image.fromarray(np.rint(shift + 128).astype(np.uint8)).filter(_THIN_DETAIL_BLUR)
    amount = (np.asarray(shifted, dtype=np.float32) - 128) * np.clip((probability - .36) / .24, 0, 1)
    scale = (light + amount) / np.maximum(light, 1)
    target = np.rint(np.clip(source * scale[..., None], 0, 255)).astype(np.uint8)
    return target


def trace_contour(source, screen, preview, probability):
    """Recover weak silhouette runs with one inside pixel and the cell's other color."""
    foreground = probability >= .50
    height = source.shape[0]

    def offset(pad, dy, dx):
        return pad[1 - dy:1 - dy + height, 1 - dx:1 - dx + WIDTH]

    neighbors = ((0, 1), (0, -1), (1, 0), (-1, 0))
    padded = np.pad(foreground, 1, mode="edge")
    outside = [~offset(padded, dy, dx) for dy, dx in neighbors]
    boundary = foreground & np.logical_or.reduce(outside)
    light = preview.astype(np.float32) @ LUMA
    smooth = np.asarray(Image.fromarray(np.uint8(np.rint(light))).filter(_CONTOUR_BLUR), dtype=np.float32)
    source_light = source.astype(np.float32) @ LUMA
    source_smooth = np.asarray(
        Image.fromarray(np.uint8(np.rint(source_light))).filter(_CONTOUR_BLUR), dtype=np.float32)
    smooth_pad = np.pad(smooth, 1, mode="edge")
    source_pad = np.pad(source_smooth, 1, mode="edge")
    outside_light = np.stack([offset(smooth_pad, dy, dx) for dy, dx in neighbors])
    outside_source = np.stack([offset(source_pad, dy, dx) for dy, dx in neighbors])
    count = np.sum(outside, axis=0).clip(1)
    background = np.where(outside, outside_light, 0).sum(axis=0) / count
    source_background = np.where(outside, outside_source, 0).sum(axis=0) / count

    attrs, bits, paper, ink = screen_pixels(screen, preview)
    alternate = np.where(bits[..., None], paper, ink)
    alternate_light = alternate.astype(np.float32) @ LUMA
    gain = abs(alternate_light - background) - abs(light - background)
    # Draw only where the smoothed output lost a boundary, and avoid
    # swapping a clearly saturated source color for a new contour hue.
    source_step = source_smooth - source_background
    rendered_step = smooth - background
    direction = (alternate_light - background) * source_step >= 0
    weak = (abs(rendered_step) < 32) & (abs(source_step) <= 45)
    chroma = np.ptp(source, axis=-1)
    change = boundary & weak & (gain > 27) & (direction | (abs(source_step) < 5)) & (chroma < 105)
    # A real contour runs through several adjacent pixels. Suppress
    # isolated replacements created by the dithering pattern.
    support_pad = np.pad(change, 1)
    support = np.lib.stride_tricks.sliding_window_view(support_pad, (3, 3)).sum(axis=(-2, -1))
    change &= support >= 2
    if not change.any():
        return screen, preview
    result = np.where(change[..., None], alternate, preview)
    return pack(bits ^ change, attrs), result


def screen_pixels(screen, preview):
    attrs = np.frombuffer(screen[6144:], dtype=np.uint8).reshape(-1, COLS)
    tiled = attrs.repeat(8, axis=0).repeat(8, axis=1)
    bright = (tiled >> 3) & 8
    paper = PALETTE[((tiled >> 3) & 7) | bright]
    ink = PALETTE[(tiled & 7) | bright]
    bits = (preview == ink).all(axis=-1)
    return attrs, bits, paper, ink


def restore_color_accents(source, baseline, adjusted):
    """Restore cells where a correctly represented dominant channel was lost."""
    old_screen, old = baseline
    screen, preview = adjusted
    source = source.astype(np.int16)
    original = old.astype(np.int16)
    strongest = source.argmax(axis=-1)
    source_sorted = np.sort(source, axis=-1)
    old_sorted = np.sort(original, axis=-1)
    faithful = ((source_sorted[..., 2] - source_sorted[..., 1] >= 13)
                & (old_sorted[..., 2] - old_sorted[..., 1] >= 40)
                & (original.argmax(axis=-1) == strongest))
    lost = faithful & np.any(preview != old, axis=-1)
    cells = to_cells(lost).any(axis=(2, 3))
    if not cells.any():
        return adjusted
    old_attrs, old_bits, _, _ = screen_pixels(old_screen, old)
    attrs, bits, _, _ = screen_pixels(screen, preview)
    lock = cells.repeat(8, axis=0).repeat(8, axis=1)
    return pack(np.where(lock, old_bits, bits), np.where(cells, old_attrs, attrs)), np.where(lock[..., None], old, preview)


def pool4(rgb):
    h, w = rgb.shape[:2]
    return rgb.reshape(h // 4, 4, w // 4, 4, *rgb.shape[2:]).mean(axis=(1, 3))


def subject_scores(source, output, mask):
    """Measure silhouette contrast and false 8x8 steps on the decoded screen."""
    source, output, mask = pool4(source.astype(np.float32)), pool4(output.astype(np.float32)), pool4(mask)
    light, colors = [], []
    seam_error = seam_weight = 0.
    for axis in (0, 1):
        step = np.diff(output, axis=axis)
        boundary = abs(np.diff(mask, axis=axis)) > .48
        light.extend(abs(step[boundary] @ LUMA))
        colors.extend(np.sqrt(np.mean(step[boundary] ** 2, axis=-1)))
        true_step = np.diff(source, axis=axis)
        seams = np.s_[1::2, :] if axis == 0 else np.s_[:, 1::2]
        weight = edge_weight(true_step[seams] / 255)
        seam_error += float((np.mean((step[seams] - true_step[seams]) ** 2, axis=-1) * weight).sum())
        seam_weight += float(weight.sum())
    return dict(boundary_samples=len(light), luma_contrast=float(np.mean(light)) if light else 0.,
                rgb_contrast=float(np.mean(colors)) if colors else 0.,
                seam_rmse=float(np.sqrt(seam_error / seam_weight)))


def improves_subject(before, after):
    """Require a contrast gain with bounded added grid error."""
    return (before["boundary_samples"] >= 16
            and after["luma_contrast"] >= before["luma_contrast"] + .5
            and after["rgb_contrast"] >= .95 * before["rgb_contrast"]
            and after["seam_rmse"] <= before["seam_rmse"] + min(1.25, .06 * before["seam_rmse"]))


def preserves_colors(source, before, after):
    """Keep saturated source hues already represented by the baseline screen."""
    def chroma(rgb):
        pooled = pool4(rgb.astype(np.float32))
        return pooled - pooled.mean(axis=-1, keepdims=True)

    original, baseline, adjusted = map(chroma, (source, before, after))
    magnitude = np.linalg.norm(original, axis=-1)
    axis = original / np.maximum(magnitude[..., None], 1)
    baseline_projection = (baseline * axis).sum(axis=-1)
    adjusted_projection = (adjusted * axis).sum(axis=-1)
    matching = baseline_projection >= .90 * np.linalg.norm(baseline, axis=-1)
    faithful = (magnitude >= 65) & matching & (baseline_projection >= .55 * magnitude)
    lost = faithful & (adjusted_projection < np.minimum(.6 * baseline_projection, .55 * magnitude))
    # A small contiguous color accent matters even in a large photograph.
    return not ((lost[1:] & lost[:-1]).any() or (lost[:, 1:] & lost[:, :-1]).any())
