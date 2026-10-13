"""Localized native texture, source colour and no-lag contracts."""
import unittest
import numpy as np
import texture_colour as colour
import five_level_dither as five
from cell_palette_quality import averaged
from dither_phase import reversed_phase


def image(rgb):
    result = np.zeros((96, 128, 3), np.uint8);result[12:84] = rgb
    return result


def reference():
    levels = np.zeros((96, 128), np.uint8);levels[12:84] = 2
    attrs = np.full(768, 71, np.uint8);attrs[:96] = attrs[672:] = 1
    return five.pack_levels(levels)+attrs.tobytes()


def false_seam():
    levels = np.zeros((96, 128), np.uint8)
    levels[12:84, :64] = 4;levels[12:84, 64:] = 3
    attrs = np.full((24, 32), 71, np.uint8);attrs[:, :16] = 7
    attrs[:3] = attrs[21:] = 1
    return five.pack_levels(levels)+attrs.tobytes()


class TextureColourTests(unittest.TestCase):
    def test_native_endpoints_and_real_contour_are_exact(self):
        for rgb in ([205]*3, [255]*3, [0]*3, [0, 205, 205], [255, 0, 0]):
            source = image(rgb);state = colour.encode(source, reference())
            np.testing.assert_array_equal(averaged(state), source)
            self.assertFalse(reversed_phase(np.frombuffer(state[3840:], np.uint8)).any())
        source = image([205, 0, 0]);source[12:84, 64:] = [0, 0, 205]
        np.testing.assert_array_equal(averaged(colour.encode(source, reference())), source)

    def test_solid_pattern_feather_is_local_and_preserves_palette(self):
        source = image([205]*3);old = false_seam();new = colour.feather(source, old)
        old_levels = five.unpack_levels(old[:3840]);levels = five.unpack_levels(new[:3840])
        changed = levels != old_levels
        self.assertTrue(changed[:, 62:64].any())
        self.assertTrue(changed[:, 64:66].any())
        self.assertFalse(changed[:, :62].any());self.assertFalse(changed[:, 66:].any())
        self.assertLess(changed.sum(), 72*4/2)
        self.assertEqual(new[3840:], old[3840:])
        self.assertEqual(colour.feather(source, old), new)

    def test_actual_source_edge_is_not_feathered(self):
        source = image([205]*3);source[12:84, 64:] = 191
        self.assertEqual(colour.feather(source, false_seam()), false_seam())

    def test_normal_bright_solid_step_has_a_local_pattern_transition(self):
        old = false_seam()
        levels = five.unpack_levels(old[:3840]);levels[12:84] = 4
        old = five.pack_levels(levels)+old[3840:]
        source = image([230]*3);new = colour.feather(source, old)
        shades = five.unpack_levels(new[:3840])
        self.assertTrue((shades[12:84, 64:66] < 4).any())
        np.testing.assert_array_equal(shades[:, :64], levels[:, :64])
        np.testing.assert_array_equal(shades[:, 66:], levels[:, 66:])
        source[12:84, :64] = 205;source[12:84, 64:] = 255
        self.assertEqual(colour.feather(source, old), old)

    def test_muted_orange_cannot_become_a_saturated_red_rectangle(self):
        source = image([180, 100, 40]);state = colour.encode(source, reference())
        actual = averaged(state)[12:84]
        self.assertTrue(colour.stable.hue_valid(source[12:84], actual, 20).all())
        self.assertFalse(set(state[3936:4512]) & {2, 66})
        red = image([205, 0, 0])
        np.testing.assert_array_equal(averaged(colour.encode(red, reference())), red)

    def test_default_converter_uses_local_fit_and_reports_actual_tradeoff(self):
        from pathlib import Path
        import tempfile
        from convert_video import convert_frames
        from generic_cell_codebook import prepare_frames, row_sets
        source = image([205]*3);source[40:42, 64:66] = 255
        with tempfile.TemporaryDirectory() as tmp:
            compact, _ = convert_frames(np.array([source[12:84]]), Path(tmp))
            prepared, quality = prepare_frames(np.array([source[12:84]]), compact, tmp)
            try:
                self.assertEqual(prepared[0].tobytes(), colour.encode(source, reference()))
                self.assertIn('localized', quality['colour_comparison']['selector'])
                self.assertNotIn('rgb_sample_bound', quality['colour_comparison'])
                row_sets(prepared)
            finally:del compact, prepared

    def test_changed_picture_has_no_palette_or_density_lag(self):
        old_source = image([200, 30, 10]);old = colour.encode(old_source, reference())
        for rgb in ([10, 30, 200], [205]*3, [20, 160, 90]):
            source = image(rgb)
            self.assertEqual(colour.encode(source, reference()), colour.encode(source, reference(), old, old_source))

    def test_identical_complex_source_is_stable_and_native_format_valid(self):
        source = image(np.random.default_rng(18).integers(0, 256, (72, 128, 3), dtype=np.uint8))
        state = colour.encode(source, reference())
        self.assertEqual(colour.encode(source, reference(), state, source), state)
        self.assertEqual(len(state), 4608)
        self.assertEqual(state[3840:3936], bytes([1])*96);self.assertEqual(state[4512:], bytes([1])*96)
        self.assertFalse((np.frombuffer(state[3840:], np.uint8) & 128).any())
        screen = five.expand(state)
        self.assertEqual((len(screen[0]), len(screen[1])), (6144, 768))


if __name__ == '__main__':unittest.main()
