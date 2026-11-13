"""Recover source-supported background gaps beside narrow subject parts."""

import numpy as np

from .screen import pack
from .subject import LUMA, box_mean, color_accents, screen_pixels


def keep_open_gaps(source, current, probability):
    screen, preview = current
    source_light = box_mean(source @ LUMA, 3)
    rendered_light = box_mean(preview @ LUMA, 3)
    attrs, bits, paper, ink = screen_pixels(screen, preview)
    raises = np.zeros_like(bits)
    lowers = np.zeros_like(bits)
    for axis in (0, 1):
        original, rendered, saliency = (np.moveaxis(values, axis, 0)
                                        for values in (source_light, rendered_light, probability))
        brighten, darken = (np.moveaxis(values, axis, 0) for values in (raises, lowers))
        for width in (3, 5):
            middle = np.s_[width:-width]
            left, right = np.s_[:-2 * width], np.s_[2 * width:]
            center = original[middle]
            left_step = center - original[left]
            right_step = center - original[right]
            # The source should show a brighter lane with two darker lips.
            # Use saliency as a neighborhood cue. Small gaps are often
            # merged into the foreground by the low-resolution mask.
            supported = ((center > 45) & (left_step > 9) & (right_step > 9)
                         & (np.maximum(saliency[left], saliency[right]) >= .72)
                         & (saliency[middle] < .66)
                         & (saliency[middle] < np.maximum(saliency[left], saliency[right]) - .21))
            supported &= np.moveaxis(box_mean(np.moveaxis(supported, 0, axis).astype(np.float32), 3), axis, 0) >= .45
            missing_left = rendered[middle] - rendered[left] < left_step * .7
            missing_right = rendered[middle] - rendered[right] < right_step * .7
            brighten[middle] |= supported & (missing_left | missing_right)
            darken[left] |= supported & missing_left & (saliency[left] >= .42)
            darken[right] |= supported & missing_right & (saliency[right] >= .42)

    # A single endpoint would overstate a faint edge in the photo. Allow
    # only pixels whose current pooled brightness already misses the source
    # in the direction of the correction and whose alternate color helps.
    light = preview @ LUMA
    alternate = np.where(bits[..., None], paper, ink)
    step = alternate @ LUMA - light
    brighten = raises & ~lowers & (step > 24)
    darken = lowers & ~raises & (step < -24)
    original = source.astype(np.float32)
    # Flip only to a color that agrees with the source hue. A legal but
    # unrelated endpoint could leave a colored fleck on the gap's edge.
    wrong_hue = ((alternate > 0) & (original < original.max(axis=-1, keepdims=True) * .50)).any(axis=-1)
    missing_channel = (alternate == 0) & (original >= original.max(axis=-1, keepdims=True) * .80)
    wrong_hue |= (alternate.max(axis=-1) > 0) & missing_channel.any(axis=-1)
    eligible = (brighten | darken) & ~wrong_hue & ~color_accents(source, preview)
    if not eligible.any():
        return current
    target = source_light + 8 * (brighten.astype(np.int8) - darken)
    # Each flip changes the surrounding 3×3 brightness averages. Evaluate
    # non-overlapping neighborhoods together so several flips cannot all
    # claim the same improvement and turn a weak boundary into a dark bar.
    for y in range(3):
        for x in range(3):
            phase = np.s_[y::3, x::3]
            delta = step[phase]
            residual = box_mean(box_mean(light, 3) - target, 3)[phase]
            improve = eligible[phase] & (delta * (2 * residual + delta / 9) < 0)
            bits[phase] ^= improve
            light[phase] += np.where(improve, delta, 0)
    preview = np.where(bits[..., None], ink, paper)
    return pack(bits, attrs), preview
