"""Draw colored subjects with solid contours and shaded Spectrum fills."""

import numpy as np
from PIL import Image, ImageFilter

from .screen import ATTRIBUTES, COLS, HEIGHT, PALETTE, ROWS, WIDTH, from_cells, pack, to_cells
from .smooth import diffuse_coverage
from .subject import LUMA, box_mean, screen_pixels, subject_scores
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
    interior = (material & silhouette & padded[:-2, 1:-1] & padded[2:, 1:-1]
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


def outline_subjects(source, current, probability=None, *, preference=None, unmasked_chroma=.44):
    """Shade suitable colored objects in place using black and their own hue."""
    screen, preview = current
    rgb = source.astype(np.float32)
    chroma = np.ptp(rgb, axis=-1)
    relative_chroma = unmasked_chroma if probability is None else .29
    color = (chroma >= 29) & (chroma >= relative_chroma * rgb.max(axis=-1))
    if probability is not None:
        color &= box_mean(probability, 5) > .23
    if np.count_nonzero(color) < 140:
        return current

    # Compare normalized chroma, so the same hue can span light and shade.
    hues = PALETTE[1:7].astype(np.float32) / 205
    normalized = (rgb - rgb.min(axis=-1, keepdims=True)) / np.maximum(chroma[..., None], 1)
    source_hue = ((normalized[..., None, :] - hues) ** 2).sum(axis=-1).argmin(axis=-1) + 1
    preview_hue = (preview > 0) @ np.array([2, 4, 1], dtype=np.uint8)
    light = rgb @ LUMA
    smooth = box_mean(light, 3)
    edges = thin_edges(.8 * light + .27 * chroma)
    attrs, bits, _, _ = screen_pixels(screen, preview)
    bright = ((attrs & 64) != 0).astype(np.uint8) * 8
    original = to_cells(preview)
    black = (original == 0).all(axis=-1)
    new_attrs, new_bits = attrs.copy(), to_cells(bits).copy()
    output = original.copy()
    reserved = np.zeros_like(attrs, dtype=bool)

    for hue in range(1, 7):
        material = color & (source_hue == hue)
        mask = material.copy()
        if mask.sum() < 140:
            continue
        image = Image.fromarray(mask.astype(np.uint8) * 255)
        closed = image.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
        mask |= (np.asarray(closed) > 0) & (source_hue == hue)
        fill = np.zeros_like(mask)
        shape = np.zeros_like(mask)
        coverage = np.zeros_like(light)
        for ys, xs in connected_pixels(mask):
            if not 140 <= len(ys) <= 6500 or min(np.ptp(ys), np.ptp(xs)) < 9:
                continue
            if (preview_hue[ys, xs] == hue).mean() < .35:
                continue
            low, high = np.percentile(smooth[ys, xs], (15, 85))
            if high - low < 13:
                continue
            # Work in a padded region so morphology and local averages
            # retain their normal support around the object's boundary.
            y, x = max(0, ys.min() - 7), max(0, xs.min() - 7)
            region = np.s_[y:ys.max() + 8, x:xs.max() + 8]
            part = np.zeros_like(mask[region])
            part[ys - y, xs - x] = True
            part = ~remove_specks(~part, 10)
            padded = np.pad(part, 1)
            inside = (part & padded[:-2, 1:-1] & padded[2:, 1:-1]
                      & padded[1:-1, :-2] & padded[1:-1, 2:])
            lines = remove_specks(edges[region] & inside, 13)
            local = box_mean(light[region] * part, 13) / box_mean(part, 13).clip(.05)
            dark = (smooth[region] < np.maximum(.85 * local, .65 * high))
            shadows = remove_specks(part & dark & (smooth[region] < np.median(smooth[region][part])), 12)
            # The closed shape can bridge small breaks in an outline, but
            # only original color evidence may receive any new colored fill.
            visible = inside & material[region] & ~lines & ~shadows
            if np.count_nonzero(lines | shadows) < 13 or not visible.any():
                continue
            shape[region] |= part
            fill[region] |= visible
            local_coverage = coverage[region]
            local_coverage[visible] = .72 + .28 * np.clip(
                (smooth[region][visible] - low) / (high - low), 0, 1,
            )

        foreground = PALETTE[bright + hue][..., None, None, :]
        same_color = (original == foreground).all(axis=-1)
        part_cells = to_cells(shape)
        outside_compatible = (part_cells | black | same_color).all(axis=(2, 3))
        minimum_coverage = .62
        if preference is not None:
            pair = np.searchsorted(ATTRIBUTES, (attrs & 64) | hue)
            minimum_coverage = .62 + 20 * np.take_along_axis(preference, pair[..., None], axis=-1)[..., 0]
        cells = (part_cells.mean(axis=(2, 3)) >= minimum_coverage) & outside_compatible & ~reserved
        cells &= (to_cells(fill).any(axis=(2, 3)) | (black | part_cells).all(axis=(2, 3)))
        if not cells.any():
            continue
        active = from_cells(np.broadcast_to(cells[..., None, None], part_cells.shape))
        strength = (active & fill).astype(np.float32)
        level = np.where(shape, np.where(fill, coverage, 0), from_cells(same_color))
        direction = np.broadcast_to(hues[hue - 1], rgb.shape)
        shaded = to_cells(diffuse_coverage(level, strength, direction))
        # Reapply the mask at writeback, even if diffusion changes later.
        shaded = np.where(part_cells, shaded & to_cells(fill), same_color)
        new_attrs[cells] = (attrs[cells] & 64) | hue
        new_bits[cells] = shaded[cells]
        output[cells] = np.where(shaded[cells][..., None], foreground[cells], 0)
        reserved |= cells

    if not reserved.any():
        return current
    result = from_cells(output)
    mask = np.zeros(source.shape[:2], dtype=np.float32)
    original_seams = subject_scores(source, preview, mask)["seam_rmse"]
    styled_seams = subject_scores(source, result, mask)["seam_rmse"]
    if styled_seams > original_seams + .8:
        return current
    return pack(from_cells(new_bits), new_attrs), result
