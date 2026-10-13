"""TR-DOS disk directory, file placement, boot BASIC and screen addressing.

Preserved from the project's verified TRD builders. The audio player loads
whole 11-byte records into banks; the container uses 256-byte disk sectors.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import math
import struct

TRD_SIZE = 655360
SECTOR_SIZE = 256
SECTORS_PER_TRACK = 16
LOGICAL_TRACKS = 160
DATA_START_TRACK = 1


@dataclass
class TrdFile:
    name: str
    file_type: str
    data: bytes
    start: int = 0
    basic_variables_offset: int | None = None
    autostart_line: int | None = None


def basic_line(line_number: int, content: bytes) -> bytes:
    body = content + b"\x0D"
    return struct.pack(">H", line_number) + struct.pack("<H", len(body)) + body


def spectrum_bitmap_offset(x_byte: int, y: int) -> int:
    return ((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2) | x_byte


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


def place_files(files: list[TrdFile], label: str) -> tuple[bytes, list[dict[str, int | str]], dict[str, int]]:
    image = bytearray(TRD_SIZE)
    track, sector = DATA_START_TRACK, 0
    used = 0
    for index, file in enumerate(files):
        track, sector, sectors = add_trd_file(image, index, file, track, sector)
        used += sectors
    info = 8 * SECTOR_SIZE
    image[info] = 0
    image[info + 225] = sector
    image[info + 226] = track
    image[info + 227] = 0x16
    image[info + 228] = len(files)
    free = (LOGICAL_TRACKS - 1) * SECTORS_PER_TRACK - used
    image[info + 229:info + 231] = struct.pack("<H", free)
    image[info + 231] = 0x10
    image[info + 233:info + 242] = b" " * 9
    image[info + 245:info + 253] = label.encode("ascii", "replace")[:8].ljust(8, b" ")
    result = bytes(image)
    return result, parse_trd_directory(result), {
        "used_sectors": used, "free_sectors": free,
        "first_free_track": track, "first_free_sector": sector,
    }


def calculate_file_start(preceding: Sequence[TrdFile]) -> tuple[int, int]:
    absolute = DATA_START_TRACK * SECTORS_PER_TRACK
    for f in preceding:
        stored_len = len(f.data) + (4 if f.file_type == "B" else 0)
        absolute += math.ceil(stored_len / SECTOR_SIZE)
    return absolute // SECTORS_PER_TRACK, absolute % SECTORS_PER_TRACK


def boot_basic():
    return b''.join([
        basic_line(10, b'\xfd \xb0 "32767"'),
        basic_line(20, b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30, b'\xf9 \xc0 \xb0 "32768"')])
