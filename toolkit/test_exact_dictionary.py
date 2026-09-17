"""Hand-authored streams test the proposed format independently of its encoder."""
import struct
import unittest

import numpy as np

from probe_exact_dictionary import decode


def skips(count):
    return bytes([63]) * (count // 64) + (bytes([count % 64 - 1]) if count % 64 else b'')


class DictionaryFormatTests(unittest.TestCase):
    def test_literal_cell_layout_attributes_and_previous_frame(self):
        data = struct.pack('<HH', 2, 0) + b'\x80\x12\x34\x56\x78\x47' + skips(767) + skips(768)
        screens = decode(data)
        expected = np.zeros((2, 3840), dtype=np.uint8)
        expected[:, [0, 32, 64, 96, 3072]] = [0x12, 0x34, 0x56, 0x78, 0x47]
        np.testing.assert_array_equal(screens, expected)

    def test_group_resets_prediction(self):
        first = struct.pack('<HH', 1, 1) + bytes([255] * 5) + b'\x40\x00' + skips(767)
        second = struct.pack('<HH', 1, 0) + skips(768)
        screens = decode(first + second)
        self.assertEqual(int(screens[0].sum()), 5 * 255)
        self.assertEqual(int(screens[1].sum()), 0)

    def test_fixed_and_tiered_indices_cross_255(self):
        table = b''.join(i.to_bytes(2, 'little') + bytes(3) for i in range(257))
        expected = np.zeros((1, 3840), dtype=np.uint8)
        expected[0, 0] = 255
        expected[0, 33] = 1
        for entries, indices in ((257, b'\xff\x00\x00\x01'),
                                 (0x8101, b'\xff\xff\x00\xff\x00\x01')):
            with self.subTest(entries=entries):
                data = struct.pack('<HH', 1, entries) + table + b'\x41' + indices + skips(766)
                np.testing.assert_array_equal(decode(data), expected)

    def test_invalid_runs_indices_and_truncation(self):
        header = struct.pack('<HH', 1, 0)
        for data in (header + b'\xc0', header + b'\x40\x00', header + b'\x80\x01',
                     header + skips(767) + b'\x01', b'\x01', bytes(4)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode(data)


if __name__ == '__main__':
    unittest.main()
