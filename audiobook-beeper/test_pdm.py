"""Native bit order, bank boundaries, constant cycles, guards and invalid sizes."""
import unittest
import numpy as np
import gzip
from pathlib import Path

from pdm_player import build_disk, BANK_BYTES, BANKS, BIT_TSTATES
from verify_pdm import native_check
from build_pdm import sigma_delta,reconstruct
from pdm_player import CPU_CLOCK


class PlayerTests(unittest.TestCase):
    def test_all_byte_values_partial_and_every_bank(self):
        for period in (52,46):
            for size in (256,BANK_BYTES,BANK_BYTES+256,len(BANKS)*BANK_BYTES):
                with self.subTest(size=size,period=period):
                    data=(bytes(range(256))*(size//256))
                    disk,meta=build_disk(data,period)
                    result=native_check(disk,meta,data)
                    self.assertTrue(result['every_bit_exact'])
                    self.assertEqual(result['interval_count'],size*8)
                    self.assertEqual(result['interval_tstates'],period)
                    self.assertEqual(result['bank_sequence'],list(BANKS[:(size+16383)//16384]))

    def test_default_disk_remains_identical_to_verified_52_t_version(self):
        directory=Path(__file__).resolve().parent/'preview'
        packed=gzip.decompress((directory/'soundtrack.pdm.gz').read_bytes())
        disk,_=build_disk(packed)
        self.assertEqual(disk,(directory/'audiobook-preview.trd').read_bytes())

    def test_repeat_preserves_two_cycles_and_both_wraps(self):
        for period in (52,46):
            for size in (256,BANK_BYTES+256,len(BANKS)*BANK_BYTES):
                with self.subTest(period=period,size=size):
                    data=bytes(range(255,-1,-1))*(size//256)
                    disk,meta=build_disk(data,period,repeat=True)
                    result=native_check(disk,meta,data)
                    self.assertEqual(result['bits'],size*8*2)
                    self.assertEqual(result['cycles_verified'],2)
                    self.assertEqual(result['final_hold_tstates'],48 if period==46 else 52)
                    self.assertFalse(result['eof_mutes'])
                    self.assertTrue(result['stack_and_code_intact'])

    def test_reject_invalid_lengths(self):
        for size in (0,1,255,257,len(BANKS)*BANK_BYTES+256):
            with self.assertRaises(ValueError): build_disk(bytes(size))
        with self.assertRaises(ValueError): build_disk(bytes(256),44)

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
