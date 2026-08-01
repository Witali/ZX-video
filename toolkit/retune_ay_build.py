#!/usr/bin/env python3
"""Replace fixed-size AY states in an existing compact video build."""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_long_video_trd as video  # noqa: E402
import build_zxv_trd as base  # noqa: E402


def replace_ay_states(stream: bytes, frames: list[video.AyFrame]) -> bytes:
    result = bytearray(stream)
    if result[:4] != video.VIDEO_MAGIC:
        raise ValueError("not a compact ZXVL stream")
    frame_count = struct.unpack_from("<H", result, 8)[0]
    if frame_count != len(frames):
        raise ValueError(f"audio/video frame mismatch: {len(frames)} vs {frame_count}")
    offset = base.SECTOR_SIZE
    for index, frame in enumerate(frames):
        sectors = result[offset]
        payload_length = struct.unpack_from("<H", result, offset + 2)[0]
        ay_length = result[offset + 4]
        if ay_length != video.AY_STATE_BYTES:
            raise ValueError(f"frame {index} has an unsupported AY state size")
        ay_first = offset + video.PACKET_HEADER_BYTES
        payload_first = ay_first + ay_length
        payload = result[payload_first:payload_first + payload_length]
        ay_state = frame.serialize()
        result[ay_first:payload_first] = ay_state
        struct.pack_into(
            "<H",
            result,
            offset + 6,
            (sum(ay_state) + sum(payload)) & 0xFFFF,
        )
        offset += sectors * base.SECTOR_SIZE
    if offset != len(result):
        raise ValueError("trailing compact stream data")
    return bytes(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-video", type=Path, required=True)
    parser.add_argument("--source-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--fps", type=video.parse_rate, default=video.parse_rate("25/3"))
    args = parser.parse_args()

    frames, stats = video.analyse_ay_frames(
        args.input_video, args.start, args.duration, args.fps
    )
    source_stream = (args.source_build / "VIDEO_full.C.bin").read_bytes()
    tuned_stream = replace_ay_states(source_stream, frames)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "VIDEO_full.C.bin").write_bytes(tuned_stream)
    metadata_path = args.source_build / "build_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["ay"] = stats
    metadata.setdefault("stats", {})["ay"] = stats
    (args.output / "build_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    wav_path = args.output / "big_buck_bunny_zx_ay_melody_preview.wav"
    video.write_ay_preview(wav_path, frames, args.fps)
    silent_preview = args.source_build / "big_buck_bunny_zx_dithered_preview.mp4"
    if silent_preview.exists():
        video.mux_ay_preview(
            silent_preview,
            wav_path,
            args.output / "big_buck_bunny_zx_dithered_ay_melody_preview.mp4",
            args.fps,
        )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
