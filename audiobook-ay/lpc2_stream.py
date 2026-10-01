"""Independent strict reader for the existing LPC2 v1 bitstream (LSB first)."""
from __future__ import annotations

import hashlib
import json
import math
import struct


def read_stream(blob):
    if len(blob) < 36:
        raise ValueError('truncated header')
    magic, version, order, rate, hop, window, count, samples, bits, pre, voicing, reserved = struct.unpack_from(
        '<4sBBHHHIIIffI', blob)
    if (magic, version, order, reserved) != (b'LPC2', 1, 10, 0):
        raise ValueError('unsupported LPC2 header')
    if not rate or not hop or window < hop or count != math.ceil(samples/hop):
        raise ValueError('invalid sample/frame counts')
    if not all(math.isfinite(x) for x in (pre, voicing)):
        raise ValueError('nonfinite header parameter')
    if len(blob) != 36+(bits+7)//8:
        raise ValueError('truncated payload or trailing bytes')
    if bits % 8 and blob[-1] >> (bits % 8):
        raise ValueError('nonzero bit padding')
    position = 0

    def take(width):
        nonlocal position
        if position+width > bits:
            raise ValueError('truncated frame')
        value = sum(((blob[36+(position+i)//8] >> ((position+i)%8)) & 1) << i for i in range(width))
        position += width
        return value

    frames = []
    for _ in range(count):
        energy = take(5)
        if not energy:
            frames.append([0, 0, 0, 0, []])
            continue
        mode, repeat = take(2), take(1)
        voiced = mode in (1, 2)
        pitch = take(6) if voiced else 0
        widths = (5, 5, 4, 4, 4, 4, 4, 3, 3, 3) if voiced else (5, 5, 4, 4)
        if repeat:
            if not frames or not frames[-1][0] or (frames[-1][1] in (1, 2)) != voiced:
                raise ValueError('invalid coefficient repeat')
            coefficients = frames[-1][4].copy()
        else:
            coefficients = [take(width) for width in widths]
        frames.append([energy, mode, pitch, repeat, coefficients])
    if position != bits:
        raise ValueError('unused payload bits')
    canonical = json.dumps(frames, separators=(',', ':')).encode()
    return dict(rate=rate, hop=hop, window=window, samples=samples, frames=count,
                payload_bits=bits, quantized_frames_sha256=hashlib.sha256(canonical).hexdigest(),
                repeat_frames=sum(f[3] for f in frames), silent_frames=sum(not f[0] for f in frames))
