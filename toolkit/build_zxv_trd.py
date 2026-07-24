#!/usr/bin/env python3
"""Build a ZX Spectrum 128 temporal-dither video demo and TR-DOS image.

The generated player alternates the normal (bank 5) and shadow (bank 7)
screens at the 50 Hz interrupt rate. Every logical source frame is converted
into two temporal phases A/B. The stream stores changed 8x8 cells relative to
the previous frame of the same phase.

The current resident-player profile intentionally keeps the compressed stream
between 0x6000 and 0xBFFF. It is suitable for short demos and for validating
the format before adding paged-RAM / disk streaming.
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH = 256
HEIGHT = 192
CELLS_X = 32
CELLS_Y = 24
CELL_COUNT = CELLS_X * CELLS_Y
SCREEN_BITMAP_BYTES = 6144
SCREEN_ATTR_BYTES = 768
SCREEN_BYTES = 6912
DEFAULT_ATTR = 0x78  # BRIGHT 1, PAPER white, INK black
LOAD_ADDRESS = 0x6000
MAX_RESIDENT_END = 0xC000
TRD_SIZE = 655360
SECTOR_SIZE = 256
SECTORS_PER_TRACK = 16
LOGICAL_TRACKS = 160
DATA_START_TRACK = 1

# Approximate Spectrum RGB values. Bright black remains black.
NORMAL_LEVEL = 205
BRIGHT_LEVEL = 255


def zx_rgb(index: int, bright: int) -> np.ndarray:
    level = BRIGHT_LEVEL if bright else NORMAL_LEVEL
    return np.array([
        level if index & 0x02 else 0,  # red
        level if index & 0x04 else 0,  # green
        level if index & 0x01 else 0,  # blue
    ], dtype=np.float64)


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    x = rgb / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


@dataclass(frozen=True)
class AttrCandidate:
    attr: int
    ink: np.ndarray
    paper: np.ndarray
    paper_is_white: bool


def build_attr_candidates() -> list[AttrCandidate]:
    candidates: list[AttrCandidate] = []
    # Main style: white paper, black or coloured ink.
    for ink_index in range(8):
        attr = 0x40 | (7 << 3) | ink_index
        candidates.append(AttrCandidate(attr, zx_rgb(ink_index, 1), zx_rgb(7, 1), True))
    # Secondary style: black ink on coloured paper. Penalized during selection.
    for paper_index in range(1, 7):
        attr = 0x40 | (paper_index << 3)
        candidates.append(AttrCandidate(attr, zx_rgb(0, 1), zx_rgb(paper_index, 1), False))
    return candidates


ATTR_CANDIDATES = build_attr_candidates()


def spectrum_bitmap_offset(x_byte: int, y: int) -> int:
    return ((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2) | x_byte


def bitmap_row0_offset(cell_index: int) -> int:
    x_cell = cell_index & 31
    y_cell = cell_index >> 5
    return ((y_cell & 0x18) << 8) | ((y_cell & 7) << 5) | x_cell


def cell_bytes(bitmap: bytes | bytearray, attrs: bytes | bytearray, cell_index: int) -> bytes:
    x_cell = cell_index & 31
    y_cell = cell_index >> 5
    rows = bytearray(8)
    for row in range(8):
        y = y_cell * 8 + row
        rows[row] = bitmap[spectrum_bitmap_offset(x_cell, y)]
    return bytes(rows) + bytes([attrs[cell_index]])


def set_cell_bytes(bitmap: bytearray, attrs: bytearray, cell_index: int, value: bytes) -> None:
    x_cell = cell_index & 31
    y_cell = cell_index >> 5
    for row in range(8):
        y = y_cell * 8 + row
        bitmap[spectrum_bitmap_offset(x_cell, y)] = value[row]
    attrs[cell_index] = value[8]


def choose_cell_phases(
    block_rgb: np.ndarray,
    global_x: int,
    global_y: int,
    previous_attr: int | None,
    paper_penalty: float,
    attr_change_penalty: float,
) -> tuple[np.ndarray, np.ndarray, int, float]:
    """Return two 8x8 bit planes and a shared Spectrum attribute.

    Candidate attributes are ranked with a fast vectorized three-level estimate.
    Floyd-Steinberg is then executed once for the winning attribute.
    """
    source_linear = srgb_to_linear(block_rgb.astype(np.float64))
    flat = source_linear.reshape(-1, 3)
    ranked: list[tuple[float, AttrCandidate, np.ndarray]] = []

    for candidate in ATTR_CANDIDATES:
        ink = srgb_to_linear(candidate.ink)
        paper = srgb_to_linear(candidate.paper)
        midpoint = (ink + paper) * 0.5
        levels = np.stack([paper, midpoint, ink], axis=0)
        distances = np.sum((flat[:, None, :] - levels[None, :, :]) ** 2, axis=2)
        states = np.argmin(distances, axis=1)
        score = float(np.sum(distances[np.arange(64), states]))
        if not candidate.paper_is_white:
            score += paper_penalty
        if previous_attr is not None and previous_attr != candidate.attr:
            score += attr_change_penalty
        ranked.append((score, candidate, levels))

    _, candidate, levels = min(ranked, key=lambda item: item[0])
    work = source_linear.copy()
    states = np.zeros((8, 8), dtype=np.uint8)
    error_sum = 0.0

    for y in range(8):
        for x in range(8):
            pixel = np.clip(work[y, x], 0.0, 1.0)
            distances = np.sum((levels - pixel) ** 2, axis=1)
            state = int(np.argmin(distances))
            states[y, x] = state
            quantized = levels[state]
            error = pixel - quantized
            error_sum += float(np.sum((source_linear[y, x] - quantized) ** 2))
            if x + 1 < 8:
                work[y, x + 1] += error * (7.0 / 16.0)
            if y + 1 < 8:
                if x > 0:
                    work[y + 1, x - 1] += error * (3.0 / 16.0)
                work[y + 1, x] += error * (5.0 / 16.0)
                if x + 1 < 8:
                    work[y + 1, x + 1] += error * (1.0 / 16.0)

    phase_a = states == 2
    phase_b = states == 2
    midpoint_mask = states == 1
    checker = np.fromfunction(
        lambda yy, xx: ((xx + global_x + yy + global_y) & 1) == 0,
        (8, 8), dtype=int,
    )
    phase_a = np.logical_or(phase_a, np.logical_and(midpoint_mask, checker))
    phase_b = np.logical_or(phase_b, np.logical_and(midpoint_mask, ~checker))
    return phase_a, phase_b, candidate.attr, error_sum


def convert_frame_to_phases(
    frame: np.ndarray,
    previous_attrs: np.ndarray | None,
    paper_penalty: float = 0.035,
    attr_change_penalty: float = 0.010,
) -> tuple[bytes, bytes, bytes, float]:
    if frame.shape != (HEIGHT, WIDTH, 3):
        raise ValueError(f"Expected {WIDTH}x{HEIGHT} RGB frame, got {frame.shape}")

    bitmap_a = bytearray(SCREEN_BITMAP_BYTES)
    bitmap_b = bytearray(SCREEN_BITMAP_BYTES)
    attrs = bytearray([DEFAULT_ATTR]) * SCREEN_ATTR_BYTES
    total_error = 0.0

    for cell_y in range(CELLS_Y):
        for cell_x in range(CELLS_X):
            index = cell_y * CELLS_X + cell_x
            block = frame[cell_y * 8:(cell_y + 1) * 8, cell_x * 8:(cell_x + 1) * 8]
            previous_attr = None if previous_attrs is None else int(previous_attrs[index])
            a_bits, b_bits, attr, error = choose_cell_phases(
                block,
                cell_x * 8,
                cell_y * 8,
                previous_attr,
                paper_penalty,
                attr_change_penalty,
            )
            attrs[index] = attr
            total_error += error

            for row in range(8):
                byte_a = 0
                byte_b = 0
                for bit in range(8):
                    if a_bits[row, bit]:
                        byte_a |= 0x80 >> bit
                    if b_bits[row, bit]:
                        byte_b |= 0x80 >> bit
                y = cell_y * 8 + row
                offset = spectrum_bitmap_offset(cell_x, y)
                bitmap_a[offset] = byte_a
                bitmap_b[offset] = byte_b

    return bytes(bitmap_a), bytes(bitmap_b), bytes(attrs), total_error


def render_spectrum_screen(bitmap: bytes, attrs: bytes) -> np.ndarray:
    output = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        cell_y = y >> 3
        for x_byte in range(32):
            value = bitmap[spectrum_bitmap_offset(x_byte, y)]
            attr = attrs[cell_y * 32 + x_byte]
            bright = (attr >> 6) & 1
            ink = zx_rgb(attr & 7, bright).astype(np.uint8)
            paper = zx_rgb((attr >> 3) & 7, bright).astype(np.uint8)
            for bit in range(8):
                output[y, x_byte * 8 + bit] = ink if value & (0x80 >> bit) else paper
    return output


def temporal_average(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    linear = (srgb_to_linear(a.astype(np.float64)) + srgb_to_linear(b.astype(np.float64))) * 0.5
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - 0.055)
    return np.clip(np.rint(srgb * 255.0), 0, 255).astype(np.uint8)


def make_demo_frames(frame_count: int) -> list[np.ndarray]:
    frames: list[np.ndarray] = []
    scale = 2
    font = ImageFont.load_default()

    for n in range(frame_count):
        t = n / frame_count
        image = Image.new("RGB", (WIDTH * scale, HEIGHT * scale), "white")
        draw = ImageDraw.Draw(image, "RGBA")

        # Pale static background grid: tests stable dither and attributes.
        for x in range(0, WIDTH * scale, 32 * scale):
            draw.line((x, 0, x, HEIGHT * scale), fill=(220, 225, 235, 120), width=1)
        for y in range(0, HEIGHT * scale, 24 * scale):
            draw.line((0, y, WIDTH * scale, y), fill=(220, 225, 235, 120), width=1)

        # Moving blue disc with a soft shadow.
        cx = int((36 + 172 * (0.5 + 0.5 * math.sin(2 * math.pi * t))) * scale)
        cy = int((52 + 22 * math.sin(4 * math.pi * t)) * scale)
        radius = 24 * scale
        draw.ellipse((cx - radius + 7, cy - radius + 9, cx + radius + 7, cy + radius + 9), fill=(40, 40, 40, 50))
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(40, 125, 235, 235), outline=(0, 45, 130, 255), width=3 * scale)

        # Red rectangle moving in the opposite direction.
        rx = int((184 - 120 * t) * scale)
        ry = int((115 + 20 * math.cos(2 * math.pi * t)) * scale)
        draw.rounded_rectangle((rx, ry, rx + 48 * scale, ry + 30 * scale), radius=6 * scale,
                               fill=(235, 70, 65, 220), outline=(125, 0, 0, 255), width=2 * scale)

        # Rotating green triangle.
        center = np.array([128.0, 104.0]) * scale
        angle = 2 * math.pi * t
        points = []
        for k in range(3):
            a = angle + k * 2 * math.pi / 3
            points.append(tuple(center + np.array([math.cos(a), math.sin(a)]) * 31 * scale))
        draw.polygon(points, fill=(70, 210, 95, 165), outline=(0, 100, 20, 255))

        # Grayscale ramp to demonstrate two-field temporal shading.
        ramp_x0 = 16 * scale
        ramp_y0 = 166 * scale
        for x in range(160 * scale):
            v = int(255 * x / (160 * scale - 1))
            draw.line((ramp_x0 + x, ramp_y0, ramp_x0 + x, ramp_y0 + 12 * scale), fill=(v, v, v, 255))

        draw.text((8 * scale, 7 * scale), "ZXV 50 Hz TEMPORAL DITHER", fill=(20, 20, 20, 255), font=font, stroke_width=0)
        draw.text((185 * scale, 171 * scale), f"{n:02d}", fill=(20, 20, 20, 255), font=font)

        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        frames.append(np.asarray(image, dtype=np.uint8))
    return frames


def read_video_frames(path: Path, frame_count: int, source_fps: float | None = None) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")
    native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    desired_fps = source_fps or 25.0
    frames: list[np.ndarray] = []
    next_time = 0.0
    duration_step = 1.0 / desired_fps
    while len(frames) < frame_count:
        cap.set(cv2.CAP_PROP_POS_MSEC, next_time * 1000.0)
        ok, bgr = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        scale = min(WIDTH / w, HEIGHT / h)
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))
        resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)
        canvas = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
        x0 = (WIDTH - nw) // 2
        y0 = (HEIGHT - nh) // 2
        canvas[y0:y0 + nh, x0:x0 + nw] = resized
        frames.append(canvas)
        next_time += duration_step
    cap.release()
    if not frames:
        raise RuntimeError("No frames decoded")
    return frames


def encode_phase(previous: tuple[bytes, bytes], current: tuple[bytes, bytes]) -> tuple[bytes, int]:
    previous_bitmap, previous_attrs = previous
    current_bitmap, current_attrs = current
    records = bytearray()
    changed = 0
    for cell_index in range(CELL_COUNT):
        old = cell_bytes(previous_bitmap, previous_attrs, cell_index)
        new = cell_bytes(current_bitmap, current_attrs, cell_index)
        rowmask = 0
        changed_rows = bytearray()
        for row in range(8):
            if old[row] != new[row]:
                rowmask |= 1 << row
                changed_rows.append(new[row])
        attr_changed = old[8] != new[8]
        if rowmask == 0 and not attr_changed:
            continue
        changed += 1
        bitmap_offset = bitmap_row0_offset(cell_index)
        records += struct.pack("<H", bitmap_offset)
        records.append(rowmask)
        records += changed_rows
        records.append(1 if attr_changed else 0)
        if attr_changed:
            records += struct.pack("<H", 0x1800 + cell_index)
            records.append(new[8])
    return struct.pack("<H", changed) + records, changed


class MiniAssembler:
    def __init__(self, origin: int):
        self.origin = origin
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.abs_fixups: list[tuple[int, str]] = []
        self.rel_fixups: list[tuple[int, str]] = []

    @property
    def pc(self) -> int:
        return self.origin + len(self.code)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"Duplicate label: {name}")
        self.labels[name] = self.pc

    def emit(self, *values: int) -> None:
        self.code.extend(v & 0xFF for v in values)

    def word(self, value: int) -> None:
        self.emit(value & 0xFF, value >> 8)

    def abs16(self, opcode: int | Sequence[int], label: str) -> None:
        if isinstance(opcode, int):
            self.emit(opcode)
        else:
            self.emit(*opcode)
        pos = len(self.code)
        self.emit(0, 0)
        self.abs_fixups.append((pos, label))

    def rel8(self, opcode: int, label: str) -> None:
        self.emit(opcode)
        pos = len(self.code)
        self.emit(0)
        self.rel_fixups.append((pos, label))

    def resolve(self, external_labels: dict[str, int] | None = None) -> bytes:
        labels = dict(self.labels)
        labels.update(external_labels or {})
        output = bytearray(self.code)
        for pos, label in self.abs_fixups:
            value = labels[label]
            output[pos] = value & 0xFF
            output[pos + 1] = value >> 8
        for pos, label in self.rel_fixups:
            operand_address = self.origin + pos
            next_address = operand_address + 1
            displacement = labels[label] - next_address
            if not -128 <= displacement <= 127:
                raise ValueError(f"Relative branch to {label} out of range: {displacement}")
            output[pos] = displacement & 0xFF
        return bytes(output)


def emit_ld_a_mem(asm: MiniAssembler, label: str) -> None:
    asm.abs16(0x3A, label)


def emit_ld_mem_a(asm: MiniAssembler, label: str) -> None:
    asm.abs16(0x32, label)


def emit_ld_hl_mem(asm: MiniAssembler, label: str) -> None:
    asm.abs16(0x2A, label)


def emit_ld_mem_hl(asm: MiniAssembler, label: str) -> None:
    asm.abs16(0x22, label)


def build_player_code(stream_start: int, loop_start: int) -> tuple[bytes, dict[str, int]]:
    a = MiniAssembler(LOAD_ADDRESS)
    a.label("start")
    a.emit(0xF3)                         # DI
    a.emit(0x31); a.word(0x5FF0)         # LD SP,5FF0
    a.emit(0xAF, 0xD3, 0xFE)             # XOR A / OUT (FE),A
    a.emit(0x3E, 0x07)                   # LD A,07: bank 7 mapped, screen 0
    a.emit(0x01); a.word(0x7FFD)         # LD BC,7FFD
    a.emit(0xED, 0x79)                   # OUT (C),A
    a.emit(0x3E, 0x40)
    a.abs16(0xCD, "clear_screen")
    a.emit(0x3E, 0xC0)
    a.abs16(0xCD, "clear_screen")
    a.emit(0x21); a.word(stream_start)   # LD HL,stream_start
    a.emit(0x3E, 0x40)
    a.abs16(0xCD, "decode_phase")        # initial A0
    a.emit(0x3E, 0xC0)
    a.abs16(0xCD, "decode_phase")        # initial B0
    emit_ld_mem_hl(a, "stream_ptr")
    a.emit(0xAF)
    emit_ld_mem_a(a, "screen_flag")
    a.emit(0x3E, 0x07)
    a.emit(0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79)
    a.emit(0xFB)                         # EI

    a.label("main_loop")
    a.emit(0x76, 0xF3)                   # HALT / DI
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xEE, 0x08)                   # XOR 8
    emit_ld_mem_a(a, "screen_flag")
    a.emit(0xF6, 0x07)                   # OR 7
    a.emit(0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79)

    # Select base of hidden screen.
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xB7)                         # OR A
    a.rel8(0x28, "hidden_bank7")        # JR Z
    a.emit(0x3E, 0x40)                   # visible bank7 -> hidden bank5
    a.rel8(0x18, "got_hidden_base")
    a.label("hidden_bank7")
    a.emit(0x3E, 0xC0)
    a.label("got_hidden_base")
    a.emit(0xF5)                         # PUSH AF
    emit_ld_hl_mem(a, "stream_ptr")

    # FFFF marks the end of the cyclic stream.
    a.emit(0x7E, 0xFE, 0xFF)             # LD A,(HL) / CP FF
    a.rel8(0x20, "not_end_marker")
    a.emit(0x23, 0x7E, 0x2B, 0xFE, 0xFF) # INC HL / LD A,(HL) / DEC HL / CP FF
    a.rel8(0x20, "not_end_marker")
    a.emit(0x21); a.word(loop_start)
    a.label("not_end_marker")
    a.emit(0xF1)                         # POP AF
    a.abs16(0xCD, "decode_phase")
    emit_ld_mem_hl(a, "stream_ptr")
    a.emit(0xFB)
    a.abs16(0xC3, "main_loop")

    # A = screen high byte (40 or C0)
    a.label("clear_screen")
    a.emit(0xF5)                         # PUSH AF
    a.emit(0x67, 0x2E, 0x00)             # LD H,A / LD L,0
    a.emit(0x54, 0x1E, 0x01)             # LD D,H / LD E,1
    a.emit(0xAF, 0x77)                   # XOR A / LD (HL),A
    a.emit(0x01); a.word(6143)
    a.emit(0xED, 0xB0)                   # LDIR bitmap
    a.emit(0xF1, 0xC6, 0x18)             # POP AF / ADD A,18
    a.emit(0x67, 0x2E, 0x00)
    a.emit(0x54, 0x1E, 0x01)
    a.emit(0x3E, DEFAULT_ATTR, 0x77)
    a.emit(0x01); a.word(767)
    a.emit(0xED, 0xB0)
    a.emit(0xC9)

    # A=base high byte, HL=stream pointer; returns updated HL.
    a.label("decode_phase")
    emit_ld_mem_a(a, "base_hi")
    a.emit(0x4E, 0x23, 0x46, 0x23)       # LD C,(HL); INC HL; LD B,(HL); INC HL
    a.label("decode_loop")
    a.emit(0x78, 0xB1)                   # LD A,B / OR C
    a.emit(0xC8)                         # RET Z
    a.emit(0xC5)                         # PUSH BC (phase record count)
    a.emit(0x5E, 0x23, 0x56, 0x23)       # bitmap offset -> DE
    emit_ld_a_mem(a, "base_hi")
    a.emit(0x82, 0x57)                   # ADD A,D / LD D,A
    a.emit(0x4E, 0x23)                   # LD C,(HL) row mask / INC HL
    a.emit(0x06, 0x08)                   # LD B,8
    a.label("decode_rows")
    a.emit(0xCB, 0x39)                   # SRL C, row bit -> carry
    a.rel8(0x30, "decode_row_skip")      # JR NC
    a.emit(0x7E, 0x23, 0x12)             # copy changed row byte
    a.label("decode_row_skip")
    a.emit(0x14)                         # INC D
    a.rel8(0x10, "decode_rows")          # DJNZ
    a.emit(0x7E, 0x23, 0xB7)             # attr flag / INC HL / OR A
    a.rel8(0x28, "decode_no_attr")       # JR Z
    a.emit(0x5E, 0x23, 0x56, 0x23)       # attribute offset -> DE
    emit_ld_a_mem(a, "base_hi")
    a.emit(0x82, 0x57)
    a.emit(0x7E, 0x23, 0x12)             # copy attribute
    a.label("decode_no_attr")
    a.emit(0xC1, 0x0B)                   # POP BC / DEC BC
    a.rel8(0x18, "decode_loop")

    a.label("stream_ptr")
    a.emit(0, 0)
    a.label("screen_flag")
    a.emit(0)
    a.label("base_hi")
    a.emit(0)

    code = a.resolve()
    return code, a.labels


def build_assembly_source(stream_start: int, loop_start: int, code_size: int) -> str:
    return f"""; ZXV temporal-dither player for ZX Spectrum 128 / TR-DOS
