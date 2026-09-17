"""Palette cache must retain levels, attributes and tie-breaking exactly."""
import unittest
from unittest.mock import patch
import numpy as np

import build_long_video_trd as video


class PaletteTests(unittest.TestCase):
    def test_preview_covers_all_attributes_and_bitmap_bytes(self):
        rng=np.random.default_rng(62)
        attrs=bytes(range(256))*3
        for bitmap in (bytes(range(256))*24,bytes(6144),bytes([255])*6144,rng.integers(0,256,6144,dtype=np.uint8).tobytes()):
            np.testing.assert_array_equal(video.base.render_spectrum_screen(bitmap,attrs),video.base.render_spectrum_screen_reference(bitmap,attrs))

    def test_exact_pixels_and_attributes(self):
        rng=np.random.default_rng(71)
        palette=rng.integers(0,256,(24,3),dtype=np.uint8)
        images=[np.zeros((96,128,3),dtype=np.uint8),
                rng.integers(0,256,(96,128,3),dtype=np.uint8),
                palette[rng.integers(0,len(palette),(96,128))]]
        for image in images:
            for dither in ('none','ordered4'):
                prepared=video.prepare_compact_palette(image,dither)
                for penalty in (0,100000,1600000):
                    previous=rng.choice(video.COLOUR_ATTRS,768) if penalty else None
                    old,oa=video.encode_compact_frame_reference(image,previous,penalty,dither)
                    new,na=video.encode_compact_frame(image,previous,penalty,dither,prepared=prepared)
                    self.assertEqual(new,old)
                    np.testing.assert_array_equal(na,oa)

    def test_feedback_selection_matches_reference(self):
        rng=np.random.default_rng(91)
        image=rng.integers(0,256,(96,128,3),dtype=np.uint8)
        args=(image,rng.choice(video.COLOUR_ATTRS,768),bytes(video.STATE_BYTES),'ordered4',6,1.25)
        new=video.encode_feedback_frame(*args)
        def reference(*args,**kwargs):return video.encode_compact_frame_reference(*args)
        with patch.object(video,'encode_compact_frame',side_effect=reference),patch.object(video.base,'render_spectrum_screen',side_effect=video.base.render_spectrum_screen_reference):
            old=video.encode_feedback_frame(*args)
        self.assertEqual(new[0],old[0]);np.testing.assert_array_equal(new[1],old[1])
        self.assertEqual(new[2],old[2])


if __name__=='__main__':unittest.main()
