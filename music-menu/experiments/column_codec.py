"""Prepare bounded-column slideshow data for the native 128K player.

Each frame stores only the 160-row illustration: its identical 32-row title
bitmap is shared. Column order is 160 bitmap bytes then 20 attributes.
Literal/RLE/LZ tokens never cross a 180-byte column boundary. LZ distances
may refer to earlier columns in the same incoming-frame buffer; this lets
the Z80 prepare one complete column per field without a frame-sized stall.
"""
from bisect import bisect_left
from pathlib import Path
import json


ART_ROWS = 160
COLUMN_BYTES = 180
MENU_BANK = 7
MENU_ADDRESS = 0xF000


def bitmap_offset(column, y):
    return ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2) | column


def picture_columns(screen):
    if len(screen) != 6912 or any(a & 128 for a in screen[6144:]):
        raise ValueError('Expected a static 6912-byte Spectrum screen')
    return [bytes(screen[bitmap_offset(x, y)] for y in range(ART_ROWS))
            + bytes(screen[6144 + y * 32 + x] for y in range(ART_ROWS // 8))
            for x in range(32)]


def pack_columns(columns):
    """Dynamic-programming token choice over each bounded output column.

    00..7F: 1..128 literal bytes; 80..BF: repeat 3..66, followed by value;
    C0..FF: copy 3..66 from a positive LE16 backwards distance. Matches may
    overlap, as with LDIR. Searching 64 recent equal-prefix positions keeps
    host work bounded; decoder correctness does not depend on the search.
    """
    source = b''.join(columns)
    positions = {}
    for i in range(len(source) - 2):
        positions.setdefault(source[i:i + 3], []).append(i)
    result = []
    start = 0
    for column in columns:
        end = start + len(column)
        costs = {end: 0}
        choices = {}
        for i in range(end - 1, start - 1, -1):
            candidates = [(1 + n + costs[i + n], 'literal', n, 0)
                          for n in range(1, min(128, end - i) + 1)]
            run = 1
            while run < min(66, end - i) and source[i + run] == source[i]:
                run += 1
            candidates.extend((2 + costs[i + n], 'repeat', n, source[i])
                              for n in range(3, run + 1))
            if end - i >= 3:
                found = positions[source[i:i + 3]]
                limit = bisect_left(found, i)
                best_length, best_distance = 2, 0
                for previous in reversed(found[max(0, limit - 64):limit]):
                    length = 3
                    while length < min(66, end - i) and source[previous + length] == source[i + length]:
                        length += 1
                    if length > best_length:
                        best_length, best_distance = length, i - previous
                    if best_length == min(66, end - i):
                        break
                candidates.extend((3 + costs[i + n], 'match', n, best_distance)
                                  for n in range(3, best_length + 1))
            choice = min(candidates, key=lambda item: (item[0], -item[2]))
            costs[i], *choices[i] = choice
        encoded = bytearray()
        i = start
        while i < end:
            kind, length, value = choices[i]
            if kind == 'literal':
                encoded.append(length - 1)
                encoded.extend(source[i:i + length])
            elif kind == 'repeat':
                encoded.extend((0x80 | (length - 3), value))
            else:
                encoded.append(0xC0 | (length - 3))
                encoded.extend(value.to_bytes(2, 'little'))
            i += length
        result.append(bytes(encoded))
        start = end
    assert unpack_columns(result) == source
    return result


def unpack_columns(records):
    output = bytearray()
    for record in records:
        origin = len(output)
        position = 0
        while position < len(record):
            token = record[position]
            position += 1
            if token < 128:
                length = token + 1
                output.extend(record[position:position + length])
                position += length
            elif token < 192:
                length = (token & 63) + 3
                output.extend(bytes([record[position]]) * length)
                position += 1
            else:
                length = (token & 63) + 3
                distance = int.from_bytes(record[position:position + 2], 'little')
                position += 2
                if not 0 < distance <= len(output):
                    raise ValueError('Invalid slideshow backwards distance')
                for _ in range(length):
                    output.append(output[-distance])
        if len(output) - origin != COLUMN_BYTES:
            raise ValueError('Slideshow token crosses its output column')
    return bytes(output)


def load_artwork(folder):
    folder = Path(folder)
    manifest = json.loads((folder / 'compiled.json').read_text())
    frames = []
    for image in manifest['images']:
        screen = (folder / f'{image["name"]}.scr').read_bytes()
        columns = picture_columns(screen)
        encoded = pack_columns(columns)
        frames.append(dict(image, screen=screen, columns=encoded,
                           packed_bytes=sum(map(len, encoded))))
    return frames


if __name__ == '__main__':
    frames = load_artwork(Path(__file__).parent.parent / 'artwork')
    print(json.dumps(dict(total=sum(f['packed_bytes'] for f in frames),
                         images=[dict(name=f['name'], bytes=f['packed_bytes']) for f in frames]), indent=2))
