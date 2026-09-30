"""Five coverages retain the established phase-aligned 2x2 pattern family."""
import unittest

import numpy as np

import build_long_video_trd as video
import dither_phase as phase
import five_level_dither as five
import hybrid_five_level as hybrid


def native(frame):
    levels, attrs = hybrid.decode(frame)
    return video.base.render_spectrum_screen(*five.expand(five.pack_levels(levels)+attrs))


def averaged(frame):
    return native(frame).astype(np.float64).reshape(96, 2, 128, 2, 3).mean(axis=(1, 3))


class FiveLevelCompatibilityTests(unittest.TestCase):
    def test_all_five_patterns_match_existing_phase_aligned_family(self):
        # The old representation could obtain the upper quarter only by
        # reversing the endpoint colours. Keep its corrected spatial phase.
        samples = [(71, 0), (71, 1), (71, 2), (120, 1), (71, 3)]
        expected = np.array([[[0,0],[0,0]], [[1,0],[0,0]], [[1,0],[0,1]],
                             [[1,1],[0,1]], [[1,1],[1,1]]], dtype=np.uint8)*255
        for count, (attr, code) in enumerate(samples):
            compact = bytes([code*85])*3072+bytes([attr])*768
            wanted = video.base.render_spectrum_screen(*phase.expand(compact, aligned=True))
            np.testing.assert_array_equal(wanted[:2,:2,0],expected[count])
            state = five.from_compact(compact)
            for canonical in (False, True):
                rendered = native(hybrid.from_five(state,canonical_quartets=canonical))
                np.testing.assert_array_equal(rendered,wanted)

    def test_all_five_coverages_coexist_inside_one_attribute_cell(self):
        levels = np.zeros((96,128),dtype=np.uint8)
        levels[:4,:4] = np.arange(16).reshape(4,4) % 5
        state = five.pack_levels(levels)+bytes([71])*768
        for canonical in (False,True):
            frame = hybrid.from_five(state,canonical_quartets=canonical)
            self.assertEqual(frame.modes[0],1)
            self.assertEqual(len(frame.cells[0]),5)
            np.testing.assert_array_equal(averaged(frame)[:4,:4,0],levels[:4,:4]*63.75)

    def test_mode_choice_does_not_change_phase_or_pixels(self):
        levels = np.zeros((96,128),dtype=np.uint8)
        levels[:4,:4] = [0,1,2,4]
        levels[:4,4:8] = [0,3,2,4]
        levels[:4,8:12] = np.arange(16).reshape(4,4) % 5
        state = five.pack_levels(levels)+bytes([71])*768
        full = hybrid.from_five(state,adaptive=False)
        canonical = hybrid.from_five(state,canonical_quartets=True)
        self.assertEqual(canonical.modes[:3],bytes([0,2,1]))
        for candidate in (canonical,hybrid.from_five(state)):
            np.testing.assert_array_equal(native(candidate),native(full))
        # Equal half-tones in different cells have the identical 2x2 phase.
        np.testing.assert_array_equal(native(canonical)[:2,4:6],native(canonical)[:2,12:14])

    def test_refinement_never_increases_individual_sample_rgb_error(self):
        rng = np.random.default_rng(505)
        compact = rng.integers(0,256,3840,dtype=np.uint8)
        compact[3072:] = np.arange(768,dtype=np.uint16) % 128
        image = rng.integers(0,256,(96,128,3),dtype=np.uint8)
        old = hybrid.from_compact(compact)
        refined = hybrid.refine_compact(compact,image)
        new = hybrid.from_five(refined,canonical_quartets=True)
        before, after = averaged(old), averaged(new)
        self.assertTrue(np.all(((after-image)**2).sum(axis=2) <= ((before-image)**2).sum(axis=2)))
        self.assertEqual(hybrid.decode(old)[1],hybrid.decode(new)[1])


if __name__ == '__main__': unittest.main()
