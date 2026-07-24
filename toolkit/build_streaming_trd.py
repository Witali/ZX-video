#!/usr/bin/env python3
"""Build a streaming temporal-dither TRD video for ZX Spectrum 128.

The TRD contains:
  boot.B    BASIC autoloader
  PLAYER.C  resident Z80 player at 6000h
  VIDEO.C   sector-streamed video data

The player keeps bank 5 and bank 7 as phase A/B screens. VIDEO.C begins with a
header sector, two raw 6912-byte key screens, and a circular list of variable
sector packets. Each packet carries delta updates for the next A/B pair.

During the hold time of the current pair the next packet is read one sector at
a time through the version-stable TR-DOS entry point 3D13h, function 05. This
keeps the 50 Hz screen alternation responsive on emulators, Gotek and SD-backed
Beta Disk implementations. A real mechanical drive may still add visible
jitter because TR-DOS sector reads are blocking.
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Import the already-tested image conversion, TRD writer and tiny assembler.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_zxv_trd as base  # noqa: E402

LOAD_ADDRESS = 0x6000
BUFFER0 = 0x8000
BUFFER1 = 0xA000
BUFFER_BYTES = 0x2000
PAGING_ROM48_BANK7 = 0x17
MAX_PACKET_SECTORS = BUFFER_BYTES // base.SECTOR_SIZE
VIDEO_MAGIC = b"ZXVS"
VIDEO_VERSION = 1
VIDEO_HEADER_SECTORS = 1
RAW_SCREEN_SECTORS = base.SCREEN_BYTES // base.SECTOR_SIZE  # 27 exactly
PACKET_HEADER_BYTES = 8
DEFAULT_INITIAL_HOLD_PAIRS = 4
DEFAULT_BASE_HOLD_PAIRS = 4


def compact_demo_frames(frame_count: int) -> list[np.ndarray]:
    """Generate source animation designed for a sector-streaming stress test.

    Motion is mostly aligned to 4/8-pixel boundaries so the delta stream remains
    compact, but antialiasing and a soft grayscale ramp still exercise temporal
    dithering and attribute selection.
    """
    frames: list[np.ndarray] = []
    scale = 2
    font = ImageFont.load_default()
    for n in range(frame_count):
        phase = n / frame_count
        img = Image.new("RGB", (base.WIDTH * scale, base.HEIGHT * scale), "white")
        d = ImageDraw.Draw(img, "RGBA")

        # Stable pale grid and title.
        for x in range(0, base.WIDTH * scale, 32 * scale):
            d.line((x, 0, x, base.HEIGHT * scale), fill=(220, 225, 235, 110), width=1)
        for y in range(0, base.HEIGHT * scale, 24 * scale):
            d.line((0, y, base.WIDTH * scale, y), fill=(220, 225, 235, 110), width=1)
        d.text((8 * scale, 7 * scale), "ZXV STREAMING TRD", fill=(20, 20, 20, 255), font=font)

        # Blue disc moves in 8-pixel steps.
        step_x = (n * 8) % 176
        cx = (40 + step_x) * scale
        cy = (56 + 8 * int(round(math.sin(2 * math.pi * phase)))) * scale
        r = 20 * scale
        d.ellipse((cx-r+6, cy-r+7, cx+r+6, cy+r+7), fill=(30, 30, 30, 45))
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(45, 125, 235, 235), outline=(0, 45, 130, 255), width=3*scale)

        # Red rectangle moves in the opposite direction, aligned to cells.
        rx = (200 - (n * 8) % 152) * scale
        ry = (112 + 8 * ((n // 3) & 1)) * scale
        d.rounded_rectangle((rx, ry, rx+40*scale, ry+24*scale), radius=5*scale,
                            fill=(235, 65, 60, 220), outline=(125, 0, 0, 255), width=2*scale)

        # Green diamond changes position less often.
        gx = (112 + 8 * ((n // 2) % 5)) * scale
        gy = (92 + 8 * ((n // 4) & 1)) * scale
        rr = 22 * scale
        d.polygon([(gx, gy-rr), (gx+rr, gy), (gx, gy+rr), (gx-rr, gy)],
                  fill=(70, 205, 95, 170), outline=(0, 100, 20, 255))

        # Static grayscale ramp demonstrates A/B temporal levels.
        x0 = 16 * scale
        y0 = 166 * scale
        for x in range(160 * scale):
            v = int(255 * x / max(1, 160 * scale - 1))
            d.line((x0+x, y0, x0+x, y0+12*scale), fill=(v, v, v, 255))
        d.text((190 * scale, 170 * scale), f"{n:02d}", fill=(20, 20, 20, 255), font=font)

        img = img.resize((base.WIDTH, base.HEIGHT), Image.Resampling.LANCZOS)
        frames.append(np.asarray(img, dtype=np.uint8))
    return frames


def encode_delta_compact(previous: tuple[bytes, bytes], current: tuple[bytes, bytes]) -> tuple[bytes, int]:
    """Encode a phase delta with the original screen-offset record structure.

    Record:
      u16 bitmap row-0 offset
      u8  changed-row mask
      changed row bytes
      u8  attribute changed flag
      if set: u16 attribute offset, u8 attribute
    """
    return base.encode_phase(previous, current)


@dataclass
class Packet:
    delta_a: bytes
    delta_b: bytes
    sector_count: int
    hold_pairs: int = DEFAULT_BASE_HOLD_PAIRS

    def serialize(self) -> bytes:
        body = bytearray(PACKET_HEADER_BYTES)
        body[0] = self.sector_count
        body[1] = self.hold_pairs
        struct.pack_into("<H", body, 2, len(self.delta_a))
        struct.pack_into("<H", body, 4, len(self.delta_b))
        checksum = (sum(self.delta_a) + sum(self.delta_b) + self.hold_pairs) & 0xFFFF
        struct.pack_into("<H", body, 6, checksum)
        body += self.delta_a
        body += self.delta_b
        expected = self.sector_count * base.SECTOR_SIZE
        if len(body) > expected:
            raise ValueError("packet size exceeds allocated sectors")
        body += bytes(expected - len(body))
        return bytes(body)


def build_video_stream(phases: Sequence[tuple[bytes, bytes, bytes]], base_hold_pairs: int) -> tuple[bytes, list[Packet], dict[str, object]]:
    if len(phases) < 2:
        raise ValueError("at least two source frames are required")

    # Initial raw A/B screens.
    first_a = phases[0][0] + phases[0][2]
    first_b = phases[0][1] + phases[0][2]
    assert len(first_a) == base.SCREEN_BYTES and len(first_b) == base.SCREEN_BYTES

    packets: list[Packet] = []
    changed_stats: list[tuple[int, int]] = []
    for i in range(len(phases)):
        j = (i + 1) % len(phases)
        prev_a = (phases[i][0], phases[i][2])
        prev_b = (phases[i][1], phases[i][2])
        next_a = (phases[j][0], phases[j][2])
        next_b = (phases[j][1], phases[j][2])
        delta_a, changed_a = encode_delta_compact(prev_a, next_a)
        delta_b, changed_b = encode_delta_compact(prev_b, next_b)
        raw_len = PACKET_HEADER_BYTES + len(delta_a) + len(delta_b)
        sectors = math.ceil(raw_len / base.SECTOR_SIZE)
        if sectors < 1 or sectors > MAX_PACKET_SECTORS:
            raise ValueError(f"packet {i} requires {sectors} sectors; max is {MAX_PACKET_SECTORS}")
        packets.append(Packet(delta_a, delta_b, sectors, base_hold_pairs))
        changed_stats.append((changed_a, changed_b))

    # Packet n must provide enough fields to prefetch packet n+1 one sector per field.
    for i, packet in enumerate(packets):
        next_sectors = packets[(i + 1) % len(packets)].sector_count
        packet.hold_pairs = max(base_hold_pairs, 1 + math.ceil(next_sectors / 2))

    header = bytearray(base.SECTOR_SIZE)
    header[0:4] = VIDEO_MAGIC
    header[4] = VIDEO_VERSION
    header[5] = 0
    header[6] = DEFAULT_INITIAL_HOLD_PAIRS
    header[7] = MAX_PACKET_SECTORS
    header[8] = len(packets) & 0xFF
    header[9] = 0
    struct.pack_into("<H", header, 10, len(phases))
    header[12] = RAW_SCREEN_SECTORS
    header[13] = RAW_SCREEN_SECTORS
    header[14] = VIDEO_HEADER_SECTORS + 2 * RAW_SCREEN_SECTORS
    header[15] = base_hold_pairs
    header[16:24] = b"ZXVSTRM1"

    stream = bytes(header) + first_a + first_b + b"".join(packet.serialize() for packet in packets)
    assert len(first_a) % base.SECTOR_SIZE == 0
    assert len(first_b) % base.SECTOR_SIZE == 0
    assert len(stream) % base.SECTOR_SIZE == 0

    stats = {
        "packet_sectors": [p.sector_count for p in packets],
        "hold_pairs": [p.hold_pairs for p in packets],
        "changed_cells": changed_stats,
        "video_sectors": len(stream) // base.SECTOR_SIZE,
        "video_bytes": len(stream),
        "duration_seconds": sum(p.hold_pairs for p in packets) / 25.0,
    }
    return stream, packets, stats


def emit_ld_a_mem(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x3A, label)


def emit_ld_mem_a(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x32, label)


def emit_ld_hl_mem(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x2A, label)


def emit_ld_mem_hl(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x22, label)


def emit_call_abs(a: base.MiniAssembler, address: int) -> None:
    a.emit(0xCD); a.word(address)


def build_streaming_player(
    video_track: int,
    video_sector: int,
    *,
    swap_screens: bool = True,
) -> tuple[bytes, dict[str, int], str]:
    """Emit the resident Z80 player.

    The code calls the stable TR-DOS dispatcher at 3D13h with C=05 to read
    logical sectors. D=logical track, E=0-based sector, B=count, HL=destination.
    """
    a = base.MiniAssembler(LOAD_ADDRESS)

    # ------------------------------------------------------------------ startup
    a.label("start")
    a.emit(0xF3)                          # DI
    a.emit(0x31); a.word(0x5FF0)          # LD SP,5FF0
    a.emit(0xAF, 0xD3, 0xFE)              # border black
    a.emit(0xAF); emit_ld_mem_a(a, "screen_flag")
    a.emit(0x3E, video_track); emit_ld_mem_a(a, "disk_track")
    a.emit(0x3E, video_sector); emit_ld_mem_a(a, "disk_sector")
    # Keep bit 4 set so an instruction fetch at 3D13h can page in Beta
    # Disk/TR-DOS. 07h selects the 128K editor ROM and makes the dispatcher
    # call fall through into the wrong ROM on real 128K-compatible hardware.
    a.emit(0x3E, PAGING_ROM48_BANK7); a.emit(0x01); a.word(0x7FFD); a.emit(0xED, 0x79)

    # Header sector -> BUFFER0.
    a.emit(0x21); a.word(BUFFER0)
    a.emit(0x06, 1)
    a.abs16(0xCD, "read_n")
    # Verify 'Z','X','V','S'.
    for off, value in enumerate(VIDEO_MAGIC):
        a.emit(0x3A); a.word(BUFFER0 + off)
        a.emit(0xFE, value)
        a.abs16(0xC2, "fatal")            # JP NZ
    a.emit(0x3A); a.word(BUFFER0 + 4)
    a.emit(0xFE, VIDEO_VERSION)
    a.abs16(0xC2, "fatal")
    a.emit(0x3A); a.word(BUFFER0 + 6); emit_ld_mem_a(a, "initial_hold")
    a.emit(0x3A); a.word(BUFFER0 + 8); emit_ld_mem_a(a, "packet_count")
    emit_ld_mem_a(a, "packet_remaining")

    # Read raw phase A to bank 5 screen at 4000h.
    a.emit(0x21); a.word(0x4000)
    a.emit(0x06, RAW_SCREEN_SECTORS)
    a.abs16(0xCD, "read_n")
    # Read raw phase B to bank 7 mapped at C000h.
    a.emit(0x3E, PAGING_ROM48_BANK7); a.emit(0x01); a.word(0x7FFD); a.emit(0xED, 0x79)
    a.emit(0x21); a.word(0xC000)
    a.emit(0x06, RAW_SCREEN_SECTORS)
    a.abs16(0xCD, "read_n")

    # Remember circular packet start.
    emit_ld_a_mem(a, "disk_track"); emit_ld_mem_a(a, "packet_start_track")
    emit_ld_a_mem(a, "disk_sector"); emit_ld_mem_a(a, "packet_start_sector")

    # Load first packet completely into BUFFER0.
    a.emit(0x21); a.word(BUFFER0)
    a.emit(0x06, 1)
    a.abs16(0xCD, "read_n")
    a.emit(0x3A); a.word(BUFFER0)
    a.emit(0xFE, 1)
    a.rel8(0x28, "first_packet_ready")
    a.emit(0x3D)                           # DEC A
    a.emit(0x47)                           # LD B,A
    a.emit(0x21); a.word(BUFFER0 + 0x100)
    a.abs16(0xCD, "read_n")
    a.label("first_packet_ready")

    a.emit(0x21); a.word(BUFFER0); emit_ld_mem_hl(a, "current_buffer")
    a.emit(0x21); a.word(BUFFER1); emit_ld_mem_hl(a, "next_buffer")
    a.emit(0xAF); emit_ld_mem_a(a, "screen_flag")
    a.emit(0x3E, PAGING_ROM48_BANK7); a.emit(0x01); a.word(0x7FFD); a.emit(0xED, 0x79)

    # Hold the initial A/B pair before first transition.
    emit_ld_a_mem(a, "initial_hold")
    a.emit(0x87)                           # ADD A,A -> fields
    a.emit(0x47)                           # LD B,A
    a.label("initial_hold_loop")
    a.emit(0x78, 0xB7)
    a.rel8(0x28, "main_loop")
    a.emit(0xC5)
    a.abs16(0xCD, "wait_swap")
    a.emit(0xC1)
    a.rel8(0x10, "initial_hold_loop")

    # ------------------------------------------------------------ apply packet
    a.label("main_loop")
    emit_ld_hl_mem(a, "current_buffer")
    a.emit(0x23)                           # +1 hold pairs
    a.emit(0x7E); emit_ld_mem_a(a, "hold_pairs")
    a.emit(0x23)                           # +2 lenA low
    a.emit(0x5E, 0x23, 0x56)               # DE=lenA
    emit_ld_hl_mem(a, "current_buffer")
    a.emit(0x01); a.word(PACKET_HEADER_BYTES)
    a.emit(0x09)                           # ADD HL,BC -> phase A
    a.emit(0xE5)                           # save phase A pointer
    a.emit(0x19)                           # ADD HL,DE -> phase B
    a.emit(0x3E, 0xC0)
    a.abs16(0xCD, "decode_phase")          # hidden bank7 while A visible
    a.abs16(0xCD, "wait_swap")             # show B
    a.emit(0xE1)                           # phase A pointer
    a.emit(0x3E, 0x40)
    a.abs16(0xCD, "decode_phase")          # hidden bank5
    a.abs16(0xCD, "wait_swap")             # show A

    # Circular packet counter and disk pointer reset before prefetch.
    emit_ld_a_mem(a, "packet_remaining")
    a.emit(0x3D); emit_ld_mem_a(a, "packet_remaining")
    a.rel8(0x20, "packet_counter_ok")
    emit_ld_a_mem(a, "packet_count"); emit_ld_mem_a(a, "packet_remaining")
    emit_ld_a_mem(a, "packet_start_track"); emit_ld_mem_a(a, "disk_track")
    emit_ld_a_mem(a, "packet_start_sector"); emit_ld_mem_a(a, "disk_sector")
    a.label("packet_counter_ok")

    # Initialize inactive-buffer prefetch.
    a.emit(0xAF); emit_ld_mem_a(a, "next_loaded")
    a.emit(0x3E, 1); emit_ld_mem_a(a, "next_required")
    emit_ld_hl_mem(a, "next_buffer"); emit_ld_mem_hl(a, "prefetch_ptr")

    # Minimum hold fields = 2*(holdPairs-1). One sector may be read each field.
    emit_ld_a_mem(a, "hold_pairs")
    a.emit(0x3D, 0x87, 0x47)               # DEC A / ADD A,A / LD B,A
    a.label("hold_field_loop")
    a.emit(0x78, 0xB7)
    a.rel8(0x28, "prefetch_ready_check")
    a.emit(0xC5)
    a.abs16(0xCD, "wait_swap")
    a.abs16(0xCD, "prefetch_one")
    a.emit(0xC1)
    a.rel8(0x10, "hold_field_loop")

    # If disk was slower or packet larger, stretch playback but keep A/B swapping.
    a.label("prefetch_ready_check")
    emit_ld_a_mem(a, "next_loaded"); a.emit(0x47)
    emit_ld_a_mem(a, "next_required"); a.emit(0xB8)  # CP B
    a.rel8(0x28, "prefetch_complete")
    a.abs16(0xCD, "wait_swap")
    a.abs16(0xCD, "prefetch_one")
    a.abs16(0xC3, "prefetch_ready_check")

    a.label("prefetch_complete")
    # Main packet application expects phase A visible.
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xB7)
    a.rel8(0x28, "screen_a_ready")
    a.abs16(0xCD, "wait_swap")
    a.label("screen_a_ready")

    # Swap current/next buffer pointers.
    emit_ld_hl_mem(a, "current_buffer")
    a.emit(0xD5)                           # PUSH DE (caller irrelevant, symmetry)
    a.emit(0xED, 0x5B)                     # LD DE,(nn)
    fixup_pos = len(a.code)
    a.emit(0, 0)
    a.abs_fixups.append((fixup_pos, "next_buffer"))
    a.emit(0xEB)                           # EX DE,HL -> HL=next
    emit_ld_mem_hl(a, "current_buffer")
    a.emit(0xEB)                           # HL=old current
    emit_ld_mem_hl(a, "next_buffer")
    a.emit(0xD1)
    a.abs16(0xC3, "main_loop")

    # -------------------------------------------------------------- wait/swap
    a.label("wait_swap")
    a.emit(0xFB, 0x76, 0xF3)               # EI / HALT / DI
    if swap_screens:
        a.abs16(0xCD, "swap_screen")
    else:
        # Preserve all label addresses while keeping bank 5 permanently
        # visible. The three NOPs replace CALL swap_screen.
        a.emit(0x00, 0x00, 0x00)
    a.emit(0xC9)

    a.label("swap_screen")
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xEE, 0x08); emit_ld_mem_a(a, "screen_flag")
    a.emit(0xF6, PAGING_ROM48_BANK7)
    a.emit(0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79)
    a.emit(0xC9)

    # ----------------------------------------------------------- prefetch one
    a.label("prefetch_one")
    emit_ld_a_mem(a, "next_loaded"); a.emit(0x47)
    emit_ld_a_mem(a, "next_required"); a.emit(0xB8)
    a.emit(0xC8)                           # RET Z
    emit_ld_hl_mem(a, "prefetch_ptr")
    a.emit(0x06, 1)
    a.abs16(0xCD, "read_n")
    emit_ld_hl_mem(a, "prefetch_ptr")
    a.emit(0x24)                           # INC H (+256)
    emit_ld_mem_hl(a, "prefetch_ptr")
    emit_ld_a_mem(a, "next_loaded")
    a.emit(0x3C); emit_ld_mem_a(a, "next_loaded")
    a.emit(0xFE, 1)
    a.emit(0xC0)                           # RET NZ
    emit_ld_hl_mem(a, "next_buffer")
    a.emit(0x7E); emit_ld_mem_a(a, "next_required")
    a.emit(0xC9)

    # ------------------------------------------------------------ read sectors
    # Input B=count, HL=destination. Uses standard TR-DOS 3D13h function 05.
    a.label("read_n")
    a.emit(0x78); emit_ld_mem_a(a, "read_count")
    emit_ld_a_mem(a, "disk_track"); a.emit(0x57)
    emit_ld_a_mem(a, "disk_sector"); a.emit(0x5F)
    a.emit(0x0E, 0x05)                     # LD C,5
    emit_call_abs(a, 0x3D13)
    a.emit(0xF3)                           # DI after DOS
    # Restore bank7 mapping and current visible page.
    emit_ld_a_mem(a, "screen_flag"); a.emit(0xF6, PAGING_ROM48_BANK7)
    a.emit(0x01); a.word(0x7FFD); a.emit(0xED, 0x79)
    emit_ld_a_mem(a, "read_count"); a.emit(0x47)
    a.label("advance_sector_loop")
    emit_ld_a_mem(a, "disk_sector")
    a.emit(0x3C, 0xFE, 16)
    a.rel8(0x38, "advance_store_sector")    # JR C
    a.emit(0xAF); emit_ld_mem_a(a, "disk_sector")
    emit_ld_a_mem(a, "disk_track"); a.emit(0x3C); emit_ld_mem_a(a, "disk_track")
    a.rel8(0x18, "advance_sector_next")
    a.label("advance_store_sector")
    emit_ld_mem_a(a, "disk_sector")
    a.label("advance_sector_next")
    a.rel8(0x10, "advance_sector_loop")
    a.emit(0xC9)

    # ------------------------------------------------------------- phase decode
    # A=screen base high byte (40h or C0h), HL=delta stream. Returns HL at end.
    a.label("decode_phase")
    emit_ld_mem_a(a, "base_hi")
    a.emit(0x4E, 0x23, 0x46, 0x23)         # count -> BC
    a.label("decode_loop")
    a.emit(0x78, 0xB1, 0xC8)               # RET if BC=0
    a.emit(0xC5)
    a.emit(0x5E, 0x23, 0x56, 0x23)         # bitmap offset DE
    emit_ld_a_mem(a, "base_hi")
    a.emit(0x82, 0x57)
    a.emit(0x4E, 0x23, 0x06, 0x08)
    a.label("decode_rows")
    a.emit(0xCB, 0x39)
    a.rel8(0x30, "decode_row_skip")
    a.emit(0x7E, 0x23, 0x12)
    a.label("decode_row_skip")
    a.emit(0x14)
    a.rel8(0x10, "decode_rows")
    a.emit(0x7E, 0x23, 0xB7)
    a.rel8(0x28, "decode_no_attr")
    a.emit(0x5E, 0x23, 0x56, 0x23)
    emit_ld_a_mem(a, "base_hi")
    a.emit(0x82, 0x57, 0x7E, 0x23, 0x12)
    a.label("decode_no_attr")
    a.emit(0xC1, 0x0B)
    a.rel8(0x18, "decode_loop")

    a.label("fatal")
    a.emit(0xF3, 0x3E, 0x02, 0xD3, 0xFE)
    a.rel8(0x18, "fatal")

    # ---------------------------------------------------------------- variables
    for name, size in [
        ("screen_flag", 1), ("disk_track", 1), ("disk_sector", 1),
        ("packet_start_track", 1), ("packet_start_sector", 1),
        ("packet_count", 1), ("packet_remaining", 1),
        ("initial_hold", 1), ("hold_pairs", 1),
        ("next_loaded", 1), ("next_required", 1), ("read_count", 1),
        ("base_hi", 1), ("current_buffer", 2), ("next_buffer", 2),
        ("prefetch_ptr", 2),
    ]:
        a.label(name)
        a.emit(*([0] * size))

    code = a.resolve()
    labels = a.labels

    screen_mode = "50 Hz A/B bank switching" if swap_screens else "fixed bank 5, no A/B switching"
    source = f"""; ZXV streaming temporal-dither player for ZX Spectrum 128
