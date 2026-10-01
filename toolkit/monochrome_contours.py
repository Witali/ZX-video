"""Experimental host-side soft contours from source RGB, before dithering.

This detects strong image edges, not semantic object boundaries. Blur and
short-component rejection limit texture noise. The Z80 format is unchanged.
"""
import cv2
import numpy as np

import five_level_dither as five
import monochrome_five_level as mono

PRESETS = dict(
    strong=dict(blur_kernel=5, blur_sigma=.9, canny_low=60, canny_high=120,
                minimum_component_pixels=6, shade_steps=1),
    soft=dict(blur_kernel=7, blur_sigma=1.4, canny_low=100, canny_high=200,
              minimum_component_pixels=12, luma_drop=24))


def edge_mask(image, *, preset='soft'):
    mono.luma_numerator(image)  # Shared shape/dtype validation.
    if preset not in PRESETS: raise ValueError('unknown contour preset')
    p = PRESETS[preset]
    active = np.ascontiguousarray(image[12:84])
    smooth = cv2.GaussianBlur(active, (p['blur_kernel'],)*2, p['blur_sigma'], borderType=cv2.BORDER_REPLICATE)
    # Multichannel gradients retain colour boundaries with similar luma.
    edges = cv2.Canny(smooth, p['canny_low'], p['canny_high'], L2gradient=True)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    keep = np.zeros(count, dtype=bool)
    keep[1:] = stats[1:,cv2.CC_STAT_AREA] >= p['minimum_component_pixels']
    result = np.zeros((96,128), dtype=bool)
    result[12:84] = keep[labels]
    return result


def encode(image, *, preset='soft'):
    original = mono.encode(image)
    levels = five.unpack_levels(original[:3840])
    mask = edge_mask(image, preset=preset)
    if preset == 'strong':
        selected = mask & (levels > 0)
        levels[selected] -= 1
    else:
        # A bounded pre-quantization change; at most one output shade step.
        y = mono.luma_numerator(image).astype(np.int64)
        y[mask] = np.maximum(0, y[mask]-PRESETS[preset]['luma_drop']*10000)
        levels[mask] = ((8*y[mask]+2550000)//5100000).astype(np.uint8)
    return five.pack_levels(levels)+original[3840:], mask