; Generated reference source. The Python builder emits identical machine code.
; Resident profile: code + compressed stream occupy 6000h..BFFFh.

        ORG     6000h
PORT7FFD EQU     7FFDh
DEFAULT_ATTR EQU 78h
STREAM_START EQU {stream_start:04X}h
LOOP_START   EQU {loop_start:04X}h

start:  DI
        LD      SP,5FF0h
        XOR     A
        OUT     (0FEh),A
        LD      A,07h
        LD      BC,PORT7FFD
        OUT     (C),A
        LD      A,40h
        CALL    clear_screen
        LD      A,0C0h
        CALL    clear_screen
        LD      HL,STREAM_START
        LD      A,40h
        CALL    decode_phase
        LD      A,0C0h
        CALL    decode_phase
        LD      (stream_ptr),HL
        XOR     A
        LD      (screen_flag),A
        LD      A,07h
        LD      BC,PORT7FFD
        OUT     (C),A
        EI

main_loop:
        HALT
        DI
        LD      A,(screen_flag)
        XOR     08h
        LD      (screen_flag),A
        OR      07h
        LD      BC,PORT7FFD
        OUT     (C),A
        LD      A,(screen_flag)
        OR      A
        JR      Z,hidden_bank7
        LD      A,40h
        JR      got_hidden_base
