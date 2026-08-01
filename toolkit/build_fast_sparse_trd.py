#!/usr/bin/env python3
"""Repack a built compact stream into direct-to-screen sparse TRD volumes."""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_long_video_trd as source  # noqa: E402
import build_streaming_trd as streaming  # noqa: E402
import build_zxv_trd as base  # noqa: E402


LOAD_ADDRESS = 0x6000
BUFFER = 0x8000
STAGING_SECTOR = 0xBF00
VIDEO_MAGIC = b"ZXFS"
VIDEO_VERSION = 5
PACKET_FIRST_HEADER = 12
FIXED_RING_SECTORS = 63
RING_BANKS = (0, 1, 3, 4, 6)
RING_CAPACITY_SECTORS = FIXED_RING_SECTORS + 64 * len(RING_BANKS)
FIELDS_PER_FRAME = 6
# Z80 timing-table model for address preparation shared by bitmap-row
# commands. The former table held two words and required row*4 plus two
# independently relocated addresses. The current table holds one word,
# indexes it with row*2, and derives the second native row with high+1.
ROW_ADDRESS_SETUP_CYCLES_PREVIOUS = 155
ROW_ADDRESS_SETUP_CYCLES_CURRENT = 109
CMD_END = 0
CMD_BITMAP_ROW = 1
CMD_ATTRIBUTES = 2
CMD_BITMAP_POINTS = 3
CMD_ATTRIBUTES_DELTA = 4
CMD_BITMAP_ROW_RLE = 5
CMD_BITMAP_ROW_SHIFT = 6
PAGING_ROM48_BANK7 = 0x17
MAX_TRDOS_FILE_SECTORS = 255
TRD_DATA_SECTORS = (base.LOGICAL_TRACKS - 1) * base.SECTORS_PER_TRACK


@dataclass(frozen=True)
class SparsePacket:
    sectors: tuple[bytes, ...]
    ay_state: bytes
    rle_rows: int = 0
    motion_rows: int = 0
    sectors_saved: int = 0
    packing_sectors_saved: int = 0
    padding_bytes: int = 0

    @property
    def sector_count(self) -> int:
        return len(self.sectors)

    def serialize(self) -> bytes:
        return b"".join(self.sectors)


def decode_compact_build(path: Path) -> tuple[list[bytes], list[bytes], float]:
    data = path.read_bytes()
    if data[:4] != source.VIDEO_MAGIC:
        raise ValueError("not a compact long-video stream")
    frame_count = struct.unpack_from("<H", data, 8)[0]
    numerator, denominator = struct.unpack_from("<HH", data, 32)
    frame_rate = numerator / denominator if denominator else float(data[5])
    offset = base.SECTOR_SIZE
    state = bytes(source.STATE_BYTES)
    states: list[bytes] = []
    ay_states: list[bytes] = []
    for _ in range(frame_count):
        sectors = data[offset]
        flags = data[offset + 1]
        payload_length = struct.unpack_from("<H", data, offset + 2)[0]
        ay_length = data[offset + 4]
        ay = data[
            offset + source.PACKET_HEADER_BYTES:
            offset + source.PACKET_HEADER_BYTES + ay_length
        ]
        payload = data[
            offset + source.PACKET_HEADER_BYTES + ay_length:
            offset + source.PACKET_HEADER_BYTES + ay_length + payload_length
        ]
        state = payload if flags & 1 else source.decode_zero_literal_rle(payload, state)
        states.append(state)
        ay_states.append(ay)
        offset += sectors * base.SECTOR_SIZE
    if offset != len(data):
        raise ValueError("trailing compact stream data")
    return states, ay_states, frame_rate


def encode_byte_rle(data: bytes) -> bytes:
    """Pack short byte strings with a decoder-friendly PackBits variant."""
    encoded = bytearray()
    position = 0
    while position < len(data):
        run = 1
        while (
            position + run < len(data)
            and data[position + run] == data[position]
            and run < 129
        ):
            run += 1
        if run >= 3:
            encoded += bytes((0x80 | (run - 2), data[position]))
            position += run
            continue
        literal_start = position
        position += run
        while position < len(data) and position - literal_start < 128:
            following_run = 1
            while (
                position + following_run < len(data)
                and data[position + following_run] == data[position]
                and following_run < 129
            ):
                following_run += 1
            if following_run >= 3:
                break
            position += following_run
        literal = data[literal_start:position]
        encoded.append(len(literal) - 1)
        encoded += literal
    return bytes(encoded)


