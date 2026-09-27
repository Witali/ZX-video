"""Bounds of the frozen-producer FIFO model; not a new playback test."""
import unittest

from profile_audio_lookahead import prefix,fifo_model,FIELD


class AudioLookaheadTests(unittest.TestCase):
    def test_active_prefix_wrap_and_old_state(self):
        ends=[0,8192,12288]
        self.assertEqual(prefix(dict(blocks_left=2,phase=2,slice_output=0xe100),ends),256)
        self.assertEqual(prefix(dict(blocks_left=2,phase=2,slice_output=0),ends),8192)
        self.assertEqual(prefix(dict(blocks_left=1,phase=0,slice_output=0),ends),8192)
        self.assertEqual(prefix(dict(blocks_left=0,phase=0,slice_output=0xf000),ends),12288)
        with self.assertRaises(ValueError):prefix(dict(blocks_left=1,phase=2,slice_output=0),ends)

    def test_capacity_only_matters_across_service_gaps(self):
        points=[(0,4)]
        opportunities=[0,3*FIELD]
        small=fifo_model([1,2,3,4],points,opportunities,FIELD,1)
        large=fifo_model([1,2,3,4],points,opportunities,FIELD,4)
        self.assertEqual(small['underruns'],2)
        self.assertEqual(large['underruns'],0)
        self.assertEqual(small['fields']-large['fields'],2)

    def test_more_capacity_cannot_supply_missing_input(self):
        points=[(0,1),(3*FIELD+1,4)]
        for capacity in (1,4,255):
            result=fifo_model([1,2,3,4],points,[0,3*FIELD+1],FIELD,capacity)
            self.assertEqual(result['underruns'],2)
            self.assertEqual(result['fields'],6)


if __name__=='__main__':unittest.main()
