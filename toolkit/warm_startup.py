"""Continuation-only startup sections; preserve tables and the compact n-1.

The fixed-RAM reset list covers the write contracts of PipelineClockCPU,
FrameStreamCPU and PipelineCPU, plus both fixed stacks. Bank 6 is read-only.
All other startup regions are restored normally. This is an experimental
storage option, not proof of a complete sequential playback or frame timing.
"""
import struct

import pipelined_frame_z80 as video
import banked_zx0


def reset_ranges(h):
    ranges = list(h.cpu.state_regions)
    ranges += [(0x7300,0x7800), (banked_zx0.STACK_BOTTOM,banked_zx0.STACK_TOP),
               (h.z['state'],h.z['ring_banks']),
               (h.audio['state'], h.audio['end']), (video.STATE, video.STATE_END),
               (0x9b00, 0x9e00)]  # disk stack, foreground/IRQ stack, row-low table
    ranges += [(p, p+1) for p in h.cpu.patches]
    ranges = sorted((max(0x7300, lo), min(0xa000, hi)) for lo, hi in ranges
                    if lo < 0xa000 and hi > 0x7300)
    merged = []
    for lo, hi in ranges:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
        else:
            merged.append((lo, hi))
    return merged


def encode_reset(fixed, ranges):
    result = bytearray()
    for lo, hi in ranges:
        result += struct.pack('<HH', hi-lo, lo) + fixed[lo-0x4000:hi-0x4000]
    result += bytes(2)
    if len(result) > 6912:
        raise ValueError('warm reset exceeds temporary screen buffer')
    return bytes(result)


def immutable_fixed(fixed, ranges):
    result = bytearray(fixed[0x3300:0x6000])
    for lo, hi in ranges:
        result[lo-0x7300:hi-0x7300] = bytes(hi-lo)
    return bytes(result)