hidden_bank7:
        LD      A,0C0h
got_hidden_base:
        PUSH    AF
        LD      HL,(stream_ptr)
        LD      A,(HL)
        CP      0FFh
        JR      NZ,not_end_marker
        INC     HL
        LD      A,(HL)
        DEC     HL
        CP      0FFh
        JR      NZ,not_end_marker
        LD      HL,LOOP_START
not_end_marker:
        POP     AF
        CALL    decode_phase
        LD      (stream_ptr),HL
        EI
        JP      main_loop

; A=40h or C0h
clear_screen:
        PUSH    AF
        LD      H,A
        LD      L,0
        LD      D,H
        LD      E,1
        XOR     A
        LD      (HL),A
        LD      BC,6143
        LDIR
        POP     AF
        ADD     A,18h
        LD      H,A
        LD      L,0
        LD      D,H
        LD      E,1
        LD      A,DEFAULT_ATTR
        LD      (HL),A
        LD      BC,767
        LDIR
        RET

; A=base high byte, HL=phase record. Returns HL at next phase.
decode_phase:
        LD      (base_hi),A
        LD      C,(HL)
        INC     HL
        LD      B,(HL)
        INC     HL
decode_loop:
        LD      A,B
        OR      C
        RET     Z
        PUSH    BC
        LD      E,(HL)
        INC     HL
        LD      D,(HL)
        INC     HL
        LD      A,(base_hi)
        ADD     A,D
        LD      D,A
        LD      C,(HL)
        INC     HL
        LD      B,8
