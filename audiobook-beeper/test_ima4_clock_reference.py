"""Use measured cold/warm clocks without widening the eight-T-state gate."""
import gzip,tempfile,unittest
from pathlib import Path
import numpy as np
from verify_ima3_series import matching_clock_reference


class ClockReference(unittest.TestCase):
    def match(self,times,both=True):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            measured=np.array([100,110,120,130,150,158,169,181,193],dtype='<u4')
            (path/'output-times.u32.gz').write_bytes(gzip.compress(measured.tobytes()))
            return matching_clock_reference(np.asarray(times),path,{'outputs_per_cycle':4},both_loops=both)

    def test_matching_warm_loop_is_used(self):
        maximum,loop,delta=self.match([0,8,19,31])
        self.assertEqual((maximum,loop),(0,2))
        self.assertFalse(np.any(delta))

    def test_ima3_keeps_its_first_loop_reference(self):
        self.assertEqual(self.match([0,8,19,31],False)[:2],(2,1))

    def test_eight_tstates_pass_nine_fail(self):
        self.assertEqual(self.match([0,10,20,38],False)[:2],(8,1))
        self.assertIsNone(self.match([0,10,20,39],False))

    def test_no_time_stretch_or_partial_prefix_acceptance(self):
        self.assertIsNone(self.match([0,20,40,80]))


if __name__=='__main__':unittest.main()
