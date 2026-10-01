"""Native bit order, bank boundaries, constant cycles, guards and invalid sizes."""
import unittest
import numpy as np

from pdm_player import build_disk, BANK_BYTES, BANKS, BIT_TSTATES
from verify_pdm import native_check
from build_pdm import sigma_delta,reconstruct
from pdm_player import CPU_CLOCK


class PlayerTests(unittest.TestCase):
    def test_all_byte_values_partial_and_every_bank(self):
        for size in (256,BANK_BYTES,BANK_BYTES+256,len(BANKS)*BANK_BYTES):
            with self.subTest(size=size):
                data=(bytes(range(256))*(size//256))
                disk,meta=build_disk(data)
                result=native_check(disk,meta,data)
                self.assertTrue(result['every_bit_exact'])
                self.assertEqual(result['interval_count'],size*8)
                self.assertEqual(result['interval_tstates'],BIT_TSTATES)
                self.assertEqual(result['bank_sequence'],list(BANKS[:(size+16383)//16384]))

    def test_reject_invalid_lengths(self):
        for size in (0,1,255,257,len(BANKS)*BANK_BYTES+256):
            with self.assertRaises(ValueError): build_disk(bytes(size))

    def test_modulator_preserves_dc_with_nonuniform_slots(self):
        intervals=np.tile([52,52,53,55,56,60],2048)
        for value in (-.65,0.,.2,.65):
            bits,report=sigma_delta(np.full(len(intervals),value),intervals)
            decoded=bits.astype(float)*2-1
            self.assertLess(abs(float(np.average(decoded,weights=intervals))-value),.001)
            self.assertLess(report['peak_error_area'],8)
        with self.assertRaises(ValueError): sigma_delta(np.array([np.nan]),np.array([52]))
        with self.assertRaises(ValueError): sigma_delta(np.array([0.]),np.array([0]))

    def test_hold_reconstruction_matches_exact_integer_bins(self):
        bits=np.array([0,1,0,1],dtype=np.uint8)
        intervals=np.array([3,11,5,7]); times=np.r_[0,np.cumsum(intervals)]
        expected=np.repeat(bits.astype(float)*2-1,intervals)
        np.testing.assert_array_equal(reconstruct(bits,times,rate=CPU_CLOCK),expected)


if __name__=='__main__': unittest.main()
