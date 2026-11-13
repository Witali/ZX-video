"""Prepare source pixels and encode legal ZX Spectrum screen bytes."""

import numpy as np
from PIL import Image, ImageOps

WIDTH, HEIGHT = 256, 192
ROWS, COLS = HEIGHT // 8, WIDTH // 8
PALETTE = np.array([
    [(255 if bright else 205) if color & channel else 0 for channel in (2, 4, 1)]
    for bright in range(2) for color in range(8)
], dtype=np.uint8)
ATTRIBUTES = np.array([
    (bright << 6) | (paper << 3) | ink
    for bright in range(2) for paper in range(8) for ink in range(paper + 1, 8)
], dtype=np.uint8)
PAPER = ((ATTRIBUTES >> 3) & 7) | ((ATTRIBUTES >> 3) & 8)
INK = (ATTRIBUTES & 7) | ((ATTRIBUTES >> 3) & 8)
PAIR_COUNT = len(ATTRIBUTES)


def prepare(image, crop=False):
    """Honor EXIF orientation and preserve aspect ratio on a black canvas."""
    source = ImageOps.exif_transpose(image).convert("RGBA")
    if crop:
        source = ImageOps.fit(source, (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    else:
        scale = min(WIDTH / source.width, HEIGHT / source.height)
        size = max(1, round(source.width * scale)), max(1, round(source.height * scale))
        source = source.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    canvas.paste(source, ((WIDTH - source.width) // 2, (HEIGHT - source.height) // 2), source)
    return np.asarray(canvas)


def to_cells(values):
    """Arrange a native raster as 24 by 32 cells of 8 by 8 samples."""
    extra = values.shape[2:]
    return values.reshape(ROWS, 8, COLS, 8, *extra).swapaxes(1, 2)


def from_cells(values):
    return values.swapaxes(1, 2).reshape(HEIGHT, WIDTH, *values.shape[4:])


def pack(bits, attrs):
    """Serialize the bitmap in Spectrum scanline order, then row-major attributes."""
    if bits.shape != (HEIGHT, WIDTH) or attrs.shape != (ROWS, COLS) or np.any(attrs & 128):
        raise ValueError("expected a 256x192 bitmap and 24x32 non-FLASH attributes")
    y = np.arange(HEIGHT)
    offsets = (((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2))[:, None]
    bitmap = np.empty(6144, np.uint8)
    bitmap[offsets + np.arange(COLS)] = np.packbits(bits, axis=1)
    return bitmap.tobytes() + attrs.tobytes()
