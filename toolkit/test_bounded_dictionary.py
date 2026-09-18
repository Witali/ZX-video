"""Check n-2 prediction and error bounds against independent native rendering."""
import struct
import unittest

import numpy as np

import build_long_video_trd as video
from build_zxv_trd import render_spectrum_screen
from probe_bounded_dictionary import accept_pattern, decode, encode_group, quality
from review_bounded_dictionary import ssim


class BoundedDictionaryTests(unittest.TestCase):
    def test_decoder_n2_and_cell_addressing(self):
        header = struct.pack('<HH', 3, 1) + bytes([0x12, 0x34, 0x56, 0x78])
        skip_rest = bytes([63]) * 11 + bytes([62])
        all_skip = bytes([63]) * 12
        attr_mask = bytes([128]) + bytes(95)
        first = b'\x40\x00' + skip_rest + attr_mask + b'\x47'
        second = b'\x80\x87\x65\x43\x21' + skip_rest + attr_mask + b'\x42'
        third = all_skip + bytes(96)
        screens = decode(header + first + second + third)
        expected = np.zeros((3, 3840), dtype=np.uint8)
        expected[0, [0, 32, 64, 96, 3072]] = [0x12, 0x34, 0x56, 0x78, 0x47]
        expected[1, [0, 32, 64, 96, 3072]] = [0x87, 0x65, 0x43, 0x21, 0x42]
        expected[2] = expected[0]
        np.testing.assert_array_equal(screens, expected)

    def test_bounds_reject_large_or_many_changes(self):
        original = np.zeros((1, 4, 4), dtype=np.uint8)
        candidate = original.copy()
        candidate[0, 0, 0] = 0x40  # one quarter-coverage change
        candidate[0, 1, 0] = 0x80  # half-coverage change
        candidate[0, 2, 0] = 0x54  # three quarter-coverage changes
        candidate[0, 3, 0] = 0x40
        attrs = np.array([[1, 1, 1, 7]], dtype=np.uint8)
        np.testing.assert_array_equal(accept_pattern(original, candidate, attrs, 12), [[True, False, False, False]])
        self.assertFalse(accept_pattern(original, candidate, attrs, 0).any())
        np.testing.assert_array_equal(accept_pattern(original, candidate, attrs, 32, 4), [[True, False, True, True]])

    def test_ssim_identical_and_constant_luminance(self):
        black = np.zeros((32, 32, 3), dtype=np.uint8)
        grey = np.full_like(black, 20)
        self.assertEqual(ssim(black, black), 1)
        self.assertAlmostEqual(ssim(black, grey), 6.5025 / (400 + 6.5025), places=10)

    def test_native_error_matches_rendered_pixels(self):
        old = np.zeros((1, 3840), dtype=np.uint8)
        old[0, 3072 + 3 * 32] = 1
        new = old.copy()
        new[0, 12 * 32] = 0x40
        report = quality(old, new)
        original = render_spectrum_screen(*video.expand_compact_screen(old[0].tobytes()))[24:168].astype(float)
        changed = render_spectrum_screen(*video.expand_compact_screen(new[0].tobytes()))[24:168].astype(float)
        mse = np.mean((original - changed) ** 2)
        self.assertAlmostEqual(report['native_rgb_psnr_db'], 10 * np.log10(255 ** 2 / mse), places=10)
        self.assertAlmostEqual(report['native_changed_fraction'], np.mean(np.any(original != changed, axis=2)))

    def test_extended_index_and_attribute_changes(self):
        table = np.zeros((257, 4), dtype=np.uint8)
        table[:, 0] = np.arange(257) & 255
        table[256, 1] = 1
        cells = np.zeros((1, 768, 4), dtype=np.uint8)
        cells[0, :257] = table
        attrs = np.arange(768, dtype=np.uint16).reshape(1, 768).astype(np.uint8)
        screen = decode(encode_group(cells, attrs, table))[0]
        self.assertEqual(screen[8 * 128 + 32], 1)
        np.testing.assert_array_equal(screen[3072:], attrs[0])

    def test_bad_stream_is_rejected(self):
        header = struct.pack('<HH', 1, 1) + bytes(4)
        for data in (b'\x01', bytes(4), header + b'\xc0', header + b'\x40\x01', header + b'\x80'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode(data)


if __name__ == '__main__':
    unittest.main()
