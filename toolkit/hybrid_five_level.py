"""Host-only cell escape: existing four-code cells or four 10-bit words.

Mode bits are separate codec metadata, never hardware FLASH. Attribute XOR
deltas are independent of pixel changes. This experimental packet format is
not FAP3 and has no native consumer or RAM allocation yet.
"""
from dataclasses import dataclass

import numpy as np

from dither_phase import reversed_phase
import five_level_dither as five
import build_long_video_trd as video


@dataclass(frozen=True)
class Frame:
    attrs: bytes
    modes: bytes
    cells: tuple


def from_compact(state):
    data = np.frombuffer(bytes(state), dtype=np.uint8)
    if data.shape != (3840,) or np.any(data[3072:] & 128):
        raise ValueError('expected non-FLASH compact frame')
    cells = data[:3072].reshape(24, 4, 32).transpose(0, 2, 1).reshape(768, 4)
    return Frame(data[3072:].tobytes(), bytes(768), tuple(row.tobytes() for row in cells))


def refine_compact(state, image):
    """Add only the missing quarter shade when it strictly improves RGB error.

    Keep the chosen colour pair, BRIGHT and all other existing samples. No
    new attribute search or temporal palette penalty is introduced here.
    """
    image = np.asarray(image)
    if image.shape != (96, 128, 3): raise ValueError('expected 128x96 RGB')
    frame = from_compact(state)
    levels, attrs = decode(frame)
    source_attrs = np.frombuffer(frame.attrs, dtype=np.uint8)
    missing = np.where(reversed_phase(source_attrs), 1, 3).reshape(24, 32).repeat(4, 0).repeat(4, 1)
    endpoints = np.array([[video.base.zx_rgb((a >> 3) & 7, (a >> 6) & 1),
                           video.base.zx_rgb(a & 7, (a >> 6) & 1)] for a in attrs], dtype=np.float64)
    endpoints = endpoints.reshape(24,32,2,3).repeat(4,0).repeat(4,1)
    paper, direction = endpoints[:,:,0], endpoints[:,:,1]-endpoints[:,:,0]
    current_error = ((paper+levels[:,:,None]/4*direction-image)**2).sum(axis=2)
    new_error = ((paper+missing[:,:,None]/4*direction-image)**2).sum(axis=2)
    selected = np.where(new_error < current_error, missing, levels).astype(np.uint8)
    return five.pack_levels(selected)+attrs


def from_five(state, *, adaptive=True, previous=None, canonical_quartets=False):
    if len(state) != five.STATE_BYTES: raise ValueError('invalid five-level frame')
    attrs = np.frombuffer(state[five.BITMAP_BYTES:], dtype=np.uint8).copy()
    if np.any(attrs & 128) or np.any(reversed_phase(attrs)):
        raise ValueError('expected canonical non-FLASH colours')
    levels = five.unpack_levels(state[:five.BITMAP_BYTES])
    cells = levels.reshape(24, 4, 32, 4).transpose(0, 2, 1, 3).reshape(768, 4, 4)
    modes, payloads = bytearray(768), []
    prior = ((np.frombuffer(previous.modes, dtype=np.uint8) == 2) if canonical_quartets
             else reversed_phase(np.frombuffer(previous.attrs, dtype=np.uint8))) if previous else np.zeros(768, bool)
    for index, cell in enumerate(cells):
        low, high = bool(np.any(cell == 1)), bool(np.any(cell == 3))
        escape = not adaptive or (low and high)
        modes[index] = escape
        if escape:
            words = cell.astype(np.uint64) @ np.array([125, 25, 5, 1], dtype=np.uint64)
            combined = sum(int(word) << shift for word, shift in zip(words, (30, 20, 10, 0)))
            payloads.append(combined.to_bytes(5, 'big'))
        else:
            reverse = high or (not low and bool(prior[index]))
            # Equal endpoints cannot carry an orientation selector.
            reverse &= (attrs[index] & 7) != ((attrs[index] >> 3) & 7)
            if canonical_quartets and reverse:
                codes = np.array([0, 255, 2, 1, 3], dtype=np.uint8)[cell]
                modes[index] = 2
            else:
                values = 4-cell if reverse else cell
                codes = np.array([0, 1, 2, 255, 3], dtype=np.uint8)[values]
            if np.any(codes == 255): raise AssertionError('quarter level needs escape')
            payloads.append(((codes[:, 0] << 6) | (codes[:, 1] << 4)
                             | (codes[:, 2] << 2) | codes[:, 3]).tobytes())
            if reverse and not canonical_quartets:
                attr = int(attrs[index])
                attrs[index] = (attr & 64) | ((attr & 7) << 3) | ((attr >> 3) & 7)
    return Frame(attrs.tobytes(), bytes(modes), tuple(payloads))


