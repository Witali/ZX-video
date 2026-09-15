"""Byte-contiguous v7 frames and their Z80 transport (screen commands are v6)."""
from __future__ import annotations

import struct
import direct_ring_input

MAGIC = b"ZXFP"
VERSION = 7
FRAME_BUFFER = 0xA000
FRAME_BUFFER_BYTES = 0x2000
FIXED_RING_SECTORS = 32
RING_CAPACITY_SECTORS = FIXED_RING_SECTORS + 5 * 64


def sector_records(sector: bytes, first: bool) -> list[bytes]:
    """Read complete v6 commands, without mistaking zero-valued data for END."""
    if len(sector) != 256:
        raise ValueError("expected one sector")
    position = 12 if first else 0
    records = []
    while position < len(sector):
        start = position
        command = sector[position]
        position += 1
        if command == 0:
            if any(sector[position:]):
                raise ValueError("nonzero sector padding")
            return records
        if command == 1:
            position += 5 + int.from_bytes(sector[position + 1:position + 5], "big").bit_count()
        elif command in (2, 4):
            count = sector[position]
            position += 1
            if command == 2:
                position += 3 * count
            else:
                for _ in range(count):
                    wide = sector[position] == 255
                    position += 4 if wide else 2
        elif command == 3:
            position += 2 + 2 * sector[position + 1]
        elif command == 5:
            position += 2 + sector[position + 1]
        elif command == 6:
            position += 2
        elif command == 7:
            count = sector[position + 1]
            position += 2
            for _ in range(count):
                position += 2 + (sector[position] & 15)
        elif command == 8:
            position += 1
        else:
            raise ValueError(f"unknown command {command}")
        if position >= len(sector):
            raise ValueError("command crosses sector END")
        records.append(sector[start:position])
    raise ValueError("missing sector END")


def frame_bytes(packet, *, natural_order: bool = False) -> bytes:
    records = [record for i, sector in enumerate(packet.sectors)
               for record in sector_records(sector, i == 0)]
    if natural_order:
        # Stable sorting retains a row predictor before its correction.
        records.sort(key=lambda record: 256 if record[0] in (2, 4) else record[1])
    payload = packet.ay_state + b"".join(records) + b"\0"
    if not 10 <= len(payload) < FRAME_BUFFER_BYTES:
        raise ValueError("frame exceeds fixed decode buffer")
    return struct.pack("<H", len(payload)) + payload


def sector_demands(lengths: list[int]) -> list[int]:
    """Additional disk sectors needed by each frame, including a shared tail."""
    position = 0
    previous = 0
    result = []
    for length in lengths:
        position += length
        required = (position + 255) // 256
        result.append(required - previous)
        previous = required
    return result


