"""Try small source transforms when they improve ZX attribute alignment."""

from itertools import product

import numpy as np
from PIL import Image, ImageOps

from .objective import edge_weight
from .screen import Framing, HEIGHT, WIDTH, placement, prepare
from .subject import pool4


def content_mask(rect):
    left, top, right, bottom = rect
    inside = np.zeros((HEIGHT, WIDTH), dtype=bool)
    inside[top:bottom, left:right] = True
    return inside


def gradients(rgb):
    pixels = rgb.astype(np.float32)
    return tuple((np.abs(np.diff(pixels, axis=axis)).max(axis=-1) - 22).clip(0) ** 2 for axis in (0, 1))


def captured_energy(vertical, horizontal, x=0, y=0):
    """Fraction of source contrast directly on the attribute grid."""
    captured = vertical[(7 - y) % 8::8].sum() + horizontal[:, (7 - x) % 8::8].sum()
    return float(captured) / max(float(vertical.sum() + horizontal.sum()), 1)


def proxy_scores(proxy, crop, options):
    """Reuse one resampled proxy and its gradients for all shifts at a scale."""
    scale = options[0].scale
    if not crop:
        centered = Framing(scale)
        _, (left, top, right, bottom) = placement(proxy.size, False, centered)
        vertical, horizontal = gradients(prepare(proxy, framing=centered)[top:bottom, left:right])
        for framing in options:
            yield framing, captured_energy(vertical, horizontal, left + framing.dx, top + framing.dy)
        return

    margin_x = max(abs(framing.dx) for framing in options)
    margin_y = max(abs(framing.dy) for framing in options)
    upper, _ = placement(proxy.size, True, Framing(scale, margin_x, margin_y))
    lower, _ = placement(proxy.size, True, Framing(scale, -margin_x, -margin_y))
    size = WIDTH + 2 * margin_x, HEIGHT + 2 * margin_y
    expanded = proxy.resize(size, Image.Resampling.LANCZOS, box=(*upper[:2], *lower[2:]))
    flat = Image.new("RGB", size)
    flat.paste(expanded, (0, 0), expanded)
    vertical, horizontal = gradients(np.asarray(flat))
    for framing in options:
        x, y = margin_x - framing.dx, margin_y - framing.dy
        yield framing, captured_energy(vertical[y:y + HEIGHT - 1, x:x + WIDTH],
                                       horizontal[y:y + HEIGHT, x:x + WIDTH - 1])


def shortlist(image, crop):
    """Rank geometry on a small proxy and spend full conversions on two candidates."""
    proxy = ImageOps.exif_transpose(image).convert("RGBA")
    size = proxy.size
    proxy.thumbnail((768, 576), Image.Resampling.LANCZOS)
    original = Framing()
    base_rect = placement(proxy.size, crop, original)[1]
    if min(base_rect[2] - base_rect[0], base_rect[3] - base_rect[1]) < 16:
        return []
    left, top, right, bottom = base_rect
    reference = captured_energy(*gradients(prepare(proxy, crop)[top:bottom, left:right]), left, top)
    scales = (1., 1. + 1/64, 1. + 2/64) if crop else (1., 1. - 1/64, 1. - 2/64)
    candidates = []
    for scale in scales:
        options = [Framing(scale, dx, dy) for dx, dy in product(range(-3, 4), repeat=2)]
        valid = [f for f in options if f != original and placement(size, crop, f) is not None
                 and placement(proxy.size, crop, f) is not None]
        if valid:
            for framing, score in proxy_scores(proxy, crop, valid):
                cost = .004 * (abs(framing.dx) + abs(framing.dy)) + .006 * abs(scale - 1) * 64
                if score - cost > reference + .012:
                    candidates.append((score - cost, framing))
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    if not candidates:
        return []
    best = candidates[0][1]
    alternate = next((option for _, option in candidates[1:]
                      if option.scale != best.scale or abs(option.dx - best.dx) + abs(option.dy - best.dy) >= 2), None)
    return [best] if alternate is None else [best, alternate]


def frame_errors(source, preview, rect):
    """Score only image content and exclude letterbox pixels from all averages."""
    pixels = source.astype(np.float32)
    inside = content_mask(rect)
    residual = preview.astype(np.float32) - pixels
    pooled, pooled_source = pool4(residual), pool4(pixels)
    valid = pool4(inside) == 1
    color = float(np.sqrt(np.mean(pooled[valid] ** 2)))
    seam_error = seam_weight = edge_error = edge_count = detail = detail_count = 0.
    for axis, seam in ((0, np.s_[1::2, :]), (1, np.s_[:, 1::2])):
        coarse_valid = (valid[1:] & valid[:-1]) if axis == 0 else (valid[:, 1:] & valid[:, :-1])
        weight = edge_weight(np.diff(pooled_source, axis=axis)[seam] / 255) * coarse_valid[seam]
        error = np.mean(np.diff(pooled, axis=axis)[seam] ** 2, axis=-1)
        seam_error += float((error * weight).sum())
        seam_weight += float(weight.sum())
        native_valid = (inside[1:] & inside[:-1]) if axis == 0 else (inside[:, 1:] & inside[:, :-1])
        contrast = np.abs(np.diff(pixels, axis=axis)).max(axis=-1)
        strong = native_valid & (contrast >= 76.5)
        edge_error += float(np.square(np.diff(residual, axis=axis)[strong]).sum())
        edge_count += int(strong.sum())
        detail += float(np.square((contrast[native_valid] - 22).clip(0)).sum())
        detail_count += int(native_valid.sum())
    return (np.sqrt(seam_error / max(seam_weight, 1)), color,
            np.sqrt(edge_error / max(3 * edge_count, 1)), detail / max(detail_count, 1))


def align_cells(image, crop, render, subject_mask=None):
    """Keep the original framing unless an actual render confirms an improvement."""
    size = ImageOps.exif_transpose(image).size
    original = Framing()
    proposals = shortlist(image, crop)

    def convert_framing(framing):
        source = prepare(image, crop, framing=framing)
        probability = None
        if subject_mask is not None:
            probability = prepare(subject_mask, crop, framing=framing)[..., 0].astype(np.float32) / 255
        return source, render(source, probability)

    source, baseline = convert_framing(original)
    if not proposals:
        return original, baseline
    seam, color, edges, detail = frame_errors(source, baseline[1], placement(size, crop, original)[1])
    best = (original, baseline)
    best_seam = seam - max(.5, .07 * seam)
    for framing in proposals:
        source, result = convert_framing(framing)
        error, rgb, structure, contrast = frame_errors(source, result[1], placement(size, crop, framing)[1])
        if error < best_seam and rgb <= color * 1.005 and structure <= edges + .5 and contrast >= .94 * detail:
            best = framing, result
            best_seam = error
    return best
