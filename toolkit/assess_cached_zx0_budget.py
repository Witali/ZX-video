"""Reject an over-budget experiment from verified completed ZX0 blocks.

Recreate the exact greedy partition from the source and 50 Hz audio. Only
matching cache entries count. Missing blocks count as zero, so even an
interrupted experiment can establish a conservative storage lower bound.
This is not a lower bound for different layouts or compression algorithms.
"""
import argparse
import hashlib
import json
from pathlib import Path

import ay_interrupt
import build_fast_sparse_trd as codec
import build_long_video_trd as video
import packed_stream
import zx0_codec


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-build', type=Path, required=True)
    p.add_argument('--ay-50hz', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--budget', type=int, default=1291776)
    args = p.parse_args()
    source_path = args.source_build / 'VIDEO_full.C.bin'
    states, old_audio, fps = codec.decode_compact_build(source_path)
    raw = args.ay_50hz.read_bytes()
    if len(raw) != len(states) * 54 or abs(fps - 25 / 3) > 1e-6:
        raise ValueError('requires six 50 Hz ticks for every video frame')
    audio = [video.AyFrame.deserialize(raw[i:i + 9]) for i in range(0, len(raw), 9)]
    ticks = ay_interrupt.encode_ticks(audio)
    _, packets = codec.make_volume_packets(states, old_audio, 0, 0x100000, packed=True)
    groups = []
    pending = bytearray()
    count = 0
    for index, packet in enumerate(packets):
        frame = packed_stream.frame_bytes(packet, natural_order=True, audio_payload=b''.join(ticks[index * 6:index * 6 + 6]))
        if len(frame) > 8192:
            raise ValueError('frame exceeds block size')
        if pending and len(pending) + len(frame) > 8192:
            groups.append((bytes(pending), count))
            pending.clear()
            count = 0
        pending += frame
        count += 1
    if pending:
        groups.append((bytes(pending), count))
    known = []
    missing = []
    for index, (decoded, count) in enumerate(groups):
        digest = sha(decoded)
        cache_path = args.cache / (digest + '.zx0')
        if not cache_path.exists():
            missing.append(index)
            continue
        encoded = cache_path.read_bytes()
        # An interrupted encoder may leave a partial file. It is not evidence.
        try:
            restored = zx0_codec.decompress(encoded)
        except ValueError:
            missing.append(index)
            continue
        if restored != decoded:
            raise ValueError('cache does not reconstruct the expected block')
        known.append(dict(index=index, frames=count, decoded_sha256=digest,
                          zx0_sha256=sha(encoded), decoded_bytes=len(decoded),
                          stored_bytes=min(len(encoded), len(decoded)) + 4))
    minimum = 256 + sum(block['stored_bytes'] for block in known)
    report = dict(scope=__doc__, source_sha256=sha(source_path.read_bytes()),
                  states_sha256=sha(b''.join(states)), audio_sha256=sha(raw),
                  frames=len(states), audio_ticks=len(audio), frame_rate=fps,
                  block_bytes=8192, audio_format='pairs', dense_video=False,
                  total_blocks=len(groups), verified_blocks=len(known),
                  complete=not missing, missing_blocks=missing,
                  budget_bytes=args.budget, minimum_stream_bytes=minimum,
                  exceeds_budget=minimum > args.budget,
                  additional_volume_headers_or_keyframes_included=False,
                  verified=known)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ('verified', 'missing_blocks')}, indent=2))


if __name__ == '__main__':
    main()
