"""Check on-the-fly conversion, all byte values, paging and loop continuity."""
import unittest
import numpy as np
from pcm_player import build_disk
from verify_pcm import native_check,reference


class LiveTests(unittest.TestCase):
    def test_every_value_pages_banks_and_partial_bank(self):
        for size in (256,16384,16640,98304):
            with self.subTest(size=size):
                pcm=bytes(range(256))*(size//256)
                disk,meta=build_disk(pcm)
                proof=native_check(disk,meta,pcm)
                self.assertTrue(proof['all_pcm_values_exact'])
                self.assertEqual(proof['bits_verified'],size*10*2+1)
                self.assertEqual(proof['cycle_tstates'],meta['deterministic_cycle_tstates'])

    def test_clock_trim_does_not_change_pcm_or_pdm(self):
        pcm=bytes(range(255,-1,-1))
        for nops in (1,4,8):
            disk,meta=build_disk(pcm,nops,steady=False)
            self.assertTrue(native_check(disk,meta,pcm)['every_pdm_bit_exact'])

    def test_density_and_pipeline_delay(self):
        for amplitude in (0,1,64,128,192,254,255):
            bits,error=reference(bytes([amplitude])*256)
            self.assertTrue(np.all(bits[:3]==0))
            self.assertLess(abs(float(bits[3:].mean())-amplitude/256),1/1000)
            self.assertTrue(0<=error<256)

    def test_invalid_payloads(self):
        for n in (0,1,255,257,98560):
            with self.assertRaises(ValueError): build_disk(bytes(n))
        with self.assertRaises(ValueError): build_disk(bytes(256),9)
        with self.assertRaises(ValueError): build_disk(bytes(256),1)


if __name__=='__main__': unittest.main()