def decode(frame):
    """Independent scalar decoding to canonical coverage and colour pairs."""
    if len(frame.attrs) != 768 or len(frame.modes) != 768 or len(frame.cells) != 768:
        raise ValueError('invalid cell frame')
    attrs = bytearray(frame.attrs)
    values = np.empty((24, 32, 4, 4), dtype=np.uint8)
    for index, data in enumerate(frame.cells):
        attr, mode = attrs[index], frame.modes[index]
        if attr & 128 or mode not in (0, 1, 2) or len(data) != 4+int(mode == 1):
            raise ValueError('invalid attribute, mode or cell length')
        cell = []
        if mode == 1:
            if (attr & 7) < ((attr >> 3) & 7): raise ValueError('inverse five-level cell')
            combined = int.from_bytes(data, 'big')
            for shift in (30, 20, 10, 0):
                word = (combined >> shift) & 1023
                if word >= 625: raise ValueError('unused radix-5 word')
                cell.append([(word//divisor) % 5 for divisor in (125, 25, 5, 1)])
        else:
            reverse = (attr & 7) < ((attr >> 3) & 7)
            if mode == 2 and reverse: raise ValueError('inverse canonical quartet')
            for value in data:
                shades = (0, 3, 2, 4) if mode == 2 else (0, 1, 2, 4)
                row = [shades[(value >> shift) & 3] for shift in (6, 4, 2, 0)]
                cell.append([4-v for v in row] if reverse else row)
            if reverse: attrs[index] = (attr & 64) | ((attr & 7) << 3) | ((attr >> 3) & 7)
        values[index//32, index % 32] = cell
    return values.transpose(0, 2, 1, 3).reshape(96, 128), bytes(attrs)


def encode_delta(previous, current, *, policy='hybrid'):
    if policy not in ('hybrid', 'canonical', 'four', 'five'): raise ValueError('unknown cell policy')
    if policy in ('four', 'five') and any(mode != int(policy == 'five') for mode in current.modes):
        raise ValueError('mode does not match fixed policy')
    if policy == 'hybrid' and any(mode > 1 for mode in current.modes): raise ValueError('two-mode policy')
    attributes = bytes(a ^ b for a,b in zip(previous.attrs, current.attrs))
    changed = [i for i in range(768)
               if current.modes[i] != previous.modes[i] or current.cells[i] != previous.cells[i]]
    flags = np.zeros(768, dtype=np.uint8); flags[changed] = 1
    header = np.packbits(np.frombuffer(attributes, dtype=np.uint8) != 0).tobytes()+np.packbits(flags).tobytes()
    values = bytes(v for v in attributes if v)
    selected = np.array([current.modes[i] for i in changed], dtype=np.uint8)
    if policy == 'canonical':
        modes = np.packbits(((selected[:, None] >> np.array([1,0])) & 1).ravel()).tobytes()
    else: modes = np.packbits(selected).tobytes() if policy == 'hybrid' else b''
    return header+values+modes+b''.join(current.cells[i] for i in changed)


def decode_delta(previous, packet, *, policy='hybrid'):
    if policy not in ('hybrid', 'canonical', 'four', 'five') or len(packet) < 192:
        raise ValueError('invalid packet or policy')
    attr_indices = np.flatnonzero(np.unpackbits(np.frombuffer(packet[:96], dtype=np.uint8)))
    pixel_indices = np.flatnonzero(np.unpackbits(np.frombuffer(packet[96:192], dtype=np.uint8)))
    pos = 192
    def take(n):
        nonlocal pos
        if pos+n > len(packet): raise ValueError('truncated packet')
        value = packet[pos:pos+n]; pos += n; return value
    attrs, modes, cells = bytearray(previous.attrs), bytearray(previous.modes), list(previous.cells)
    for i, v in zip(attr_indices, take(len(attr_indices))):
        if not v or v & 128: raise ValueError('invalid non-FLASH attribute delta')
        attrs[i] ^= v
    if policy in ('hybrid', 'canonical'):
        bits = 2 if policy == 'canonical' else 1
        flags = np.unpackbits(np.frombuffer(take((len(pixel_indices)*bits+7)//8), dtype=np.uint8))
        if np.any(flags[len(pixel_indices)*bits:]): raise ValueError('nonzero padding mode bits')
        selected = flags[:len(pixel_indices)*bits].reshape(-1,bits) @ np.array([2,1] if bits == 2 else [1])
        if np.any(selected > 2): raise ValueError('reserved cell mode')
    else: selected = np.full(len(pixel_indices), int(policy == 'five'), dtype=np.uint8)
    for i, mode in zip(pixel_indices, selected):
        modes[i] = int(mode); cells[i] = take(4+int(mode == 1))
    if pos != len(packet): raise ValueError('trailing packet bytes')
    result = Frame(bytes(attrs), bytes(modes), tuple(cells))
    decode(result)
    return result
