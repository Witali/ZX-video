"""Experimental five-level cells: four radix-5 samples per 10-bit word.

Full-frame storage is 3840 pattern bytes + 768 attribute bytes. This host
prototype has no player/stream integration. Expansion uses two 1024-byte
lookup pages groups; divisions are needed only when generating host tables.
"""
import numpy as np

import build_long_video_trd as video
from dither_phase import reversed_phase

PATTERNS = ((0, 0), (2, 0), (2, 1), (3, 1), (3, 3))
BITMAP_BYTES, STATE_BYTES = 3840, 4608


def pack_levels(levels):
    levels = np.asarray(levels)
    if (levels.shape != (96, 128) or not np.issubdtype(levels.dtype, np.integer)
            or np.any(levels < 0) or np.any(levels > 4)):
        raise ValueError('expected 128x96 integer levels in 0..4')
    row = levels.astype(np.uint64).reshape(-1, 4)
    words = ((row[:, 0]*5+row[:, 1])*5+row[:, 2])*5+row[:, 3]
    group = words.reshape(-1, 4)
    packed = (group[:, 0] << 30) | (group[:, 1] << 20) | (group[:, 2] << 10) | group[:, 3]
    return ((packed[:, None] >> np.array([32, 24, 16, 8, 0], dtype=np.uint64)) & 255).astype(np.uint8).tobytes()


def unpack_words(data):
    if len(data) != BITMAP_BYTES:
        raise ValueError('expected 3840 packed five-level bytes')
    group = np.frombuffer(data, dtype=np.uint8).astype(np.uint64).reshape(-1, 5)
    combined = np.zeros(len(group), dtype=np.uint64)
    for column in range(5):
        combined = (combined << 8) | group[:, column]
    words = ((combined[:, None] >> np.array([30, 20, 10, 0], dtype=np.uint64)) & 1023).astype(np.uint16)
    if np.any(words >= 625):
        raise ValueError('unused five-level word (625..1023)')
    return words.reshape(96, 32)


def unpack_levels(data):
    words = unpack_words(data)
    return ((words[..., None] // np.array([125, 25, 5, 1])) % 5).astype(np.uint8).reshape(96, 128)


def from_compact(state):
    state = np.frombuffer(bytes(state), dtype=np.uint8)
    if state.shape != (3840,) or np.any(state[3072:] & 128):
        raise ValueError('expected a compact frame without FLASH')
    attrs = state[3072:].reshape(24, 32).copy()
    reverse = reversed_phase(attrs)
    levels = ((state[:3072].reshape(96, 32)[..., None] >> np.array([6, 4, 2, 0])) & 3).reshape(96, 128)
    levels = np.array([0, 1, 2, 4], dtype=np.uint8)[levels]
    levels = np.where(reverse.repeat(4, axis=0).repeat(4, axis=1), 4-levels, levels)
    swapped = (attrs & 0xc0) | ((attrs & 7) << 3) | ((attrs >> 3) & 7)
    attrs = np.where(reverse, swapped, attrs)
    return pack_levels(levels)+attrs.tobytes()


def encode_image(image, previous_attrs=None, attr_change_penalty=0):
    """Quantize scaled RGB with all five shades available in every cell.

    Host experiment only. Keep the main converter's existing RGB distance
    and palette endpoints; canonical INK is brighter than PAPER. Unlike
    from_compact(), this can choose both quarter shades inside one cell.
    """
    image = np.asarray(image)
    if image.shape != (96, 128, 3) or np.any(image < 0) or np.any(image > 255):
        raise ValueError('expected a 128x96 RGB image in 0..255')
    if attr_change_penalty < 0:
        raise ValueError('negative attribute-change penalty')
    keep = ~reversed_phase(video.COLOUR_ATTRS)
    attrs = video.COLOUR_ATTRS[keep]
    paper, ink = video.COLOUR_PAPERS[keep], video.COLOUR_INKS[keep]
    palettes = paper[:, None]+np.arange(5)[None, :, None]/4*(ink-paper)[:, None]
    colours, inverse = np.unique(image.reshape(-1, 3), axis=0, return_inverse=True)
    errors = np.empty((len(colours), len(attrs)))
    choices = np.empty(errors.shape, dtype=np.uint8)
    for first in range(0, len(colours), 512):
        distance = ((colours[first:first+512, None, None].astype(np.float64)-palettes[None])**2).sum(axis=3)
        errors[first:first+512] = distance.min(axis=2)
        choices[first:first+512] = distance.argmin(axis=2)
    def cells(data):
        return data[inverse].reshape(24, 4, 32, 4, len(attrs)).transpose(0, 2, 1, 3, 4).reshape(768, 16, len(attrs))
    score = cells(errors).sum(axis=1)
    if previous_attrs is not None:
        previous_attrs = np.asarray(previous_attrs, dtype=np.uint8)
        if previous_attrs.shape != (768,):
            raise ValueError('expected 768 previous attributes')
        reverse = reversed_phase(previous_attrs)
        canonical = (previous_attrs & 0xc0) | ((previous_attrs & 7) << 3) | ((previous_attrs >> 3) & 7)
        previous_attrs = np.where(reverse, canonical, previous_attrs)
        score += (attrs[None] != previous_attrs[:, None])*attr_change_penalty
    best = score.argmin(axis=1)
    selected = cells(choices)[np.arange(768), :, best]
    levels = selected.reshape(24, 32, 4, 4).transpose(0, 2, 1, 3).reshape(96, 128)
    return pack_levels(levels)+attrs[best].tobytes()


def build_tables():
    # Unused entries stay zero and are rejected by the host validator.
    top, bottom = bytearray(1024), bytearray(1024)
    for word in range(625):
        for index, divisor in enumerate((125, 25, 5, 1)):
            upper, lower = PATTERNS[(word//divisor) % 5]
            top[word] |= upper << (6-index*2)
            bottom[word] |= lower << (6-index*2)
    return bytes(top), bytes(bottom)


TOP, BOTTOM = build_tables()


def expand(state):
    if len(state) != STATE_BYTES:
        raise ValueError('expected one 4608-byte five-level frame')
    words = unpack_words(state[:BITMAP_BYTES])
    top, bottom = np.frombuffer(TOP, dtype=np.uint8)[words], np.frombuffer(BOTTOM, dtype=np.uint8)[words]
    bitmap = bytearray(6144)
    for row in range(96):
        for offset, data in ((0, top[row]), (1, bottom[row])):
            at = video.base.spectrum_bitmap_offset(0, row*2+offset)
            bitmap[at:at+32] = data.tobytes()
    return bytes(bitmap), bytes(state[BITMAP_BYTES:])
