"""Image accuracy contracts of hardware-feasible source-colour fills."""
import unittest
import numpy as np

import lineart_colour as line
import lineart_feasible as feasible
import five_level_dither as five
from cell_palette_quality import averaged
from stable_colour import hue_valid


def image(rgb):
    result = np.zeros((96, 128, 3), np.uint8);result[12:84] = rgb
    return result


class FeasibleFillTests(unittest.TestCase):
    def check_contracts(self, source):
        old = averaged(line.encode(source));state = feasible.encode(source);new = averaged(state)
        changed = np.any(old != new, axis=-1)
        old_error = np.mean((old-source)**2, axis=-1);new_error = np.mean((new-source)**2, axis=-1)
        self.assertTrue((new_error <= old_error).all())
        self.assertTrue((new_error[changed] < old_error[changed]).all())
        lines = line.source_lines(source);fills = line.source_fills(source)
        mandatory = lines | (fills == 0) | (fills == 7)
        np.testing.assert_array_equal(new[mandatory], old[mandatory])
        coloured = np.ptp(new, axis=-1) > 0
        self.assertTrue((np.mean((new[coloured]-source[coloured])**2, axis=-1) <= 60**2).all())
        self.assertTrue((np.max(np.abs(new[coloured]-source[coloured]), axis=-1) <= 100).all())
        self.assertTrue(hue_valid(source[coloured], new[coloured], 30).all())
        self.assertFalse(((five.unpack_levels(state[:3840]) > 0) & (five.unpack_levels(state[:3840]) < 4)).any())
        return changed

    def test_mixed_source_brightness_restores_real_colour_without_losing_black(self):
        source = image([245, 245, 35]);source[40:44, 60:62] = [205, 205, 35]
        self.assertTrue(self.check_contracts(source).any())

    def test_actual_source_colours_and_uniform_unmatched_paper_are_unchanged(self):
        for colour in (*range(7), *range(9, 15)):
            self.assertFalse(self.check_contracts(image(line.COLOURS[colour].astype(np.uint8))).any())
        self.assertFalse(self.check_contracts(image([100]*3)).any())

    def test_three_required_colours_cannot_tint_unmatched_paper(self):
        source = image([110]*3);source[40:44, 60:62] = [245, 245, 35];source[40:44, 62] = 0
        self.check_contracts(source)

    def test_existing_coloured_samples_never_become_worse_and_history_cannot_lag(self):
        source = image([245, 245, 35]);source[40:44, 60:62] = [205, 205, 35]
        source[30:50, 82:100] = [235, 25, 35]
        self.check_contracts(source)
        old_source = image([0, 205, 205]);old = feasible.encode(old_source)
        self.assertEqual(feasible.encode(source, old, old_source), feasible.encode(source))
        with self.assertRaises(ValueError):feasible.encode(source, old)


if __name__ == '__main__':unittest.main()
