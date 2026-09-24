import unittest
import numpy as np
from probe_bounded_fragments import row_candidates,simplify,cell_counts
from probe_bounded_dictionary import bitmap_cells
from probe_bounded_motion import CHANGES


class BoundedFragmentsTests(unittest.TestCase):
    def test_quarter_step_and_cell_limits(self):
        tile=np.zeros((1,16),np.uint8);tile[0,0]=64;tile[0,2]=16
        new,found=row_candidates(tile,tile,np.ones((1,4),np.uint8))
        self.assertTrue(found[0]);self.assertTrue(np.all(new==0))
        self.assertEqual(cell_counts(CHANGES[tile,new]).tolist(),[[2,0,0,0]])
        # Level 3 has coverage 4, so a transition to level 2 is TWO steps.
        tile[0,0]=192;tile[0,2]=128
        new,found=row_candidates(tile,tile,np.ones((1,4),np.uint8))
        if found[0]:self.assertEqual(new[0,0],192)

    def test_frame_budget_and_forced_temporal_reset(self):
        states=np.zeros((5,3840),np.uint8);states[:,3072:]=1
        for tile in range(32,48):
            y,x=divmod(tile,16);states[:,y*256+2*x]=64;states[:,y*256+2*x+32]=16
        result,rows=simplify(states,states,budget=4,max_inexact=3)
        self.assertTrue(all(r['logical_changes']<=4 for r in rows))
        errors=np.any(bitmap_cells(states)!=bitmap_cells(result),axis=2);ages=np.zeros(768,int)
        for e in errors:
            ages=np.where(e,ages+1,0);self.assertLessEqual(ages.max(),3)
        zero,_=simplify(states,states,budget=0)
        self.assertTrue(np.array_equal(zero,states))

    def test_existing_errors_share_the_budget(self):
        original=np.zeros((2,3840),np.uint8);original[:,3072:]=1
        old=original.copy();old[:,512]=64;old[:,514]=64;old[:,516]=64
        result,rows=simplify(original,old,budget=1)
        self.assertEqual([r['logical_changes'] for r in rows],[1,1])
        self.assertTrue(np.array_equal(original[:,3072:],result[:,3072:]))
        old[:,3072]=2
        with self.assertRaises(ValueError):simplify(original,old)

    def test_disallowed_tiles_stay_exact(self):
        original=np.zeros((1,3840),np.uint8);original[:,3072:]=1
        original[:,512]=64;original[:,544]=16
        result,rows=simplify(original,original,eligible_tiles=np.zeros((1,192),bool))
        self.assertTrue(np.array_equal(result,original));self.assertEqual(rows[0]['selected_tiles'],0)


if __name__=='__main__':unittest.main()
