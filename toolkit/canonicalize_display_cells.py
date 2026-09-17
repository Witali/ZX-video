"""Remove equivalent encodings without changing any displayed RGB pixel.

Uniform 8x8 cells need only PAPER; two-colour cells using logical levels 0/3
can exchange INK and PAPER if their bitmap is complemented. This is not
quantization: all 256x192 displayed pixels are compared on every frame.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import build_fast_sparse_trd as codec
import build_long_video_trd as video


def sha(data):
    return hashlib.sha256(data).hexdigest()


def to_cells(state):
    state = np.frombuffer(state, dtype=np.uint8)
    pixels = state[:3072].reshape(24, 4, 32).transpose(0, 2, 1).reshape(768, 4)
    return np.column_stack((pixels, state[3072:]))


def from_cells(cells):
    pixels = cells[:, :4].reshape(24, 32, 4).transpose(0, 2, 1).reshape(-1)
    return pixels.tobytes() + cells[:, 4].tobytes()


def displayed_colours(cells):
    """Native pixels as palette indices; normal/bright black are identical."""
    top = np.frombuffer(video.PLAYER_DITHER_TOP, dtype=np.uint8)[cells[:, :4]]
    bottom = np.frombuffer(video.PLAYER_DITHER_BOTTOM, dtype=np.uint8)[cells[:, :4]]
    rows = np.stack((top, bottom), axis=2).reshape(768, 8)
    bits = np.unpackbits(rows, axis=1).reshape(768, 8, 8)
    attrs = cells[:, 4]
    if np.any(attrs & 128):
        raise ValueError('FLASH cells require verification of both phases')
    bright = (attrs >> 3) & 8
    ink = (attrs & 7) | bright
    paper = ((attrs >> 3) & 7) | bright
    ink[ink == 8] = 0
    paper[paper == 8] = 0
    return np.where(bits, ink[:, None, None], paper[:, None, None])


def canonicalize(state):
    cells = to_cells(state)
    result = cells.copy()
    attrs = cells[:, 4]
    bright = (attrs >> 3) & 8
    ink = (attrs & 7) | bright
    paper = ((attrs >> 3) & 7) | bright
    ink[ink == 8] = 0
    paper[paper == 8] = 0
    paper_only = np.all(cells[:, :4] == 0, axis=1) | (ink == paper)
    ink_only = np.all(cells[:, :4] == 255, axis=1)
    uniform = paper_only | ink_only
    colour = np.where(paper_only, paper, ink)
    result[uniform, :4] = 0
    result[uniform, 4] = ((colour[uniform] & 7) << 3) | ((colour[uniform] & 8) << 3)
    binary = np.all(((cells[:, :4] ^ (cells[:, :4] >> 1)) & 0x55) == 0, axis=1)
    swapped_attr = (attrs & 64) | ((attrs & 7) << 3) | ((attrs >> 3) & 7)
    swap = ~uniform & binary & (swapped_attr < attrs)
    result[swap, :4] ^= 255
    result[swap, 4] = swapped_attr[swap]
    if not np.array_equal(displayed_colours(cells), displayed_colours(result)):
        raise AssertionError('displayed RGB changed')
    return from_cells(result), int(np.count_nonzero(np.any(cells != result, axis=1)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    states, sound, fps = codec.decode_compact_build(args.source_build / 'VIDEO_full.C.bin')
    output = []
    changes = 0
    for index, state in enumerate(states):
        converted, changed = canonicalize(state)
        output.append(converted)
        changes += changed
        if index % 500 == 0:
            print(f'Verified native RGB frame {index}/{len(states)}', flush=True)
    packets = [video.make_packet(state, output[index - 1] if index else None, sound[index])
               for index, state in enumerate(output)]
    stream = video.serialize_video(packets, fps, fps)
    video.verify_video(stream, output)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'VIDEO_full.C.bin').write_bytes(stream)
    restored, restored_sound, restored_fps = codec.decode_compact_build(args.output / 'VIDEO_full.C.bin')
    if restored != output or restored_sound != sound or restored_fps != fps:
        raise AssertionError('written compact stream differs from the verified source')
    np.savez(args.output / 'conversion.npz', states=np.frombuffer(b''.join(output), dtype=np.uint8).reshape(-1, 3840))
    metadata = json.loads((args.source_build / 'build_metadata.json').read_text())
    report = dict(scope=__doc__, frames=len(states), frame_rate=fps,
                  logical_resolution=[128, 96], screen_resolution=[256, 192],
                  original_states_sha256=sha(b''.join(states)), states_sha256=sha(b''.join(output)),
                  changed_cells=changes, total_cells=len(states) * 768,
                  all_native_pixels_identical=True, source_ay_bytes_identical=True,
                  player_instruction_delta_tstates=0)
    metadata['display_canonicalization'] = report
    metadata['logical_states_sha256'] = report['states_sha256']
    metadata['last_state_sha256'] = sha(output[-1])
    (args.output / 'build_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    (args.output / 'canonicalization.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
