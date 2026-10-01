"""Pure monochrome pixels, fixed phase, luma and border contracts."""
import unittest

import numpy as np

import five_level_dither as five
import monochrome_five_level as mono
from build_zxv_trd import render_spectrum_screen
from verify_cell_codebook_movie import independent_screen


class MonochromeTests(unittest.TestCase):
    def test_gray_ramp_keeps_all_five_levels_and_extremes(self):
        image = np.zeros((96,128,3), dtype=np.uint8)
        image[12:84] = np.resize(np.arange(256, dtype=np.uint8),(72,128))[:,:,None]
        encoded = mono.encode(image)
        levels = five.unpack_levels(encoded[:3840])
        expected = np.floor(image[12:84,:,0].astype(float)*4/255+.5).astype(np.uint8)
        np.testing.assert_array_equal(levels[12:84], expected)
        self.assertEqual(set(levels[12:84].ravel()), set(range(5)))
        self.assertEqual(encoded[3936:4512], bytes([71])*576)
        self.assertEqual(encoded[3840:3936]+encoded[4512:], bytes([1])*192)

    def test_colours_become_luma_not_brightness_by_max_channel(self):
        values = []
        for colour in ([255,0,0], [0,255,0], [0,0,255]):
            image = np.full((96,128,3), colour, dtype=np.uint8)
            encoded = mono.encode(image)
            values.append(int(five.unpack_levels(encoded[:3840])[12,0]))
        self.assertEqual(values, [1,3,0])

    def test_all_physical_pixels_are_black_or_bright_white(self):
        image = np.random.default_rng(47).integers(0,256,(96,128,3), dtype=np.uint8)
        state = mono.encode(image)
        screen = five.expand(state)
        self.assertEqual(b''.join(screen), independent_screen(state))
        rgb = render_spectrum_screen(*screen)
        np.testing.assert_array_equal(rgb[:,:,0], rgb[:,:,1])
        np.testing.assert_array_equal(rgb[:,:,1], rgb[:,:,2])
        self.assertEqual(set(np.unique(rgb)), {0,255})
        self.assertFalse(np.any(rgb[:24]) or np.any(rgb[168:]))

    def test_input_validation(self):
        for image in (np.zeros((96,128,3)), np.zeros((72,128,3),dtype=np.uint8)):
            with self.assertRaises(ValueError): mono.encode(image)


if __name__ == '__main__':
    unittest.main()