def frame_records(
    current: bytes,
    previous: bytes,
    allow_dense_rle: bool = False,
    allow_motion: bool = False,
) -> list[bytes]:
    records: list[bytes] = []
    for row in range(source.LOGICAL_HEIGHT):
        start = row * (source.LOGICAL_WIDTH // 4)
        current_row = current[start:start + source.LOGICAL_WIDTH // 4]
        previous_row = previous[start:start + source.LOGICAL_WIDTH // 4]

        def delta_record(predicted: bytes) -> bytes | None:
            mask = 0
            values = bytearray()
            for column, value in enumerate(current_row):
                if value != predicted[column]:
                    mask |= 1 << (31 - column)
                    values.append(value)
            if not mask:
                return None
            changed_columns = [
                column
                for column in range(source.LOGICAL_WIDTH // 4)
                if mask & (1 << (31 - column))
            ]
            mask_record = (
                bytes((CMD_BITMAP_ROW, row))
                + mask.to_bytes(4, "big")
                + values
            )
            point_record = bytearray((CMD_BITMAP_POINTS, row, len(changed_columns)))
            for column, value in zip(changed_columns, values):
                point_record += bytes((column, value))
            return min(mask_record, bytes(point_record), key=len)

        direct = delta_record(previous_row)
        candidates: list[list[bytes]] = [[] if direct is None else [direct]]
        if allow_dense_rle and direct is not None:
            row_rle = encode_byte_rle(current_row)
            candidates.append(
                [bytes((CMD_BITMAP_ROW_RLE, row, len(row_rle))) + row_rle]
            )
        if allow_motion and direct is not None:
            for shift in (*range(-8, 0), *range(1, 9)):
                if shift > 0:
                    predicted = bytes(shift) + previous_row[:-shift]
                else:
                    amount = -shift
                    predicted = previous_row[amount:] + bytes(amount)
                correction = delta_record(predicted)
                motion = [bytes((CMD_BITMAP_ROW_SHIFT, row, shift & 0xFF))]
                if correction is not None:
                    motion.append(correction)
                candidates.append(motion)
        selected = min(candidates, key=lambda candidate: sum(map(len, candidate)))
        # A motion predictor and its correction must remain adjacent if the
        # sector packer later reorders independent row records.
        if selected:
            records.append(b"".join(selected))

    changes = [
        (index, current[source.STATE_LEVEL_BYTES + index])
        for index in range(source.STATE_ATTR_BYTES)
        if current[source.STATE_LEVEL_BYTES + index]
        != previous[source.STATE_LEVEL_BYTES + index]
    ]
    while changes:
        group = changes[:80]
        changes = changes[80:]
        record = bytearray((CMD_ATTRIBUTES_DELTA, len(group)))
        previous_index = -1
        for index, value in group:
            gap = index - previous_index - 1
            if gap < 255:
                record.append(gap)
            else:
                record.append(255)
                record += struct.pack("<H", gap)
            record.append(value)
            previous_index = index
        records.append(bytes(record))
    return records


def pack_packet(
    records: list[bytes],
    ay_state: bytes,
    *,
    rle_rows: int = 0,
    motion_rows: int = 0,
    sectors_saved: int = 0,
) -> SparsePacket:
    if len(ay_state) != source.AY_STATE_BYTES:
        raise ValueError("invalid AY state")
    for record in records:
        if len(record) + 1 > base.SECTOR_SIZE:
            raise ValueError("sparse record does not fit a sector")

    # Baseline sector count used by the former in-order greedy packer.
    greedy_used = PACKET_FIRST_HEADER
    greedy_sectors = 1
    for record in records:
        if greedy_used + len(record) + 1 > base.SECTOR_SIZE:
            greedy_sectors += 1
            greedy_used = 0
        greedy_used += len(record)

    # Best-fit decreasing keeps complete row records intact but fills holes in
    # earlier sectors. Record execution order is irrelevant, except that a
    # motion operation and its correction were joined above into one record.
    payloads: list[bytearray] = [bytearray(PACKET_FIRST_HEADER)]
    for record in sorted(records, key=len, reverse=True):
        fitting = [
            (base.SECTOR_SIZE - len(payload) - 1 - len(record), index)
            for index, payload in enumerate(payloads)
            if len(payload) + len(record) + 1 <= base.SECTOR_SIZE
        ]
        if fitting:
            payloads[min(fitting)[1]] += record
        else:
            payloads.append(bytearray(record))
    unpadded_bytes = sum(len(payload) + 1 for payload in payloads)
    for payload in payloads:
        payload.append(CMD_END)
        payload += bytes(base.SECTOR_SIZE - len(payload))
    if len(payloads) > 255:
        raise ValueError("too many sparse sectors")
    payloads[0][0] = len(payloads)
    payloads[0][1] = VIDEO_VERSION
    payloads[0][3:3 + source.AY_STATE_BYTES] = ay_state
    return SparsePacket(
        tuple(bytes(payload) for payload in payloads),
        ay_state,
        rle_rows,
        motion_rows,
        sectors_saved,
        greedy_sectors - len(payloads),
        len(payloads) * base.SECTOR_SIZE - unpadded_bytes,
    )


def apply_packet_reference(packet: SparsePacket, previous: bytes) -> bytes:
    state = bytearray(previous)
    for sector_index, sector in enumerate(packet.sectors):
        position = PACKET_FIRST_HEADER if sector_index == 0 else 0
        while True:
            command = sector[position]
            position += 1
            if command == CMD_END:
                break
            if command == CMD_BITMAP_ROW:
                row = sector[position]
                mask = int.from_bytes(sector[position + 1:position + 5], "big")
                position += 5
                row_start = row * (source.LOGICAL_WIDTH // 4)
                for column in range(source.LOGICAL_WIDTH // 4):
                    if mask & (1 << (31 - column)):
                        state[row_start + column] = sector[position]
                        position += 1
            elif command == CMD_BITMAP_POINTS:
                row = sector[position]
                count = sector[position + 1]
                position += 2
                row_start = row * (source.LOGICAL_WIDTH // 4)
                for _ in range(count):
                    column = sector[position]
                    state[row_start + column] = sector[position + 1]
                    position += 2
            elif command == CMD_ATTRIBUTES_DELTA:
                count = sector[position]
                position += 1
                index = -1
                for _ in range(count):
                    gap = sector[position]
                    position += 1
                    if gap == 255:
                        gap = struct.unpack_from("<H", sector, position)[0]
                        position += 2
                    index += gap + 1
                    state[source.STATE_LEVEL_BYTES + index] = sector[position]
                    position += 1
            elif command == CMD_BITMAP_ROW_RLE:
                row = sector[position]
                encoded_length = sector[position + 1]
                position += 2
                encoded_end = position + encoded_length
                decoded = bytearray()
                while position < encoded_end:
                    token = sector[position]
                    position += 1
                    if token & 0x80:
                        count = (token & 0x7F) + 2
                        decoded += bytes((sector[position],)) * count
                        position += 1
                    else:
                        count = token + 1
                        decoded += sector[position:position + count]
                        position += count
                if len(decoded) != source.LOGICAL_WIDTH // 4:
                    raise ValueError("invalid RLE bitmap row")
                row_start = row * (source.LOGICAL_WIDTH // 4)
                state[row_start:row_start + len(decoded)] = decoded
            elif command == CMD_BITMAP_ROW_SHIFT:
                row = sector[position]
                shift = struct.unpack_from("b", sector, position + 1)[0]
                position += 2
                row_start = row * (source.LOGICAL_WIDTH // 4)
                old = bytes(state[row_start:row_start + source.LOGICAL_WIDTH // 4])
                if shift > 0:
                    shifted = bytes(shift) + old[:-shift]
                else:
                    amount = -shift
                    shifted = old[amount:] + bytes(amount)
                state[row_start:row_start + len(shifted)] = shifted
            else:
                raise ValueError(f"unknown sparse command {command}")
    return bytes(state)


def make_volume_packets(
    states: list[bytes], ay_states: list[bytes], start: int, limit: int
) -> tuple[int, list[SparsePacket]]:
    zero = bytes(source.STATE_BYTES)
    previous = [zero, zero]
    packets: list[SparsePacket] = []
    used = 1
    end = start
    while end < len(states):
        local = end - start
        if local == 0:
            prior = zero
        else:
            prior = previous[local & 1]
        packet = pack_packet(frame_records(states[end], prior), ay_states[end])
        if packet.sector_count > 5:
            rle_records = frame_records(
                states[end],
                prior,
                allow_dense_rle=True,
            )
            rle_packet = pack_packet(
                rle_records,
                ay_states[end],
                rle_rows=sum(
                    record[0] == CMD_BITMAP_ROW_RLE
                    for record in rle_records
                ),
            )
            motion_records = frame_records(
                states[end],
                prior,
                allow_dense_rle=True,
                allow_motion=True,
            )
            motion_packet = pack_packet(
                motion_records,
                ay_states[end],
                rle_rows=sum(
                    record[0] == CMD_BITMAP_ROW_RLE
                    for record in motion_records
                ),
                motion_rows=sum(
                    record[0] == CMD_BITMAP_ROW_SHIFT
                    for record in motion_records
                ),
            )
            compressed = min(
                (rle_packet, motion_packet),
                key=lambda candidate: (
                    candidate.sector_count,
                    candidate.motion_rows > 0,
                ),
            )
            if compressed.sector_count < packet.sector_count:
                compressed = SparsePacket(
                    compressed.sectors,
                    compressed.ay_state,
                    compressed.rle_rows,
                    compressed.motion_rows,
                    packet.sector_count - compressed.sector_count,
                    compressed.packing_sectors_saved,
                    compressed.padding_bytes,
                )
                packet = compressed
        if apply_packet_reference(packet, prior) != states[end]:
            raise AssertionError(f"sparse reference mismatch at frame {end}")
        if packets and used + packet.sector_count > limit:
            break
        packets.append(packet)
        used += packet.sector_count
        if local == 0:
            previous = [states[end], states[end]]
        else:
            previous[local & 1] = states[end]
        used += 0
        end += 1
    return end, packets


def serialize_volume(packets: list[SparsePacket], frame_rate: float) -> bytes:
    header = bytearray(base.SECTOR_SIZE)
    header[:4] = VIDEO_MAGIC
    header[4] = VIDEO_VERSION
    struct.pack_into("<H", header, 8, len(packets))
    rate = source.Fraction(frame_rate).limit_denominator(1000)
    struct.pack_into("<HH", header, 12, rate.numerator, rate.denominator)
    sector_counts = [packet.sector_count for packet in packets]
    struct.pack_into("<H", header, 16, sum(sector_counts))
    struct.pack_into("<H", header, 18, minimum_startup_backlog(sector_counts))
    struct.pack_into("<H", header, 20, RING_CAPACITY_SECTORS)
    return bytes(header) + b"".join(packet.serialize() for packet in packets)


def minimum_startup_backlog(sector_counts: list[int]) -> int:
    """Find the smallest backlog that sustains one frame every six fields."""
    for initial in range(RING_CAPACITY_SECTORS + 1):
        queued = initial
        sustainable = True
        for index, sectors in enumerate(sector_counts):
            if queued < sectors:
                sustainable = False
                break
            queued -= sectors
            # Frame zero and frame one are decoded before the first timed
            # producer interval. Later packets follow six sector opportunities.
            if index:
                queued = min(
                    RING_CAPACITY_SECTORS,
                    queued + FIELDS_PER_FRAME,
                )
        if sustainable:
            return initial
    raise ValueError("packet sequence cannot be sustained by the 16 KiB ring")


def ld_a_mem(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x3A, label)


def ld_mem_a(a: base.MiniAssembler, label: str) -> None:
    a.abs16(0x32, label)


def call_rom(a: base.MiniAssembler, address: int) -> None:
    a.emit(0xCD); a.word(address)


def build_player(video_track: int, video_sector: int) -> tuple[bytes, dict[str, int]]:
    a = base.MiniAssembler(LOAD_ADDRESS)
    a.label("start")
    a.emit(0xF3, 0x31); a.word(0x5FF0)
    a.emit(0xAF, 0xD3, 0xFE)
    ld_mem_a(a, "screen_flag")
    a.emit(0x3E, video_track); ld_mem_a(a, "disk_track")
    a.emit(0x3E, video_sector); ld_mem_a(a, "disk_sector")
    a.emit(0x3E, PAGING_ROM48_BANK7, 0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79)

    # Stream header.
    a.emit(0x21); a.word(BUFFER)
    a.emit(0x06, 1); a.abs16(0xCD, "read_n")
    for offset, value in enumerate(VIDEO_MAGIC):
        a.emit(0x3A); a.word(BUFFER + offset)
        a.emit(0xFE, value); a.abs16(0xC2, "fatal")
    a.emit(0x2A); a.word(BUFFER + 8)
    a.emit(0x2B); a.abs16(0x22, "frames_remaining")
    a.emit(0x2A); a.word(BUFFER + 16); a.abs16(0x22, "disk_sectors_remaining")
    a.emit(0x2A); a.word(BUFFER + 18); a.abs16(0x22, "startup_target")
    a.emit(0xAF)
    ld_mem_a(a, "ring_read_region"); ld_mem_a(a, "ring_write_region")
    a.emit(0x21); a.word(0); a.abs16(0x22, "ring_count")
    a.emit(0x3E, 0x80)
    ld_mem_a(a, "ring_read_high"); ld_mem_a(a, "ring_write_high")
    a.abs16(0xCD, "startup_fill")

    # Clear bank 5, apply frame zero there, then clone it to bank 7.
    a.emit(0x21); a.word(0x4000)
    a.emit(0x11); a.word(0x4001)
    a.emit(0x01); a.word(base.SCREEN_BYTES - 1)
    a.emit(0x36, 0, 0xED, 0xB0)
    a.emit(0x3E, 0x40); ld_mem_a(a, "update_base")
    a.emit(0x21); a.word(0x5800); a.abs16(0x22, "attr_base")
    a.abs16(0xCD, "prepare_read_sector")
    a.abs16(0xCD, "ring_packet")
    a.emit(0x21); a.word(0x4000)
    a.emit(0x11); a.word(0xC000)
    a.emit(0x01); a.word(base.SCREEN_BYTES)
    a.emit(0xED, 0xB0)
    a.abs16(0xCD, "ay_apply")

    a.label("main_loop")
    a.emit(0x2A); a.abs16([], "frames_remaining")
    a.emit(0x7C, 0xB5); a.abs16(0xCA, "finished")
    ld_a_mem(a, "screen_flag"); a.emit(0xB7)
    a.rel8(0x28, "target_bank7")
    a.emit(0x3E, 0x40); ld_mem_a(a, "update_base")
    a.emit(0x21); a.word(0x5800); a.abs16(0x22, "attr_base")
    a.rel8(0x18, "target_ready")
    a.label("target_bank7")
    a.emit(0x3E, 0xC0); ld_mem_a(a, "update_base")
    a.emit(0x21); a.word(0xD800); a.abs16(0x22, "attr_base")
    a.label("target_ready")
    a.abs16(0xCD, "wait_packet")
    a.abs16(0xCD, "ring_packet")
    a.emit(0x3E, FIELDS_PER_FRAME); ld_mem_a(a, "hold_counter")
    a.label("prefetch_loop")
    a.abs16(0xCD, "wait_field")
    a.abs16(0xCD, "producer_one")
    a.abs16(0xCD, "decrement_hold")
    ld_a_mem(a, "hold_counter"); a.emit(0xB7)
    a.rel8(0x20, "prefetch_loop")
    a.abs16(0xCD, "flip_screen")
    a.abs16(0xCD, "ay_apply")
    a.emit(0x2A); a.abs16([], "frames_remaining")
    a.emit(0x2B); a.abs16(0x22, "frames_remaining")
    a.abs16(0xC3, "main_loop")

    # Fill the ring before frame zero. Each volume carries the exact minimum
    # backlog calculated by the host-side buffer simulation.
    a.label("startup_fill")
    a.emit(0x2A); a.abs16([], "ring_count")
    a.emit(0xED, 0x5B); a.abs16([], "startup_target")
    a.emit(0xAF, 0xED, 0x52, 0xC8)
    a.abs16(0xCD, "producer_one")
    a.rel8(0x18, "startup_fill")

    # Wait only on an actual underflow. With the encoded startup backlog this
    # path is not expected during normal playback.
    a.label("wait_packet")
    a.emit(0x2A); a.abs16([], "ring_count")
    a.emit(0x7C, 0xB5)
    a.rel8(0x28, "wait_packet_fill")
    a.abs16(0xCD, "prepare_read_sector")
    a.emit(0x2A); a.abs16([], "sector_pointer")
    a.emit(0x46)
    a.emit(0x2A); a.abs16([], "ring_count")
    a.emit(0x7C, 0xB7, 0xC0, 0x7D, 0xB8, 0xD0)
    a.label("wait_packet_fill")
    a.abs16(0xCD, "wait_field")
    a.abs16(0xCD, "producer_one")
    a.rel8(0x18, "wait_packet")

    # Consume one complete packet from the RAM ring without disk accesses.
    a.label("ring_packet")
    a.emit(0x2A); a.abs16([], "sector_pointer")
    a.emit(0x7E); ld_mem_a(a, "packet_remaining")
    a.emit(0x11); a.word(3); a.emit(0x19)
    a.emit(0x11); a.abs16([], "ay_state")
    a.emit(0x01); a.word(source.AY_STATE_BYTES)
    a.emit(0xED, 0xB0)
    a.emit(0x2A); a.abs16([], "sector_pointer")
    a.emit(0x11); a.word(PACKET_FIRST_HEADER); a.emit(0x19, 0xE5, 0xDD, 0xE1)
    a.abs16(0xCD, "command_loop")
    a.abs16(0xCD, "consume_sector")
    a.label("ring_packet_more")
    ld_a_mem(a, "packet_remaining"); a.emit(0xB7, 0xC8)
    a.abs16(0xCD, "prepare_read_sector")
    a.emit(0x2A); a.abs16([], "sector_pointer")
    a.emit(0xE5, 0xDD, 0xE1)
    a.abs16(0xCD, "command_loop")
    a.abs16(0xCD, "consume_sector")
    a.rel8(0x18, "ring_packet_more")

    a.label("consume_sector")
    a.emit(0x2A); a.abs16([], "ring_count")
    a.emit(0x2B); a.abs16(0x22, "ring_count")
    ld_a_mem(a, "packet_remaining"); a.emit(0x3D); ld_mem_a(a, "packet_remaining")
    ld_a_mem(a, "ring_read_region"); a.emit(0xB7)
    a.rel8(0x20, "consume_banked")
    ld_a_mem(a, "ring_read_high"); a.emit(0x3C, 0xFE, 0xBF)
    a.rel8(0x20, "consume_store_high")
    a.emit(0x3E, 1); ld_mem_a(a, "ring_read_region")
    a.emit(0x3E, 0xC0)
    a.rel8(0x18, "consume_store_high")
    a.label("consume_banked")
    ld_a_mem(a, "ring_read_high"); a.emit(0x3C)
    a.rel8(0x20, "consume_store_high")
    ld_a_mem(a, "ring_read_region"); a.emit(0x3C, 0xFE, len(RING_BANKS) + 1)
    a.rel8(0x38, "consume_next_bank")
    a.emit(0xAF); ld_mem_a(a, "ring_read_region")
    a.emit(0x3E, 0x80)
    a.rel8(0x18, "consume_store_high")
    a.label("consume_next_bank")
    ld_mem_a(a, "ring_read_region")
    a.emit(0x3E, 0xC0)
    a.label("consume_store_high")
    ld_mem_a(a, "ring_read_high")
    a.emit(0xC9)

    # Make the current read sector visible at a stable address. Banked sectors
    # are copied through BF00h because bank 7 may simultaneously be the target.
    a.label("prepare_read_sector")
    ld_a_mem(a, "ring_read_region"); a.emit(0xB7)
    a.rel8(0x28, "prepare_fixed")
    a.abs16(0xCD, "page_queue_region")
    ld_a_mem(a, "ring_read_high"); a.emit(0x67, 0x2E, 0)
    a.emit(0x11); a.word(STAGING_SECTOR)
    a.emit(0x01); a.word(base.SECTOR_SIZE)
    a.emit(0xED, 0xB0)
    a.abs16(0xCD, "page_bank7")
    a.emit(0x21); a.word(STAGING_SECTOR)
    a.abs16(0x22, "sector_pointer")
    a.emit(0xC9)
    a.label("prepare_fixed")
    ld_a_mem(a, "ring_read_high"); a.emit(0x67, 0x2E, 0)
    a.abs16(0x22, "sector_pointer")
    a.abs16(0xCD, "page_bank7")
    a.emit(0xC9)

    # Read at most one future sector. The caller supplies the display-field
    # pacing, so startup can call this routine without waits.
    a.label("producer_one")
    a.emit(0x2A); a.abs16([], "disk_sectors_remaining")
    a.emit(0x7C, 0xB5, 0xC8)
    a.emit(0x2A); a.abs16([], "ring_count")
    a.emit(0x11); a.word(RING_CAPACITY_SECTORS)
    a.emit(0xAF, 0xED, 0x52, 0xD0)
    ld_a_mem(a, "ring_write_region"); a.emit(0xB7)
    a.rel8(0x28, "producer_fixed")
    a.abs16(0xCD, "page_queue_region")
    a.label("producer_fixed")
    ld_a_mem(a, "ring_write_high"); a.emit(0x67, 0x2E, 0)
    a.emit(0x06, 1); a.abs16(0xCD, "read_n")
    a.emit(0x2A); a.abs16([], "ring_count")
    a.emit(0x23); a.abs16(0x22, "ring_count")
    a.emit(0x2A); a.abs16([], "disk_sectors_remaining")
    a.emit(0x2B); a.abs16(0x22, "disk_sectors_remaining")
    ld_a_mem(a, "ring_write_region"); a.emit(0xB7)
    a.rel8(0x20, "producer_banked")
    ld_a_mem(a, "ring_write_high"); a.emit(0x3C, 0xFE, 0xBF)
    a.rel8(0x20, "producer_store_high")
    a.emit(0x3E, 1); ld_mem_a(a, "ring_write_region")
    a.emit(0x3E, 0xC0)
    a.rel8(0x18, "producer_store_high")
    a.label("producer_banked")
    ld_a_mem(a, "ring_write_high"); a.emit(0x3C)
    a.rel8(0x20, "producer_store_high")
    ld_a_mem(a, "ring_write_region"); a.emit(0x3C, 0xFE, len(RING_BANKS) + 1)
    a.rel8(0x38, "producer_next_bank")
    a.emit(0xAF); ld_mem_a(a, "ring_write_region")
    a.emit(0x3E, 0x80)
    a.rel8(0x18, "producer_store_high")
    a.label("producer_next_bank")
    ld_mem_a(a, "ring_write_region")
    a.emit(0x3E, 0xC0)
    a.label("producer_store_high")
    ld_mem_a(a, "ring_write_high")
    a.emit(0xC9)

    a.label("page_queue_region")
    a.emit(0x3D, 0x5F, 0x16, 0)
    a.emit(0x21); a.abs16([], "queue_banks")
    a.emit(0x19, 0x56)
    ld_a_mem(a, "screen_flag"); a.emit(0xF6, 0x10, 0xB2)
    a.emit(0x01); a.word(0x7FFD); a.emit(0xED, 0x79, 0xC9)
    a.label("page_bank7")
    ld_a_mem(a, "screen_flag"); a.emit(0xF6, PAGING_ROM48_BANK7)
    a.emit(0x01); a.word(0x7FFD); a.emit(0xED, 0x79, 0xC9)

    a.label("decrement_hold")
    ld_a_mem(a, "hold_counter"); a.emit(0xB7, 0xC8, 0x3D); ld_mem_a(a, "hold_counter"); a.emit(0xC9)
    a.label("wait_field")
    a.emit(0xFB, 0x76, 0xF3, 0xC9)

    a.label("apply_first")
    a.emit(0xDD, 0x21); a.word(BUFFER + PACKET_FIRST_HEADER)
    a.rel8(0x18, "command_loop")
    a.label("apply_following")
    a.emit(0xDD, 0x21); a.word(BUFFER)
    a.label("command_loop")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23, 0xB7, 0xC8)
    a.emit(0xFE, CMD_BITMAP_ROW); a.abs16(0xCA, "command_row")
    a.emit(0xFE, CMD_ATTRIBUTES); a.abs16(0xCA, "command_attrs")
    a.emit(0xFE, CMD_BITMAP_POINTS); a.abs16(0xCA, "command_points")
    a.emit(0xFE, CMD_ATTRIBUTES_DELTA); a.abs16(0xCA, "command_attrs_delta")
    a.emit(0xFE, CMD_BITMAP_ROW_RLE); a.abs16(0xCA, "command_row_rle")
    a.emit(0xFE, CMD_BITMAP_ROW_SHIFT); a.abs16(0xCA, "command_row_shift")
    a.abs16(0xC3, "fatal")

    a.label("command_row")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "row_index")
    for mask_name in ("mask0", "mask1", "mask2", "mask3"):
        a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, mask_name)
    ld_a_mem(a, "row_index")
    a.emit(0x6F, 0x26, 0, 0x29)
    a.emit(0x11); a.abs16([], "row_addresses")
    a.emit(0x19, 0x4E, 0x23, 0x46)
    ld_a_mem(a, "update_base"); a.emit(0x80, 0x47, 0x3C, 0x57, 0x59)
    a.emit(0x21); a.abs16([], "dither_top")
    for group, mask_name in enumerate(("mask0", "mask1", "mask2", "mask3")):
        for bit in range(8):
            unchanged = f"unchanged_{group}_{bit}"
            ld_a_mem(a, mask_name); a.emit(0x87); ld_mem_a(a, mask_name)
            a.rel8(0x30, unchanged)
            a.emit(0xDD, 0x7E, 0, 0xDD, 0x23, 0x6F, 0x7E, 0x02, 0x24, 0x7E, 0x12, 0x25)
            a.label(unchanged)
            a.emit(0x03, 0x13)
    a.abs16(0xC3, "command_loop")

    a.label("command_points")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "row_index")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "point_count")
    ld_a_mem(a, "row_index")
    a.emit(0x6F, 0x26, 0, 0x29)
    a.emit(0x11); a.abs16([], "row_addresses")
    a.emit(0x19, 0x4E, 0x23, 0x46)
    ld_a_mem(a, "update_base"); a.emit(0x80, 0x47, 0x3C, 0x57, 0x59)
    a.emit(0xED, 0x43); a.abs16([], "point_top")
    a.emit(0xED, 0x53); a.abs16([], "point_bottom")
    a.label("point_loop")
    ld_a_mem(a, "point_count"); a.emit(0xB7); a.abs16(0xCA, "command_loop")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "point_column")
    a.emit(0xED, 0x4B); a.abs16([], "point_top")
    a.emit(0xED, 0x5B); a.abs16([], "point_bottom")
    ld_a_mem(a, "point_column"); a.emit(0x81, 0x4F)
    ld_a_mem(a, "point_column"); a.emit(0x83, 0x5F)
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23, 0x6F)
    a.emit(0x26, 0)  # dither_top page, patched after table placement
    # MiniAssembler has no high-byte fixup; replace the immediate after resolve.
    point_table_high_pos = len(a.code) - 1
    a.emit(0x7E, 0x02, 0x24, 0x7E, 0x12)
    ld_a_mem(a, "point_count"); a.emit(0x3D); ld_mem_a(a, "point_count")
    a.rel8(0x18, "point_loop")

    a.label("command_attrs")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "attr_count")
    a.label("attr_loop")
    ld_a_mem(a, "attr_count"); a.emit(0xB7); a.abs16(0xCA, "command_loop")
    a.emit(0xDD, 0x6E, 0, 0xDD, 0x23, 0xDD, 0x66, 0, 0xDD, 0x23)
    a.emit(0xED, 0x4B); a.abs16([], "attr_base")
    a.emit(0x09, 0xDD, 0x7E, 0, 0xDD, 0x23, 0x77)
    ld_a_mem(a, "attr_count"); a.emit(0x3D); ld_mem_a(a, "attr_count")
    a.rel8(0x18, "attr_loop")

    a.label("command_attrs_delta")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "attr_count")
    a.emit(0x21); a.word(0xFFFF); a.abs16(0x22, "attr_index")
    a.label("attr_delta_loop")
    ld_a_mem(a, "attr_count"); a.emit(0xB7); a.abs16(0xCA, "command_loop")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23, 0xFE, 0xFF)
    a.rel8(0x28, "attr_gap_wide")
    a.emit(0x5F, 0x16, 0); a.rel8(0x18, "attr_gap_ready")
    a.label("attr_gap_wide")
    a.emit(0xDD, 0x5E, 0, 0xDD, 0x23, 0xDD, 0x56, 0, 0xDD, 0x23)
    a.label("attr_gap_ready")
    a.emit(0x2A); a.abs16([], "attr_index")
    a.emit(0x23, 0x19); a.abs16(0x22, "attr_index")
    a.emit(0xED, 0x4B); a.abs16([], "attr_base")
    a.emit(0x09, 0xDD, 0x7E, 0, 0xDD, 0x23, 0x77)
    ld_a_mem(a, "attr_count"); a.emit(0x3D); ld_mem_a(a, "attr_count")
    a.rel8(0x18, "attr_delta_loop")

    a.label("command_row_rle")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "row_index")
    # The encoded byte length is useful to the host verifier; the player
    # terminates after exactly 32 decoded bytes.
    a.emit(0xDD, 0x23)
    ld_a_mem(a, "row_index")
    a.emit(0x6F, 0x26, 0, 0x29)
    a.emit(0x11); a.abs16([], "row_addresses")
    a.emit(0x19, 0x4E, 0x23, 0x46)
    ld_a_mem(a, "update_base"); a.emit(0x80, 0x47, 0x3C, 0x57, 0x59)
    a.emit(0x3E, source.LOGICAL_WIDTH // 4); ld_mem_a(a, "rle_remaining")
    a.label("rle_token_loop")
    ld_a_mem(a, "rle_remaining"); a.emit(0xB7); a.abs16(0xCA, "command_loop")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23, 0xCB, 0x7F)
    a.rel8(0x20, "rle_run")
    a.emit(0x3C); ld_mem_a(a, "rle_count")
    a.label("rle_literal_loop")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23)
    a.abs16(0xCD, "rle_write")
    ld_a_mem(a, "rle_count"); a.emit(0x3D); ld_mem_a(a, "rle_count")
    a.rel8(0x20, "rle_literal_loop")
    a.rel8(0x18, "rle_token_loop")
    a.label("rle_run")
    a.emit(0xE6, 0x7F, 0xC6, 2); ld_mem_a(a, "rle_count")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "rle_value")
    a.label("rle_run_loop")
    ld_a_mem(a, "rle_value"); a.abs16(0xCD, "rle_write")
    ld_a_mem(a, "rle_count"); a.emit(0x3D); ld_mem_a(a, "rle_count")
    a.rel8(0x20, "rle_run_loop")
    a.rel8(0x18, "rle_token_loop")
    a.label("rle_write")
    a.emit(0x6F, 0x26, 0)  # dither_top page, patched after placement
    rle_table_high_pos = len(a.code) - 1
    a.emit(0x7E, 0x02, 0x24, 0x7E, 0x12, 0x03, 0x13)
    ld_a_mem(a, "rle_remaining"); a.emit(0x3D); ld_mem_a(a, "rle_remaining")
    a.emit(0xC9)

    a.label("command_row_shift")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "row_index")
    a.emit(0xDD, 0x7E, 0, 0xDD, 0x23); ld_mem_a(a, "motion_shift")
    ld_a_mem(a, "row_index")
    a.emit(0x6F, 0x26, 0, 0x29)
    a.emit(0x11); a.abs16([], "row_addresses")
    a.emit(0x19, 0x4E, 0x23, 0x46)
    ld_a_mem(a, "update_base"); a.emit(0x80, 0x47, 0x3C, 0x57, 0x59)
    a.emit(0xED, 0x43); a.abs16([], "motion_top")
    a.emit(0xED, 0x53); a.abs16([], "motion_bottom")
    ld_a_mem(a, "motion_shift"); a.emit(0xCB, 0x7F)
    a.rel8(0x20, "motion_left")
    a.emit(0xED, 0x4B); a.abs16([], "motion_top")
    a.abs16(0xCD, "shift_right_row")
    a.emit(0xED, 0x4B); a.abs16([], "motion_bottom")
    a.abs16(0xCD, "shift_right_row")
    a.abs16(0xC3, "command_loop")
    a.label("motion_left")
    a.emit(0xED, 0x44); ld_mem_a(a, "motion_shift")
    a.emit(0xED, 0x4B); a.abs16([], "motion_top")
    a.abs16(0xCD, "shift_left_row")
    a.emit(0xED, 0x4B); a.abs16([], "motion_bottom")
    a.abs16(0xCD, "shift_left_row")
    a.abs16(0xC3, "command_loop")

    # Shift one physical 32-byte bitmap row. Input BC is its base address;
    # the small exposed edge is cleared and later sparse corrections replace it.
    a.label("shift_right_row")
    a.emit(0xC5, 0xC5, 0xE1)  # save base, HL = base
    a.emit(0x11); a.word(31); a.emit(0x19, 0xEB)  # DE = base + 31
    a.emit(0xE1, 0xC5)  # HL = base, keep base for clearing
    a.emit(0x01); a.word(31); a.emit(0x09)
    ld_a_mem(a, "motion_shift"); a.emit(0x4F, 0x7D, 0x91, 0x6F)
    ld_a_mem(a, "motion_shift"); a.emit(0x4F, 0x3E, 32, 0x91, 0x4F, 0x06, 0)
    a.emit(0xED, 0xB8)  # LDDR
    a.emit(0xE1)  # exposed left edge
    ld_a_mem(a, "motion_shift"); a.emit(0x4F, 0xAF)
    a.label("shift_right_clear")
    a.emit(0x77, 0x23, 0x0D); a.rel8(0x20, "shift_right_clear")
    a.emit(0xC9)

    a.label("shift_left_row")
    a.emit(0xC5, 0xC5, 0xC5, 0xE1)  # save base twice, HL = base
    ld_a_mem(a, "motion_shift"); a.emit(0x85, 0x6F)  # HL = base + shift
    a.emit(0xD1)  # DE = base
    ld_a_mem(a, "motion_shift"); a.emit(0x4F, 0x3E, 32, 0x91, 0x4F, 0x06, 0)
    a.emit(0xED, 0xB0)  # LDIR
    a.emit(0xE1)  # base for exposed right edge
    a.emit(0x11); a.word(32)
    ld_a_mem(a, "motion_shift"); a.emit(0x4F, 0x06, 0, 0xB7, 0xED, 0x42, 0x19)
    ld_a_mem(a, "motion_shift"); a.emit(0x4F, 0xAF)
    a.label("shift_left_clear")
    a.emit(0x77, 0x23, 0x0D); a.rel8(0x20, "shift_left_clear")
    a.emit(0xC9)

    a.label("flip_screen")
    ld_a_mem(a, "screen_flag"); a.emit(0xEE, 0x08); ld_mem_a(a, "screen_flag")
    a.emit(0xF6, PAGING_ROM48_BANK7, 0x01); a.word(0x7FFD)
    a.emit(0xED, 0x79, 0xC9)
    a.label("ay_apply")
    a.emit(0x3E, 7, 0x01); a.word(0xFFFD); a.emit(0xED, 0x79)
    a.emit(0x3E, 0x38, 0x06, 0xBF, 0xED, 0x79)
    a.emit(0x21); a.abs16([], "ay_state")
    for register in (0, 1, 2, 3, 4, 5, 8, 9, 10):
        a.emit(0x3E, register, 0x01); a.word(0xFFFD)
        a.emit(0xED, 0x79, 0x7E, 0x23, 0x06, 0xBF, 0xED, 0x79)
    a.emit(0xC9)

    a.label("read_n")
    ld_a_mem(a, "disk_track"); a.emit(0x57)
    ld_a_mem(a, "disk_sector"); a.emit(0x5F, 0x0E, 0x05)
    call_rom(a, 0x3D13); a.emit(0xF3)
    ld_a_mem(a, "screen_flag"); a.emit(0xF6, PAGING_ROM48_BANK7, 0x01); a.word(0x7FFD); a.emit(0xED, 0x79)
    ld_a_mem(a, "disk_sector"); a.emit(0x3C, 0xFE, 16); a.rel8(0x38, "store_sector")
    a.emit(0xAF); ld_mem_a(a, "disk_sector")
    ld_a_mem(a, "disk_track"); a.emit(0x3C); ld_mem_a(a, "disk_track"); a.emit(0xC9)
    a.label("store_sector"); ld_mem_a(a, "disk_sector"); a.emit(0xC9)

    a.label("finished")
    for register in (8, 9, 10):
        a.emit(0x3E, register, 0x01); a.word(0xFFFD); a.emit(0xED, 0x79, 0xAF, 0x06, 0xBF, 0xED, 0x79)
    a.emit(0xFB)
    a.label("finished_wait"); a.emit(0x76); a.rel8(0x18, "finished_wait")
    a.label("fatal"); a.emit(0x3E, 2, 0xD3, 0xFE); a.rel8(0x18, "fatal")

    for name, size in (
        ("screen_flag", 1), ("disk_track", 1), ("disk_sector", 1),
        ("frames_remaining", 2), ("packet_remaining", 1),
        ("hold_counter", 1), ("update_base", 1), ("attr_base", 2),
        ("disk_sectors_remaining", 2), ("startup_target", 2),
        ("ring_count", 2), ("ring_read_region", 1),
        ("ring_read_high", 1), ("ring_write_region", 1),
        ("ring_write_high", 1), ("sector_pointer", 2),
        ("row_index", 1), ("mask0", 1), ("mask1", 1), ("mask2", 1),
        ("mask3", 1), ("attr_count", 1), ("attr_index", 2),
        ("point_count", 1), ("point_column", 1), ("point_top", 2),
        ("point_bottom", 2), ("ay_state", source.AY_STATE_BYTES),
        ("rle_remaining", 1), ("rle_count", 1), ("rle_value", 1),
        ("motion_shift", 1), ("motion_top", 2), ("motion_bottom", 2),
    ):
        a.label(name); a.emit(*([0] * size))
    a.label("queue_banks"); a.emit(*RING_BANKS)
    a.label("row_addresses")
    for y in range(source.LOGICAL_HEIGHT):
        top = base.spectrum_bitmap_offset(0, y * 2)
        bottom = base.spectrum_bitmap_offset(0, y * 2 + 1)
        if bottom != top + 0x100:
            raise AssertionError("native row pair is not 0100h apart")
        a.word(top)
    while a.pc & 0xFF:
        a.emit(0)
    a.label("dither_top"); a.emit(*source.PLAYER_DITHER_TOP)
    a.label("dither_bottom"); a.emit(*source.PLAYER_DITHER_BOTTOM)
    a.code[point_table_high_pos] = (a.labels["dither_top"] >> 8) & 0xFF
    a.code[rle_table_high_pos] = (a.labels["dither_top"] >> 8) & 0xFF
    code = a.resolve()
    if LOAD_ADDRESS + len(code) >= BUFFER:
        raise ValueError(f"fast player overlaps buffer: {len(code)} bytes")
    return code, dict(a.labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_stream = args.source_build / "VIDEO_full.C.bin"
    metadata = json.loads((args.source_build / "build_metadata.json").read_text())
    states, ay_states, frame_rate = decode_compact_build(source_stream)
    args.output.mkdir(parents=True, exist_ok=True)

    boot = streaming.build_boot_basic()
    provisional, _ = build_player(0, 0)
    preceding = [
        base.TrdFile("boot", "B", boot, basic_variables_offset=len(boot), autostart_line=10),
        base.TrdFile("PLAYER", "C", provisional, start=LOAD_ADDRESS),
    ]
    video_track, video_sector = streaming.calculate_file_start(preceding)
    player, labels = build_player(video_track, video_sector)
    boot_sectors = math.ceil((len(boot) + 4) / base.SECTOR_SIZE)
    player_sectors = math.ceil(len(player) / base.SECTOR_SIZE)
    limit = TRD_DATA_SECTORS - boot_sectors - player_sectors

    volumes: list[dict[str, object]] = []
    start = 0
    all_sector_counts: list[int] = []
    rle_frames = 0
    rle_rows = 0
    motion_frames = 0
    motion_rows = 0
    rle_sectors_saved = 0
    packing_sectors_saved = 0
    packet_padding_bytes = 0
    while start < len(states):
        end, packets = make_volume_packets(states, ay_states, start, limit)
        video = serialize_volume(packets, frame_rate)
        chunks = [
            video[offset:offset + MAX_TRDOS_FILE_SECTORS * base.SECTOR_SIZE]
            for offset in range(0, len(video), MAX_TRDOS_FILE_SECTORS * base.SECTOR_SIZE)
        ]
        files = [
            base.TrdFile("boot", "B", boot, basic_variables_offset=len(boot), autostart_line=10),
            base.TrdFile("PLAYER", "C", player, start=LOAD_ADDRESS),
        ] + [base.TrdFile(f"VIDEO{i:03d}", "C", chunk, start=0) for i, chunk in enumerate(chunks)]
        index = len(volumes) + 1
        trd, directory, stats = streaming.place_files(files, f"FST{index:02d}")
        name = f"big_buck_bunny_2min_zx_fast_sparse_25over3fps_part{index:02d}.trd"
        (args.output / name).write_bytes(trd)
        counts = [packet.sector_count for packet in packets]
        startup_backlog = minimum_startup_backlog(counts)
        all_sector_counts += counts
        rle_frames += sum(packet.rle_rows > 0 for packet in packets)
        rle_rows += sum(packet.rle_rows for packet in packets)
        motion_frames += sum(packet.motion_rows > 0 for packet in packets)
        motion_rows += sum(packet.motion_rows for packet in packets)
        rle_sectors_saved += sum(packet.sectors_saved for packet in packets)
        packing_sectors_saved += sum(packet.packing_sectors_saved for packet in packets)
        packet_padding_bytes += sum(packet.padding_bytes for packet in packets)
        volumes.append({
            "index": index, "trd_name": name, "frame_start": start,
            "frame_end": end, "frames": end - start,
            "packet_sectors": counts,
            "packet_sector_total": sum(counts),
            "startup_backlog_sectors": startup_backlog,
            "ring_capacity_sectors": RING_CAPACITY_SECTORS,
            "directory": directory, "trd_stats": stats,
        })
        start = end

    (args.output / "PLAYER.C.bin").write_bytes(player)
    output_metadata = {
        "profile": "banked_ring_fast_sparse_direct_screen", "frame_rate": frame_rate,
        "frames": len(states), "player_labels": labels, "player_bytes": len(player),
        "video_track": video_track, "video_sector": video_sector,
        "volumes": volumes, "trd_names": [v["trd_name"] for v in volumes],
        "packet_sector_mean": sum(all_sector_counts) / len(all_sector_counts),
        "packet_sector_max": max(all_sector_counts),
        "packets_over_six": sum(value > 6 for value in all_sector_counts),
        "ring_capacity_sectors": RING_CAPACITY_SECTORS,
        "disk_sectors_per_frame": FIELDS_PER_FRAME,
        "cycle_model": {
            "unit": "Z80 T-states",
            "scope": "bitmap row-pair address setup, excluding command dispatch",
            "previous": ROW_ADDRESS_SETUP_CYCLES_PREVIOUS,
            "current": ROW_ADDRESS_SETUP_CYCLES_CURRENT,
            "saved_per_row_command": (
                ROW_ADDRESS_SETUP_CYCLES_PREVIOUS - ROW_ADDRESS_SETUP_CYCLES_CURRENT
            ),
            "saved_percent": round(
                100 * (ROW_ADDRESS_SETUP_CYCLES_PREVIOUS - ROW_ADDRESS_SETUP_CYCLES_CURRENT)
                / ROW_ADDRESS_SETUP_CYCLES_PREVIOUS,
                1,
            ),
            "disk_rom_and_physical_latency_included": False,
        },
        "rle_frames": rle_frames,
        "rle_rows": rle_rows,
        "motion_frames": motion_frames,
        "motion_rows": motion_rows,
        "rle_sectors_saved": rle_sectors_saved,
        "packing_sectors_saved": packing_sectors_saved,
        "packet_padding_bytes": packet_padding_bytes,
        "source_metadata": metadata,
    }
    (args.output / "build_metadata.json").write_text(json.dumps(output_metadata, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in output_metadata.items() if key not in ("volumes", "source_metadata")}, indent=2))
    for volume in volumes:
        print(f"part {volume['index']}: frames {volume['frame_start']}..{int(volume['frame_end']) - 1}")


if __name__ == "__main__":
    main()
