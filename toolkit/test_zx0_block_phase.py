import unittest
from zx0_block_phase import ranges


class BlockPhaseTests(unittest.TestCase):
    def test_all_phases_cover_boundaries_without_empty_or_oversize_blocks(self):
        for phase in range(8192):
            for first,length in ((0,1),(3379,1),(4813,1025898),(8191,8194),(8192,16384)):
                spans=list(ranges(first,first+length,phase))
                self.assertEqual(spans[0][0],first)
                self.assertEqual(spans[-1][1],first+length)
                self.assertEqual(sum(b-a for a,b in spans),length)
                self.assertTrue(all(1<=b-a<=8192 for a,b in spans))
                self.assertTrue(all(a[1]==b[0] for a,b in zip(spans,spans[1:])))
                self.assertTrue(all(b%8192==phase for _,b in spans[:-1]))

    def test_bad_ranges_are_rejected(self):
        for args in ((0,0,0),(1,0,0),(-1,2,0),(0,1,-1),(0,1,8192)):
            with self.assertRaises(ValueError):list(ranges(*args))


if __name__=='__main__':unittest.main()
