#!/usr/bin/env python3
"""Build long 2-bit brightness video with player-side native dithering.

The profile is deliberately different from the temporal-dither demo:

* the stream stores 128x96 logical pixels with four brightness levels;
* the player expands every level to a real 2x2 pattern on the 256x192 screen;
* one attribute describes each real 8x8 Spectrum character cell;
* frames are XOR-delta encoded with zero/repeat/literal RLE;
* bank 5 and bank 7 are used as ordinary frame buffers and are flipped only
  when a complete logical frame is ready;
* the visible frame stays on screen while the next packet is read a sector at
  a time through the stable TR-DOS entry point 3D13h.

This makes two-minute clips practical in a 640 KiB TRD without the 50 Hz A/B
temporal flicker used by the original experiment.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import sys
import wave
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import BinaryIO

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_streaming_trd as streaming  # noqa: E402
import build_zxv_trd as base  # noqa: E402


LOAD_ADDRESS = 0x6000
BUFFER = 0x8000
BUFFER_BYTES = 0x2000
STATE_ADDRESS = BUFFER + BUFFER_BYTES
LOGICAL_WIDTH = 128
LOGICAL_HEIGHT = 96
ACTIVE_Y0 = 12
ACTIVE_HEIGHT = 72
ANALYSIS_WIDTH = 256
ANALYSIS_HEIGHT = 144
ATTR_COLS = base.CELLS_X
ATTR_ROWS = base.CELLS_Y
ATTR_SOURCE_WIDTH = LOGICAL_WIDTH // ATTR_COLS
ATTR_SOURCE_HEIGHT = LOGICAL_HEIGHT // ATTR_ROWS
STATE_LEVEL_BYTES = LOGICAL_WIDTH * LOGICAL_HEIGHT * 2 // 8
STATE_ATTR_BYTES = ATTR_COLS * ATTR_ROWS
STATE_BITMAP_BYTES = STATE_LEVEL_BYTES
STATE_BYTES = STATE_BITMAP_BYTES + STATE_ATTR_BYTES
PACKET_HEADER_BYTES = 8
VIDEO_MAGIC = b"ZXVL"
VIDEO_VERSION = 4
AY_CLOCK_HZ = 1_773_400
AY_STATE_BYTES = 9
PAGING_ROM48_BANK7 = 0x17
MAX_PACKET_SECTORS = BUFFER_BYTES // base.SECTOR_SIZE
MAX_TRDOS_FILE_SECTORS = 255
TRD_DATA_SECTORS = (
    (base.LOGICAL_TRACKS - 1) * base.SECTORS_PER_TRACK
)


@dataclass
class Packet:
    payload: bytes
    raw: bool
    sectors: int
    ay_state: bytes

    def serialize(self) -> bytes:
        result = bytearray(PACKET_HEADER_BYTES)
        result[0] = self.sectors
        result[1] = 1 if self.raw else 0
        struct.pack_into("<H", result, 2, len(self.payload))
        result[4] = AY_STATE_BYTES
        struct.pack_into(
            "<H", result, 6, (sum(self.ay_state) + sum(self.payload)) & 0xFFFF
        )
        result += self.ay_state
        result += self.payload
        expected = self.sectors * base.SECTOR_SIZE
        if len(result) > expected:
            raise ValueError("packet exceeds its sector allocation")
        result += bytes(expected - len(result))
        return bytes(result)


@dataclass(frozen=True)
class ToneRange:
    black_point: float
    white_point: float
    centers: tuple[float, float, float, float]
    thresholds: tuple[float, float, float]
    black_percentile: float = 3.0
    white_percentile: float = 97.0


@dataclass(frozen=True)
class AyFrame:
    periods: tuple[int, int, int]
    volumes: tuple[int, int, int]

    def serialize(self) -> bytes:
        result = bytearray()
        for period in self.periods:
            result += bytes((period & 0xFF, (period >> 8) & 0x0F))
        result += bytes(self.volumes)
        if len(result) != AY_STATE_BYTES:
            raise AssertionError("invalid AY state size")
        return bytes(result)


@dataclass(frozen=True)
class ReframeWindow:
    center_x: float
    center_y: float
    zoom: float


def colour_candidates() -> list[tuple[int, np.ndarray, np.ndarray]]:
    result: list[tuple[int, np.ndarray, np.ndarray]] = []
    # Try every legal Spectrum INK/PAPER combination at both intensity levels.
    # The attribute grid and player cost stay unchanged; only the offline search
    # becomes richer. Keeping both orientations also favours temporal stability
    # when a previous cell already uses one of them.
    for bright in range(2):
        for paper in range(8):
            for ink in range(8):
                if ink == paper:
                    continue
                attr = (bright << 6) | (paper << 3) | ink
                result.append(
                    (
                        attr,
                        base.zx_rgb(ink, bright),
                        base.zx_rgb(paper, bright),
                    )
                )
    return result


COLOUR_CANDIDATES = colour_candidates()
COLOUR_ATTRS = np.array(
    [candidate[0] for candidate in COLOUR_CANDIDATES], dtype=np.uint8
)
COLOUR_INKS = np.stack(
    [candidate[1] for candidate in COLOUR_CANDIDATES]
).astype(np.float64)
COLOUR_PAPERS = np.stack(
    [candidate[2] for candidate in COLOUR_CANDIDATES]
).astype(np.float64)

BAYER_4X4 = (
    np.array(
        [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ],
        dtype=np.float64,
    )
    + 0.5
) / 16.0

BAYER_8X8 = (
    np.array(
        [
            [0, 48, 12, 60, 3, 51, 15, 63],
            [32, 16, 44, 28, 35, 19, 47, 31],
            [8, 56, 4, 52, 11, 59, 7, 55],
            [40, 24, 36, 20, 43, 27, 39, 23],
            [2, 50, 14, 62, 1, 49, 13, 61],
            [34, 18, 46, 30, 33, 17, 45, 29],
            [10, 58, 6, 54, 9, 57, 5, 53],
            [42, 26, 38, 22, 41, 25, 37, 21],
        ],
        dtype=np.float64,
    )
    + 0.5
) / 64.0


def encode_compact_frame(
    image: np.ndarray,
    previous_attrs: np.ndarray | None,
    attr_change_penalty: int,
    dither: str,
) -> tuple[bytes, np.ndarray]:
    """Convert one 128x96 image to packed two-bit brightness levels."""
    if image.shape != (LOGICAL_HEIGHT, LOGICAL_WIDTH, 3):
        raise ValueError(f"unexpected compact frame shape {image.shape}")
    work = image.astype(np.float64)
    levels = np.empty((LOGICAL_HEIGHT, LOGICAL_WIDTH), dtype=np.uint8)
    attrs = np.empty(STATE_ATTR_BYTES, dtype=np.uint8)
    coverages = (
        np.array([0.0, 0.25, 0.5, 1.0], dtype=np.float64)
        if dither != "none"
        else np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float64)
    )
    directions = COLOUR_INKS - COLOUR_PAPERS
    palettes = (
        COLOUR_PAPERS[:, None, :]
        + coverages[None, :, None] * directions[:, None, :]
    )
    cell = 0
    for by in range(ATTR_ROWS):
        for bx in range(ATTR_COLS):
            block = work[
                by * ATTR_SOURCE_HEIGHT:(by + 1) * ATTR_SOURCE_HEIGHT,
                bx * ATTR_SOURCE_WIDTH:(bx + 1) * ATTR_SOURCE_WIDTH,
            ]
            flat = block.reshape(-1, 3)
            distances = np.sum(
                (flat[:, None, None, :] - palettes[None, :, :, :]) ** 2,
                axis=3,
            )
            candidate_levels = np.argmin(distances, axis=2).astype(np.uint8)
            scores = np.min(distances, axis=2).sum(axis=0)
            if previous_attrs is not None:
                scores += (
                    COLOUR_ATTRS != int(previous_attrs[cell])
                ) * attr_change_penalty
            best_index = int(np.argmin(scores))
            best_attr = int(COLOUR_ATTRS[best_index])
            best_levels = candidate_levels[:, best_index].reshape(
                ATTR_SOURCE_HEIGHT, ATTR_SOURCE_WIDTH
            )
            attrs[cell] = best_attr
            levels[
                by * ATTR_SOURCE_HEIGHT:(by + 1) * ATTR_SOURCE_HEIGHT,
                bx * ATTR_SOURCE_WIDTH:(bx + 1) * ATTR_SOURCE_WIDTH,
            ] = best_levels
            cell += 1

    packed = (
        (levels[:, 0::4] << 6)
        | (levels[:, 1::4] << 4)
        | (levels[:, 2::4] << 2)
        | levels[:, 3::4]
    )
    return packed.tobytes() + attrs.tobytes(), attrs


def encode_zero_literal_rle(data: bytes) -> bytes:
    """Pack zero runs, repeated bytes, and literal runs.

    Token 00xxxxxx skips (token&63)+1 zero bytes. Token 01xxxxxx repeats the
    following byte (token&63)+1 times. Token 1xxxxxxx is followed by
    (token&127)+1 literal bytes. Literal runs may contain isolated zeroes.
    """
    result = bytearray()
    pos = 0

    def repeated_length(offset: int) -> int:
        length = 1
        while (
            offset + length < len(data)
            and data[offset + length] == data[offset]
            and length < 64
        ):
            length += 1
        return length

    while pos < len(data):
        repeated = repeated_length(pos)
        if data[pos] == 0 and repeated >= 2:
            result.append(repeated - 1)
            pos += repeated
            continue
        if data[pos] != 0 and repeated >= 3:
            result += bytes((0x40 | (repeated - 1), data[pos]))
            pos += repeated
            continue

        start = pos
        pos += 1
        while pos < len(data) and pos - start < 128:
            repeated = repeated_length(pos)
            if (
                (data[pos] == 0 and repeated >= 2)
                or (data[pos] != 0 and repeated >= 3)
            ):
                break
            pos += 1
        result.append(0x80 | (pos - start - 1))
        result += data[start:pos]
    return bytes(result)


def decode_zero_literal_rle(encoded: bytes, previous: bytes) -> bytes:
    state = bytearray(previous)
    source = 0
    dest = 0
    while dest < len(state):
        token = encoded[source]
        source += 1
        if token & 0x80:
            length = (token & 0x7F) + 1
            for value in encoded[source:source + length]:
                state[dest] ^= value
                dest += 1
            source += length
        elif token & 0x40:
            length = (token & 0x3F) + 1
            value = encoded[source]
            source += 1
            for _ in range(length):
                state[dest] ^= value
                dest += 1
        else:
            length = (token & 0x3F) + 1
            dest += length
    if dest != len(state) or source != len(encoded):
        raise ValueError("invalid RLE payload")
    return bytes(state)


def build_player_dither_tables() -> tuple[bytes, bytes]:
    """Map four packed brightness levels to two native output scanlines."""
    top = bytearray(256)
    bottom = bytearray(256)
    patterns = (
        (0b00, 0b00),
        (0b10, 0b00),
        (0b10, 0b01),
        (0b11, 0b11),
    )
    for packed in range(256):
        top_byte = 0
        bottom_byte = 0
        for index, shift in enumerate((6, 4, 2, 0)):
            level = (packed >> shift) & 3
            top_pair, bottom_pair = patterns[level]
            output_shift = 6 - index * 2
            top_byte |= top_pair << output_shift
            bottom_byte |= bottom_pair << output_shift
        top[packed] = top_byte
        bottom[packed] = bottom_byte
    return bytes(top), bytes(bottom)


PLAYER_DITHER_TOP, PLAYER_DITHER_BOTTOM = build_player_dither_tables()


def expand_compact_screen(state: bytes) -> tuple[bytes, bytes]:
    """Reference rendering of player-side 2x2 native dithering."""
    if len(state) != STATE_BYTES:
        raise ValueError("invalid two-bit brightness state size")
    packed = np.frombuffer(
        state[:STATE_LEVEL_BYTES], dtype=np.uint8
    ).reshape(LOGICAL_HEIGHT, LOGICAL_WIDTH // 4)
    bitmap = bytearray(base.SCREEN_BITMAP_BYTES)
    for source_y in range(LOGICAL_HEIGHT):
        top_offset = base.spectrum_bitmap_offset(0, source_y * 2)
        bottom_offset = base.spectrum_bitmap_offset(0, source_y * 2 + 1)
        bitmap[top_offset:top_offset + 32] = bytes(
            PLAYER_DITHER_TOP[value] for value in packed[source_y]
        )
        bitmap[bottom_offset:bottom_offset + 32] = bytes(
            PLAYER_DITHER_BOTTOM[value] for value in packed[source_y]
        )

    attrs = state[STATE_LEVEL_BYTES:]
    if len(attrs) != base.SCREEN_ATTR_BYTES:
        raise AssertionError("native 32x24 attribute grid is incomplete")
    return bytes(bitmap), attrs


def make_packet(
    state: bytes,
    previous: bytes | None,
    ay_state: bytes,
) -> Packet:
    if len(ay_state) != AY_STATE_BYTES:
        raise ValueError("invalid AY state")
    if previous is None:
        payload = state
        raw = True
    else:
        delta = bytes(current ^ old for current, old in zip(state, previous))
        compressed = encode_zero_literal_rle(delta)
        raw = len(compressed) >= len(state)
        payload = state if raw else compressed
    sectors = math.ceil(
        (PACKET_HEADER_BYTES + AY_STATE_BYTES + len(payload)) / base.SECTOR_SIZE
    )
    if not 1 <= sectors <= MAX_PACKET_SECTORS:
        raise ValueError(f"frame packet needs {sectors} sectors")
    return Packet(payload, raw, sectors, ay_state)


def serialize_video(
    packets: list[Packet],
    fps: float,
    timing_fps: float,
) -> bytes:
    if not packets:
        raise ValueError("cannot serialize an empty video")
    packet_data = b"".join(packet.serialize() for packet in packets)
    header = bytearray(base.SECTOR_SIZE)
    header[:4] = VIDEO_MAGIC
    header[4] = VIDEO_VERSION
    rate = Fraction(fps).limit_denominator(1000)
    header[5] = round(fps)
    header[6] = round(50 / timing_fps)
    header[7] = 0
    struct.pack_into("<H", header, 8, len(packets))
    struct.pack_into("<H", header, 10, LOGICAL_WIDTH)
    struct.pack_into("<H", header, 12, LOGICAL_HEIGHT)
    header[14] = 1
    struct.pack_into("<I", header, 16, round(len(packets) * 1000 / fps))
    struct.pack_into(
        "<H", header, 20, 1 + len(packet_data) // base.SECTOR_SIZE
    )
    header[24:32] = b"ZXVAY04 "
    struct.pack_into("<HH", header, 32, rate.numerator, rate.denominator)
    return bytes(header) + packet_data


def split_video_volumes(
    states: list[bytes],
    packets: list[Packet],
    fps: float,
    timing_fps: float,
    max_video_sectors: int,
) -> list[tuple[int, int, bytes, list[Packet]]]:
    """Split a long stream into independently bootable TRD-sized volumes."""
    if len(states) != len(packets):
        raise ValueError("state and packet counts differ")
    volumes: list[tuple[int, int, bytes, list[Packet]]] = []
    start = 0
    while start < len(states):
        part_packets = [
            make_packet(states[start], None, packets[start].ay_state)
        ]
        used_sectors = 1 + part_packets[0].sectors
        end = start + 1
        while end < len(states):
            candidate = packets[end]
            if used_sectors + candidate.sectors > max_video_sectors:
                break
            part_packets.append(candidate)
            used_sectors += candidate.sectors
            end += 1
        if end == start:
            raise AssertionError("volume splitter made no progress")
        video = serialize_video(part_packets, fps, timing_fps)
        volumes.append((start, end, video, part_packets))
        start = end
    return volumes


def emit_ld_a_mem(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x3A, label)


def emit_ld_mem_a(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x32, label)


def emit_ld_hl_mem(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x2A, label)


def emit_ld_mem_hl(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x22, label)


def emit_ld_de_mem(a: base.MiniAssembler, label: str) -> None:
    a.emit(0xED, 0x5B)
    pos = len(a.code)
    a.emit(0, 0)
    a.abs_fixups.append((pos, label))


def emit_ld_bc_mem(a: base.MiniAssembler, label: str) -> None:
    a.emit(0xED, 0x4B)
    pos = len(a.code)
    a.emit(0, 0)
    a.abs_fixups.append((pos, label))


def emit_ld_mem_de(a: base.MiniAssembler, label: str) -> None:
    a.emit(0xED, 0x53)
    pos = len(a.code)
    a.emit(0, 0)
    a.abs_fixups.append((pos, label))


def emit_call(a: base.MiniAssembler, address: int) -> None:
    a.emit(0xCD)
    a.word(address)


def build_player(
    video_track: int,
    video_sector: int,
    timing_fps: float,
) -> tuple[bytes, dict[str, int]]:
    if not 1.0 <= timing_fps <= 25.0:
        raise ValueError("timing_fps must be in 1..25")
    if float(timing_fps).is_integer():
        timing_limit = int(timing_fps)
        hold_base, hold_remainder = divmod(50, timing_limit)
    else:
        fields_per_frame = 50.0 / timing_fps
        rounded_fields = round(fields_per_frame)
        if not math.isclose(fields_per_frame, rounded_fields):
            raise ValueError(
                "fractional timing_fps must map to a whole number of 50 Hz fields"
            )
        timing_limit = 1
        hold_base = rounded_fields
        hold_remainder = 0
    a = base.MiniAssembler(LOAD_ADDRESS)

    # --------------------------------------------------------------- startup
    a.label("start")
    a.emit(0xF3)
    a.emit(0x31); a.word(0x5FF0)
    a.emit(0xAF, 0xD3, 0xFE)
    a.emit(0xAF); emit_ld_mem_a(a, "screen_flag")
    emit_ld_mem_a(a, "hold_accumulator")
    a.emit(0x3E, video_track); emit_ld_mem_a(a, "disk_track")
    a.emit(0x3E, video_sector); emit_ld_mem_a(a, "disk_sector")
    a.emit(0x3E, PAGING_ROM48_BANK7)
    a.emit(0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79)

    # Header sector.
    a.emit(0x21); a.word(BUFFER)
    a.emit(0x06, 1)
    a.abs16(0xCD, "read_n")
    for offset, value in enumerate(VIDEO_MAGIC):
        a.emit(0x3A); a.word(BUFFER + offset)
        a.emit(0xFE, value)
        a.abs16(0xC2, "fatal")
    a.emit(0x3A); a.word(BUFFER + 4)
    a.emit(0xFE, VIDEO_VERSION)
    a.abs16(0xC2, "fatal")
    a.emit(0x2A); a.word(BUFFER + 8)
    a.emit(0x2B)
    emit_ld_mem_hl(a, "frames_remaining")

    # First packet is raw and initializes the two-bit brightness state.
    a.abs16(0xCD, "read_packet")
    a.abs16(0xCD, "apply_packet")
    a.abs16(0xCD, "ay_apply")
    a.emit(0x3E, 0x40)
    a.abs16(0xCD, "render_state")
    a.emit(0x3E, 0xC0)
    a.abs16(0xCD, "render_state")
    a.emit(0xAF); emit_ld_mem_a(a, "screen_flag")
    a.emit(0x3E, PAGING_ROM48_BANK7)
    a.emit(0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79)

    # ------------------------------------------------------------ frame loop
    a.label("main_loop")
    emit_ld_hl_mem(a, "frames_remaining")
    a.emit(0x7C, 0xB5)
    a.abs16(0xCA, "finished")
    a.abs16(0xCD, "set_hold")
    a.emit(0xAF); emit_ld_mem_a(a, "next_loaded")
    a.emit(0x3E, 1); emit_ld_mem_a(a, "next_required")
    a.emit(0x21); a.word(BUFFER); emit_ld_mem_hl(a, "prefetch_ptr")

    a.label("load_loop")
    emit_ld_a_mem(a, "next_loaded"); a.emit(0x47)
    emit_ld_a_mem(a, "next_required"); a.emit(0xB8)
    a.rel8(0x28, "packet_ready")
    a.abs16(0xCD, "wait_field")
    a.abs16(0xCD, "decrement_hold")
    a.abs16(0xCD, "prefetch_one")
    a.abs16(0xC3, "load_loop")

    a.label("packet_ready")
    a.abs16(0xCD, "apply_packet")
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xB7)
    a.rel8(0x28, "render_bank7")
    a.emit(0x3E, 0x40)
    a.rel8(0x18, "render_selected")
    a.label("render_bank7")
    a.emit(0x3E, 0xC0)
    a.label("render_selected")
    a.abs16(0xCD, "render_state")

    a.label("hold_loop")
    emit_ld_a_mem(a, "hold_counter")
    a.emit(0xB7)
    a.rel8(0x28, "flip_ready")
    a.abs16(0xCD, "wait_field")
    a.abs16(0xCD, "decrement_hold")
    a.abs16(0xC3, "hold_loop")

    a.label("flip_ready")
    a.abs16(0xCD, "flip_screen")
    a.abs16(0xCD, "ay_apply")
    emit_ld_hl_mem(a, "frames_remaining")
    a.emit(0x2B)
    emit_ld_mem_hl(a, "frames_remaining")
    a.abs16(0xC3, "main_loop")

    # ------------------------------------------------------------ scheduling
    a.label("set_hold")
    emit_ld_a_mem(a, "hold_accumulator")
    if hold_remainder:
        a.emit(0xC6, hold_remainder)
        a.emit(0xFE, timing_limit)
        a.rel8(0x38, "hold_no_extra")
        a.emit(0xD6, timing_limit)
        emit_ld_mem_a(a, "hold_accumulator")
        a.emit(0x3E, hold_base + 1)
        emit_ld_mem_a(a, "hold_counter")
        a.emit(0xC9)
        a.label("hold_no_extra")
    emit_ld_mem_a(a, "hold_accumulator")
    a.emit(0x3E, hold_base)
    emit_ld_mem_a(a, "hold_counter")
    a.emit(0xC9)

    a.label("decrement_hold")
    emit_ld_a_mem(a, "hold_counter")
    a.emit(0xB7, 0xC8)
    a.emit(0x3D); emit_ld_mem_a(a, "hold_counter")
    a.emit(0xC9)

    a.label("wait_field")
    a.emit(0xFB, 0x76, 0xF3, 0xC9)

    a.label("flip_screen")
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xEE, 0x08); emit_ld_mem_a(a, "screen_flag")
    a.emit(0xF6, PAGING_ROM48_BANK7)
    a.emit(0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79, 0xC9)

    # --------------------------------------------------------------- AY sound
    # Tone generators A/B/C only; noise is disabled. One compact sound state
    # is applied per completed logical frame, so video rendering stays fast.
    a.label("ay_apply")
    a.emit(0x3E, 7, 0x01); a.word(0xFFFD); a.emit(0xED, 0x79)
    a.emit(0x3E, 0x38, 0x06, 0xBF, 0xED, 0x79)
    a.emit(0x21); a.abs16([], "ay_state")
    for register in (0, 1, 2, 3, 4, 5, 8, 9, 10):
        a.emit(0x3E, register, 0x01); a.word(0xFFFD)
        a.emit(0xED, 0x79, 0x7E, 0x23, 0x06, 0xBF, 0xED, 0x79)
    a.emit(0xC9)

    # -------------------------------------------------------------- packets
    a.label("read_packet")
    a.emit(0x21); a.word(BUFFER)
    a.emit(0x06, 1)
    a.abs16(0xCD, "read_n")
    a.emit(0x3A); a.word(BUFFER)
    a.emit(0xFE, 1)
    a.emit(0xC8)
    a.emit(0x3D, 0x47)
    a.emit(0x21); a.word(BUFFER + base.SECTOR_SIZE)
    a.abs16(0xCD, "read_n")
    a.emit(0xC9)

    a.label("prefetch_one")
    emit_ld_a_mem(a, "next_loaded"); a.emit(0x47)
    emit_ld_a_mem(a, "next_required"); a.emit(0xB8, 0xC8)
    emit_ld_hl_mem(a, "prefetch_ptr")
    a.emit(0x06, 1)
    a.abs16(0xCD, "read_n")
    emit_ld_hl_mem(a, "prefetch_ptr")
    a.emit(0x24)
    emit_ld_mem_hl(a, "prefetch_ptr")
    emit_ld_a_mem(a, "next_loaded")
    a.emit(0x3C); emit_ld_mem_a(a, "next_loaded")
    a.emit(0xFE, 1, 0xC0)
    a.emit(0x3A); a.word(BUFFER)
    emit_ld_mem_a(a, "next_required")
    a.emit(0xC9)

    # Raw packet copy or XOR zero/repeat/literal RLE.
    a.label("apply_packet")
    a.emit(0x21); a.word(BUFFER + PACKET_HEADER_BYTES)
    a.emit(0x11); a.abs16([], "ay_state")
    a.emit(0x01); a.word(AY_STATE_BYTES)
    a.emit(0xED, 0xB0)
    a.emit(0x3A); a.word(BUFFER + 1)
    a.emit(0xE6, 1)
    a.rel8(0x28, "apply_delta")
    a.emit(0x21); a.word(BUFFER + PACKET_HEADER_BYTES + AY_STATE_BYTES)
    a.emit(0x11); a.word(STATE_ADDRESS)
    a.emit(0x01); a.word(STATE_BYTES)
    a.emit(0xED, 0xB0, 0xC9)

    a.label("apply_delta")
    a.emit(0x21); a.word(BUFFER + PACKET_HEADER_BYTES + AY_STATE_BYTES)
    a.emit(0x11); a.word(STATE_ADDRESS)
    a.emit(0x01); a.word(STATE_BYTES)
    a.label("rle_next")
    a.emit(0x78, 0xB1, 0xC8)
    a.emit(0x7E, 0x23)
    a.emit(0xCB, 0x7F)
    a.rel8(0x20, "rle_literal")
    a.emit(0xCB, 0x77)
    a.rel8(0x20, "rle_repeat")
    a.emit(0x3C); emit_ld_mem_a(a, "run_count")
    a.label("rle_zero_loop")
    a.emit(0x13, 0x0B)
    emit_ld_a_mem(a, "run_count")
    a.emit(0x3D); emit_ld_mem_a(a, "run_count")
    a.rel8(0x20, "rle_zero_loop")
    a.rel8(0x18, "rle_next")

    a.label("rle_repeat")
    a.emit(0xE6, 0x3F, 0x3C); emit_ld_mem_a(a, "run_count")
    a.emit(0x7E, 0x23); emit_ld_mem_a(a, "repeat_value")
    a.emit(0xE5)
    a.emit(0x21); a.abs16([], "repeat_value")
    a.label("rle_repeat_loop")
    a.emit(0x1A, 0xAE, 0x12, 0x13, 0x0B)
    emit_ld_a_mem(a, "run_count")
    a.emit(0x3D); emit_ld_mem_a(a, "run_count")
    a.rel8(0x20, "rle_repeat_loop")
    a.emit(0xE1)
    a.rel8(0x18, "rle_next")

    a.label("rle_literal")
    a.emit(0xE6, 0x7F, 0x3C); emit_ld_mem_a(a, "run_count")
    a.label("rle_literal_loop")
    a.emit(0x1A, 0xAE, 0x12, 0x23, 0x13, 0x0B)
    emit_ld_a_mem(a, "run_count")
    a.emit(0x3D); emit_ld_mem_a(a, "run_count")
    a.rel8(0x20, "rle_literal_loop")
    a.rel8(0x18, "rle_next")

    # --------------------------------------------------------------- renderer
    a.label("render_state")
    emit_ld_mem_a(a, "render_base")
    a.emit(0x11); a.word(STATE_ADDRESS)
    a.emit(0x21); a.abs16([], "row_addresses")
    emit_ld_mem_hl(a, "row_table_ptr")
    a.emit(0x3E, LOGICAL_HEIGHT); emit_ld_mem_a(a, "render_rows")

    a.label("render_row")
    emit_ld_mem_de(a, "source_row")
    emit_ld_hl_mem(a, "row_table_ptr")
    a.emit(0x4E, 0x23, 0x46, 0x23)        # BC = top row offset
    emit_ld_a_mem(a, "render_base")
    a.emit(0x80, 0x47)                    # add screen base to B
    a.emit(0x5E, 0x23, 0x56, 0x23)        # DE = bottom row offset
    emit_ld_a_mem(a, "render_base")
    a.emit(0x82, 0x57)                    # add screen base to D
    emit_ld_mem_de(a, "second_row")
    emit_ld_mem_hl(a, "row_table_ptr")

    emit_ld_de_mem(a, "source_row")
    a.emit(0x21); a.abs16([], "dither_top")
    for _ in range(LOGICAL_WIDTH // 4):
        a.emit(0x1A, 0x13, 0x6F, 0x7E, 0x02, 0x03)

    emit_ld_de_mem(a, "source_row")
    emit_ld_bc_mem(a, "second_row")
    a.emit(0x21); a.abs16([], "dither_bottom")
    for _ in range(LOGICAL_WIDTH // 4):
        a.emit(0x1A, 0x13, 0x6F, 0x7E, 0x02, 0x03)

    emit_ld_a_mem(a, "render_rows")
    a.emit(0x3D); emit_ld_mem_a(a, "render_rows")
    a.abs16(0xC2, "render_row")

    # Copy the native 32x24 attribute grid without scaling.
    a.emit(0x21); a.word(STATE_ADDRESS + STATE_LEVEL_BYTES)
    emit_ld_a_mem(a, "render_base")
    a.emit(0xC6, 0x18, 0x57, 0x1E, 0x00)
    a.emit(0x01); a.word(base.SCREEN_ATTR_BYTES)
    a.emit(0xED, 0xB0, 0xC9)

    # ----------------------------------------------------------- TR-DOS read
    a.label("read_n")
    a.emit(0x78); emit_ld_mem_a(a, "read_count")
    emit_ld_a_mem(a, "disk_track"); a.emit(0x57)
    emit_ld_a_mem(a, "disk_sector"); a.emit(0x5F)
    a.emit(0x0E, 0x05)
    emit_call(a, 0x3D13)
    a.emit(0xF3)
    emit_ld_a_mem(a, "screen_flag"); a.emit(0xF6, PAGING_ROM48_BANK7)
    a.emit(0x01); a.word(0x7FFD); a.emit(0xED, 0x79)
    emit_ld_a_mem(a, "read_count"); a.emit(0x47)
    a.label("advance_sector_loop")
    emit_ld_a_mem(a, "disk_sector")
    a.emit(0x3C, 0xFE, 16)
    a.rel8(0x38, "advance_store_sector")
    a.emit(0xAF); emit_ld_mem_a(a, "disk_sector")
    emit_ld_a_mem(a, "disk_track")
    a.emit(0x3C); emit_ld_mem_a(a, "disk_track")
    a.rel8(0x18, "advance_sector_next")
    a.label("advance_store_sector")
    emit_ld_mem_a(a, "disk_sector")
    a.label("advance_sector_next")
    a.rel8(0x10, "advance_sector_loop")
    a.emit(0xC9)

    # ---------------------------------------------------------- stop/errors
    a.label("finished")
    for register in (8, 9, 10):
        a.emit(0x3E, register, 0x01); a.word(0xFFFD)
        a.emit(0xED, 0x79, 0xAF, 0x06, 0xBF, 0xED, 0x79)
    a.emit(0xFB)
    a.label("finished_wait")
    a.emit(0x76)
    a.rel8(0x18, "finished_wait")
    a.label("fatal")
    a.emit(0x3E, 2, 0xD3, 0xFE)
    a.rel8(0x18, "fatal")

    # -------------------------------------------------------------- variables
    for name, size in (
        ("screen_flag", 1),
        ("disk_track", 1),
        ("disk_sector", 1),
        ("read_count", 1),
        ("frames_remaining", 2),
        ("hold_counter", 1),
        ("hold_accumulator", 1),
        ("next_loaded", 1),
        ("next_required", 1),
        ("prefetch_ptr", 2),
        ("run_count", 1),
        ("repeat_value", 1),
        ("render_base", 1),
        ("render_rows", 1),
        ("row_table_ptr", 2),
        ("source_row", 2),
        ("second_row", 2),
        ("ay_state", AY_STATE_BYTES),
    ):
        a.label(name)
        a.emit(*([0] * size))

    a.label("row_addresses")
    for source_y in range(LOGICAL_HEIGHT):
        a.word(base.spectrum_bitmap_offset(0, source_y * 2))
        a.word(base.spectrum_bitmap_offset(0, source_y * 2 + 1))

    while a.pc & 0xFF:
        a.emit(0)
    a.label("dither_top")
    a.emit(*PLAYER_DITHER_TOP)
    a.label("dither_bottom")
    a.emit(*PLAYER_DITHER_BOTTOM)

    code = a.resolve()
    if LOAD_ADDRESS + len(code) >= BUFFER:
        raise ValueError(
            f"player size {len(code)} overlaps packet buffer at {BUFFER:04X}h"
        )
    return code, dict(a.labels)


def read_exact(stream: BinaryIO, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        part = stream.read(length - len(chunks))
        if not part:
            break
        chunks += part
    return bytes(chunks)


def ffmpeg_frames(
    source: Path,
    start: float,
    duration: float,
    fps: float,
) -> tuple[subprocess.Popen[bytes], list[str]]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is not available")
    command = [
        ffmpeg,
        "-v", "error",
        "-ss", f"{start:g}",
        "-t", f"{duration:g}",
        "-i", str(source),
        "-vf",
        f"fps={fps},scale={ANALYSIS_WIDTH}:{ANALYSIS_HEIGHT}:flags=area",
        "-pix_fmt", "rgb24",
        "-f", "rawvideo",
        "-",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    assert process.stdout is not None
    return process, command


def analyse_motion_reframe(
    source: Path,
    start: float,
    duration: float,
    fps: float,
) -> tuple[list[ReframeWindow], dict[str, float]]:
    """Find and smoothly centre the most persistent moving image region."""
    process, _ = ffmpeg_frames(source, start, duration, fps)
    assert process.stdout is not None
    frame_bytes = ANALYSIS_WIDTH * ANALYSIS_HEIGHT * 3
    grid_width, grid_height = 32, 18
    previous_gray: np.ndarray | None = None
    targets: list[tuple[float, float, float]] = []
    try:
        while True:
            raw = read_exact(process.stdout, frame_bytes)
            if not raw:
                break
            if len(raw) != frame_bytes:
                raise RuntimeError("ffmpeg returned a partial motion frame")
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                ANALYSIS_HEIGHT, ANALYSIS_WIDTH, 3
            )
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            if previous_gray is None:
                targets.append((0.5, 0.5, 1.15))
            else:
                difference = cv2.absdiff(gray, previous_gray).astype(np.float32)
                energy = cv2.resize(
                    difference * difference,
                    (grid_width, grid_height),
                    interpolation=cv2.INTER_AREA,
                )
                floor = float(np.percentile(energy, 55.0))
                weights = np.maximum(energy - floor, 0.0)
                total = float(weights.sum())
                if total < 1.0:
                    targets.append((0.5, 0.5, 1.15))
                else:
                    yy, xx = np.mgrid[0:grid_height, 0:grid_width]
                    center_x = float(
                        np.sum(weights * (xx + 0.5)) / total / grid_width
                    )
                    center_y = float(
                        np.sum(weights * (yy + 0.5)) / total / grid_height
                    )
                    variance = float(
                        np.sum(
                            weights
                            * (
                                ((xx + 0.5) / grid_width - center_x) ** 2
                                + ((yy + 0.5) / grid_height - center_y) ** 2
                            )
                        )
                        / total
                    )
                    concentration = float(np.clip(1.0 - variance / 0.14, 0.0, 1.0))
                    zoom = 1.15 + 0.35 * concentration
                    targets.append((center_x, center_y, zoom))
            previous_gray = gray
    finally:
        process.stdout.close()
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"motion-analysis ffmpeg exited with {return_code}")
    if not targets:
        raise RuntimeError("motion analysis decoded no frames")

    values = np.asarray(targets, dtype=np.float64)
    # A centred two-second triangular filter avoids camera hunting and makes
    # scene transitions look like deliberate pans rather than crop jumps.
    radius = max(1, round(fps))
    positions = np.arange(-radius, radius + 1)
    kernel = (radius + 1 - np.abs(positions)).astype(np.float64)
    kernel /= kernel.sum()
    smooth = np.empty_like(values)
    for column in range(3):
        padded = np.pad(values[:, column], radius, mode="edge")
        smooth[:, column] = np.convolve(padded, kernel, mode="valid")

    candidate_windows: list[ReframeWindow] = []
    for center_x, center_y, zoom in smooth:
        zoom = float(np.clip(zoom, 1.15, 1.5))
        half_width = 0.5 / zoom
        half_height = 0.5 / zoom
        candidate_windows.append(
            ReframeWindow(
                center_x=float(np.clip(center_x, half_width, 1.0 - half_width)),
                center_y=float(np.clip(center_y, half_height, 1.0 - half_height)),
                zoom=zoom,
            )
        )
    # Continuous sub-pixel zoom/pan destroys inter-frame compression because
    # nearly every source pixel changes. Use stable virtual shots and reframe
    # only when the subject has moved materially. The occasional larger packet
    # is preferable to slowing every frame of the video.
    windows: list[ReframeWindow] = []
    current = candidate_windows[0]
    last_change = 0
    minimum_hold = max(1, round(fps * 1.5))
    reframe_changes = 0
    for index, candidate in enumerate(candidate_windows):
        displacement = math.hypot(
            candidate.center_x - current.center_x,
            candidate.center_y - current.center_y,
        )
        zoom_change = abs(candidate.zoom - current.zoom)
        if (
            index - last_change >= minimum_hold
            and (displacement >= 0.055 or zoom_change >= 0.09)
        ):
            zoom = round(candidate.zoom / 0.05) * 0.05
            half_width = 0.5 / zoom
            half_height = 0.5 / zoom
            current = ReframeWindow(
                center_x=float(
                    np.clip(round(candidate.center_x * 64.0) / 64.0, half_width, 1.0 - half_width)
                ),
                center_y=float(
                    np.clip(round(candidate.center_y * 64.0) / 64.0, half_height, 1.0 - half_height)
                ),
                zoom=float(zoom),
            )
            last_change = index
            reframe_changes += 1
        windows.append(current)
    xs = np.array([window.center_x for window in windows])
    ys = np.array([window.center_y for window in windows])
    zooms = np.array([window.zoom for window in windows])
    stats = {
        "center_x_min": float(xs.min()),
        "center_x_max": float(xs.max()),
        "center_y_min": float(ys.min()),
        "center_y_max": float(ys.max()),
        "zoom_min": float(zooms.min()),
        "zoom_max": float(zooms.max()),
        "zoom_mean": float(zooms.mean()),
        "changes": float(reframe_changes),
    }
    print(
        f"motion reframe: x={xs.min():.3f}..{xs.max():.3f}, "
        f"y={ys.min():.3f}..{ys.max():.3f}, "
        f"zoom={zooms.min():.2f}..{zooms.max():.2f} "
        f"(mean {zooms.mean():.2f}), changes={reframe_changes}",
        flush=True,
    )
    return windows, stats


def apply_reframe(image: np.ndarray, window: ReframeWindow) -> np.ndarray:
    crop_width = ANALYSIS_WIDTH / window.zoom
    crop_height = ANALYSIS_HEIGHT / window.zoom
    x0 = int(round(window.center_x * ANALYSIS_WIDTH - crop_width * 0.5))
    y0 = int(round(window.center_y * ANALYSIS_HEIGHT - crop_height * 0.5))
    x0 = int(np.clip(x0, 0, ANALYSIS_WIDTH - round(crop_width)))
    y0 = int(np.clip(y0, 0, ANALYSIS_HEIGHT - round(crop_height)))
    x1 = min(ANALYSIS_WIDTH, x0 + round(crop_width))
    y1 = min(ANALYSIS_HEIGHT, y0 + round(crop_height))
    active = cv2.resize(
        image[y0:y1, x0:x1],
        (LOGICAL_WIDTH, ACTIVE_HEIGHT),
        interpolation=cv2.INTER_AREA,
    )
    result = np.zeros((LOGICAL_HEIGHT, LOGICAL_WIDTH, 3), dtype=np.uint8)
    result[ACTIVE_Y0:ACTIVE_Y0 + ACTIVE_HEIGHT] = active
    return result


def analyse_ay_frames(
    source: Path,
    start: float,
    duration: float,
    fps: float,
) -> tuple[list[AyFrame], dict[str, object]]:
    """Reduce the soundtrack to three stable, note-quantised AY tone voices."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is not available")
    sample_rate = 48_000
    command = [
        ffmpeg,
        "-v", "error",
        "-ss", f"{start:g}",
        "-t", f"{duration:g}",
        "-i", str(source),
        "-map", "0:a:0",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-f", "f32le",
        "pipe:1",
    ]
    completed = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    if completed.returncode:
        raise RuntimeError(f"audio-analysis ffmpeg exited with {completed.returncode}")
    samples = np.frombuffer(completed.stdout, dtype="<f4").astype(np.float64)
    expected_frames = round(duration * fps)
    window_size = 4096
    half_window = window_size // 2
    window = np.hanning(window_size)
    frequencies = np.fft.rfftfreq(window_size, 1.0 / sample_rate)
    usable = (frequencies >= 55.0) & (frequencies <= 1760.0)
    usable_indices = np.flatnonzero(usable)
    midi_bins = np.rint(
        69.0 + 12.0 * np.log2(frequencies[usable] / 440.0)
    ).astype(np.int32)
    midi_min = 33
    midi_max = 93
    smoothed_salience = np.zeros(128, dtype=np.float64)
    result: list[AyFrame] = []
    used_notes: set[int] = set()
    active_voice_frames = 0
    frame_rms: list[float] = []
    for frame_index in range(expected_frames):
        center = round((frame_index + 0.5) * sample_rate / fps)
        first = center - half_window
        source_first = max(0, first)
        source_last = min(len(samples), first + window_size)
        segment = np.zeros(window_size, dtype=np.float64)
        if source_last > source_first:
            segment[source_first - first:source_last - first] = samples[
                source_first:source_last
            ]
        frame_rms.append(float(np.sqrt(np.mean(segment * segment))))
    rms_db = 20.0 * np.log10(np.maximum(frame_rms, 1e-8))
    audible_db = rms_db[rms_db > -70.0]
    if len(audible_db):
        quiet_db = float(np.percentile(audible_db, 10.0))
        loud_db = float(np.percentile(audible_db, 95.0))
    else:
        quiet_db, loud_db = -48.0, -12.0
    loud_db = max(loud_db, quiet_db + 6.0)
    master_volumes: list[int] = []

    for frame_index in range(expected_frames):
        center = round((frame_index + 0.5) * sample_rate / fps)
        first = center - half_window
        segment = np.zeros(window_size, dtype=np.float64)
        source_first = max(0, first)
        source_last = min(len(samples), first + window_size)
        if source_last > source_first:
            segment[source_first - first:source_last - first] = samples[
                source_first:source_last
            ]
        db = float(rms_db[frame_index])
        if db <= -70.0:
            master_volume = 0
        else:
            master_volume = int(
                np.clip(
                    round(1.0 + 14.0 * (db - quiet_db) / (loud_db - quiet_db)),
                    1,
                    15,
                )
            )
        master_volumes.append(master_volume)
        spectrum = np.abs(np.fft.rfft(segment * window)) ** 2
        local = spectrum[usable_indices]
        peak_mask = np.zeros_like(local, dtype=bool)
        peak_mask[1:-1] = (
            (local[1:-1] > local[:-2]) & (local[1:-1] >= local[2:])
        )
        peak_power = np.where(peak_mask, local, 0.0)
        salience = np.bincount(
            midi_bins,
            weights=peak_power,
            minlength=128,
        ).astype(np.float64)
        smoothed_salience = smoothed_salience * 0.55 + salience * 0.45
        ranked = np.argsort(smoothed_salience[midi_min:midi_max + 1])[::-1]
        selected: list[int] = []
        for relative_note in ranked:
            note = int(relative_note + midi_min)
            if smoothed_salience[note] <= 0.0:
                break
            if all(abs(note - other) >= 2 for other in selected):
                selected.append(note)
            if len(selected) == 3:
                break
        selected.sort()
        selected_count = len(selected)
        while len(selected) < 3:
            selected.append(69)

        maximum = max((smoothed_salience[note] for note in selected), default=0.0)
        periods: list[int] = []
        volumes: list[int] = []
        for voice, note in enumerate(selected):
            frequency = 440.0 * 2.0 ** ((note - 69) / 12.0)
            period = int(np.clip(round(AY_CLOCK_HZ / (16.0 * frequency)), 1, 4095))
            periods.append(period)
            score = smoothed_salience[note]
            if master_volume == 0 or maximum <= 0.0 or voice >= selected_count:
                volume = 0
            else:
                relative_db = 10.0 * math.log10(max(score / maximum, 1e-8))
                volume = int(
                    np.clip(
                        round(master_volume + relative_db / 3.0),
                        1,
                        master_volume,
                    )
                )
            volumes.append(volume)
            if volume:
                used_notes.add(note)
        if any(volumes):
            active_voice_frames += 1
        result.append(AyFrame(tuple(periods), tuple(volumes)))

    print(
        f"AY analysis: {len(result)} frames, {len(used_notes)} notes, "
        f"active {active_voice_frames / max(1, len(result)):.1%}, "
        f"master volume {min(master_volumes)}..{max(master_volumes)}",
        flush=True,
    )
    return result, {
        "mode": "three_note_spectral",
        "clock_hz": AY_CLOCK_HZ,
        "update_rate_hz": float(fps),
        "distinct_notes": len(used_notes),
        "active_frame_ratio": active_voice_frames / max(1, len(result)),
        "source_quiet_dbfs": quiet_db,
        "source_loud_dbfs": loud_db,
        "master_volume_min": min(master_volumes),
        "master_volume_max": max(master_volumes),
        "master_volume_mean": float(np.mean(master_volumes)),
    }


