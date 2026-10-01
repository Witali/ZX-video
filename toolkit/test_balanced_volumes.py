"""Small exhaustive oracles for minimax planning, frame coverage and row history."""
import itertools
import unittest

from balance_cb41_cadence import balanced_parts


class BalancedVolumesTests(unittest.TestCase):
    def test_matches_exhaustive_minimax_without_encoding(self):
        costs=[9,1,4,8,2,7,3,5,6]
        for count in (2,3,4):
            parts,report=balanced_parts(costs,5,count,grid=1)
            candidates=[]
            for inner in itertools.combinations(range(1,len(costs)),count-1):
                cuts=(0,*inner,len(costs));spans=list(zip(cuts,cuts[1:]))
                if max(b-a for a,b in spans)>5:continue
                sizes=[sum(costs[a:b]) for a,b in spans]
                candidates.append((max(sizes),sum(x*x for x in sizes),list(cuts)))
            best=min(candidates)
            self.assertEqual(report['estimated_peak_video_bytes'],best[0])
            self.assertEqual([i for a,b in parts for i in range(a,b)],list(range(len(costs))))

    def test_static_rows_include_both_previous_screens(self):
        sets=[set(range(1,121)),set(range(121,241)),set(range(241,361)),{0}]
        with self.assertRaisesRegex(ValueError,'no valid volume'):
            balanced_parts([1]*4,2,2,sets=sets,grid=1)
        parts,_=balanced_parts([1]*4,2,2,grid=1)
        self.assertEqual(parts,[(0,2),(2,4)])

    def test_impossible_bounds_fail(self):
        with self.assertRaisesRegex(ValueError,'no valid volume'):
            balanced_parts([1]*9,2,4,grid=1)


if __name__=='__main__':unittest.main()
