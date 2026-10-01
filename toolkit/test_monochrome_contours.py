"""Contour detection must preserve the monochrome ABI and avoid fake borders."""
import unittest

import numpy as np

import five_level_dither as five
import monochrome_five_level as mono
import monochrome_contours as contours


class ContourTests(unittest.TestCase):
    def test_flat_picture_has_no_outline_or_letterbox_edge(self):
        image = np.zeros((96,128,3), dtype=np.uint8)
        image[12:84] = 128
        encoded, mask = contours.encode(image)
        self.assertFalse(mask.any())
        self.assertEqual(encoded, mono.encode(image))

    def test_equal_luma_colour_boundary_remains_detectable(self):
        image = np.zeros((96,128,3), dtype=np.uint8)
        image[12:84,:64] = [255,0,0]
        image[12:84,64:] = [0,76,0]
        baseline = mono.encode(image)
        encoded, mask = contours.encode(image)
        levels = five.unpack_levels(baseline[:3840])
        self.assertTrue(np.all(levels[12:84]==1))
        self.assertGreater(np.count_nonzero(mask), 50)
        ys,xs = np.nonzero(mask)
        self.assertTrue(np.all((xs>=61)&(xs<=66)))
        self.assertTrue(np.all(five.unpack_levels(encoded[:3840])[mask]==0))
        self.assertEqual(encoded[3840:], baseline[3840:])

    def test_weak_texture_is_ignored(self):
        image = np.zeros((96,128,3), dtype=np.uint8)
        image[12:84] = (120+4*(np.indices((72,128)).sum(axis=0)%2))[:,:,None]
        self.assertFalse(contours.edge_mask(image).any())

    def test_one_level_limit_determinism_and_input_immutability(self):
        image = np.random.default_rng(42).integers(0,256,(96,128,3), dtype=np.uint8)
        before = image.copy()
        encoded, mask = contours.encode(image)
        old = five.unpack_levels(mono.encode(image)[:3840]).astype(int)
        new = five.unpack_levels(encoded[:3840]).astype(int)
        self.assertTrue(np.all((old-new>=0)&(old-new<=1)))
        self.assertTrue(np.all(old[~mask]==new[~mask]))
        self.assertFalse(mask[:12].any() or mask[84:].any())
        self.assertEqual(encoded, contours.encode(image)[0])
        np.testing.assert_array_equal(image, before)


if __name__ == '__main__':
    unittest.main()