def histogram_percentile(histogram: np.ndarray, percentile: float) -> float:
    cumulative = np.cumsum(histogram, dtype=np.int64)
    if cumulative[-1] == 0:
        raise ValueError("empty luminance histogram")
    target = cumulative[-1] * percentile / 100.0
    index = int(np.searchsorted(cumulative, target, side="left"))
    return (index + 0.5) / len(histogram)


def tone_range_from_histogram(
    histogram: np.ndarray,
    black_percentile: float,
    white_percentile: float,
) -> ToneRange:
    black = histogram_percentile(histogram, black_percentile)
    white = histogram_percentile(histogram, white_percentile)
    bins = len(histogram)
    if white - black < 1.0 / bins:
        raise RuntimeError("analysed luminance range is empty")

    bin_values = (np.arange(bins, dtype=np.float64) + 0.5) / bins
    included = (bin_values >= black) & (bin_values <= white)
    values = bin_values[included]
    weights = histogram[included].astype(np.float64)
    centers = np.linspace(black, white, 4)
    for _ in range(32):
        thresholds = (centers[:-1] + centers[1:]) * 0.5
        groups = np.digitize(values, thresholds)
        updated = centers.copy()
        for group in range(4):
            selected = groups == group
            total = float(weights[selected].sum())
            if total:
                updated[group] = float(
                    np.sum(values[selected] * weights[selected]) / total
                )
        if np.max(np.abs(updated - centers)) < 1e-7:
            centers = updated
            break
        centers = updated
    thresholds = (centers[:-1] + centers[1:]) * 0.5
    return ToneRange(
        black_point=float(black),
        white_point=float(white),
        centers=tuple(float(value) for value in centers),
        thresholds=tuple(float(value) for value in thresholds),
        black_percentile=black_percentile,
        white_percentile=white_percentile,
    )


