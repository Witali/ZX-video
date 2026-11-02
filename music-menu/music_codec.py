"""Lossless bounded-depth byte-pair grammar for the existing AY row format.

The dictionary is shared by both complete songs. Root bytes 00..7f are
literal, 80..fe select one of 127 pairs, and ff escapes a literal 80..ff.
Pair children are LE16: 0..255 literal bytes, 256..382 pair references.
Expansion needs at most 12 pending right children, not a history buffer.
"""
from collections import Counter
import struct


def compress(streams, max_pairs=127, max_depth=12):
    sequences = [list(data) for data in streams]
    pairs, depths = [], [0]*256
    def cost(symbol):
        return 2 if 128 <= symbol < 256 else 1
    for _ in range(max_pairs):
        counts = Counter()
        for seq in sequences:
            # A run of identical symbols has floor(n/2), not n-1 replacements.
            previous = None
            skip = False
            for left, right in zip(seq, seq[1:]):
                pair = (left, right)
                if pair == previous and left == right and skip:
                    skip = False
                    continue
                counts[pair] += 1
                skip = left == right
                previous = pair
        candidates = [(n*(cost(a)+cost(b)-1)-4, n, a, b)
                      for (a,b),n in counts.items()
                      if max(depths[a],depths[b]) < max_depth]
        if not candidates:
            break
        gain, _, a, b = max(candidates)
        if gain <= 0:
            break
        symbol = 256+len(pairs)
        pairs.append((a,b))
        depths.append(1+max(depths[a],depths[b]))
        for index, seq in enumerate(sequences):
            result, pos = [], 0
            while pos < len(seq):
                if pos+1 < len(seq) and (seq[pos],seq[pos+1]) == (a,b):
                    result.append(symbol)
                    pos += 2
                else:
                    result.append(seq[pos])
                    pos += 1
            sequences[index] = result
    encoded = []
    for seq in sequences:
        out = bytearray()
        for symbol in seq:
            if symbol >= 256:
                out.append(128+symbol-256)
            elif symbol >= 128:
                out.extend((255,symbol))
            else:
                out.append(symbol)
        encoded.append(bytes(out))
    dictionary = b''.join(struct.pack('<HH',a,b) for a,b in pairs)
    for original, data in zip(streams,encoded):
        assert decompress(data,dictionary) == original
    return encoded, dictionary, max(depths)


def decompress(data, dictionary):
    pairs = list(struct.iter_unpack('<HH',dictionary))
    output = bytearray()
    pos = 0
    while pos < len(data):
        symbol = data[pos]
        pos += 1
        if symbol == 255:
            output.append(data[pos])
            pos += 1
            continue
        pending = [symbol+128 if symbol >= 128 else symbol]
        while pending:
            symbol = pending.pop()
            if symbol < 256:
                output.append(symbol)
            else:
                a,b = pairs[symbol-256]
                pending.extend((b,a))
    return bytes(output)
