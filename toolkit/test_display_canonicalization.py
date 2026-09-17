"""Displayed colours agree with the existing native-screen renderer."""
import unittest

import numpy as np

import canonicalize_display_cells as canonical
import build_long_video_trd as video


class CanonicalDisplayTests(unittest.TestCase):
    def test_all_attributes_and_brightness_patterns_match_native_renderer(self):
        rng = np.random.default_rng(3951)
        for variant in range(4):
            pixels = rng.integers(0, 256, 3072, dtype=np.uint8)
            if variant < 2:
                pixels.fill(255 * variant)
            elif variant == 2:
                pixels = np.choose(pixels & 3, np.array([0, 3, 192, 255], dtype=np.uint8))
            state = pixels.tobytes() + np.tile(np.arange(128, dtype=np.uint8), 6).tobytes()
            converted, _ = canonical.canonicalize(state)
            original_rgb = video.base.render_spectrum_screen(*video.expand_compact_screen(state))
            converted_rgb = video.base.render_spectrum_screen(*video.expand_compact_screen(converted))
            self.assertTrue(np.array_equal(original_rgb, converted_rgb))
            colours = canonical.displayed_colours(canonical.to_cells(state))
            keys = colours.reshape(24, 32, 8, 8).transpose(0, 2, 1, 3).reshape(192, 256)
            self.assertTrue(np.array_equal(video.base.SCREEN_PALETTE[keys], original_rgb))
            self.assertEqual(canonical.canonicalize(converted)[0], converted)


if __name__ == '__main__':
    unittest.main()