def analyse_tone_ranges(
    source: Path,
    start: float,
    duration: float,
    fps: float,
    black_percentile: float,
    white_percentile: float,
    window_seconds: float,
    reframe_windows: list[ReframeWindow],
) -> list[ToneRange]:
    """Calculate smoothly adaptive tone groups in a centred time window."""
    process, _ = ffmpeg_frames(source, start, duration, fps)
    assert process.stdout is not None
    bins = 1024
    frame_histograms: list[np.ndarray] = []
    frame_bytes = ANALYSIS_WIDTH * ANALYSIS_HEIGHT * 3
    try:
        while True:
            raw = read_exact(process.stdout, frame_bytes)
            if not raw:
                break
            if len(raw) != frame_bytes:
                raise RuntimeError("ffmpeg returned a partial analysis frame")
            image = np.frombuffer(raw, dtype=np.uint8).reshape(
                ANALYSIS_HEIGHT, ANALYSIS_WIDTH, 3
            )
            if len(frame_histograms) >= len(reframe_windows):
                raise RuntimeError("motion analysis has fewer frames than video")
            image = apply_reframe(
                image, reframe_windows[len(frame_histograms)]
            )
            active = image[ACTIVE_Y0:ACTIVE_Y0 + ACTIVE_HEIGHT]
            linear = base.srgb_to_linear(active.astype(np.float64))
            luminance = (
                linear[:, :, 0] * 0.2126
                + linear[:, :, 1] * 0.7152
                + linear[:, :, 2] * 0.0722
            )
            frame_histograms.append(
                np.histogram(luminance, bins=bins, range=(0.0, 1.0))[0]
            )
    finally:
        process.stdout.close()
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"tone-analysis ffmpeg exited with {return_code}")
    if not frame_histograms:
        raise RuntimeError("tone analysis decoded no frames")

    histograms = np.stack(frame_histograms).astype(np.int64, copy=False)
    prefix = np.vstack(
        [np.zeros((1, bins), dtype=np.int64), np.cumsum(histograms, axis=0)]
    )
    radius = max(1, round(window_seconds * fps * 0.5))
    ranges: list[ToneRange] = []
    for index in range(len(histograms)):
        first = max(0, index - radius)
        last = min(len(histograms), index + radius + 1)
        ranges.append(
            tone_range_from_histogram(
                prefix[last] - prefix[first],
                black_percentile,
                white_percentile,
            )
        )

    # A symmetric one-second low-pass removes histogram-bin jitter without
    # delaying or anticipating scene changes by more than the analysis window.
    parameter_rows = np.array(
        [
            (tone.black_point, tone.white_point, *tone.centers)
            for tone in ranges
        ],
        dtype=np.float64,
    )
    smooth_radius = max(1, round(fps * 0.5))
    kernel_positions = np.arange(-smooth_radius, smooth_radius + 1)
    kernel = (smooth_radius + 1 - np.abs(kernel_positions)).astype(np.float64)
    kernel /= kernel.sum()
    smoothed = np.empty_like(parameter_rows)
    for column in range(parameter_rows.shape[1]):
        padded = np.pad(
            parameter_rows[:, column], smooth_radius, mode="edge"
        )
        smoothed[:, column] = np.convolve(padded, kernel, mode="valid")

    result: list[ToneRange] = []
    for row in smoothed:
        black_point = float(np.clip(row[0], 0.0, 1.0 - 1.0 / bins))
        white_point = float(np.clip(row[1], black_point + 1.0 / bins, 1.0))
        centers = np.clip(row[2:], black_point, white_point)
        centers = np.maximum.accumulate(centers)
        thresholds = (centers[:-1] + centers[1:]) * 0.5
        result.append(
            ToneRange(
                black_point=black_point,
                white_point=white_point,
                centers=tuple(float(value) for value in centers),
                thresholds=tuple(float(value) for value in thresholds),
                black_percentile=black_percentile,
                white_percentile=white_percentile,
            )
        )

    black_values = np.array([tone.black_point for tone in result])
    white_values = np.array([tone.white_point for tone in result])
    middle = result[len(result) // 2]
    print(
        f"adaptive tone window={window_seconds:g}s, "
        f"P{black_percentile:g}={black_values.min():.5f}.."
        f"{black_values.max():.5f}, "
        f"P{white_percentile:g}={white_values.min():.5f}.."
        f"{white_values.max():.5f}, "
        f"middle thresholds={','.join(f'{x:.5f}' for x in middle.thresholds)}",
        flush=True,
    )
    return result


def apply_tone_groups(image: np.ndarray, tone: ToneRange) -> np.ndarray:
    """Map the current adaptive luminance groups while retaining pixel hue."""
    linear = base.srgb_to_linear(image.astype(np.float64))
    active = linear[ACTIVE_Y0:ACTIVE_Y0 + ACTIVE_HEIGHT]
    luminance = (
        active[:, :, 0] * 0.2126
        + active[:, :, 1] * 0.7152
        + active[:, :, 2] * 0.0722
    )
    clipped = np.clip(luminance, tone.black_point, tone.white_point)
    groups = np.digitize(clipped, np.asarray(tone.thresholds))
    target_levels = np.array([0.0, 0.25, 0.5, 1.0], dtype=np.float64)
    target = target_levels[groups]
    scale = np.divide(
        target,
        np.maximum(luminance, 1e-8),
        out=np.zeros_like(target),
    )
    active[:] = np.clip(active * scale[:, :, None], 0.0, 1.0)
    srgb = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * np.power(linear, 1.0 / 2.4) - 0.055,
    )
    return np.clip(np.rint(srgb * 255.0), 0, 255).astype(np.uint8)


