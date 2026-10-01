"""Contracts for the experimental palette and endpoint selectors."""
import unittest

import numpy as np

import five_level_dither as five
from cell_palette_quality import averaged, encode, restore_endpoints
from dither_phase import reversed_phase


def state(levels, attr=71):
    levels = np.broadcast_to(levels, (96, 128)).astype(np.uint8).copy()
    levels[:12] = 0
    levels[84:] = 0
    attrs = np.full(768, attr, dtype=np.uint8)
    attrs[:96] = 1
    attrs[672:] = 1
    return five.pack_levels(levels) + attrs.tobytes()


def flat_image(value):
    image = np.zeros((96, 128, 3), dtype=np.uint8)
    image[12:84] = value
    return image


class CellPaletteQualityTests(unittest.TestCase):
    def test_normal_white_and_bright_white_are_available(self):
        for value in (205, 255):
            image = flat_image(value)
            result = encode(image, state(4), np.full(768, 69, dtype=np.uint8))
            np.testing.assert_array_equal(averaged(result), image)
            self.assertFalse(reversed_phase(np.frombuffer(result[3840:], dtype=np.uint8)).any())

    def test_five_levels_and_black_borders_survive(self):
        levels = np.resize(np.arange(5, dtype=np.uint8), (96, 128))
        reference = state(levels)
        image = np.rint(averaged(reference)).astype(np.uint8)
        result = encode(image, reference)
        np.testing.assert_array_equal(five.unpack_levels(result[:3840]), five.unpack_levels(reference[:3840]))
        self.assertEqual(set(five.unpack_levels(result[:3840])[12:84].ravel()), set(range(5)))
        self.assertEqual(result[3840:3936], bytes([1])*96)
        self.assertEqual(result[4512:], bytes([1])*96)

    def test_stale_colour_pair_cannot_override_cell_error_bound(self):
        image = flat_image(205)
        reference = state(4, 7)  # Exactly representable normal white.
        old = np.full(768, 69, dtype=np.uint8)  # Magenta on black.
        result = encode(image, reference, old, keep_mse=1000000)
        np.testing.assert_array_equal(averaged(result), image)

    def test_endpoint_bias_only_changes_adjacent_neutral_samples(self):
        image = flat_image(0)
        image[12:84] = np.tile(np.array([38, 64, 128, 191, 217, 255, 0, 128], dtype=np.uint8), 16)[None, :, None]
        levels = np.tile([1, 1, 2, 3, 3, 4, 0, 2], (96, 16))
        before = state(levels)
        after = restore_endpoints(image, before)
        expected = np.tile([0, 1, 2, 3, 4, 4, 0, 2], (72, 16))
        np.testing.assert_array_equal(five.unpack_levels(after[:3840])[12:84], expected)
        self.assertEqual(after[3840:], before[3840:])
        # A saturated-colour endpoint is never promoted to a solid block.
        coloured = state(3, 65)
        self.assertEqual(restore_endpoints(flat_image([0, 0, 217]), coloured), coloured)

    def test_exact_extremes_are_preserved(self):
        for level, value in ((0, 0), (4, 255)):
            before = state(level)
            self.assertEqual(restore_endpoints(flat_image(value), before), before)

    def test_flash_and_invalid_inputs_are_rejected(self):
        image = flat_image(0)
        bad = bytearray(state(0)); bad[3840+96] |= 128
        with self.assertRaises(ValueError): encode(image, bad)
        with self.assertRaises(ValueError): restore_endpoints(image, bad)
        with self.assertRaises(ValueError): encode(image.astype(float), state(0))
        with self.assertRaises(ValueError): encode(image, state(0), keep_mse=-1)
        with self.assertRaises(ValueError): restore_endpoints(image, state(0), margin=128)


if __name__ == '__main__':
    unittest.main()
