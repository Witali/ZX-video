#!/usr/bin/env python3
"""Build the short ZXV demo with all video preloaded into paged RAM.

The complete single-phase stream is loaded into RAM banks 0 and 1 before
playback starts. During playback the player never calls TR-DOS:

    paged-RAM stream -> fixed packet buffer -> hidden screen -> vblank flip

Bank 5 and bank 7 are ordinary double buffers. They are switched once per
logical frame, never at the 50 Hz A/B temporal-dither rate.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_streaming_trd as streaming  # noqa: E402
import build_zxv_trd as base  # noqa: E402


LOAD_ADDRESS = 0x6000
BUFFER = 0x8000
PACKET_HEADER_BYTES = 8
VIDEO_MAGIC = b"ZXVP"
VIDEO_VERSION = 1
VIDEO_HEADER_SECTORS = 1
RAW_SCREEN_SECTORS = base.SCREEN_BYTES // base.SECTOR_SIZE
PACKET_START_SECTOR = VIDEO_HEADER_SECTORS + RAW_SCREEN_SECTORS
PAGING_ROM48 = 0x10
RAM_BANKS = (0, 1)
PACKETS = 24
HOLD_FIELDS = 7


@dataclass
class Packet:
    delta: bytes
    sectors: int

    def serialize(self) -> bytes:
        output = bytearray(PACKET_HEADER_BYTES)
        output[0] = self.sectors
        output[1] = HOLD_FIELDS
        struct.pack_into("<H", output, 2, len(self.delta))
        struct.pack_into("<H", output, 4, sum(self.delta) & 0xFFFF)
        output += self.delta
        expected = self.sectors * base.SECTOR_SIZE
        if len(output) > expected:
            raise ValueError("packet exceeds sector allocation")
        output += bytes(expected - len(output))
        return bytes(output)


def build_single_phase_stream(
    phases: Sequence[tuple[bytes, bytes, bytes]],
) -> tuple[bytes, list[Packet], dict[str, object]]:
    if len(phases) != PACKETS:
        raise ValueError(f"expected exactly {PACKETS} frames")
    first = phases[0][0] + phases[0][2]
    packets: list[Packet] = []
    changed_cells: list[int] = []
    for index in range(len(phases)):
        next_index = (index + 1) % len(phases)
        previous = (phases[index][0], phases[index][2])
        current = (phases[next_index][0], phases[next_index][2])
        delta, changed = base.encode_phase(previous, current)
        sectors = math.ceil((PACKET_HEADER_BYTES + len(delta)) / base.SECTOR_SIZE)
        packets.append(Packet(delta, sectors))
        changed_cells.append(changed)

    header = bytearray(base.SECTOR_SIZE)
    header[:4] = VIDEO_MAGIC
    header[4] = VIDEO_VERSION
    header[5] = len(packets)
    header[6] = HOLD_FIELDS
    header[7] = len(RAM_BANKS)
    struct.pack_into("<H", header, 8, len(packets))
    header[10] = RAW_SCREEN_SECTORS
    header[11] = PACKET_START_SECTOR
    header[16:24] = b"ZXVPRE1 "
    video = bytes(header) + first + b"".join(packet.serialize() for packet in packets)
    if len(video) % base.SECTOR_SIZE:
        raise AssertionError("preloaded stream is not sector aligned")
    if len(video) > len(RAM_BANKS) * 0x4000:
        raise ValueError("single-phase stream does not fit RAM banks 0/1")
    stats: dict[str, object] = {
        "frames": len(phases),
        "hold_fields": HOLD_FIELDS,
        "nominal_fps": 50 / (HOLD_FIELDS + 3),
        "video_bytes": len(video),
        "video_sectors": len(video) // base.SECTOR_SIZE,
        "packet_sectors": [packet.sectors for packet in packets],
        "changed_cells": changed_cells,
        "ram_banks": list(RAM_BANKS),
    }
    return video, packets, stats


def decode_reference(video: bytes) -> list[tuple[bytes, bytes]]:
    if video[:4] != VIDEO_MAGIC or video[4] != VIDEO_VERSION:
        raise ValueError("invalid preloaded stream")
    count = video[5]
    offset = base.SECTOR_SIZE
    screen = bytearray(video[offset:offset + base.SCREEN_BYTES])
    offset += base.SCREEN_BYTES
    bitmap = screen[:base.SCREEN_BITMAP_BYTES]
    attrs = screen[base.SCREEN_BITMAP_BYTES:]
    frames = [(bytes(bitmap), bytes(attrs))]
    for _ in range(count):
        sectors = video[offset]
        length = struct.unpack_from("<H", video, offset + 2)[0]
        checksum = struct.unpack_from("<H", video, offset + 4)[0]
        delta = video[
            offset + PACKET_HEADER_BYTES:
            offset + PACKET_HEADER_BYTES + length
        ]
        if (sum(delta) & 0xFFFF) != checksum:
            raise ValueError("packet checksum mismatch")
        pointer = 0
        changed = struct.unpack_from("<H", delta, pointer)[0]
        pointer += 2
        for _ in range(changed):
            bitmap_offset = struct.unpack_from("<H", delta, pointer)[0]
            pointer += 2
            row_mask = delta[pointer]
            pointer += 1
            x_cell = bitmap_offset & 31
            y_cell = ((bitmap_offset >> 8) & 0x18) | ((bitmap_offset >> 5) & 7)
            cell = y_cell * 32 + x_cell
            current = bytearray(base.cell_bytes(bitmap, attrs, cell))
            for row in range(8):
                if row_mask & (1 << row):
                    current[row] = delta[pointer]
                    pointer += 1
            attr_changed = delta[pointer]
            pointer += 1
            if attr_changed:
                expected_attr = 0x1800 + cell
                attr_offset = struct.unpack_from("<H", delta, pointer)[0]
                pointer += 2
                if attr_offset != expected_attr:
                    raise ValueError("bad attribute offset")
                current[8] = delta[pointer]
                pointer += 1
            base.set_cell_bytes(bitmap, attrs, cell, current)
        if pointer != len(delta):
            raise ValueError("delta length mismatch")
        frames.append((bytes(bitmap), bytes(attrs)))
        offset += sectors * base.SECTOR_SIZE
    if offset != len(video):
        raise ValueError("trailing stream data")
    return frames


def emit_ld_a_mem(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x3A, label)


def emit_ld_mem_a(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x32, label)


def emit_ld_hl_mem(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x2A, label)


def emit_ld_mem_hl(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x22, label)


def emit_call(a: base.MiniAssembler, address: int) -> None:
    a.emit(0xCD)
    a.word(address)


def build_player(
    video_track: int,
    video_sector: int,
    video_sectors: int,
) -> tuple[bytes, dict[str, int]]:
    if not 65 <= video_sectors <= 128:
        raise ValueError(
            f"expected a two-bank stream of 65..128 sectors, got {video_sectors}"
        )
    bank0_sectors = 64
    bank1_sectors = video_sectors - bank0_sectors
    packet_start_address = 0xC000 + PACKET_START_SECTOR * base.SECTOR_SIZE

    a = base.MiniAssembler(LOAD_ADDRESS)

    # --------------------------------------------------------------- startup
    a.label("start")
    a.emit(0xF3)
    a.emit(0x31); a.word(0x5FF0)
    a.emit(0xAF, 0xD3, 0xFE)
    a.emit(0xAF); emit_ld_mem_a(a, "screen_flag")
    emit_ld_mem_a(a, "mapped_bank")
    a.emit(0x3E, video_track); emit_ld_mem_a(a, "disk_track")
    a.emit(0x3E, video_sector); emit_ld_mem_a(a, "disk_sector")
    a.abs16(0xCD, "page_current")

    # Read the entire VIDEO file before playback: bank 0 then bank 1.
    a.emit(0x21); a.word(0xC000)
    a.emit(0x06, bank0_sectors)
    a.abs16(0xCD, "read_n")
    a.emit(0x3E, 1); emit_ld_mem_a(a, "mapped_bank")
    a.abs16(0xCD, "page_current")
    a.emit(0x21); a.word(0xC000)
    a.emit(0x06, bank1_sectors)
    a.abs16(0xCD, "read_n")

    # Verify the resident header from bank 0.
    a.emit(0xAF); emit_ld_mem_a(a, "mapped_bank")
    a.abs16(0xCD, "page_current")
    for offset, value in enumerate(VIDEO_MAGIC):
        a.emit(0x3A); a.word(0xC000 + offset)
        a.emit(0xFE, value)
        a.abs16(0xC2, "fatal")
    a.emit(0x3A); a.word(0xC004)
    a.emit(0xFE, VIDEO_VERSION)
    a.abs16(0xC2, "fatal")

    # Initial complete frame -> bank 5, then duplicate to bank 7.
    a.emit(0x21); a.word(0xC000 + base.SECTOR_SIZE)
    a.emit(0x11); a.word(0x4000)
    a.emit(0x01); a.word(base.SCREEN_BYTES)
    a.emit(0xED, 0xB0)
    a.emit(0x3E, 7); emit_ld_mem_a(a, "mapped_bank")
    a.abs16(0xCD, "page_current")
    a.emit(0x21); a.word(0x4000)
    a.emit(0x11); a.word(0xC000)
    a.emit(0x01); a.word(base.SCREEN_BYTES)
    a.emit(0xED, 0xB0)

    a.emit(0xAF); emit_ld_mem_a(a, "stream_bank")
    a.emit(0x21); a.word(packet_start_address)
    emit_ld_mem_hl(a, "stream_ptr")
    a.emit(0x3E, PACKETS); emit_ld_mem_a(a, "packets_remaining")
    a.emit(0x3E, 1); emit_ld_mem_a(a, "playback_started")

    # ------------------------------------------------------------ frame loop
    a.label("main_loop")
    a.abs16(0xCD, "copy_packet")
    a.abs16(0xCD, "copy_visible_to_hidden")
    a.emit(0x21); a.word(BUFFER + PACKET_HEADER_BYTES)
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xB7)
    a.rel8(0x28, "decode_bank7")
    a.emit(0x3E, 0x40)
    a.rel8(0x18, "decode_selected")
    a.label("decode_bank7")
    a.emit(0x3E, 0xC0)
    a.label("decode_selected")
    a.abs16(0xCD, "decode_phase")

    # The new frame is complete before the first possible flip.
    a.emit(0x06, HOLD_FIELDS)
    a.label("hold_loop")
    a.emit(0xFB, 0x76, 0xF3)
    a.rel8(0x10, "hold_loop")
    a.abs16(0xCD, "flip_screen")

    emit_ld_a_mem(a, "packets_remaining")
    a.emit(0x3D); emit_ld_mem_a(a, "packets_remaining")
    a.rel8(0x20, "main_loop")
    a.emit(0x3E, PACKETS); emit_ld_mem_a(a, "packets_remaining")
    a.emit(0xAF); emit_ld_mem_a(a, "stream_bank")
    a.emit(0x21); a.word(packet_start_address)
    emit_ld_mem_hl(a, "stream_ptr")
    a.abs16(0xC3, "main_loop")

    # ----------------------------------------------------- resident packet copy
    a.label("copy_packet")
    emit_ld_a_mem(a, "stream_bank")
    emit_ld_mem_a(a, "mapped_bank")
    a.abs16(0xCD, "page_current")
    emit_ld_hl_mem(a, "stream_ptr")
    a.emit(0x7E); emit_ld_mem_a(a, "copy_sectors")
    a.emit(0x11); a.word(BUFFER)
    a.label("copy_sector_loop")
    a.emit(0x01); a.word(base.SECTOR_SIZE)
    a.emit(0xED, 0xB0)
    a.emit(0x7C, 0xB5)
    a.rel8(0x20, "copy_no_wrap")
    emit_ld_a_mem(a, "stream_bank")
    a.emit(0x3C); emit_ld_mem_a(a, "stream_bank")
    emit_ld_mem_a(a, "mapped_bank")
    a.abs16(0xCD, "page_current")
    a.emit(0x21); a.word(0xC000)
    a.label("copy_no_wrap")
    emit_ld_a_mem(a, "copy_sectors")
    a.emit(0x3D); emit_ld_mem_a(a, "copy_sectors")
    a.rel8(0x20, "copy_sector_loop")
    emit_ld_mem_hl(a, "stream_ptr")
    a.emit(0xC9)

    # ------------------------------------------------------- screen double buf
    a.label("copy_visible_to_hidden")
    a.emit(0x3E, 7); emit_ld_mem_a(a, "mapped_bank")
    a.abs16(0xCD, "page_current")
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xB7)
    a.rel8(0x28, "copy_5_to_7")
    a.emit(0x21); a.word(0xC000)
    a.emit(0x11); a.word(0x4000)
    a.rel8(0x18, "copy_screen")
    a.label("copy_5_to_7")
    a.emit(0x21); a.word(0x4000)
    a.emit(0x11); a.word(0xC000)
    a.label("copy_screen")
    a.emit(0x01); a.word(base.SCREEN_BYTES)
    a.emit(0xED, 0xB0, 0xC9)

    a.label("flip_screen")
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xEE, 0x08); emit_ld_mem_a(a, "screen_flag")
    a.abs16(0xCD, "page_current")
    a.emit(0xC9)

    a.label("page_current")
    emit_ld_a_mem(a, "mapped_bank")
    a.emit(0xE6, 0x07, 0x47)
    emit_ld_a_mem(a, "screen_flag")
    a.emit(0xB0, 0xF6, PAGING_ROM48)
    a.emit(0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79, 0xC9)

    # ------------------------------------------------------------- phase delta
    a.label("decode_phase")
    emit_ld_mem_a(a, "base_hi")
    a.emit(0x4E, 0x23, 0x46, 0x23)
    a.label("decode_loop")
    a.emit(0x78, 0xB1, 0xC8)
    a.emit(0xC5)
    a.emit(0x5E, 0x23, 0x56, 0x23)
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

    # ----------------------------------------------------------- startup disk
    a.label("read_n")
    a.emit(0x78); emit_ld_mem_a(a, "read_count")
    emit_ld_a_mem(a, "disk_track"); a.emit(0x57)
    emit_ld_a_mem(a, "disk_sector"); a.emit(0x5F)
    a.emit(0x0E, 0x05)
    emit_call(a, 0x3D13)
    a.emit(0xF3)
    a.abs16(0xCD, "page_current")
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

    a.label("fatal")
    a.emit(0x3E, 2, 0xD3, 0xFE)
    a.rel8(0x18, "fatal")

    for name, size in (
        ("screen_flag", 1),
        ("mapped_bank", 1),
        ("disk_track", 1),
        ("disk_sector", 1),
        ("read_count", 1),
        ("stream_bank", 1),
        ("stream_ptr", 2),
        ("copy_sectors", 1),
        ("packets_remaining", 1),
        ("base_hi", 1),
        ("playback_started", 1),
    ):
        a.label(name)
        a.emit(*([0] * size))

    code = a.resolve()
    if len(code) > 0x1000:
        raise ValueError("preloaded player unexpectedly exceeds 4 KiB")
    return code, dict(a.labels)


def write_preview(
    path: Path,
    phases: Sequence[tuple[bytes, bytes, bytes]],
) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        5,
        (base.WIDTH, base.HEIGHT),
    )
    if not writer.isOpened():
        raise RuntimeError("cannot create preview")
    for bitmap_a, _, attrs in phases:
        frame = base.render_spectrum_screen(bitmap_a, attrs)
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    writer.release()


def write_contact_sheet(
    path: Path,
    phases: Sequence[tuple[bytes, bytes, bytes]],
) -> None:
    indices = np.linspace(0, len(phases) - 1, 6, dtype=int)
    sheet = Image.new("RGB", (base.WIDTH * 3, base.HEIGHT * 2), "black")
    for position, index in enumerate(indices):
        bitmap_a, _, attrs = phases[int(index)]
        rendered = base.render_spectrum_screen(bitmap_a, attrs)
        sheet.paste(
            Image.fromarray(rendered),
            ((position % 3) * base.WIDTH, (position // 3) * base.HEIGHT),
        )
    sheet.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "build_preloaded_single",
        help="output directory (not a .trd filename)",
    )
    args = parser.parse_args()
    out = args.output
    if out.suffix.lower() == ".trd":
        parser.error("--output expects a directory, not a .trd filename")
    out.mkdir(parents=True, exist_ok=True)

    sources = streaming.compact_demo_frames(PACKETS)
    phases: list[tuple[bytes, bytes, bytes]] = []
    previous_attrs: np.ndarray | None = None
    for index, frame in enumerate(sources):
        bitmap_a, bitmap_b, attrs, _ = base.convert_frame_to_phases(
            frame, previous_attrs
        )
        phases.append((bitmap_a, bitmap_b, attrs))
        previous_attrs = np.frombuffer(attrs, dtype=np.uint8).copy()
        print(f"converted frame {index + 1}/{PACKETS}", flush=True)

    video, packets, stats = build_single_phase_stream(phases)
    decoded = decode_reference(video)
    if len(decoded) != len(phases) + 1:
        raise AssertionError("reference frame count mismatch")
    for index in range(len(phases)):
        expected = phases[(index + 1) % len(phases)]
        if decoded[index + 1] != (expected[0], expected[2]):
            raise AssertionError(f"reference mismatch at packet {index}")

    boot = streaming.build_boot_basic()
    provisional, _ = build_player(0, 0, len(video) // base.SECTOR_SIZE)
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
    player, labels = build_player(
        video_track, video_sector, len(video) // base.SECTOR_SIZE
    )
    files = [
        base.TrdFile(
            "boot",
            "B",
            boot,
            basic_variables_offset=len(boot),
            autostart_line=10,
        ),
        base.TrdFile("PLAYER", "C", player, start=LOAD_ADDRESS),
        base.TrdFile("VIDEO", "C", video, start=0),
    ]
    trd, directory, trd_stats = streaming.place_files(files, "ZXVPRE")
    trd_name = "zxv_preloaded_single_phase.trd"
    (out / trd_name).write_bytes(trd)
    (out / "PLAYER.C.bin").write_bytes(player)
    (out / "VIDEO.C.bin").write_bytes(video)
    write_preview(out / "zxv_preloaded_single_phase_preview.mp4", phases)
    write_contact_sheet(
        out / "zxv_preloaded_single_phase_contact_sheet.png", phases
    )

    packet_sectors = stats["packet_sectors"]
    assert isinstance(packet_sectors, list)
    report = f"""# ZXV preloaded single-phase player

- Frames: {stats['frames']}
- VIDEO.C: {stats['video_bytes']} bytes, {stats['video_sectors']} sectors
- Preload RAM: banks 0 and 1
- Disk reads during playback: zero
- Display buffers: bank 5 and bank 7
- Page flips: one per complete logical frame
- 50 Hz temporal A/B switching: disabled
- Hold loop: {HOLD_FIELDS} vblanks after preparation
- Packet sectors: {min(packet_sectors)}..{max(packet_sectors)}
- Player: {len(player)} bytes
- TRD used sectors: {trd_stats['used_sectors']}
- Host reference decode: all {len(packets)} transitions exact
"""
    (out / "README.md").write_text(report, encoding="utf-8")
    metadata = {
        "player_labels": labels,
        "video_track": video_track,
        "video_sector": video_sector,
        "trd_name": trd_name,
        "directory": directory,
        "stats": stats,
        "playback": {
            "preload_banks": list(RAM_BANKS),
            "disk_reads_after_main_loop": 0,
            "screen_banks": [5, 7],
            "single_phase": True,
        },
    }
    (out / "build_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(report)


if __name__ == "__main__":
    main()