decode_rows:
        SRL     C
        JR      NC,decode_row_skip
        LD      A,(HL)
        INC     HL
        LD      (DE),A
decode_row_skip:
        INC     D
        DJNZ    decode_rows
        LD      A,(HL)
        INC     HL
        OR      A
        JR      Z,decode_no_attr
        LD      E,(HL)
        INC     HL
        LD      D,(HL)
        INC     HL
        LD      A,(base_hi)
        ADD     A,D
        LD      D,A
        LD      A,(HL)
        INC     HL
        LD      (DE),A
decode_no_attr:
        POP     BC
        DEC     BC
        JR      decode_loop

stream_ptr:  DW 0
screen_flag: DB 0
base_hi:     DB 0

; Machine-code size before stream: {code_size} bytes
"""


def basic_line(line_number: int, content: bytes) -> bytes:
    body = content + b"\x0D"
    return struct.pack(">H", line_number) + struct.pack("<H", len(body)) + body


def build_boot_basic() -> bytes:
    TOK = {
        "CODE": 0xAF,
        "VAL": 0xB0,
        "USR": 0xC0,
        "REM": 0xEA,
        "LOAD": 0xEF,
        "RANDOMIZE": 0xF9,
        "CLEAR": 0xFD,
    }
    lines = []
    lines.append(basic_line(10, bytes([TOK["CLEAR"], 0x20, TOK["VAL"]]) + b' "24575"'))
    lines.append(basic_line(
        20,
        bytes([TOK["RANDOMIZE"], 0x20, TOK["USR"], 0x20, TOK["VAL"]]) +
        b' "15619":' + bytes([TOK["REM"]]) + b':' + bytes([TOK["LOAD"]]) + b' "PLAYER" ' + bytes([TOK["CODE"]]),
    ))
    lines.append(basic_line(
        30,
        bytes([TOK["RANDOMIZE"], 0x20, TOK["USR"], 0x20, TOK["VAL"]]) + b' "24576"',
    ))
    return b"".join(lines)


@dataclass
class TrdFile:
    name: str
    file_type: str
    data: bytes
    start: int = 0
    basic_variables_offset: int | None = None
    autostart_line: int | None = None


def logical_sector_offset(track: int, sector: int) -> int:
    return (track * SECTORS_PER_TRACK + sector) * SECTOR_SIZE


def add_trd_file(
    image: bytearray,
    directory_index: int,
    file: TrdFile,
    start_track: int,
    start_sector: int,
) -> tuple[int, int, int]:
    if len(file.name.encode("ascii")) > 8:
        raise ValueError("TR-DOS filename too long")
    stored = file.data
    directory_length = len(file.data)
    if file.file_type == "B":
        if file.autostart_line is None:
            autostart = 0x8000
        else:
            autostart = file.autostart_line
        stored = file.data + bytes([0x80, 0xAA]) + struct.pack("<H", autostart)
    sectors = math.ceil(len(stored) / SECTOR_SIZE)
    if sectors > 255:
        raise ValueError(f"TR-DOS file {file.name} exceeds 255 sectors")

    absolute_sector = start_track * SECTORS_PER_TRACK + start_sector
    data_offset = absolute_sector * SECTOR_SIZE
    padded = stored + bytes(sectors * SECTOR_SIZE - len(stored))
    image[data_offset:data_offset + len(padded)] = padded

    entry = bytearray(16)
    entry[0:8] = file.name.encode("ascii").ljust(8, b" ")
    entry[8] = ord(file.file_type)
    if file.file_type == "B":
        entry[9:11] = struct.pack("<H", directory_length)
        variables = file.basic_variables_offset if file.basic_variables_offset is not None else directory_length
        entry[11:13] = struct.pack("<H", variables)
    else:
        entry[9:11] = struct.pack("<H", file.start)
        entry[11:13] = struct.pack("<H", directory_length)
    entry[13] = sectors
    entry[14] = start_sector
    entry[15] = start_track
    image[directory_index * 16:(directory_index + 1) * 16] = entry

    next_absolute = absolute_sector + sectors
    return next_absolute // SECTORS_PER_TRACK, next_absolute % SECTORS_PER_TRACK, sectors


def build_trd(boot: bytes, player: bytes, label: str = "ZXV DEMO") -> tuple[bytes, dict[str, int]]:
    image = bytearray(TRD_SIZE)
    track, sector = DATA_START_TRACK, 0
    used = 0
    files = [
        TrdFile("boot", "B", boot, basic_variables_offset=len(boot), autostart_line=10),
        TrdFile("PLAYER", "C", player, start=LOAD_ADDRESS),
    ]
    for index, file in enumerate(files):
        track, sector, sectors = add_trd_file(image, index, file, track, sector)
        used += sectors

    info = 8 * SECTOR_SIZE
    image[info] = 0
    image[info + 225] = sector
    image[info + 226] = track
    image[info + 227] = 0x16  # 80 tracks, double side
    image[info + 228] = len(files)
    free_sectors = (LOGICAL_TRACKS - 1) * SECTORS_PER_TRACK - used
    image[info + 229:info + 231] = struct.pack("<H", free_sectors)
    image[info + 231] = 0x10
    image[info + 233:info + 242] = b" " * 9
    image[info + 245:info + 253] = label.encode("ascii", "replace")[:8].ljust(8, b" ")
    return bytes(image), {"used_sectors": used, "free_sectors": free_sectors, "first_free_track": track, "first_free_sector": sector}


def parse_trd_directory(image: bytes) -> list[dict[str, int | str]]:
    result = []
    for index in range(128):
        entry = image[index * 16:(index + 1) * 16]
        if entry[0] == 0:
            break
        if entry[0] == 1:
            continue
        result.append({
            "name": entry[0:8].decode("ascii").rstrip(),
            "type": chr(entry[8]),
            "field1": struct.unpack_from("<H", entry, 9)[0],
            "length": struct.unpack_from("<H", entry, 11)[0],
            "sectors": entry[13],
            "sector": entry[14],
            "track": entry[15],
        })
    return result


def decode_stream_python(
    stream: bytes,
    initial_a: tuple[bytearray, bytearray],
    initial_b: tuple[bytearray, bytearray],
    phase_count: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Reference decoder for structural validation of the generated stream."""
    offset = 0
    state_a = (bytearray(initial_a[0]), bytearray(initial_a[1]))
    state_b = (bytearray(initial_b[0]), bytearray(initial_b[1]))
    outputs: list[tuple[np.ndarray, np.ndarray]] = []

    def apply(state: tuple[bytearray, bytearray]) -> None:
        nonlocal offset
        count = struct.unpack_from("<H", stream, offset)[0]
        offset += 2
        for _ in range(count):
            bitmap_offset = struct.unpack_from("<H", stream, offset)[0]
            offset += 2
            rowmask = stream[offset]
            offset += 1
            x_cell = bitmap_offset & 31
            y_cell = ((bitmap_offset >> 8) & 0x18) | ((bitmap_offset >> 5) & 0x07)
            index = y_cell * 32 + x_cell
            current = bytearray(cell_bytes(state[0], state[1], index))
            for row in range(8):
                if rowmask & (1 << row):
                    current[row] = stream[offset]
                    offset += 1
            attr_changed = stream[offset]
            offset += 1
            if attr_changed:
                attr_offset = struct.unpack_from("<H", stream, offset)[0]
                offset += 2
                assert attr_offset == 0x1800 + index
                current[8] = stream[offset]
                offset += 1
            set_cell_bytes(state[0], state[1], index, bytes(current))

    apply(state_a)
    apply(state_b)
    outputs.append((render_spectrum_screen(*state_a), render_spectrum_screen(*state_b)))
    # Cyclic section starts after two startup phases.
    for phase_index in range(phase_count):
        apply(state_a if phase_index % 2 == 0 else state_b)
        if phase_index % 2 == 1:
            outputs.append((render_spectrum_screen(*state_a), render_spectrum_screen(*state_b)))
    marker = struct.unpack_from("<H", stream, offset)[0]
    assert marker == 0xFFFF
    return outputs


