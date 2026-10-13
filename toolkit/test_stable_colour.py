"""Independent source fidelity, no-lag and temporal quantization contracts."""
import unittest
from pathlib import Path
import tempfile
import numpy as np

import five_level_dither as five
import stable_colour as colour
from cell_palette_quality import averaged
from dither_phase import reversed_phase


def image(rgb):
    result = np.zeros((96, 128, 3), dtype=np.uint8)
    result[12:84] = rgb
    return result


def reference():
    levels = np.zeros((96, 128), dtype=np.uint8)
    levels[12:84] = 2
    attrs = np.full(768, 71, dtype=np.uint8)
    attrs[:96] = attrs[672:] = 1
    return five.pack_levels(levels)+attrs.tobytes()


class StableColourTests(unittest.TestCase):
    def test_actual_spectrum_colours_and_normal_white_are_exact(self):
        for rgb in ([205]*3, [255]*3, [0, 205, 205], [255, 0, 0], [0, 0, 0]):
            source = image(rgb)
            result = colour.encode(source, reference())
            np.testing.assert_array_equal(averaged(result), source)
            self.assertFalse(reversed_phase(np.frombuffer(result[3840:], np.uint8)).any())

    def test_moving_colour_uses_current_frame_with_no_history_influence(self):
        old_source = image([200, 30, 10])
        old = colour.encode(old_source, reference())
        for rgb in ([10, 30, 200], [205]*3, [20, 160, 90]):
            source = image(rgb)
            independent = colour.encode(source, reference())
            with_history = colour.encode(source, reference(), old, old_source)
            # A changed cell must be exactly the same as fresh current-source
            # quantization, not merely remain within a forgiving error bound.
            self.assertEqual(with_history, independent)

    def test_identical_source_is_stable_and_actual_pixels_respect_source_bounds(self):
        rng = np.random.default_rng(18)
        source = image(rng.integers(0, 256, (72, 128, 3), dtype=np.uint8))
        baseline = reference()
        result = colour.encode(source, baseline)
        replay = colour.encode(source, baseline, result, source)
        self.assertEqual(replay, result)
        import build_long_video_trd as video
        import monochrome_five_level as mono
        pixels = video.base.render_spectrum_screen(*five.expand(result)).astype(float)
        neutral = video.base.render_spectrum_screen(*five.expand(mono.encode(source))).astype(float)
        expanded = source.repeat(2, axis=0).repeat(2, axis=1).astype(float)
        actual_error = ((pixels-expanded)**2).reshape(96, 2, 128, 2, 3).mean(axis=(1, 3, 4))
        neutral_error = ((neutral-expanded)**2).reshape(96, 2, 128, 2, 3).mean(axis=(1, 3, 4))
        self.assertTrue(np.all(actual_error[12:84] <= neutral_error[12:84]+64+1e-8))
        actual_chroma = (((pixels-expanded) @ colour.CHROMA)**2).reshape(96, 2, 128, 2, 2).mean(axis=(1, 3, 4))
        neutral_chroma = (((neutral-expanded) @ colour.CHROMA)**2).reshape(96, 2, 128, 2, 2).mean(axis=(1, 3, 4))
        self.assertTrue(np.all(actual_chroma[12:84] <= 2*neutral_chroma[12:84]+16+1e-8))
        self.assertEqual(result[3840:3936], bytes([1])*96)
        self.assertEqual(result[4512:], bytes([1])*96)

    def test_small_source_perturbations_stay_source_bounded(self):
        prior = prior_source = None
        for rgb in ([150, 152, 100], [151, 152, 100], [150, 152, 100]):
            source = image(rgb)
            result = colour.encode(source, reference(), prior, prior_source)
            self.assertLessEqual(np.mean((averaged(result)[12:84]-source[12:84])**2),
                                 np.mean((averaged(reference())[12:84]-source[12:84])**2))
            if prior is not None:
                self.assertEqual(result[3936:4512], prior[3936:4512])
            prior, prior_source = result, source

    def test_invalid_temporal_or_flash_inputs_are_rejected(self):
        source = image([0]*3)
        with self.assertRaises(ValueError): colour.encode(source, reference(), reference())
        with self.assertRaises(ValueError): colour.encode(source.astype(float), reference())
        bad = bytearray(reference());bad[3936] |= 128
        with self.assertRaises(ValueError): colour.encode(source, bad)

    def test_smooth_gradient_has_no_artificial_gray_attribute_islands(self):
        from convert_video import convert_frames
        import hybrid_five_level as hybrid
        source = image([0]*3)
        source[12:84] = np.tile(np.rint(np.linspace(25, 225, 128)).astype(np.uint8), (72, 1))[:, :, None]
        with tempfile.TemporaryDirectory() as tmp:
            compact, _ = convert_frames(np.array([source[12:84]]), Path(tmp))
            old = hybrid.refine_compact(compact[0].tobytes(), source)
            result = colour.encode(source, old)
            self.assertLess(colour.boundary_error(source[12:84], averaged(result)[12:84]),
                            colour.boundary_error(source[12:84], averaged(old)[12:84])/10)
            self.assertTrue(set(np.frombuffer(result[3936:4512], np.uint8)) <= {1, 71})
            del compact

    def test_real_source_colour_contour_is_not_smoothed_away(self):
        source = image([205, 0, 0])
        source[12:84, 64:] = [0, 0, 205]
        result = colour.encode(source, reference())
        np.testing.assert_array_equal(averaged(result), source)

    def test_monochrome_flag_preserves_native_black_white_in_both_formats(self):
        from convert_video import convert_frames
        from generic_cell_codebook import prepare_frames
        import build_long_video_trd as video
        source = np.empty((72, 128, 3), dtype=np.uint8)
        source[:] = [80, 180, 240]
        source[:, :32] = [255, 0, 0]
        source[:, 64:96] = [0, 255, 0]
        source[:, 96:] = [0, 0, 255]
        with tempfile.TemporaryDirectory() as tmp:
            compact, _ = convert_frames(np.array([source]), Path(tmp), monochrome=True)
            selected, report = prepare_frames(np.array([source]), compact, tmp, monochrome=True)
            for screen in (video.expand_compact_screen(compact[0].tobytes()), five.expand(selected[0].tobytes())):
                rgb = video.base.render_spectrum_screen(*screen)
                np.testing.assert_array_equal(rgb[:, :, 0], rgb[:, :, 1])
                np.testing.assert_array_equal(rgb[:, :, 1], rgb[:, :, 2])
                self.assertTrue(set(np.unique(rgb)) <= {0, 255})
            self.assertTrue(report['monochrome'])
            self.assertEqual(report['colour_policy'], 'monochrome')
            self.assertEqual(report['colour_comparison']['stable']['temporal_chroma_residual_mse'], 0)
            del compact, selected


if __name__ == '__main__':
    unittest.main()