def build_video(
    source: Path,
    start: float,
    duration: float,
    fps: float,
    timing_fps: float,
    tone_ranges: list[ToneRange],
    ay_frames: list[AyFrame],
    reframe_windows: list[ReframeWindow],
    attr_change_penalty: int,
    dither: str,
    preview_path: Path,
) -> tuple[bytes, list[Packet], list[bytes], dict[str, object]]:
    process, ffmpeg_command = ffmpeg_frames(source, start, duration, fps)
    assert process.stdout is not None
    packets: list[Packet] = []
    states: list[bytes] = []
    previous_state: bytes | None = None
    previous_attrs: np.ndarray | None = None
    raw_packets = 0
    writer = cv2.VideoWriter(
        str(preview_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        timing_fps,
        (base.WIDTH, base.HEIGHT),
    )
    if not writer.isOpened():
        process.kill()
        raise RuntimeError("cannot create preview video")

    frame_bytes = ANALYSIS_WIDTH * ANALYSIS_HEIGHT * 3
    try:
        while True:
            raw = read_exact(process.stdout, frame_bytes)
            if not raw:
                break
            if len(raw) != frame_bytes:
                raise RuntimeError("ffmpeg returned a partial frame")
            image = np.frombuffer(raw, dtype=np.uint8).reshape(
                ANALYSIS_HEIGHT, ANALYSIS_WIDTH, 3
            )
            if len(packets) >= len(reframe_windows):
                raise RuntimeError("motion analysis has fewer frames than video")
            image = apply_reframe(image, reframe_windows[len(packets)])
            if len(packets) >= len(tone_ranges):
                raise RuntimeError("tone analysis has fewer frames than video")
            image = apply_tone_groups(image, tone_ranges[len(packets)])
            state, attrs = encode_compact_frame(
                image, previous_attrs, attr_change_penalty, dither
            )
            if len(packets) >= len(ay_frames):
                raise RuntimeError("audio analysis has fewer frames than video")
            packet = make_packet(
                state,
                previous_state,
                ay_frames[len(packets)].serialize(),
            )
            packets.append(packet)
            states.append(state)
            raw_packets += int(packet.raw)
            previous_state = state
            previous_attrs = attrs.copy()

            bitmap, screen_attrs = expand_compact_screen(state)
            rendered = base.render_spectrum_screen(bitmap, screen_attrs)
            writer.write(cv2.cvtColor(rendered, cv2.COLOR_RGB2BGR))
            if len(packets) == 1 or len(packets) % 20 == 0:
                print(f"converted frame {len(packets)}", flush=True)
    finally:
        writer.release()
        process.stdout.close()
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"ffmpeg exited with {return_code}")
    if len(packets) < 2:
        raise RuntimeError("not enough source frames")
    if len(packets) != len(tone_ranges):
        raise RuntimeError(
            f"tone/video frame mismatch: {len(tone_ranges)} vs {len(packets)}"
        )
    if len(packets) != len(ay_frames):
        raise RuntimeError(
            f"audio/video frame mismatch: {len(ay_frames)} vs {len(packets)}"
        )
    if len(packets) != len(reframe_windows):
        raise RuntimeError(
            f"motion/video frame mismatch: {len(reframe_windows)} vs {len(packets)}"
        )
    if len(packets) > 0xFFFF:
        raise ValueError("too many frames for the long-video header")

    video = serialize_video(packets, fps, timing_fps)
    stats: dict[str, object] = {
        "frames": len(packets),
        "fps": fps,
        "screen_fps": timing_fps,
        "ay_state_bytes_per_frame": AY_STATE_BYTES,
        "colour_candidates": len(COLOUR_CANDIDATES),
        "distinct_attributes": len(
            {
                value
                for state in states
                for value in state[STATE_LEVEL_BYTES:]
            }
        ),
        "tone_range": {
            "mode": "adaptive",
            "black_percentile": tone_ranges[0].black_percentile,
            "white_percentile": tone_ranges[0].white_percentile,
            "black_point_min": min(t.black_point for t in tone_ranges),
            "black_point_max": max(t.black_point for t in tone_ranges),
            "white_point_min": min(t.white_point for t in tone_ranges),
            "white_point_max": max(t.white_point for t in tone_ranges),
        },
        "duration_seconds": len(packets) / fps,
        "video_bytes": len(video),
        "video_sectors": len(video) // base.SECTOR_SIZE,
        "packet_sectors": [packet.sectors for packet in packets],
        "raw_packets": raw_packets,
        "delta_packets": len(packets) - raw_packets,
        "dither": dither,
        "ffmpeg_command": ffmpeg_command,
    }
    return video, packets, states, stats


