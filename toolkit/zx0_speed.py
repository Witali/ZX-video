"""Trade short ZX0 matches for longer literal runs, preserving every byte.

ZX0 v2 bit conventions follow zx0_codec.py and the bundled decoder.
Reference algorithm copyright (c) 2021 Einar Saukas. All rights reserved.
See third_party/zx0/LICENSE for the BSD-3-Clause conditions and disclaimer.
This changes the stream, not the Z80 instructions.
"""
from dataclasses import dataclass
import zx0_codec


@dataclass(frozen=True)
class Token:
    position: int
    length: int
    offset: int = 0


def parse(data):
    position = mask = value = last = 0
    backtrack = False
    output = bytearray(); tokens = []

    def byte():
        nonlocal position, last
        if position == len(data): raise ValueError('truncated stream')
        last = data[position]; position += 1
        return last

    def bit():
        nonlocal mask, value, backtrack
        if backtrack:
            backtrack = False
            return last & 1
        mask >>= 1
        if not mask: mask = 128; value = byte()
        return int(bool(value & mask))

    def gamma(inverted=0):
        result = 1
        while not bit():
            result = result * 2 + (bit() ^ inverted)
            if result > 65535: raise ValueError('oversized gamma')
        return result

    def match(offset, length):
        if not 0 < offset <= len(output): raise ValueError('invalid match')
        tokens.append(Token(len(output), length, offset))
        for _ in range(length): output.append(output[-offset])

    offset = 1; mode = 'literal'
    while True:
        if mode == 'literal':
            length = gamma(); tokens.append(Token(len(output), length))
            for _ in range(length): output.append(byte())
            if not bit():
                match(offset, gamma())
                if not bit(): continue
        offset = gamma(1)
        if offset == 256:
            if position != len(data): raise ValueError('trailing input')
            return bytes(output), tokens
        offset = offset * 128 - (byte() >> 1)
        backtrack = True
        match(offset, gamma() + 1)
        mode = 'offset' if bit() else 'literal'


def encode(raw, tokens):
    output = bytearray(); mask = 0; bit_position = 0; backtrack = False

    def bit(value):
        nonlocal mask, bit_position, backtrack
        if backtrack:
            output[-1] |= int(bool(value)); backtrack = False
            return
        if not mask:
            bit_position = len(output); output.append(0); mask = 128
        if value: output[bit_position] |= mask
        mask >>= 1

    def gamma(value, inverted=0):
        if value < 1: raise ValueError('invalid gamma')
        for shift in range(value.bit_length() - 2, -1, -1):
            bit(0); bit(((value >> shift) & 1) ^ inverted)
        bit(1)

    previous_match = False; last_offset = 1; cursor = 0
    for token in tokens:
        if token.position != cursor or token.length < 1: raise ValueError('invalid token order')
        if not token.offset:
            if cursor:
                if not previous_match: raise ValueError('adjacent literal runs')
                bit(0)
            gamma(token.length); output.extend(raw[cursor:cursor + token.length])
        elif not previous_match and token.offset == last_offset:
            bit(0); gamma(token.length)
        else:
            if not cursor or token.length < 2: raise ValueError('invalid new match')
            bit(1); gamma((token.offset - 1) // 128 + 1, 1)
            output.append((127 - (token.offset - 1) % 128) * 2)
            backtrack = True; gamma(token.length - 1)
            last_offset = token.offset
        cursor += token.length; previous_match = bool(token.offset)
    if cursor != len(raw): raise ValueError('incomplete token coverage')
    bit(1); gamma(256, 1)
    result = bytes(output)
    if zx0_codec.decompress(result, limit=len(raw)) != raw: raise AssertionError('ZX0 round trip')
    return result


def rewrite(data, minimum_match):
    if minimum_match < 2: return data
    raw, tokens = parse(data); result = []
    for token in tokens:
        if token.offset and token.length < minimum_match:
            token = Token(token.position, token.length)
        if result and not result[-1].offset and not token.offset:
            previous = result.pop()
            token = Token(previous.position, previous.length + token.length)
        result.append(token)
    return encode(raw, result)
