"""Hardware-format, source-detail and limited-dither contracts for flat colour."""
from pathlib import Path
import tempfile
import unittest

import numpy as np

import flat_colour as flat
import five_level_dither as five
from cell_palette_quality import averaged, PAIRS
from stable_colour import cells


def image(rgb):
    result = np.zeros((96, 128, 3), np.uint8);result[12:84] = rgb
    return result


class FlatColourTests(unittest.TestCase):
    def test_all_actual_spectrum_colours_and_mixed_cell_are_exact(self):
        # Check normal as well as BRIGHT endpoints, including solid fills and
        # an internal boundary not aligned with a hardware attribute edge.
        for rgb in np.unique(PAIRS.reshape(-1, 3), axis=0).astype(np.uint8):
            source = image(rgb);state = flat.encode(source)
            np.testing.assert_array_equal(averaged(state), source)
        source = image([205, 0, 0]);source[12:84, 61:] = [0, 0, 205]
        np.testing.assert_array_equal(averaged(flat.encode(source)), source)

    def test_flat_has_no_native_dots_and_keeps_eyes_mouth_and_silhouette(self):
        source = image([0, 205, 205])
        source[30:68, 45:77] = [205]*3
        source[40:42, 52:54] = source[40:42, 66:68] = 0
        source[55, 54:66] = 0
        state = flat.encode(source, contours=True, vision='regions')
        np.testing.assert_array_equal(averaged(state), source)
        levels = five.unpack_levels(state[:3840])
        self.assertTrue(set(np.unique(levels)) <= {0, 4})
        top, bottom = five.expand(state)
        self.assertEqual((len(top), len(bottom)), (6144, 768))
        from build_zxv_trd import render_spectrum_screen
        rendered = render_spectrum_screen(top, bottom)
        np.testing.assert_array_equal(rendered, source.repeat(2, 0).repeat(2, 1))

    def test_minimal_dither_is_hard_bounded_and_replay_stable(self):
        source = image(np.random.default_rng(12).integers(0, 256, (72, 128, 3), dtype=np.uint8))
        state = flat.encode(source, dither='minimal')
        levels = five.unpack_levels(state[:3840])
        dots = cells(((levels > 0) & (levels < 4))[..., None])[..., 0].sum(axis=1)
        self.assertLessEqual(dots.max(), 1)
        self.assertGreater(dots.sum(), 0)
        self.assertEqual(flat.encode(source, state, source, dither='minimal'), state)
        self.assertEqual(state[3840:3936], bytes([1])*96)
        self.assertEqual(state[4512:], bytes([1])*96)

    def test_region_target_protects_small_source_feature_and_limits_pull(self):
        source = image([160, 155, 140]);source[12:84, :64] += 8
        source[40:42, 50:52] = 0
        target = flat.region_guidance(source)
        self.assertLessEqual(np.max(np.abs(target-cells(source.astype(float)))), 12)
        full = target.reshape(24, 32, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(96, 128, 3)
        np.testing.assert_array_equal(full[39:43, 49:53], source[39:43, 49:53])

    def test_contours_never_add_a_false_blue_line(self):
        source = image([185, 183, 190]);source[40:42, 60:68] = [115, 113, 120]
        normal = flat.encode(source)
        traced = flat.encode(source, contours=True)
        before = averaged(normal);after = averaged(traced)
        changed = np.any(before != after, axis=-1)
        self.assertTrue(changed.any())
        self.assertTrue((np.ptp(after[changed], axis=-1) == 0).all())
        # A missing line may be restored using black; the selected neutral
        # colour is already part of the hardware cell's original palette.
        self.assertEqual(normal[3840:], traced[3840:])

    def test_source_change_bypasses_temporal_palette_and_pixel_history(self):
        old_source = image([205, 0, 0]);old = flat.encode(old_source)
        for rgb in ([0, 0, 205], [205]*3, [25, 170, 60]):
            source = image(rgb)
            for settings in ({}, dict(dither='minimal'), dict(vision='regions', contours=True)):
                self.assertEqual(flat.encode(source, **settings),
                    flat.encode(source, old, old_source, **settings))

    def test_repeat_and_format_reject_invalid_controls(self):
        source = image([137, 113, 56]);state = flat.encode(source)
        self.assertEqual(flat.encode(source), flat.encode(source, state, source))
        for settings in (dict(dither='strong'), dict(vision='person'), dict(previous=state)):
            with self.assertRaises(ValueError):flat.encode(source, **settings)
        with self.assertRaises(ValueError):flat.encode(source.astype(float))
        with self.assertRaises(ValueError):flat.validate_state(state[:4000])
        damaged = state[:3936]+bytes([128])+state[3937:]
        with self.assertRaises(ValueError):flat.encode(source, damaged, source)

    def test_generic_preparation_and_exact_packet_roundtrip(self):
        from convert_video import convert_frames
        from generic_cell_codebook import prepare_frames, row_sets, representation
        source = image([205, 205, 0]);source[30:65, 41:87] = [0, 0, 205]
        images = np.stack([source[12:84]]*2)
        with tempfile.TemporaryDirectory() as tmp:
            compact, _ = convert_frames(images, Path(tmp))
            original = compact.copy()
            prepared, report = prepare_frames(images, compact, tmp, colour_policy='flat')
            try:
                np.testing.assert_array_equal(compact, original)
                self.assertEqual(report['dither'], 'none')
                self.assertEqual(report['colour_comparison']['selector'],
                    'solid endpoints with source-aware cell coordination')
                self.assertFalse(report['colour_comparison']['actual_pixel_error_bounded_by_old_quantizer'])
                self.assertEqual(prepared[0].tobytes(), flat.encode(source))
                row_sets(prepared)
                self.assertTrue(representation(prepared, 0, 2)['full_host_screens_exact'])
            finally:del prepared, compact
            with self.assertRaises(ValueError):
                prepare_frames(images, original, tmp, colour_contours=True)
            with self.assertRaises(ValueError):
                prepare_frames(images, original, tmp, colour_policy='flat', monochrome=True)


if __name__ == '__main__':unittest.main()
