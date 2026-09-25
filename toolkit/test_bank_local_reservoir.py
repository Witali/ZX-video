import unittest
from probe_bank_local_reservoir import Queue,simulate


def block(size,cost):
    return dict(raw_bytes=size,compressed_bytes=size//2,tstates=cost,
        slices=[dict(produced=size//2,tstates=cost//2),dict(produced=size,tstates=cost-cost//2)])


class ReservoirTests(unittest.TestCase):
    def test_fractional_budget_terminates_and_conserves_work(self):
        q=Queue([block(511,17777),block(8192,531111)],1,32,False)
        for budget in (1e-310,0.123456789,100.999,555.13):q.advance(budget)
        q.require(8703)
        self.assertAlmostEqual(q.work,17777+531111+32*(255+4096),places=6)
        self.assertEqual(q.peak,1)

    def test_partial_blocks_still_occupy_slots(self):
        for atomic in (False,True):
            q=Queue([block(100,1000),block(8192,81920),block(31,310)],2,0,atomic)
            q.advance(float('inf'))
            self.assertEqual(q.position,8292)
            q.require(99);self.assertEqual(q.advance(float('inf')),0)
            q.require(100);self.assertEqual(q.advance(float('inf')),310)
            self.assertEqual(q.position,8323)
            self.assertEqual(q.peak,2)

    def test_full_movie_scope_and_work_conservation_both_models(self):
        blocks=[block(8192,555555) for _ in range(8)]+[block(721,65432)]
        total=sum(b['raw_bytes'] for b in blocks)
        frames=[dict(frame=i,end=(i+1)*total//100,draw=80000,pre=160000,irq=5000) for i in range(100)]
        for atomic in (False,True):
            result=simulate(blocks,frames,3,32,0,atomic)
            self.assertEqual(result['late_frames'],0)
            self.assertEqual(result['peak_slots'],3)
            self.assertAlmostEqual(result['total_decoder_tstates'],sum(b['tstates']+32*b['compressed_bytes'] for b in blocks),places=3)


if __name__=='__main__':unittest.main()