; Generated by build_streaming_trd.py
; Uses TR-DOS stable dispatcher 3D13h, function C=05.
; Screen mode: {screen_mode}.
;
; VIDEO.C starts at logical track {video_track}, sector {video_sector} (0-based).
; Bank 5 screen: 4000h, bank 7 shadow screen: C000h when page 7 selected.
; Packet buffers: 8000h and A000h, 8 KiB each.
;
        ORG 6000h
VIDEO_TRACK  EQU {video_track}
VIDEO_SECTOR EQU {video_sector}
BUFFER0      EQU 8000h
BUFFER1      EQU A000h
PORT7FFD     EQU 7FFDh
TRDOS        EQU 3D13h
ROM48_BANK7  EQU {PAGING_ROM48_BANK7:02X}h

; The complete emitted machine code is {len(code)} bytes.
; See ZXV_STREAMING_FORMAT_ru.md for packet layout and the Python builder for
; the exact generated instruction sequence.
"""
    return code, labels, source


def build_boot_basic() -> bytes:
    return base.build_boot_basic()


def place_files(files: list[base.TrdFile], label: str) -> tuple[bytes, list[dict[str, int | str]], dict[str, int]]:
    image = bytearray(base.TRD_SIZE)
    track, sector = base.DATA_START_TRACK, 0
    used = 0
    for index, file in enumerate(files):
        track, sector, sectors = base.add_trd_file(image, index, file, track, sector)
        used += sectors
    info = 8 * base.SECTOR_SIZE
    image[info] = 0
    image[info + 225] = sector
    image[info + 226] = track
    image[info + 227] = 0x16
    image[info + 228] = len(files)
    free = (base.LOGICAL_TRACKS - 1) * base.SECTORS_PER_TRACK - used
    image[info + 229:info + 231] = struct.pack("<H", free)
    image[info + 231] = 0x10
    image[info + 233:info + 242] = b" " * 9
    image[info + 245:info + 253] = label.encode("ascii", "replace")[:8].ljust(8, b" ")
    result = bytes(image)
    return result, base.parse_trd_directory(result), {
        "used_sectors": used, "free_sectors": free,
        "first_free_track": track, "first_free_sector": sector,
    }


def calculate_file_start(preceding: Sequence[base.TrdFile]) -> tuple[int, int]:
    absolute = base.DATA_START_TRACK * base.SECTORS_PER_TRACK
    for f in preceding:
        stored_len = len(f.data) + (4 if f.file_type == "B" else 0)
        absolute += math.ceil(stored_len / base.SECTOR_SIZE)
    return absolute // base.SECTORS_PER_TRACK, absolute % base.SECTORS_PER_TRACK


def decode_video_reference(video: bytes) -> list[tuple[bytes, bytes, bytes]]:
    if video[:4] != VIDEO_MAGIC or video[4] != VIDEO_VERSION:
        raise ValueError("invalid streaming video")
    packet_count = video[8]
    offset = base.SECTOR_SIZE
    screen_a = bytearray(video[offset:offset + base.SCREEN_BYTES]); offset += base.SCREEN_BYTES
    screen_b = bytearray(video[offset:offset + base.SCREEN_BYTES]); offset += base.SCREEN_BYTES
    state_a = (screen_a[:base.SCREEN_BITMAP_BYTES], screen_a[base.SCREEN_BITMAP_BYTES:])
    state_b = (screen_b[:base.SCREEN_BITMAP_BYTES], screen_b[base.SCREEN_BITMAP_BYTES:])
    outputs = [(bytes(state_a[0]), bytes(state_b[0]), bytes(state_a[1]))]

    def apply(delta: bytes, state: tuple[bytearray, bytearray]) -> None:
        p = 0
        count = struct.unpack_from("<H", delta, p)[0]; p += 2
        for _ in range(count):
            boff = struct.unpack_from("<H", delta, p)[0]; p += 2
            mask = delta[p]; p += 1
            x_cell = boff & 31
            y_cell = ((boff >> 8) & 0x18) | ((boff >> 5) & 7)
            idx = y_cell * 32 + x_cell
            current = bytearray(base.cell_bytes(state[0], state[1], idx))
            for row in range(8):
                if mask & (1 << row):
                    current[row] = delta[p]; p += 1
            attr = delta[p]; p += 1
            if attr:
                attr_off = struct.unpack_from("<H", delta, p)[0]; p += 2
                if attr_off != 0x1800 + idx:
                    raise ValueError("bad attribute offset")
                current[8] = delta[p]; p += 1
            base.set_cell_bytes(state[0], state[1], idx, current)
        if p != len(delta):
            raise ValueError(f"delta length mismatch {p} != {len(delta)}")

    for _ in range(packet_count):
        sectors = video[offset]
        if not 1 <= sectors <= MAX_PACKET_SECTORS:
            raise ValueError("bad packet sector count")
        packet = video[offset:offset + sectors * base.SECTOR_SIZE]
        len_a = struct.unpack_from("<H", packet, 2)[0]
        len_b = struct.unpack_from("<H", packet, 4)[0]
        delta_a = packet[8:8 + len_a]
        delta_b = packet[8 + len_a:8 + len_a + len_b]
        checksum = struct.unpack_from("<H", packet, 6)[0]
        if checksum != (sum(delta_a) + sum(delta_b) + packet[1]) & 0xFFFF:
            raise ValueError("packet checksum mismatch")
        apply(delta_b, state_b)
        apply(delta_a, state_a)
        if state_a[1] != state_b[1]:
            raise ValueError("phase attributes diverged")
        outputs.append((bytes(state_a[0]), bytes(state_b[0]), bytes(state_a[1])))
        offset += sectors * base.SECTOR_SIZE
    return outputs


def write_stream_preview(
    path: Path,
    decoded: Sequence[tuple[bytes, bytes, bytes]],
    packets: Sequence[Packet],
    initial_hold: int,
    *,
    swap_screens: bool,
) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 50, (base.WIDTH, base.HEIGHT))
    if not writer.isOpened():
        raise RuntimeError("cannot create preview")
    initial_a = base.render_spectrum_screen(decoded[0][0], decoded[0][2])
    initial_b = base.render_spectrum_screen(decoded[0][1], decoded[0][2])
    for _ in range(initial_hold):
        writer.write(cv2.cvtColor(initial_a, cv2.COLOR_RGB2BGR))
        visible = initial_b if swap_screens else initial_a
        writer.write(cv2.cvtColor(visible, cv2.COLOR_RGB2BGR))
    for i, packet in enumerate(packets):
        frame = decoded[i + 1]
        a = base.render_spectrum_screen(frame[0], frame[2])
        b = base.render_spectrum_screen(frame[1], frame[2])
        for _ in range(packet.hold_pairs):
            writer.write(cv2.cvtColor(a, cv2.COLOR_RGB2BGR))
            visible = b if swap_screens else a
            writer.write(cv2.cvtColor(visible, cv2.COLOR_RGB2BGR))
    writer.release()


def write_average_preview(path: Path, decoded: Sequence[tuple[bytes, bytes, bytes]], packets: Sequence[Packet], initial_hold: int) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (base.WIDTH, base.HEIGHT))
    if not writer.isOpened():
        raise RuntimeError("cannot create average preview")
    def avg(frame: tuple[bytes, bytes, bytes]) -> np.ndarray:
        a = base.render_spectrum_screen(frame[0], frame[2])
        b = base.render_spectrum_screen(frame[1], frame[2])
        return base.temporal_average(a, b)
    first = avg(decoded[0])
    for _ in range(initial_hold):
        writer.write(cv2.cvtColor(first, cv2.COLOR_RGB2BGR))
    for i, packet in enumerate(packets):
        image = avg(decoded[i + 1])
        for _ in range(packet.hold_pairs):
            writer.write(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    writer.release()


def write_contact_sheet(path: Path, sources: Sequence[np.ndarray], phases: Sequence[tuple[bytes, bytes, bytes]]) -> None:
    indices = np.linspace(0, len(sources) - 1, min(6, len(sources)), dtype=int)
    sheet = Image.new("RGB", (base.WIDTH * len(indices), base.HEIGHT * 3), "white")
    for col, idx in enumerate(indices):
        a = base.render_spectrum_screen(phases[idx][0], phases[idx][2])
        b = base.render_spectrum_screen(phases[idx][1], phases[idx][2])
        avg = base.temporal_average(a, b)
        sheet.paste(Image.fromarray(sources[idx]), (col * base.WIDTH, 0))
        sheet.paste(Image.fromarray(avg), (col * base.WIDTH, base.HEIGHT))
        sheet.paste(Image.fromarray(a), (col * base.WIDTH, base.HEIGHT * 2))
    sheet.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=HERE / "build_streaming")
    ap.add_argument("--frames", type=int, default=16)
    ap.add_argument("--base-hold-pairs", type=int, default=4)
    ap.add_argument("--input-video", type=Path)
    ap.add_argument(
        "--no-flicker",
        action="store_true",
        help="keep bank 5 visible instead of alternating A/B screens at 50 Hz",
    )
    args = ap.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    if args.input_video:
        sources = base.read_video_frames(args.input_video, args.frames, source_fps=6.25)
    else:
        sources = compact_demo_frames(args.frames)

    phases: list[tuple[bytes, bytes, bytes]] = []
    previous_attrs: np.ndarray | None = None
    total_error = 0.0
    for index, frame in enumerate(sources):
        bitmap_a, bitmap_b, attrs, error = base.convert_frame_to_phases(frame, previous_attrs)
        phases.append((bitmap_a, bitmap_b, attrs))
        previous_attrs = np.frombuffer(attrs, dtype=np.uint8).copy()
        total_error += error
        print(f"converted frame {index + 1}/{len(sources)}", flush=True)

    video, packets, stats = build_video_stream(phases, args.base_hold_pairs)

    boot = build_boot_basic()
    # Code size is independent of embedded two-byte disk location, so one provisional pass is enough.
    swap_screens = not args.no_flicker
    provisional_player, _, _ = build_streaming_player(
        0, 0, swap_screens=swap_screens
    )
    preceding = [
        base.TrdFile("boot", "B", boot, basic_variables_offset=len(boot), autostart_line=10),
        base.TrdFile("PLAYER", "C", provisional_player, start=LOAD_ADDRESS),
    ]
    video_track, video_sector = calculate_file_start(preceding)
    player, labels, asm_source = build_streaming_player(
        video_track, video_sector, swap_screens=swap_screens
    )
    if len(player) != len(provisional_player):
        raise AssertionError("player size changed after embedding VIDEO location")

    files = [
        base.TrdFile("boot", "B", boot, basic_variables_offset=len(boot), autostart_line=10),
        base.TrdFile("PLAYER", "C", player, start=LOAD_ADDRESS),
        base.TrdFile("VIDEO", "C", video, start=0),
    ]
    trd, directory, trd_stats = place_files(files, "ZXVSTRM")
    decoded = decode_video_reference(video)
    if len(decoded) != len(phases) + 1:
        raise AssertionError("reference decode count mismatch")
    # Every transition packet ends at the corresponding next source frame; final packet returns frame 0.
    for i in range(len(packets)):
        expected = phases[(i + 1) % len(phases)]
        actual = decoded[i + 1]
        if actual != expected:
            raise AssertionError(f"decoded packet {i} does not match expected phases")

    trd_name = (
        "zxv_streaming_128.trd"
        if swap_screens
        else "zxv_streaming_128_noflicker.trd"
    )
    preview_name = (
        "zxv_streaming_50hz_preview.mp4"
        if swap_screens
        else "zxv_streaming_noflicker_preview.mp4"
    )
    (out / trd_name).write_bytes(trd)
    (out / "PLAYER.C.bin").write_bytes(player)
    (out / "VIDEO.C.bin").write_bytes(video)
    (out / "streaming_player.asm").write_text(asm_source, encoding="utf-8")
    write_stream_preview(
        out / preview_name,
        decoded,
        packets,
        DEFAULT_INITIAL_HOLD_PAIRS,
        swap_screens=swap_screens,
    )
    write_average_preview(out / "zxv_streaming_temporal_average.mp4", decoded, packets, DEFAULT_INITIAL_HOLD_PAIRS)
    write_contact_sheet(out / "zxv_streaming_contact_sheet.png", sources, phases)

    changed = [v for pair in stats["changed_cells"] for v in pair]
    packet_sectors = stats["packet_sectors"]
    report = f"""# ZXV streaming TRD demo

