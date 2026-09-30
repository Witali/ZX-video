"""Host-only adaptive 4x4 native dithering on the existing 128x96 grid.

Eight target coverages are regional averages. Five-level cells are retained
unless a smooth 2x2 logical tile gains mean-colour accuracy. No temporal
phase, palette search, player integration or resolution reduction is added.
"""
from dataclasses import dataclass

import numpy as np

import build_long_video_trd as video
import five_level_dither as five


BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                  [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.uint8)
DOT_COUNTS = np.array([0, 2, 5, 7, 9, 11, 14, 16], dtype=np.uint8)
PALETTE = np.array([[video.base.zx_rgb((a >> 3) & 7, (a >> 6) & 1),
                     video.base.zx_rgb(a & 7, (a >> 6) & 1)]
                    for a in range(128)], dtype=np.float64)


@dataclass(frozen=True)
class Frame:
    attrs: bytes
    modes: bytes
    cells: tuple


def pool(image, size):
    h, w, c = image.shape
    return image.reshape(h//size, size, w//size, size, c).mean(axis=(1, 3))


def endpoints(attrs, scale=4):
    return PALETTE[np.frombuffer(attrs, dtype=np.uint8)].reshape(24, 32, 2, 3).repeat(scale, 0).repeat(scale, 1)


def pattern(levels):
    """Independent five-level pattern expansion in linear screen order."""
    pairs = np.array(five.PATTERNS, dtype=np.uint8)[levels]
    out = np.empty((192, 256), dtype=np.uint8)
    for y in range(2):
        for x in range(2):
            out[y::2, x::2] = (pairs[:, :, y] >> (1-x)) & 1
    return out


def ordered(projected):
    indices = np.abs(projected[..., None]*16-DOT_COUNTS).argmin(axis=2)
    count = DOT_COUNTS[indices].repeat(2, 0).repeat(2, 1)
    return (np.tile(BAYER, (48, 64)) < count).astype(np.uint8)


def rgb(bits, attrs):
    pair = endpoints(attrs, 8)
    return pair[:, :, 0]+bits[:, :, None]*(pair[:, :, 1]-pair[:, :, 0])


def make_frame(levels, attrs, bits, selected):
    logical = levels.reshape(24, 4, 32, 4).transpose(0, 2, 1, 3).reshape(768, 4, 4)
    native = np.packbits(bits, axis=1).reshape(24, 8, 32).transpose(0, 2, 1).reshape(768, 8)
    modes = selected.reshape(24, 2, 32, 2).any(axis=(1, 3)).reshape(768)
    cells = []
    for cell, raw, escape in zip(logical, native, modes):
        if escape:
            cells.append(raw.tobytes())
        else:
            words = cell.astype(np.uint64) @ np.array([125, 25, 5, 1], dtype=np.uint64)
            cells.append(sum(int(word) << shift for word, shift in zip(words, (30, 20, 10, 0))).to_bytes(5, 'big'))
    return Frame(attrs, modes.astype(np.uint8).tobytes(), tuple(cells))


def quantize(image, compact, smooth_limit=32):
    image = np.asarray(image, dtype=np.float64)
    if image.shape != (96, 128, 3) or not np.isfinite(image).all() or np.any((image < 0) | (image > 255)):
        raise ValueError('expected finite 128x96 RGB in 0..255')
    if not 0 <= smooth_limit <= 255: raise ValueError('invalid smoothness limit')
    attrs = five.from_compact(compact)[3840:]
    pairs = endpoints(attrs)
    dark, direction = pairs[:, :, 0], pairs[:, :, 1]-pairs[:, :, 0]
    norm = (direction**2).sum(axis=2)
    projection = np.clip(((image-dark)*direction).sum(axis=2)/np.maximum(norm, 1), 0, 1)
    # This is the minimum squared-RGB-error five-level choice for these endpoints.
    levels = np.abs(projection[:, :, None]*4-np.arange(5)).argmin(axis=2).astype(np.uint8)
    before, candidate = pattern(levels), ordered(projection)
    tiles = image.reshape(48, 2, 64, 2, 3)
    smooth = (tiles.max(axis=(1, 3))-tiles.min(axis=(1, 3))).max(axis=2) <= smooth_limit
    target = pool(image, 2)
    old_error = ((pool(rgb(before, attrs), 4)-target)**2).mean(axis=2)
    new_error = ((pool(rgb(candidate, attrs), 4)-target)**2).mean(axis=2)
    selected = smooth & (new_error < old_error-1e-9)
    after = np.where(selected.repeat(4, 0).repeat(4, 1), candidate, before)
    baseline = make_frame(levels, attrs, before, np.zeros_like(selected))
    result = make_frame(levels, attrs, after, selected)
    return baseline, result, selected


def decode(frame):
    if len(frame.attrs) != 768 or len(frame.modes) != 768 or len(frame.cells) != 768:
        raise ValueError('invalid frame size')
    if any(a & 128 or (a & 7) < ((a >> 3) & 7) for a in frame.attrs):
        raise ValueError('expected canonical FLASH=0 attributes')
    bits = np.zeros((192, 256), dtype=np.uint8)
    # Scalar decoder is separate from vectorized quantization and packing.
    for index, (mode, data) in enumerate(zip(frame.modes, frame.cells)):
        if mode not in (0, 1) or len(data) != (8 if mode else 5): raise ValueError('invalid cell')
        cy, cx = divmod(index, 32)
        if mode:
            rows = data
        else:
            value, rows = int.from_bytes(data, 'big'), []
            for shift in (30, 20, 10, 0):
                word = (value >> shift) & 1023
                if word >= 625: raise ValueError('invalid five-level word')
                row = [five.PATTERNS[(word//divisor) % 5] for divisor in (125, 25, 5, 1)]
                rows.extend(sum(p[y] << (6-x*2) for x, p in enumerate(row)) for y in range(2))
        for y, row in enumerate(rows):
            bits[cy*8+y, cx*8:cx*8+8] = [(row >> (7-x)) & 1 for x in range(8)]
    return bits


def encode_delta(previous, current, *, escapes):
    changed_attrs = np.frombuffer(previous.attrs, dtype=np.uint8) ^ np.frombuffer(current.attrs, dtype=np.uint8)
    changed = [i for i in range(768) if previous.cells[i] != current.cells[i] or previous.modes[i] != current.modes[i]]
    mask = np.zeros(768, dtype=np.uint8); mask[changed] = 1
    flags = [current.modes[i] for i in changed]
    if not escapes and any(current.modes): raise ValueError('native cell in five-level stream')
    mode_bytes = np.packbits(flags).tobytes() if escapes else b''
    return (np.packbits(changed_attrs != 0).tobytes()+np.packbits(mask).tobytes()
            +changed_attrs[changed_attrs != 0].tobytes()+mode_bytes
            +b''.join(current.cells[i] for i in changed))


def decode_delta(previous, packet, *, escapes):
    if len(packet) < 192: raise ValueError('truncated masks')
    attrs, modes, cells = bytearray(previous.attrs), bytearray(previous.modes), list(previous.cells)
    attribute_ids, cell_ids = [[i for i in range(768) if packet[base+i//8] & (128 >> (i % 8))]
                               for base in (0, 96)]
    pos = 192
    for i in attribute_ids:
        if pos >= len(packet) or not 0 < packet[pos] < 128: raise ValueError('invalid attribute residual')
        attrs[i] ^= packet[pos]; pos += 1
    mode_size = (len(cell_ids)+7)//8 if escapes else 0
    if pos+mode_size > len(packet): raise ValueError('truncated modes')
    flags = packet[pos:pos+mode_size]; pos += mode_size
    if escapes and len(cell_ids) % 8 and flags[-1] & ((1 << (8-len(cell_ids) % 8))-1):
        raise ValueError('nonzero mode padding')
    for j, i in enumerate(cell_ids):
        mode = int(bool(flags[j//8] & (128 >> (j % 8)))) if escapes else 0
        length = 8 if mode else 5
        if pos+length > len(packet): raise ValueError('truncated cell')
        modes[i], cells[i] = mode, packet[pos:pos+length]; pos += length
    if pos != len(packet): raise ValueError('trailing data')
    result = Frame(bytes(attrs), bytes(modes), tuple(cells))
    decode(result)
    return result
