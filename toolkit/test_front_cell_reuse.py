"""Exact front-screen copy semantics, settled cells and row dictionaries."""
import unittest
import numpy as np

from dynamic_row_dictionary import representation
from front_cell_reuse import encode
from test_generic_cell_codebook import frame
from test_dynamic_cell_dictionary import scenes


class FrontReuseTests(unittest.TestCase):
    def test_settled_cells_and_independent_histories(self):
        frames=scenes()
        for lo in (0,3):
            base=representation(frames,lo,len(frames));result=encode(base,frames,lo,len(frames))
            self.assertTrue(result['proof']['both_screens_exact'])
            self.assertGreater(sum(d['front_same_cells'] for d in result['details']),0)
            self.assertEqual(result['proof']['screen_sha256'],base['screen_sha256'])

    def test_neighbour_sources_stay_on_immutable_front(self):
        rng=np.random.default_rng(32)
        words=rng.integers(0,120,(72,32),dtype=np.uint16)
        frames=np.stack([frame(np.roll(words,i,axis=1).ravel()) for i in range(4)])
        base=representation(frames,0,4);result=encode(base,frames,0,4,neighbours=True)
        self.assertGreater(sum(d['front_moved_cells'] for d in result['details']),0)
        self.assertTrue(result['proof']['both_screens_exact'])

    def test_refitted_book_including_one_frame_volume(self):
        frames=scenes()
        for lo,hi in ((0,1),(3,4),(3,len(frames))):
            base=representation(frames,lo,hi,book_front_reuse=True)
            result=encode(base,frames,lo,hi)
            self.assertTrue(result['proof']['both_screens_exact'])

    def test_attribute_xor_uses_old_back_screen(self):
        from attribute_delta_stream import encode as attribute_delta
        frames=scenes()
        for lo in (0,3):
            base=representation(frames,lo,len(frames),book_front_reuse=True)
            front=encode(base,frames,lo,len(frames))
            delta=attribute_delta(front,frames,lo,len(frames))
            self.assertEqual(front['proof']['screen_sha256'],delta['proof']['screen_sha256'])


if __name__=='__main__':unittest.main()
