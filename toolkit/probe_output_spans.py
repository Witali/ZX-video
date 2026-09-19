"""Exact n-2 native-screen updates described as runs of compact byte pairs.

Each row: row index (bitmap 0..95, attributes 128..151), span count,
then (start_pair << 4 | length_pairs-1) bytes. FF terminates a frame.
Values remain in the reconstructed compact screen, never in this stream.
This storage probe does not itself implement or time a Spectrum player.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_lossless_layouts import sha, measure


def runs(active, gap=0):
    positions = np.flatnonzero(active)
    if not len(positions):
        return []
    first = last = int(positions[0])
    result = []
    for value in positions[1:]:
        value = int(value)
        if value-last > gap+1:
            result.append((first, last-first+1))
            first = value
        last = value
    result.append((first, last-first+1))
    return result


def encode_frame(current, previous, gap=0):
    if len(current) != 3840 or len(previous) != 3840 or not 0 <= gap <= 15:
        raise ValueError('invalid compact frame or merge gap')
    changed = (np.frombuffer(current, dtype=np.uint8) != np.frombuffer(previous, dtype=np.uint8))
    pairs = changed.reshape(120, 16, 2).any(axis=2)
    out, spans, bitmap_bytes, attr_bytes = bytearray(), 0, 0, 0
    for row, active in enumerate(pairs):
        segments = runs(active, gap)
        if not segments:
            continue
        out.extend((row if row < 96 else row+32, len(segments)))
        for start, length in segments:
            out.append(start*16+length-1)
            spans += 1
            if row < 96:
                bitmap_bytes += 2*length
            else:
                attr_bytes += 2*length
    out.append(255)
    return bytes(out), dict(spans=spans, bitmap_bytes=bitmap_bytes, attribute_bytes=attr_bytes)


def replay(data, current, previous):
    screen, pos, last_row = bytearray(previous), 0, -1
    while pos < len(data):
        tag = data[pos]; pos += 1
        if tag == 255:
            if pos != len(data):
                raise ValueError('trailing data')
            return bytes(screen)
        row = tag if tag < 96 else tag-32 if 128 <= tag < 152 else -1
        if row <= last_row or pos == len(data):
            raise ValueError('invalid row order or truncated command')
        count = data[pos]; pos += 1
        if not 1 <= count <= 8 or pos+count >= len(data):
            raise ValueError('invalid span count')
        end = 0
        for descriptor in data[pos:pos+count]:
            first, length = descriptor >> 4, (descriptor & 15)+1
            if first < end or first+length > 16:
                raise ValueError('overlapping/out-of-range spans')
            begin = row*32+2*first
            screen[begin:begin+2*length] = current[begin:begin+2*length]
            end = first+length
        pos += count
        last_row = row
    raise ValueError('missing terminator')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--gap', type=int, default=1)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    if states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840:
        raise ValueError('invalid states')
    screens = [bytes(3840), bytes(3840)]
    parts, rows, offset = [], [], 0
    for index, state in enumerate(states):
        current = state.tobytes()
        data, detail = encode_frame(current, screens[index % 2], args.gap)
        if replay(data, current, screens[index % 2]) != current:
            raise AssertionError('screen mismatch')
        screens[index % 2] = current
        rows.append(dict(index=index, offset=offset, bytes=len(data), **detail))
        parts.append(data); offset += len(data)
    data = b''.join(parts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    report = dict(scope=__doc__, complete=True, states_sha256=sha(states.tobytes()),
        stream_sha256=sha(data), frames=len(states), gap=args.gap, raw_bytes=len(data),
        deflate_8192_bytes=measure(data, 8192), exact_screen_replay=True,
        summary={k: dict(total=sum(r[k] for r in rows), mean=sum(r[k] for r in rows)/len(rows),
                        maximum=max(r[k] for r in rows)) for k in ('spans', 'bitmap_bytes', 'attribute_bytes')},
        rows=rows, player_changed=False, integrated_player_delta_tstates=0,
        full_frame_delivery_measured=False)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
