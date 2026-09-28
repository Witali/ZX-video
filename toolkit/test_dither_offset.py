"""Offset selection cannot represent both extremes in one attribute cell."""
import unittest

import numpy as np

from probe_dither_offset import canonical, decode, picture, shift
from test_dither_phase import frame


class DitherOffsetTests(unittest.TestCase):
    def test_existing_orientation_already_selects_endpoint_preserving_quartets(self):
        for attr, expected in ((71, {0, 1, 2, 4}), (120, {0, 2, 3, 4})):
            values, _ = canonical(frame(attr, 0x1b))
            self.assertEqual(set(map(int, values[12:84].ravel())), expected)

    def test_each_quartet_can_be_retained_without_extra_flag(self):
        for attr, byte in ((71, 0x18), (120, 0x18)):
            state = frame(attr, byte)
            encoded, offsets, wanted, actual, attrs, _, _ = shift(state)
            self.assertEqual(len(encoded), 3840)
            np.testing.assert_array_equal(wanted, actual)
            values, restored = decode(encoded)
            np.testing.assert_array_equal(restored, attrs)
            np.testing.assert_array_equal(values, wanted)
            np.testing.assert_array_equal(picture(state), picture(encoded, shifted=True))
            self.assertTrue(np.all(offsets[3:21] == (attr == 120)))

    def test_both_extremes_force_one_step_error(self):
        state = frame(71, 0x03)  # three black and one white sample per row.
        _, offsets, wanted, actual, _, black, white = shift(state)
        self.assertFalse(offsets.any())
        self.assertEqual(int((wanted[12:84] != actual[12:84]).sum()), 576*4)
        self.assertEqual(int(np.minimum(black, white).sum()), 576*4)
        self.assertEqual(int(actual[12:84].max()), 3)
        # With three white samples, preserve white and lift the rare black.
        _, offsets, wanted, actual, _, _, _ = shift(frame(71, 0x3f))
        self.assertTrue(offsets[3:21].all())
        self.assertEqual(int(actual[12:84].min()), 1)
        self.assertEqual(int(np.abs(wanted.astype(int)-actual).max()), 1)

    def test_temporal_tie_retains_selector_without_worsening_error(self):
        state = frame(71, 0x0f)
        results = [shift(state, np.full((24, 32), value)) for value in (False, True)]
        self.assertFalse(results[0][1][3:21].any())
        self.assertTrue(results[1][1][3:21].all())
        for row in results:
            _, _, wanted, actual, _, _, _ = row
            self.assertEqual(int((wanted[12:84] != actual[12:84]).sum()), 576*8)

    def test_scalar_exhaustive_codes_attributes_and_palette_selection(self):
        # Every compact byte and endpoint orientation, including equal pairs.
        for attr in range(128):
            state = frame(attr)
            state[384:2688] = np.tile(np.arange(256, dtype=np.uint8), 9)
            encoded, _, wanted, actual, attrs, black, white = shift(state)
            values, restored = decode(encoded)
            np.testing.assert_array_equal(values, actual)
            np.testing.assert_array_equal(restored, attrs)
            self.assertLessEqual(np.abs(wanted.astype(int)-actual).max(), 1)
            for by, bx in ((3, 0), (5, 17), (17, 31)):
                cell = wanted[by*4:by*4+4, bx*4:bx*4+4].astype(int)
                errors = [int(((cell-np.clip(cell, offset, offset+3))**2).sum()) for offset in (0, 1)]
                error = int(((cell-actual[by*4:by*4+4, bx*4:bx*4+4])**2).sum())
                if attr & 7 != (attr >> 3) & 7:
                    self.assertEqual(error, min(errors))


if __name__ == '__main__':
    unittest.main()
