"""Audit packed levels and actual palette use in saved full-movie states.

Reads conversion/candidate NPZ files only. No re-encoding, pixel changes,
player changes, compression estimates or claims about physical luminance.
Four levels are INK coverage in 2x2 patterns, not a global gray palette.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import build_long_video_trd as video


def inspect(path, expected_frames):
    with np.load(path, allow_pickle=False) as saved:
        states = saved['states']
    if states.dtype != np.uint8 or states.shape != (expected_frames, video.STATE_BYTES):
        raise ValueError(f'unexpected state shape/dtype: {path}')
    # Rows are attribute bytes, columns are the four 2-bit codes.
    joint = np.zeros((256, 4), dtype=np.int64)
    active_joint = np.zeros_like(joint)
    for first in range(0, len(states), 64):
        batch = states[first:first+64]
        packed = batch[:, :video.STATE_LEVEL_BYTES].reshape(-1, 96, 32)
        levels = ((packed[..., None] >> np.array([6, 4, 2, 0])) & 3).reshape(-1, 96, 128)
        attrs = batch[:, video.STATE_LEVEL_BYTES:].reshape(-1, 24, 32)
        attrs = attrs.repeat(4, axis=1).repeat(4, axis=2)
        pairs = attrs.astype(np.int16)*4+levels
        joint += np.bincount(pairs.ravel(), minlength=1024).reshape(256, 4)
        active = pairs[:, video.ACTIVE_Y0:video.ACTIVE_Y0+video.ACTIVE_HEIGHT]
        active_joint += np.bincount(active.ravel(), minlength=1024).reshape(256, 4)
    if joint.sum() != len(states)*96*128 or active_joint.sum() != len(states)*72*128:
        raise AssertionError('incomplete pixel coverage')
    attrs_used = np.flatnonzero(joint.sum(axis=1))
    if any(int(a) & 128 for a in attrs_used):
        raise ValueError('FLASH requires a time-dependent palette audit')
    colours = set()
    for attr in attrs_used:
        bright = (int(attr) >> 6) & 1
        if joint[attr, 1:].sum():
            colours.add(tuple(int(c) for c in video.base.zx_rgb(int(attr) & 7, bright)))
        if joint[attr, :3].sum():
            colours.add(tuple(int(c) for c in video.base.zx_rgb((int(attr) >> 3) & 7, bright)))
    return dict(input=str(path), frames=len(states), states_sha256=hashlib.sha256(states.tobytes()).hexdigest(),
        bitmap_bytes_per_frame=video.STATE_LEVEL_BYTES, attribute_bytes_per_frame=video.STATE_ATTR_BYTES,
        full_frame_level_counts=joint.sum(axis=0).tolist(), active_area_level_counts=active_joint.sum(axis=0).tolist(),
        used_level_codes=np.flatnonzero(joint.sum(axis=0)).tolist(), used_attribute_bytes=attrs_used.tolist(),
        used_attribute_count=len(attrs_used), native_rgb_colours=[list(c) for c in sorted(colours)],
        native_rgb_colour_count=len(colours))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, nargs='+', required=True)
    p.add_argument('--expected-frames', type=int, default=4971)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    top, bottom = video.build_player_dither_tables()
    patterns = []
    for level in range(4):
        packed = level*0x55
        upper, lower = top[packed] >> 6, bottom[packed] >> 6
        ink_dots = upper.bit_count()+lower.bit_count()
        patterns.append(dict(code=level, top=f'{upper:02b}', bottom=f'{lower:02b}', ink_dots=ink_dots,
                             ink_coverage=ink_dots/4))
    if [p['ink_dots'] for p in patterns] != [0, 1, 2, 4]:
        raise AssertionError('player patterns changed; revisit four-level interpretation')
    report = dict(scope=__doc__, complete=True, logical_size=[128, 96], native_size=[256, 192],
        active_native_size=[256, 144], bits_per_logical_pixel=2, patterns=patterns,
        palette_scope='INK/PAPER/BRIGHT per native 8x8 cell; no global four-gray palette',
        integrated_player_delta_tstates=0, rows=[inspect(p, args.expected_frames) for p in args.inputs])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
