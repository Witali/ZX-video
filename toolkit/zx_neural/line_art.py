"""Extract and draw saturated red subjects as two-color Spectrum artwork."""

import numpy as np
from PIL import Image, ImageFilter

from .screen import COLS, HEIGHT, PALETTE, ROWS, WIDTH, pack
from .smooth import diffuse_coverage
from .subject import LUMA, box_mean
from .subject_continuity import connected_pixels


def remove_specks(mask, min_pixels):
    filtered = np.zeros_like(mask)
    for ys, xs in connected_pixels(mask):
        if len(ys) >= min_pixels:
            filtered[ys, xs] = True
    return filtered


def thin_edges(tone):
    """Keep gradient peaks in the direction across each source edge."""
    blurred = Image.fromarray(np.rint(tone).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.9))
    pad = np.pad(np.asarray(blurred, dtype=np.float32), 1, mode="edge")
    horizontal = pad[1:-1, 2:] - pad[1:-1, :-2]
    vertical = pad[2:, 1:-1] - pad[:-2, 1:-1]
    magnitude = np.hypot(horizontal, vertical)
    direction = np.rint(np.arctan2(vertical, horizontal) * (4 / np.pi)).astype(np.int8) % 4
    height, width = tone.shape
    pad = np.pad(magnitude, 1, mode="edge")
    lines = np.zeros_like(magnitude, dtype=bool)
    for axis, (dy, dx) in enumerate(((0, 1), (1, 1), (1, 0), (1, -1))):
        before = pad[1 - dy:1 - dy + height, 1 - dx:1 - dx + width]
        after = pad[1 + dy:1 + dy + height, 1 + dx:1 + dx + width]
        lines |= (direction == axis) & (magnitude >= before) & (magnitude > after)
    return lines & (magnitude >= 18)


def red_shapes(source, probability=None):
    """Return a red fill and its full silhouette, without object-specific inputs."""
    rgb = source.astype(np.float32)
    red, green, blue = rgb.transpose(2, 0, 1)
    warmth = red - np.maximum(green, blue)
    material = (warmth > 20) & (red > 1.33 * green) & (red > 1.25 * blue)
    if probability is not None:
        material &= (probability > .22) | ((box_mean(probability, 5) > .13) & (warmth > 38))

    mask = Image.fromarray(material.astype(np.uint8) * 255)
    mask = np.asarray(mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))) > 0
    silhouette = remove_specks(mask, 25)
    if not silhouette.any():
        return silhouette, silhouette
    # The black outline is drawn inside the silhouette. Keep genuine gaps
    # between parts when closing small holes in the color mask.
    silhouette = ~remove_specks(~silhouette, 10)
    padded = np.pad(silhouette, 1)
    interior = (silhouette & padded[:-2, 1:-1] & padded[2:, 1:-1]
                & padded[1:-1, :-2] & padded[1:-1, 2:])
    light = rgb @ LUMA
    tone = .8 * light + .27 * warmth.clip(0)
    lines = remove_specks(thin_edges(tone) & interior, 13)
    local_light = box_mean(light * silhouette, 13) / box_mean(silhouette, 13).clip(.05)
    shadow = box_mean(light, 3)
    shadows = remove_specks(silhouette & (shadow < .85 * local_light) & (shadow < 88), 12)
    return interior & ~lines & ~shadows, silhouette


def render_red_line_art(source, probability=None, *, shaded=False):
    """Center solid or shaded line art in a uniform Spectrum black/red pair."""
    fill, silhouette = red_shapes(source, probability)
    canvas = np.zeros((HEIGHT, WIDTH), dtype=bool)
    ys, xs = np.nonzero(silhouette)
    if ys.size:
        region = np.s_[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        crop = fill[region]
        height, width = crop.shape
        # Integer scaling keeps the original pixel contours sharp.
        scale = max(1, min((HEIGHT - 16) // height, (WIDTH - 16) // width))
        crop = crop.repeat(scale, axis=0).repeat(scale, axis=1)
        if shaded and crop.any():
            light = box_mean(source @ LUMA, 3)
            low, high = np.percentile(light[fill], (10, 90))
            coverage = .64 + .36 * np.clip((light - low) / max(1., high - low), 0, 1)
            coverage = coverage[region].repeat(scale, axis=0).repeat(scale, axis=1)
            coverage = np.where(crop, coverage, 0.)
            # The solid contour is outside the diffusion mask. Error cannot
            # leak into the line, the deep shadows, or the black background.
            direction = np.broadcast_to(np.array([1., 0., 0.], dtype=np.float32), (*crop.shape, 3))
            crop = diffuse_coverage(coverage, crop.astype(np.float32), direction)
        y, x = (HEIGHT - crop.shape[0]) // 2, (WIDTH - crop.shape[1]) // 2
        canvas[y:y + crop.shape[0], x:x + crop.shape[1]] = crop
    attrs = np.full((ROWS, COLS), 64 | 2, dtype=np.uint8)
    preview = PALETTE[np.where(canvas, 10, 8)]
    return pack(canvas, attrs), preview
