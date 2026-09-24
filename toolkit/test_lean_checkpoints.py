"""Checkpoint safety at ZX0/frame boundaries; real Z80 comparisons use the probe."""
import unittest
import numpy as np
from build_fap3_trd import Builder
from frame_output_pipeline import display_screen


class LeanCheckpointTests(unittest.TestCase):
    def fixture(self):
        b=Builder.__new__(Builder)
        b.raw=bytes(i%251 for i in range(17000))
        b.native_map_offsets=[500,8150,9000,12000]
        b.cold_bitmaps=True
        return b

    def test_map_straddling_zx0_boundary(self):
        b=self.fixture(); original=b.raw
        result=b.stream_block(8000,8192,1,4)+b.stream_block(8192,12500,1,4)
        expected=bytearray(original[8000:12500])
        expected[150:230]=b'\xff'*80; expected[1000:1080]=b'\xff'*80
        self.assertEqual(result,expected)
        self.assertEqual(b.raw,original)

    def test_single_frame_volume_does_not_rewrite_following_map(self):
        b=self.fixture(); expected=bytearray(b.raw[8000:10000]); expected[150:230]=b'\xff'*80
        self.assertEqual(b.stream_block(8000,10000,1,2),expected)

    def test_first_volume_and_disabled_option_preserve_stream(self):
        b=self.fixture()
        self.assertEqual(b.stream_block(0,len(b.raw),0,4),b.raw)
        b.cold_bitmaps=False
        self.assertEqual(b.stream_block(8000,10000,1,4),b.raw[8000:10000])

    def test_keep_attribute_predictors(self):
        b=self.fixture(); rng=np.random.default_rng(43)
        b.states=rng.integers(0,256,(1,3840),dtype=np.uint8)
        original=display_screen(b.states[0].tobytes(),black_borders=True)
        self.assertEqual(b.checkpoint_screen(0),bytes(6144)+original[6144:])
        b.cold_bitmaps=False
        self.assertEqual(b.checkpoint_screen(0),original)


if __name__=='__main__': unittest.main()
