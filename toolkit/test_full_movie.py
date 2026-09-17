"""Full-length source bounds and final partial audio interval."""
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from build_full_movie import full_duration
import build_long_video_trd as video


class FullMovieTests(unittest.TestCase):
    def test_final_partial_frame_is_included(self):
        source,count,duration=full_duration(dict(streams=[
            dict(codec_type='video',duration='596.458333'),
            dict(codec_type='audio',duration='596.461667'),
            dict(codec_type='data',duration='999')]))
        self.assertEqual(count,4971)
        self.assertEqual(duration,Fraction('596.52'))
        self.assertGreaterEqual(duration,source)
        self.assertLess(duration-source,Fraction(3,25))
        self.assertEqual(count*6,29826)

    def test_exact_grid_end_is_not_extended(self):
        self.assertEqual(full_duration(dict(streams=[],format=dict(duration='120')))[1:],(1000,Fraction(120)))

    def test_audio_tail_padding_is_opt_in(self):
        raw=np.array([.25,-.5,.75],dtype='<f4').tobytes()
        with patch.object(video.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=raw)):
            args=('ffmpeg',Path('source.mov'),0,1,5,True)
            np.testing.assert_array_equal(video.decode_analysis_audio(*args),[.25,-.5,.75])
            np.testing.assert_array_equal(video.decode_analysis_audio(*args,pad_end=True),[.25,-.5,.75,0,0])


if __name__=='__main__':unittest.main()