def minimum_startup_backlog(lengths: list[int], capacity: int = RING_CAPACITY_SECTORS) -> int:
    """Simulate ownership of partially consumed sectors, including end of disk."""
    total = (sum(lengths) + 255) // 256
    for initial in range(min(capacity, total) + 1):
        produced = initial
        position = 0
        for index, length in enumerate(lengths):
            position += length
            if produced < (position + 255) // 256:
                break
            if index:
                produced = min(total, produced + 6, position // 256 + capacity)
        else:
            return initial
    raise ValueError("frame sequence exceeds packed ring capacity")


def emit_transport(a, *, blocked: bool = False, input_limit=FRAME_BUFFER_BYTES, lookahead=False, direct_input=False) -> None:
    """Emit header reads and whole-frame copies from the banked sector ring."""
    def load(name):
        a.abs16(0x3A, name)

    def save(name):
        a.abs16(0x32, name)

    a.label("load_block_header" if blocked else "wait_packet")
    a.abs16(0xCD, "stream_byte"); save("frame_length")
    a.abs16(0xCD, "stream_byte"); save("frame_length_high")
    if blocked:
        a.emit(0xE6, 0x80); save("block_stored")
        load("frame_length_high"); a.emit(0xE6, 0x7F); save("frame_length_high")
        a.abs16(0xCD, "stream_byte"); save("block_length")
        a.abs16(0xCD, "stream_byte"); save("block_length_high")
    # Bounds are checked before any copy to A000h..BFFFh.
    a.abs16(0x2A, "frame_length")
    a.emit(0x7C, 0xFE, input_limit >> 8)
    if blocked:
        a.rel8(0x38, "block_size_below_limit")
        a.abs16(0xC2, "fatal")
        a.emit(0x7D, 0xB7); a.abs16(0xC2, "fatal")
        a.rel8(0x18, "frame_length_valid")
        a.label("block_size_below_limit")
        a.emit(0x7C)
    else:
        a.abs16(0xD2, "fatal")
    a.emit(0xB7); a.rel8(0x20, "frame_length_valid")
    a.emit(0x7D, 0xFE, 1 if blocked else 10); a.abs16(0xDA, "fatal")
    a.label("frame_length_valid")
    load("ring_read_low"); a.emit(0x5F, 0x16, 0, 0x19, 0x2B, 0x7C, 0x3C)
    save("frame_sector_need")
    a.label("wait_packet_check")
    load("frame_sector_need"); a.emit(0x47)
    a.abs16(0x2A, "ring_count")
    a.emit(0x7C, 0xB7, 0xC0, 0x7D, 0xB8, 0xD0)
    a.label("wait_packet_fill")
    a.abs16(0xCD, "wait_field"); a.abs16(0xCD, "producer_one")
    a.rel8(0x18, "wait_packet_check")

    a.label("stream_byte")
    a.abs16(0x2A, "ring_count"); a.emit(0x7C, 0xB5)
    a.rel8(0x20, "stream_byte_ready")
    a.label("stream_byte_fill")
    a.abs16(0xCD, "wait_field"); a.abs16(0xCD, "producer_one")
    a.rel8(0x18, "stream_byte")
    a.label("stream_byte_ready")
    a.abs16(0xCD, "prepare_read_sector")
    load("ring_read_low"); a.emit(0x6F, 0x7E, 0xF5)
    load("ring_read_low"); a.emit(0x3C); save("ring_read_low")
    a.abs16(0xCC, "consume_sector")
    a.abs16(0xCD, "page_bank7"); a.emit(0xF1, 0xC9)

    a.label("load_block_body" if blocked else "ring_packet")
    if direct_input:direct_ring_input.emit_load(a)
    a.abs16(0x2A, "frame_length"); a.abs16(0x22, "frame_remaining")
    a.emit(0x21); a.word(FRAME_BUFFER); a.abs16(0x22, "frame_destination")
    a.label("frame_copy_loop")
    if lookahead:a.abs16(0xCD,'ahead_checkpoint')
    # The paged source is copied directly into fixed RAM. Unlike v6, no
    # intermediate BF00h staging copy is needed before the frame copy.
    a.abs16(0xCD, "prepare_read_sector")
    load("ring_read_low"); a.emit(0xED, 0x44, 0x4F, 0x06, 0)
    a.rel8(0x20, "frame_chunk_limit"); a.emit(0x04)
    a.label("frame_chunk_limit")
    a.abs16(0x2A, "frame_remaining"); a.emit(0xB7, 0xED, 0x42)
    a.rel8(0x30, "frame_chunk_ready")
    a.abs16((0xED, 0x4B), "frame_remaining")
    a.label("frame_chunk_ready")
    a.abs16((0xED, 0x43), "frame_chunk")
    a.abs16(0x2A, "sector_pointer")
    load("ring_read_low"); a.emit(0x6F)
    a.abs16((0xED, 0x5B), "frame_destination")
    a.emit(0xED, 0xB0)
    a.abs16((0xED, 0x53), "frame_destination")
    a.abs16(0x2A, "frame_remaining")
    a.abs16((0xED, 0x4B), "frame_chunk")
    a.emit(0xB7, 0xED, 0x42); a.abs16(0x22, "frame_remaining")
    load("ring_read_low"); a.emit(0x81); save("ring_read_low")
    a.abs16(0xCC, "consume_sector")
    a.abs16(0x2A, "frame_remaining"); a.emit(0x7C, 0xB5)
    a.abs16(0xC2, "frame_copy_loop")
    a.abs16(0xCD, "page_bank7")
    if blocked:
        a.emit(0xC9)
        return
    a.emit(0x21); a.word(FRAME_BUFFER)
    a.abs16(0x11, "ay_state")
    a.emit(0x01); a.word(9); a.emit(0xED, 0xB0)
    a.emit(0xDD, 0x21); a.word(FRAME_BUFFER + 9)
    a.abs16(0xCD, "command_loop"); a.emit(0xC9)


def emit_prepare_sector(a) -> None:
    a.label("prepare_read_sector")
    a.abs16(0x3A, "ring_read_region"); a.emit(0xB7)
    a.rel8(0x28, "prepare_fixed")
    a.abs16(0xCD, "page_queue_region")
    a.label("prepare_fixed")
    a.abs16(0x3A, "ring_read_high"); a.emit(0x67, 0x2E, 0)
    a.abs16(0x22, "sector_pointer"); a.emit(0xC9)


def emit_variables(a) -> None:
    for name, size in (("ring_read_low", 1), ("frame_length", 2),
                       ("frame_sector_need", 1), ("frame_remaining", 2),
                       ("frame_destination", 2), ("frame_chunk", 2)):
        a.label(name); a.emit(*([0] * size))
    a.labels["frame_length_high"] = a.labels["frame_length"] + 1
