"""Regression cases for attribute reversals, native phase and n-2 maps."""
import unittest

import numpy as np

import build_long_video_trd as video
from dither_phase import dirty_maps, expand, reversed_phase, scanlines
from probe_cell_output_masks import masks


def frame(attr=71, value=0xaa):
    result = np.zeros(3840, dtype=np.uint8)
    result[384:2688] = value
    result[3072:] = 1
    result[3168:3744] = attr
    return result


class DitherPhaseTests(unittest.TestCase):
    def test_existing_renderer_reproduces_opposite_half_phase(self):
        normal, inverted = frame(71), frame(120)
        def picture(state, aligned):
            return video.base.render_spectrum_screen(*expand(state, aligned=aligned))
        self.assertFalse(np.array_equal(picture(normal, False), picture(inverted, False)))
        np.testing.assert_array_equal(picture(normal, True), picture(inverted, True))

    def test_all_packed_values_preserve_each_logical_pixel_colour_sum(self):
        # Every non-FLASH attribute and every possible packed source byte.
        for attr in range(128):
            state = frame(attr)
            state[384:2688] = np.tile(np.arange(256, dtype=np.uint8), 9)
            before = video.base.render_spectrum_screen(*expand(state))
            after = video.base.render_spectrum_screen(*expand(state, aligned=True))
            def sums(image):
                return image.astype(np.uint16).reshape(96, 2, 128, 2, 3).sum(axis=(1, 3))
            np.testing.assert_array_equal(sums(before), sums(after))
            self.assertEqual(expand(state), video.expand_compact_screen(state.tobytes()))

    def test_all_distinct_pairs_have_the_same_half_phase(self):
        for bright in (0, 64):
            for ink in range(8):
                for paper in range(ink):
                    a = frame(bright | (paper << 3) | ink)
                    b = frame(bright | (ink << 3) | paper)
                    pa = video.base.render_spectrum_screen(*expand(a, aligned=True))
                    pb = video.base.render_spectrum_screen(*expand(b, aligned=True))
                    np.testing.assert_array_equal(pa, pb)

    def test_five_neutral_coverages_use_nested_white_pixels(self):
        samples = [(71, 0), (71, 1), (71, 2), (120, 1), (71, 3)]
        previous = np.zeros((2, 2), dtype=bool)
        for count, (attr, code) in enumerate(samples):
            image = video.base.render_spectrum_screen(*expand(frame(attr, code*85), aligned=True))
            white = image[24:26, :2, 0] == 255
            self.assertEqual(int(white.sum()), count)
            self.assertTrue(np.all(white | ~previous))
            previous = white

    def test_attribute_only_change_needs_same_back_screen_redraw(self):
        states = np.array([frame(71), frame(71), frame(120), frame(120), frame(120)])
        legacy = masks(states)[0]
        np.testing.assert_array_equal(dirty_maps(states)[0], legacy)
        aligned, exact = dirty_maps(states, aligned=True)
        self.assertFalse(legacy[2:].any())
        self.assertEqual(int(exact[2].sum()), 576)
        self.assertEqual(int(exact[3].sum()), 576)
        self.assertFalse(aligned[4].any())
        # Replay actual bitmap bytes into independent alternating screens.
        screens = [np.zeros((2, 96, 32), dtype=np.uint8) for _ in range(2)]
        for index, state in enumerate(states):
            wanted = np.stack(scanlines(state, aligned=True))
            bits = np.unpackbits(aligned[index], axis=1).repeat(4, axis=0)
            np.copyto(screens[index % 2][:, 8:88], wanted[:, 8:88], where=bits[None].astype(bool))
            np.testing.assert_array_equal(screens[index % 2], wanted)

    def test_flash_requires_explicit_policy(self):
        with self.assertRaisesRegex(ValueError, 'FLASH'):
            expand(frame(199), aligned=True)


if __name__ == '__main__':
    unittest.main()
