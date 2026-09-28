"""Host reference for attribute-independent spatial dither phase.

This is an explicit reference mode, not a change to existing player bytes.
Keep two-bit values and attributes intact. For dark INK, exchange the two
native scanlines in each 2x2 pattern. Dirty maps must then include changes
in attribute orientation relative to the same back screen two frames ago.
"""
import numpy as np

import build_long_video_trd as video


def reversed_phase(attributes):
    attributes = np.asarray(attributes, dtype=np.uint8)
    # Both endpoints share BRIGHT. Spectrum indices (B,R,G bit weights)
    # increase in luminance: black, blue, red, magenta, green, cyan, yellow,
    # white. Equal endpoints have no visible dither phase.
    return (attributes & 7) < ((attributes >> 3) & 7)


def scanlines(state, *, aligned=False):
    state = np.frombuffer(bytes(state), dtype=np.uint8)
    if state.shape != (video.STATE_BYTES,):
        raise ValueError('expected one 3840-byte compact frame')
    attrs = state[3072:].reshape(24, 32)
    if aligned and np.any(attrs & 128):
        raise ValueError('FLASH needs a separate time-dependent phase policy')
    packed = state[:3072].reshape(96, 32)
    top_table, bottom_table = video.build_player_dither_tables()
    top = np.frombuffer(top_table, dtype=np.uint8)[packed]
    bottom = np.frombuffer(bottom_table, dtype=np.uint8)[packed]
    if aligned:
        reverse = reversed_phase(attrs).repeat(4, axis=0)
        top, bottom = np.where(reverse, bottom, top), np.where(reverse, top, bottom)
    return top, bottom


def expand(state, *, aligned=False):
    top, bottom = scanlines(state, aligned=aligned)
    bitmap = bytearray(6144)
    for row in range(96):
        for offset, data in ((0, top[row]), (1, bottom[row])):
            at = video.base.spectrum_bitmap_offset(0, row*2+offset)
            bitmap[at:at+32] = data.tobytes()
    return bytes(bitmap), bytes(state)[3072:]


def dirty_maps(states, *, aligned=False, dense=18):
    """Native bitmap differences against n-2, including attribute-only flips.

    An offline map generator for the reference renderer. Existing compact
    predictors, palettes and packet formats are not modified here.
    """
    if (states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840
            or not 1 <= dense <= 32 or np.any(states[:, :256])
            or np.any(states[:, 2816:3072])):
        raise ValueError('invalid states, density or omitted rows')
    previous = [np.zeros((2, 96, 32), dtype=np.uint8) for _ in range(2)]
    maps, exact_cells = [], []
    for index, state in enumerate(states):
        native = np.stack(scanlines(state, aligned=aligned))
        changed = (native[:, 8:88] != previous[index % 2][:, 8:88]).reshape(2, 20, 4, 32).any(axis=(0, 2))
        exact_cells.append(changed.copy())
        changed[changed.sum(axis=1) >= dense] = True
        maps.append(np.packbits(changed, axis=1))
        previous[index % 2] = native
    return np.asarray(maps, dtype=np.uint8), np.asarray(exact_cells, dtype=bool)


def phase_seams(state, previous=None):
    """Count matching 50% samples with reversed endpoint colours.

    Counts are diagnostic opportunities for the reported checkerboard seam,
    not measurements of perceived aliasing or comparisons to original media.
    Only the active picture is counted, excluding the fixed black bands.
    """
    data = np.frombuffer(bytes(state), dtype=np.uint8)
    attrs = data[3072:].reshape(24, 32)[3:21]
    packed = data[:3072].reshape(96, 32)[12:84]
    levels = ((packed[..., None] >> np.array([6, 4, 2, 0])) & 3).reshape(18, 4, 32, 4)

    def swapped(a, b):
        reverse = (a & 0xc0) | ((a & 7) << 3) | ((a >> 3) & 7)
        return (a != b) & (b == reverse)

    horizontal = (levels[:, :, :-1, -1] == 2) & (levels[:, :, 1:, 0] == 2)
    horizontal &= swapped(attrs[:, :-1], attrs[:, 1:])[:, None, :]
    vertical = (levels[:-1, -1] == 2) & (levels[1:, 0] == 2)
    vertical &= swapped(attrs[:-1], attrs[1:])[:, :, None]
    temporal = 0
    if previous is not None:
        before = np.frombuffer(bytes(previous), dtype=np.uint8)
        pa = before[3072:].reshape(24, 32)[3:21]
        pl = ((before[:3072].reshape(96, 32)[12:84, :, None]
               >> np.array([6, 4, 2, 0])) & 3).reshape(18, 4, 32, 4)
        temporal = int(((levels == 2) & (pl == 2)
                        & swapped(pa, attrs)[:, None, :, None]).sum())
    return dict(horizontal_samples=int(horizontal.sum()), vertical_samples=int(vertical.sum()),
                temporal_half_samples=temporal,
                reversed_half_samples=int(((levels == 2)
                    & reversed_phase(attrs)[:, None, :, None]).sum()))
