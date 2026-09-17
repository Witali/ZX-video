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
    def test_compact_verification_accepts_tones_and_noise(self):
        states=[bytes(video.STATE_BYTES),bytes([85])*video.STATE_BYTES]
        for noise in (0,17):
            sound=video.AyFrame((200,300,400),(10,11,12),noise).serialize()
            packets=[video.make_packet(states[0],None,sound),video.make_packet(states[1],states[0],sound)]
            stream=video.serialize_video(packets,25/3,25/3)
            self.assertEqual(stream[4],video.VIDEO_NOISE_VERSION if noise else video.VIDEO_VERSION)
            video.verify_video(stream,states)
            with self.assertRaises(ValueError):video.verify_video(stream[:4]+bytes([99])+stream[5:],states)

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
            self.assertEqual(video.decode_analysis_audio(*args).tolist(),[.25,-.5,.75])
            self.assertEqual(video.decode_analysis_audio(*args,pad_end=True).tolist(),[.25,-.5,.75,0,0])


if __name__=='__main__':unittest.main()
