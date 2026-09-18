"""Context boundaries, causal previous values, empty groups and exact inverse."""
import struct
import unittest

from probe_motion_entropy import groups
from probe_context_values import MODELS, context_ids, train, encode, decode


def fields(n):
    vectors = bytes([0, 1, 2])+bytes(189)
    masks = bytearray(480)
    for bit in (0, 1, 2, 5, 16, 20, 41):
        masks[bit//8] |= 128 >> (bit % 8)
    values = bytes([1, 0x55, 4, 3, 0x10, 8, 0x40])
    return struct.pack('<H', n)+vectors*n+bytes(masks)*n, values*n


def source(empty=False):
    symbols = bytes(p ^ c for p in range(4) for c in range(4))
    header = b'FPR1'+symbols+b'FMO1\x08FMR1'+struct.pack('<BBIbbbb', 8, 2, 3, 0, 0, 1, 0)
    out = bytearray(header)
    for n in (2, 1):
        fixed, values = fields(n)
        out += struct.pack('<H', n)+bytes(n*672) if empty else fixed+values
    return bytes(out)


class ContextValueTests(unittest.TestCase):
    def test_known_metadata_and_previous_value_contexts(self):
        fixed, values = fields(1)
        expected = {
            0: [0]*7,
            1: [0, 0, 0, 0, 1, 0, 0],
            2: [1, 1, 1, 1, 3, 0, 0],
            3: [0, 0, 0, 0, 3, 1, 2],
            4: [1, 1, 1, 1, 9, 3, 6],
            5: [0, 1, 4, 0, 5, 0, 0],
            6: [0, 1, 4, 0, 15, 5, 10],
        }
        for mode, wanted in expected.items():
            self.assertEqual(context_ids(fixed, values, mode, 2).tolist(), wanted)

    def test_every_model_empty_and_short_last_group(self):
        for empty in (False, True):
            raw = source(empty)
            header, parsed = groups(raw)
            for mode in range(len(MODELS)):
                tables, _ = train(parsed, mode, header[30])
                data, _ = encode(header, parsed, mode, tables)
                self.assertEqual(decode(data), raw)
                for bad in (data[:-1], data+b'\0', data[:4]+b'\xff'+data[5:]):
                    with self.assertRaises(ValueError):
                        decode(bad)


if __name__ == '__main__':
    unittest.main()