- Source frames: {len(sources)}
- Screen mode: {"50 Hz A/B phase switching" if swap_screens else "fixed bank 5 (no A/B switching)"}
- A/B pair rate: 25 Hz
- Loop duration: {stats['duration_seconds']:.2f} s plus initial hold
- Player size: {len(player)} bytes
- VIDEO.C: {len(video)} bytes, {stats['video_sectors']} sectors
- Packet buffers: 2 × {BUFFER_BYTES // 1024} KiB
- Packet sector range: {min(packet_sectors)}..{max(packet_sectors)}
- Mean packet sectors: {sum(packet_sectors)/len(packet_sectors):.2f}
- Mean changed cells per phase: {sum(changed)/len(changed):.1f} of 768
- Maximum changed cells in a phase: {max(changed)}
- TRD used sectors: {trd_stats['used_sectors']}
- Reference decode: all {len(packets)} circular transitions match exactly

## Directory

"""
    for item in directory:
        report += f"- {item['name']}.{item['type']}: {item['length']} bytes, {item['sectors']} sectors, track {item['track']}, sector {item['sector']}\n"
    report += """

## Streaming model

The player reads VIDEO.C by logical TR-DOS sectors through the stable entry
point 3D13h, function 05. The current packet is decoded from one 8 KiB buffer;
one sector of the next packet is read into the other buffer after each display
field. If the packet is not ready by the nominal update time, playback
stretches the current frame instead of decoding incomplete data.

The implementation is intended first for emulators, Gotek and SD-backed Beta
Disk systems. A mechanical floppy can add visible 50 Hz jitter because the
standard TR-DOS sector routine is blocking and may incur rotational latency.
"""
    (out / "README.md").write_text(report, encoding="utf-8")

    metadata = {
        "player_labels": labels,
        "video_track": video_track,
        "video_sector": video_sector,
        "screen_swapping": swap_screens,
        "trd_name": trd_name,
        "directory": directory,
        "stats": stats,
    }
    import json
    (out / "build_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
