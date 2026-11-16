"""Prepare source pixels and encode legal ZX Spectrum screen bytes."""

from dataclasses import dataclass

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


@dataclass(frozen=True)
class Framing:
    scale: float = 1.
    dx: int = 0
    dy: int = 0


def placement(size, crop, framing=Framing()):
    """Return the source window and destination rectangle, or reject clipping."""
    width, height = size
    if min(size) <= 0 or not np.isfinite(framing.scale) or framing.scale <= 0:
        return None
    ratios = WIDTH / width, HEIGHT / height
    if crop:
        scale = max(ratios) * framing.scale
        box = (width / 2 - (WIDTH / 2 + framing.dx) / scale,
               height / 2 - (HEIGHT / 2 + framing.dy) / scale,
               width / 2 + (WIDTH / 2 - framing.dx) / scale,
               height / 2 + (HEIGHT / 2 - framing.dy) / scale)
        if min(box[:2]) < -1e-8 or box[2] > width + 1e-8 or box[3] > height + 1e-8:
            return None
        box = max(0, box[0]), max(0, box[1]), min(width, box[2]), min(height, box[3])
        return box, (0, 0, WIDTH, HEIGHT)
    scale = min(ratios) * framing.scale
    w, h = max(1, round(width * scale)), max(1, round(height * scale))
    x, y = (WIDTH - w) // 2 + framing.dx, (HEIGHT - h) // 2 + framing.dy
    if x < 0 or y < 0 or x + w > WIDTH or y + h > HEIGHT:
        return None
    return None, (x, y, x + w, y + h)


def prepare(image, crop=False, *, framing=Framing()):
    """Honor EXIF orientation and preserve aspect ratio on a black canvas."""
    source = ImageOps.exif_transpose(image).convert("RGBA")
    if crop and framing == Framing():
        source = ImageOps.fit(source, (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        x = y = 0
    else:
        layout = placement(source.size, crop, framing)
        if layout is None:
            raise ValueError("framing clips the fitted image or leaves a gap in the crop")
        box, (x, y, right, bottom) = layout
        source = source.resize((right - x, bottom - y), Image.Resampling.LANCZOS, box=box)
    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    canvas.paste(source, (x, y), source)
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
