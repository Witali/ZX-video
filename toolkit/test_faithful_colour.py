"""Joint palette/coverage search must never defeat its monochrome fallback."""
import unittest
import numpy as np

import faithful_colour as colour
import five_level_dither as five
import monochrome_five_level as mono
from build_zxv_trd import render_spectrum_screen


class FaithfulColourTests(unittest.TestCase):
    def test_saturated_green_restores_colour_without_changing_coverage(self):
        image=np.zeros((96,128,3),dtype=np.uint8);image[12:84]=[0,255,0]
        state=colour.encode(image)
        np.testing.assert_array_equal(colour.averaged(state),image)
        self.assertEqual(set(np.unique(five.unpack_levels(state[:3840])[12:84])),{4})

    def test_exact_black_white_and_five_gray_levels(self):
        image=np.zeros((96,128,3),dtype=np.uint8)
        image[12:84]=np.resize(np.array([0,64,128,191,255],dtype=np.uint8),(72,128))[:,:,None]
        state=colour.encode(image)
        self.assertEqual(state,mono.encode(image))

    def test_normal_white_is_available_and_grain_is_reoptimized(self):
        image=np.zeros((96,128,3),dtype=np.uint8);image[12:84]=205
        state=colour.encode(image)
        np.testing.assert_array_equal(colour.averaged(state),image)
        self.assertEqual(float(colour.errors(image,state)['grain'][12:84].max()),0)

    def test_guards_hold_with_mixed_cells_and_stale_palette(self):
        image=np.random.default_rng(71).integers(0,256,(96,128,3),dtype=np.uint8)
        state=colour.encode(image,np.full(768,69,dtype=np.uint8))
        a,b=colour.errors(image,mono.encode(image)),colour.errors(image,state)
        for key in ('rgb','physical_rgb'):
            self.assertTrue(np.all(b[key][12:84]<=a[key][12:84]+1e-7))
        delta=(b['luma']-a['luma'])[12:84].reshape(18,4,32,4).sum(axis=(1,3))
        self.assertTrue(np.all(delta<=1e-6))
        strict=colour.errors(image,colour.encode(image,luma_guard='sample'))
        self.assertTrue(np.all(strict['luma'][12:84]<=a['luma'][12:84]+1e-7))
        self.assertEqual(state[3840:3936]+state[4512:],bytes([1])*192)
        self.assertFalse(np.any(np.frombuffer(state[3840:],dtype=np.uint8)&128))

    def test_physical_error_identity_against_expanded_constant_source(self):
        image=np.zeros((96,128,3),dtype=np.uint8)
        image[12:84]=np.random.default_rng(9).integers(0,256,(72,128,3),dtype=np.uint8)
        state=colour.encode(image)
        screen=render_spectrum_screen(*five.expand(state)).astype(float)
        source=image.repeat(2,0).repeat(2,1).astype(float)
        actual=((screen-source)**2).reshape(96,2,128,2,3).mean(axis=(1,3,4))
        np.testing.assert_allclose(actual,colour.errors(image,state)['physical_rgb'],atol=1e-7)


if __name__=='__main__':unittest.main()
