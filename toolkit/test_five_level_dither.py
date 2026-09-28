"""Five independent cell shades and exact colour coverage round trips."""
import unittest

import numpy as np

import build_long_video_trd as video
import dither_phase
import five_level_dither as five
from test_dither_phase import frame


class FiveLevelTests(unittest.TestCase):
    def test_all_625_words_roundtrip_at_all_four_bit_positions(self):
        all_levels = np.array([[(word//d) % 5 for d in (125, 25, 5, 1)] for word in range(625)], dtype=np.uint8)
        for shift in range(4):
            source = np.resize(np.roll(all_levels, shift, axis=0), (96, 128))
            packed = five.pack_levels(source)
            self.assertEqual(len(packed), 3840)
            np.testing.assert_array_equal(five.unpack_levels(packed), source)
        for word in range(625):
            digits = all_levels[word]
            self.assertEqual(five.TOP[word].bit_count()+five.BOTTOM[word].bit_count(), int(digits.sum()))

    def test_all_five_levels_coexist_in_one_attribute_cell(self):
        levels = np.zeros((96, 128), dtype=np.uint8)
        levels[12:16, :4] = np.arange(16).reshape(4, 4) % 5
        state = five.pack_levels(levels)+frame()[3072:].tobytes()
        image = video.base.render_spectrum_screen(*five.expand(state))
        counts = (image[24:32, :8, 0] == 255).reshape(4, 2, 4, 2).sum(axis=(1, 3))
        np.testing.assert_array_equal(counts, levels[12:16, :4])
        self.assertEqual(set(counts.ravel()), set(range(5)))

    def test_conversion_matches_aligned_reference_for_every_attribute(self):
        for attr in range(128):
            old = frame(attr)
            old[384:2688] = np.tile(np.arange(256, dtype=np.uint8), 9)
            new = five.from_compact(old)
            a = video.base.render_spectrum_screen(*dither_phase.expand(old, aligned=True))
            b = video.base.render_spectrum_screen(*five.expand(new))
            np.testing.assert_array_equal(a, b)
            self.assertFalse(dither_phase.reversed_phase(np.frombuffer(new[3840:], dtype=np.uint8)).any())

    def test_rgb_encoder_selects_all_five_shades_inside_one_cell(self):
        image = np.zeros((96, 128, 3), dtype=np.uint8)
        wanted = np.arange(16).reshape(4, 4) % 5
        image[12:16, :4] = np.array([0, 64, 128, 191, 255], dtype=np.uint8)[wanted, None]
        encoded = five.encode_image(image)
        self.assertEqual(encoded[3840+3*32], 71)
        np.testing.assert_array_equal(five.unpack_levels(encoded[:3840])[12:16, :4], wanted)
        # A previous inverse endpoint orientation is canonicalized too.
        again = five.encode_image(image, np.full(768, 120, dtype=np.uint8), 100000)
        np.testing.assert_array_equal(five.unpack_levels(again[:3840])[12:16, :4], wanted)

    def test_invalid_levels_lengths_and_unused_words_rejected(self):
        for value in (-1, 5, 0.5):
            with self.assertRaises(ValueError):
                five.pack_levels(np.full((96, 128), value))
        with self.assertRaises(ValueError):
            five.unpack_words(bytes(3839))
        with self.assertRaisesRegex(ValueError, 'unused'):
            five.unpack_words(bytes([255])*3840)


if __name__ == '__main__':
    unittest.main()