def verify_video(video: bytes, expected_states: list[bytes]) -> None:
    if video[:4] != VIDEO_MAGIC or video[4] != VIDEO_VERSION:
        raise ValueError("invalid long-video header")
    frame_count = struct.unpack_from("<H", video, 8)[0]
    if frame_count != len(expected_states):
        raise ValueError("frame count mismatch")
    offset = base.SECTOR_SIZE
    state = bytes(STATE_BYTES)
    for index in range(frame_count):
        sectors = video[offset]
        flags = video[offset + 1]
        payload_length = struct.unpack_from("<H", video, offset + 2)[0]
        ay_length = video[offset + 4]
        if ay_length != AY_STATE_BYTES:
            raise ValueError(f"packet {index} has invalid AY state")
        checksum = struct.unpack_from("<H", video, offset + 6)[0]
        ay_state = video[
            offset + PACKET_HEADER_BYTES:
            offset + PACKET_HEADER_BYTES + ay_length
        ]
        payload = video[
            offset + PACKET_HEADER_BYTES + ay_length:
            offset + PACKET_HEADER_BYTES + ay_length + payload_length
        ]
        if ((sum(ay_state) + sum(payload)) & 0xFFFF) != checksum:
            raise ValueError(f"packet {index} checksum mismatch")
        if flags & 1:
            state = payload
        else:
            state = decode_zero_literal_rle(payload, state)
        if state != expected_states[index]:
            raise ValueError(f"packet {index} reference decode mismatch")
        offset += sectors * base.SECTOR_SIZE
    if offset != len(video):
        raise ValueError("trailing bytes after final packet")