def write_preview_video(path: Path, phases: Sequence[tuple[np.ndarray, np.ndarray]], fps: int = 50) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError("Could not create preview MP4")
    for a, b in phases:
        writer.write(cv2.cvtColor(a, cv2.COLOR_RGB2BGR))
        writer.write(cv2.cvtColor(b, cv2.COLOR_RGB2BGR))
    writer.release()


def write_contact_sheet(path: Path, source: Sequence[np.ndarray], phases: Sequence[tuple[np.ndarray, np.ndarray]]) -> None:
    indices = np.linspace(0, min(len(source), len(phases)) - 1, 6, dtype=int)
    sheet = Image.new("RGB", (WIDTH * 3, HEIGHT * len(indices)), "white")
    draw = ImageDraw.Draw(sheet)
    for row, index in enumerate(indices):
        avg = temporal_average(phases[index][0], phases[index][1])
        sheet.paste(Image.fromarray(source[index]), (0, row * HEIGHT))
        sheet.paste(Image.fromarray(avg), (WIDTH, row * HEIGHT))
        combined = np.concatenate([phases[index][0][:, :WIDTH // 2], phases[index][1][:, WIDTH // 2:]], axis=1)
        sheet.paste(Image.fromarray(combined), (WIDTH * 2, row * HEIGHT))
        draw.text((4, row * HEIGHT + 4), f"source {index}", fill="black")
        draw.text((WIDTH + 4, row * HEIGHT + 4), "temporal average", fill="black")
        draw.text((WIDTH * 2 + 4, row * HEIGHT + 4), "A | B", fill="black")
    sheet.save(path)


def build_project(args: argparse.Namespace) -> dict[str, object]:
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    if args.input_video:
        source_frames = read_video_frames(args.input_video, args.frames, args.logical_fps)
    else:
        source_frames = make_demo_frames(args.frames)

    phase_screens: list[tuple[bytes, bytes, bytes]] = []
    previous_attrs: np.ndarray | None = None
    errors: list[float] = []
    for index, frame in enumerate(source_frames):
        bitmap_a, bitmap_b, attrs, error = convert_frame_to_phases(frame, previous_attrs)
        phase_screens.append((bitmap_a, bitmap_b, attrs))
        previous_attrs = np.frombuffer(attrs, dtype=np.uint8).copy()
        errors.append(error)
        print(f"converted {index + 1}/{len(source_frames)}", file=sys.stderr)

    blank = (bytes(SCREEN_BITMAP_BYTES), bytes([DEFAULT_ATTR]) * SCREEN_ATTR_BYTES)
    initial_a = (phase_screens[0][0], phase_screens[0][2])
    initial_b = (phase_screens[0][1], phase_screens[0][2])
    stream = bytearray()
    changed_counts: list[int] = []
    payload, changed = encode_phase(blank, initial_a)
    stream += payload; changed_counts.append(changed)
    payload, changed = encode_phase(blank, initial_b)
    stream += payload; changed_counts.append(changed)
    startup_size = len(stream)

    # Loop stream. A logical source frame can be held for several A/B pairs
    # while the physical A/B alternation continues at 50 Hz.
    runtime_indices = [0]
    for target_index in list(range(1, len(phase_screens))) + [0]:
        previous_index = (target_index - 1) % len(phase_screens)
        previous_a = (phase_screens[previous_index][0], phase_screens[previous_index][2])
        previous_b = (phase_screens[previous_index][1], phase_screens[previous_index][2])
        for _ in range(args.hold_pairs - 1):
            payload, changed = encode_phase(previous_a, previous_a)
            stream += payload; changed_counts.append(changed)
            payload, changed = encode_phase(previous_b, previous_b)
            stream += payload; changed_counts.append(changed)
            runtime_indices.append(previous_index)
        for phase in (0, 1):
            previous = (phase_screens[previous_index][phase], phase_screens[previous_index][2])
            current = (phase_screens[target_index][phase], phase_screens[target_index][2])
            payload, changed = encode_phase(previous, current)
            stream += payload
            changed_counts.append(changed)
        runtime_indices.append(target_index)
    stream += b"\xFF\xFF"

    # First pass determines player length; second pass patches stream addresses.
    placeholder_code, _ = build_player_code(0, 0)
    stream_start = LOAD_ADDRESS + len(placeholder_code)
    loop_start = stream_start + startup_size
    player_code, labels = build_player_code(stream_start, loop_start)
    if len(player_code) != len(placeholder_code):
        raise AssertionError("Player code size changed during address patching")
    player = player_code + stream
    end_address = LOAD_ADDRESS + len(player)
    if end_address > MAX_RESIDENT_END:
        raise RuntimeError(
            f"Resident stream is too large: {len(player)} bytes, ends at {end_address:04X}h. "
            f"Reduce --frames or use the future paged/disk streaming profile."
        )

    boot = build_boot_basic()
    trd, disk_stats = build_trd(boot, player)
    directory = parse_trd_directory(trd)

    # Reference stream decode checks every patch and the cyclic end marker.
    decoded_phases = decode_stream_python(
        bytes(stream),
        (bytearray(SCREEN_BITMAP_BYTES), bytearray([DEFAULT_ATTR]) * SCREEN_ATTR_BYTES),
        (bytearray(SCREEN_BITMAP_BYTES), bytearray([DEFAULT_ATTR]) * SCREEN_ATTR_BYTES),
        len(source_frames) * 2 * args.hold_pairs,
    )
    # The final pair returns to frame zero and duplicates the initial loop state.
    decoded_phases = decoded_phases[:-1]
    runtime_indices = runtime_indices[:-1]
    if len(decoded_phases) != len(runtime_indices):
        raise AssertionError("Reference decoder produced wrong runtime frame count")

    # Verify every held and changed phase against its source logical frame.
    for runtime_index, ((rendered_a, rendered_b), source_index) in enumerate(zip(decoded_phases, runtime_indices)):
        expected_a = render_spectrum_screen(phase_screens[source_index][0], phase_screens[source_index][2])
        expected_b = render_spectrum_screen(phase_screens[source_index][1], phase_screens[source_index][2])
        if not np.array_equal(rendered_a, expected_a) or not np.array_equal(rendered_b, expected_b):
            raise AssertionError(f"Decoded phase mismatch at runtime pair {runtime_index}")

    trd_path = out / "zxv_demo_128.trd"
    player_path = out / "PLAYER.C.bin"
    stream_path = out / "video_stream.bin"
    asm_path = out / "player.asm"
    preview_path = out / "zxv_demo_50hz_preview.mp4"
    average_path = out / "zxv_demo_temporal_average.mp4"
    contact_path = out / "zxv_contact_sheet.png"

    trd_path.write_bytes(trd)
    player_path.write_bytes(player)
    stream_path.write_bytes(stream)
    asm_path.write_text(build_assembly_source(stream_start, loop_start, len(player_code)), encoding="utf-8")
    write_preview_video(preview_path, decoded_phases, 50)

    average_writer = cv2.VideoWriter(
        str(average_path), cv2.VideoWriter_fourcc(*"mp4v"), args.logical_fps, (WIDTH, HEIGHT)
    )
    if not average_writer.isOpened():
        raise RuntimeError("Could not create temporal-average preview")
    mse_sum = 0.0
    runtime_sources = [source_frames[index] for index in runtime_indices]
    for source, (phase_a, phase_b) in zip(runtime_sources, decoded_phases):
        average = temporal_average(phase_a, phase_b)
        mse_sum += float(np.mean((source.astype(np.float64) - average.astype(np.float64)) ** 2))
        average_writer.write(cv2.cvtColor(average, cv2.COLOR_RGB2BGR))
    average_writer.release()
    write_contact_sheet(contact_path, runtime_sources, decoded_phases)

    mse = mse_sum / len(runtime_sources)
    psnr = float("inf") if mse == 0 else 10.0 * math.log10(255.0 * 255.0 / mse)
    report = f"""# ZXV temporal-dither demo for ZX Spectrum 128

## Built prototype

- ZX Spectrum 128, 256×192.
- Normal screen in RAM bank 5 and shadow screen in bank 7.
- The two screens alternate on every 50 Hz interrupt.
- One logical frame consists of temporal phases A and B.
- Attributes are identical in both phases to avoid colour flicker.
- A three-level block-local Floyd–Steinberg quantizer chooses PAPER/PAPER,
  INK/PAPER, or INK/INK per source pixel.
- The resident stream stores changed 8×8 cells against the previous frame of
  the same phase.

## Demo statistics

- Unique source frames in loop: {len(source_frames)}
- A/B pairs per source frame: {args.hold_pairs}
- Source animation update rate: {args.logical_fps / args.hold_pairs:.2f} fps
- A/B pair rate: {args.logical_fps} fps
- Physical phase rate: 50 Hz
- Loop duration: {len(runtime_indices) / args.logical_fps:.2f} seconds
- Player code: {len(player_code)} bytes
- Compressed stream: {len(stream)} bytes
- Complete CODE file: {len(player)} bytes
- Load range: {LOAD_ADDRESS:04X}h–{end_address - 1:04X}h
- Mean changed cells per phase: {np.mean(changed_counts):.1f} of 768
- Maximum changed cells in one phase: {max(changed_counts)}
- Temporal-average RGB PSNR: {psnr:.2f} dB
- TRD size: {len(trd)} bytes
- Used TR-DOS sectors: {disk_stats['used_sectors']}

## TRD directory

{chr(10).join(f"- {entry['name']}.{entry['type']}: {entry['length']} bytes, track {entry['track']}, sector {entry['sector']}" for entry in directory)}

## Running

Mount `zxv_demo_128.trd` as drive A in a Spectrum 128/Pentagon emulator with
TR-DOS/Beta Disk support. Boot TR-DOS and run the `boot` BASIC file. Many
emulators automatically run a file named `boot`; otherwise enter `RUN` or load
it through the emulator's TR-DOS browser.

The demo loops continuously. It writes only to the hidden screen and switches
screens immediately after the frame interrupt.

## Current limitation

This first working profile is resident: player and video stream must fit below
C000h, because bank 7 is mapped at C000h as the shadow screen. The encoder
therefore targets short loops. The next profile should place compressed chunks
in banks 0/1/3/4/6 and use a double sector buffer for long TRD video. Direct
floppy streaming at 25 logical fps needs careful handling of rotational latency;
TRD on an emulator or SD-based Beta Disk is much less restrictive.
"""
    (out / "README.md").write_text(report, encoding="utf-8")

    return {
        "trd": trd_path,
        "player": player_path,
        "stream": stream_path,
        "asm": asm_path,
        "preview": preview_path,
        "average": average_path,
        "contact": contact_path,
        "report": out / "README.md",
        "player_code_bytes": len(player_code),
        "stream_bytes": len(stream),
        "total_bytes": len(player),
        "end_address": end_address,
        "psnr": psnr,
        "mean_changed": float(np.mean(changed_counts)),
        "max_changed": max(changed_counts),
        "directory": directory,
    }


def make_zip(output_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output_dir.parent))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("zxv_build"))
    parser.add_argument("--input-video", type=Path)
    parser.add_argument("--frames", type=int, default=10)
    parser.add_argument("--logical-fps", type=int, default=25)
    parser.add_argument("--hold-pairs", type=int, default=4, help="A/B pairs shown per unique source frame")
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args()
    if args.frames < 2:
        parser.error("--frames must be at least 2")
    if args.hold_pairs < 1:
        parser.error("--hold-pairs must be at least 1")
    result = build_project(args)
    if args.zip:
        make_zip(args.output, args.zip)
    print("TRD:", result["trd"])
    print("Player bytes:", result["total_bytes"])
    print("Stream bytes:", result["stream_bytes"])
    print("PSNR:", f"{result['psnr']:.2f} dB")


if __name__ == "__main__":
    main()
