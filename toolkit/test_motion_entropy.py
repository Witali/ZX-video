"""Known bit codes and serialized groups for the FPR1 entropy experiment."""
import struct
import unittest

from probe_motion_entropy import codes_for, decode, encode, groups, huffman_lengths, pack, unpack


class MotionEntropyTests(unittest.TestCase):
    def test_known_prefix_codes_and_padding(self):
        table = bytes([1, 2, 3])
        # 1=00, 2=01, 9=11 00001001: 00011100 001001xx.
        expected = bytes([0x1c, 0x24])
        self.assertEqual(pack(bytes([1, 2, 9]), codes_for(2, table)), (14, expected))
        self.assertEqual(unpack(expected, 14, 3, 2, table), bytes([1, 2, 9]))
        with self.assertRaises(ValueError):
            unpack(bytes([0x1c, 0x25]), 14, 3, 2, table)
        with self.assertRaises(ValueError):
            unpack(expected, 14, 4, 2, table)

    def test_known_huffman_codes_and_single_symbol(self):
        lengths = bytearray(256)
        lengths[1:4] = bytes([1, 2, 2])  # 0, 10, 11
        self.assertEqual(pack(bytes([1, 2, 3]), codes_for(255, lengths)), (5, b'X'))
        self.assertEqual(unpack(b'X', 5, 3, 255, lengths), bytes([1, 2, 3]))
        single = huffman_lengths({7: 100})
        self.assertEqual(unpack(b'\0', 3, 3, 255, single), bytes([7, 7, 7]))
        with self.assertRaises(ValueError):
            unpack(b'\x80', 1, 1, 255, single)
        bad = bytes([1, 1, 1]) + bytes(253)
        for operation in (lambda: codes_for(255, bad), lambda: unpack(b'\0', 1, 1, 255, bad)):
            with self.assertRaises(ValueError):
                operation()

    def test_every_nonzero_byte(self):
        values = bytes(range(1, 256)) * 2
        variants = [(0, b'')] + [(k, bytes(range(1, 1 << k))) for k in range(2, 7)]
        variants += [(255, huffman_lengths(dict.fromkeys(range(1, 256), 1)))]
        for mode, table in variants:
            bits, packed = pack(values, codes_for(mode, table))
            self.assertEqual(unpack(packed, bits, len(values), mode, table), values)

    def test_groups_and_truncation(self):
        symbols = bytes(p ^ c for p in range(4) for c in range(4))
        header = b'FPR1' + symbols + b'FMO1\x08FMR1' + struct.pack('<BBIbb', 8, 1, 3, 0, 0)
        original = header
        for count in (2, 1):
            masks = bytes([128]) + bytes(480 * count - 1)
            original += struct.pack('<H', count) + bytes(192 * count) + masks + b'\x01'
        h, parsed = groups(original)
        for mode, table in ((0, b''), (2, bytes([1, 2, 3])), (255, huffman_lengths({1: 2}))):
            encoded, _ = encode(h, parsed, mode, table)
            self.assertEqual(decode(encoded), original)
            for bad in (encoded[:-1], encoded + b'\0'):
                with self.assertRaises(ValueError):
                    decode(bad)


if __name__ == '__main__':
    unittest.main()