def write_contact_sheet(path: Path, states: list[bytes]) -> None:
    indices = np.linspace(0, len(states) - 1, 6, dtype=int)
    sheet = Image.new("RGB", (base.WIDTH * 3, base.HEIGHT * 2), "black")
    for position, index in enumerate(indices):
        bitmap, attrs = expand_compact_screen(states[int(index)])
        rendered = base.render_spectrum_screen(bitmap, attrs)
        sheet.paste(
            Image.fromarray(rendered),
            ((position % 3) * base.WIDTH, (position // 3) * base.HEIGHT),
        )
    sheet.save(path)


def write_ay_preview(
    path: Path,
    frames: list[AyFrame],
    update_rate: float,
    sample_rate: int = 44_100,
) -> None:
    """Render a listening preview of the three AY square-wave voices."""
    samples_per_frame = sample_rate / update_rate
    total_samples = round(len(frames) * samples_per_frame)
    output = np.empty(total_samples, dtype=np.float64)
    phases = np.zeros(3, dtype=np.float64)
    frame_index = 0
    next_boundary = samples_per_frame
    for sample_index in range(total_samples):
        while sample_index >= next_boundary and frame_index + 1 < len(frames):
            frame_index += 1
            next_boundary = (frame_index + 1) * samples_per_frame
        frame = frames[frame_index]
        mixed = 0.0
        for voice in range(3):
            frequency = AY_CLOCK_HZ / (16.0 * frame.periods[voice])
            phases[voice] = (phases[voice] + frequency / sample_rate) % 1.0
            level = frame.volumes[voice] / 15.0
            mixed += (1.0 if phases[voice] < 0.5 else -1.0) * level
        output[sample_index] = mixed / 4.0
    pcm = np.clip(np.rint(output * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def mux_ay_preview(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    frame_rate: float,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is not available")
    rate = Fraction(frame_rate).limit_denominator(1000)
    rate_text = f"{rate.numerator}/{rate.denominator}"
    completed = subprocess.run(
        [
            ffmpeg,
            "-v", "error",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-vf", f"setpts=N*{rate.denominator}/({rate.numerator}*TB)",
            "-r", rate_text,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-y", str(output_path),
        ],
        check=False,
    )
    if completed.returncode:
        raise RuntimeError("could not create AY listening preview")


def parse_rate(value: str) -> float:
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            return float(Fraction(int(numerator), int(denominator)))
        return float(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise argparse.ArgumentTypeError(
            "rate must be a number or fraction such as 25/3"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-video", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "build_long")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument(
        "--fps",
        type=parse_rate,
        default=parse_rate("25/3"),
        help="source frames encoded per second",
    )
    parser.add_argument(
        "--timing-fps",
        type=parse_rate,
        default=parse_rate("25/3"),
        help=(
            "presentation rate tied to the 50 Hz screen; 25/3 means "
            "one completed frame every six fields"
        ),
    )
    parser.add_argument("--attr-change-penalty", type=int, default=100_000)
    parser.add_argument(
        "--black-percentile",
        type=float,
        default=3.0,
        help="clip luminance below this adaptive-window percentile",
    )
    parser.add_argument(
        "--white-percentile",
        type=float,
        default=97.0,
        help="clip luminance above this adaptive-window percentile",
    )
    parser.add_argument(
        "--tone-window-seconds",
        type=float,
        default=4.0,
        help="centred window for smoothly adaptive luminance groups",
    )
    parser.add_argument(
        "--dither",
        choices=("none", "ordered4", "ordered8"),
        default="ordered4",
        help="spatial halftone matrix; does not use temporal A/B flicker",
    )
    args = parser.parse_args()
    if not args.input_video.is_file():
        parser.error(f"input video does not exist: {args.input_video}")
    if args.start < 0 or args.duration <= 0:
        parser.error("start must be non-negative and duration positive")
    if not 1 <= args.fps <= 25:
        parser.error("fps must be in 1..25")
    if not 1.0 <= args.timing_fps <= 25.0:
        parser.error("timing-fps must be in 1..25")
    if (
        not float(args.timing_fps).is_integer()
        and not math.isclose(
            50.0 / args.timing_fps, round(50.0 / args.timing_fps)
        )
    ):
        parser.error(
            "timing-fps must map to a whole number of 50 Hz fields"
        )
    if not 0.0 <= args.black_percentile < args.white_percentile <= 100.0:
        parser.error(
            "percentiles must satisfy 0 <= black < white <= 100"
        )
    if args.tone_window_seconds <= 0.0:
        parser.error("tone-window-seconds must be positive")

    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    dithered = args.dither != "none"
    preview_path = out / (
        "big_buck_bunny_zx_dithered_preview.mp4"
        if dithered
        else "big_buck_bunny_zx_preview.mp4"
    )
    reframe_windows, reframe_stats = analyse_motion_reframe(
        args.input_video,
        args.start,
        args.duration,
        args.fps,
    )
    tone_ranges = analyse_tone_ranges(
        args.input_video,
        args.start,
        args.duration,
        args.fps,
        args.black_percentile,
        args.white_percentile,
        args.tone_window_seconds,
        reframe_windows,
    )
    ay_frames, ay_stats = analyse_ay_frames(
        args.input_video,
        args.start,
        args.duration,
        args.fps,
    )
    ay_stats["update_rate_hz"] = args.timing_fps
    video, packets, states, stats = build_video(
        args.input_video,
        args.start,
        args.duration,
        args.fps,
        args.timing_fps,
        tone_ranges,
        ay_frames,
        reframe_windows,
        args.attr_change_penalty,
        args.dither,
        preview_path,
    )
    verify_video(video, states)
    ay_preview_path = out / "big_buck_bunny_zx_ay_preview.wav"
    ay_muxed_preview_path = out / "big_buck_bunny_zx_dithered_ay_preview.mp4"
    write_ay_preview(ay_preview_path, ay_frames, args.timing_fps)
    mux_ay_preview(
        preview_path,
        ay_preview_path,
        ay_muxed_preview_path,
        args.timing_fps,
    )

    boot = streaming.build_boot_basic()
    provisional, _ = build_player(0, 0, args.timing_fps)
    preceding = [
        base.TrdFile(
            "boot",
            "B",
            boot,
            basic_variables_offset=len(boot),
            autostart_line=10,
        ),
        base.TrdFile("PLAYER", "C", provisional, start=LOAD_ADDRESS),
    ]
    video_track, video_sector = streaming.calculate_file_start(preceding)
    player, labels = build_player(video_track, video_sector, args.timing_fps)
    if len(player) != len(provisional):
        raise AssertionError("player size changed after embedding disk location")

    boot_sectors = math.ceil((len(boot) + 4) / base.SECTOR_SIZE)
    player_sectors = math.ceil(len(player) / base.SECTOR_SIZE)
    max_video_sectors = TRD_DATA_SECTORS - boot_sectors - player_sectors
    volumes = split_video_volumes(
        states,
        packets,
        args.fps,
        args.timing_fps,
        max_video_sectors,
    )
    video_chunk_bytes = MAX_TRDOS_FILE_SECTORS * base.SECTOR_SIZE
    volume_metadata: list[dict[str, object]] = []
    total_chunks = 0
    total_volume_bytes = 0
    stem = (
        "big_buck_bunny_2min_zx_motion_crop_colour_ay_dithered"
        if dithered
        else "big_buck_bunny_2min_zx_motion_crop_colour_ay"
    )
    for volume_index, (
        frame_start,
        frame_end,
        volume_video,
        volume_packets,
    ) in enumerate(volumes, start=1):
        verify_video(volume_video, states[frame_start:frame_end])
        video_chunks = [
            volume_video[offset:offset + video_chunk_bytes]
            for offset in range(0, len(volume_video), video_chunk_bytes)
        ]
        files = [
            base.TrdFile(
                "boot",
                "B",
                boot,
                basic_variables_offset=len(boot),
                autostart_line=10,
            ),
            base.TrdFile("PLAYER", "C", player, start=LOAD_ADDRESS),
        ]
        files.extend(
            base.TrdFile(f"VIDEO{index:03d}", "C", chunk, start=0)
            for index, chunk in enumerate(video_chunks)
        )
        trd, directory, trd_stats = streaming.place_files(
            files, f"BBN{volume_index:02d}"
        )
        trd_name = f"{stem}_part{volume_index:02d}.trd"
        (out / trd_name).write_bytes(trd)
        (out / f"VIDEO_part{volume_index:02d}.C.bin").write_bytes(
            volume_video
        )
        total_chunks += len(video_chunks)
        total_volume_bytes += len(volume_video)
        volume_metadata.append(
            {
                "index": volume_index,
                "trd_name": trd_name,
                "frame_start": frame_start,
                "frame_end": frame_end,
                "frames": frame_end - frame_start,
                "source_start_seconds": args.start + frame_start / args.fps,
                "source_end_seconds": args.start + frame_end / args.fps,
                "video_bytes": len(volume_video),
                "video_sectors": len(volume_video) // base.SECTOR_SIZE,
                "packet_sectors": sum(
                    packet.sectors for packet in volume_packets
                ),
                "video_chunks": len(video_chunks),
                "directory": directory,
                "trd_stats": trd_stats,
            }
        )

    (out / "PLAYER.C.bin").write_bytes(player)
    (out / "VIDEO_full.C.bin").write_bytes(video)
    contact_name = (
        "big_buck_bunny_zx_dithered_contact_sheet.png"
        if dithered
        else "big_buck_bunny_zx_contact_sheet.png"
    )
    write_contact_sheet(out / contact_name, states)

    packet_sectors = stats["packet_sectors"]
    assert isinstance(packet_sectors, list)
    middle_tone = tone_ranges[len(tone_ranges) // 2]
    volume_lines = "\n".join(
        (
            f"  - part {entry['index']:02d}: frames "
            f"{entry['frame_start']}..{int(entry['frame_end']) - 1}, "
            f"{entry['source_start_seconds']:.3f}.."
            f"{entry['source_end_seconds']:.3f} s, "
            f"{entry['video_sectors']} sectors"
        )
        for entry in volume_metadata
    )
    report = f"""# Big Buck Bunny — ZX player-side native-dither profile

- Source: {args.input_video}
- Source interval: {args.start:.3f}..{args.start + args.duration:.3f} s
- Encoded frames: {stats['frames']}
- Encoded source rate: {args.fps:g} fps (25/3 profile)
- Screen scheduler: {args.timing_fps:g} fps
  ({50 / args.timing_fps:g} fields per completed frame)
- Encoded source duration: {stats['duration_seconds']:.3f} s
- Ideal screen duration: {stats['frames'] / args.timing_fps:.3f} s
- Stored brightness image: 128x96, four levels (2 bits per pixel)
- Player output: native 256x192 one-dot 2x2 patterns
- Motion-aware reframe: centre x {reframe_stats['center_x_min']:.3f}..{reframe_stats['center_x_max']:.3f}, y {reframe_stats['center_y_min']:.3f}..{reframe_stats['center_y_max']:.3f}
- Motion-aware zoom: {reframe_stats['zoom_min']:.2f}..{reframe_stats['zoom_max']:.2f}x (mean {reframe_stats['zoom_mean']:.2f}x)
- Motion-aware virtual-shot changes: {int(reframe_stats['changes'])}
- Colour attributes: native 32x24 Spectrum cells (768 bytes)
- Attribute search: all {stats['colour_candidates']} legal oriented INK/PAPER pairs; {stats['distinct_attributes']} used
- Adaptive tone window: {args.tone_window_seconds:g} s, P{args.black_percentile:g}..P{args.white_percentile:g}
- Linear black-point range: {min(t.black_point for t in tone_ranges):.5f}..{max(t.black_point for t in tone_ranges):.5f}
- Linear white-point range: {min(t.white_point for t in tone_ranges):.5f}..{max(t.white_point for t in tone_ranges):.5f}
- Middle-frame Lloyd-Max thresholds: {', '.join(f'{value:.5f}' for value in middle_tone.thresholds)}
- Spatial dithering: {args.dither}
- Screen presentation: bank 5/7 double buffer, one flip per logical frame
- 50 Hz temporal A/B flicker: disabled
- Audio: three note-quantised AY-3-8912/YM2149F tone voices
- AY update rate: {args.timing_fps:g} Hz; distinct selected notes: {ay_stats['distinct_notes']}
- AY active-frame ratio: {ay_stats['active_frame_ratio']:.1%}
- AY source loudness anchors: {ay_stats['source_quiet_dbfs']:.1f}..{ay_stats['source_loud_dbfs']:.1f} dBFS
- AY master volume: {ay_stats['master_volume_min']}..{ay_stats['master_volume_max']} (mean {ay_stats['master_volume_mean']:.2f})
- Unsplit encoded stream: {stats['video_bytes']} bytes, {stats['video_sectors']} sectors
- Bootable TRD volumes: {len(volume_metadata)}
- Total volume payload: {total_volume_bytes} bytes
- TR-DOS stream chunks: {total_chunks} files of at most {MAX_TRDOS_FILE_SECTORS} sectors
- Packet sectors: {min(packet_sectors)}..{max(packet_sectors)}, mean {sum(packet_sectors) / len(packet_sectors):.2f}
- Raw packets: {stats['raw_packets']}
- RLE delta packets: {stats['delta_packets']}
- Player: {len(player)} bytes
- Host reference decode: all frames exact

Volumes:
{volume_lines}

The visible screen remains stable while the next packet is loaded. The player
uses the standard TR-DOS 3D13h sector API, so a mechanical drive or
cycle-accurate emulator may still lengthen an occasional frame at a track
boundary.
"""
    (out / "README.md").write_text(report, encoding="utf-8")
    metadata = {
        "player_labels": labels,
        "video_track": video_track,
        "video_sector": video_sector,
        "trd_names": [entry["trd_name"] for entry in volume_metadata],
        "volumes": volume_metadata,
        "video_chunks": total_chunks,
        "stats": stats,
        "timing_fps": args.timing_fps,
        "tone_window_seconds": args.tone_window_seconds,
        "ay": ay_stats,
        "motion_reframe": reframe_stats,
        "source": {
            "path": str(args.input_video),
            "start_seconds": args.start,
            "requested_duration_seconds": args.duration,
        },
        "format": {
            "magic": VIDEO_MAGIC.decode("ascii"),
            "version": VIDEO_VERSION,
            "logical_width": LOGICAL_WIDTH,
            "logical_height": LOGICAL_HEIGHT,
            "brightness_bits_per_pixel": 2,
            "brightness_levels": 4,
            "attribute_columns": ATTR_COLS,
            "attribute_rows": ATTR_ROWS,
            "player_output_width": base.WIDTH,
            "player_output_height": base.HEIGHT,
            "state_bytes": STATE_BYTES,
            "ay_state_bytes": AY_STATE_BYTES,
        },
    }
    (out / "build_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(report)


if __name__ == "__main__":
    main()
