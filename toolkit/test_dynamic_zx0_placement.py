"""Relocated decoder execution keeps exact bytes, suspension and cycle sums."""
import struct
import unittest
from unittest.mock import patch

import bank2_zx0
import faster_zx0
from benchmark_faster_zx0 import fixture
from test_inplace_slot import block


class PlacementTests(unittest.TestCase):
    def test_bank2_relocations_and_bounds(self):
        _,original,old=bank2_zx0.build()
        _,moved,new=bank2_zx0.build(origin=0x8de0,limit=0x8ef7)
        for name,address in original.items():
            expected=address-18 if old['new_origin']<=address<=old['new_end'] else address
            self.assertEqual(moved[name],expected)
        self.assertEqual(new['code_bytes'],old['code_bytes'])
        self.assertEqual(new['instruction_tstate_delta'],0)
        with self.assertRaises(ValueError): bank2_zx0.build(origin=0x8de0,limit=0x8ef6)
        with self.assertRaises(ValueError): faster_zx0.build(core=0x8de0,core_limit=0x8de1)

    def test_fast_real_cpu_and_boundaries_have_zero_cycle_delta(self):
        blocks=[block(15872),block(2100,literal=True)]
        stream=b''.join(struct.pack('<HH',len(raw),len(payload))+payload for payload,raw in blocks)
        baseline,_=fixture(stream,53,'fast'); original=faster_zx0.build
        with patch.object(faster_zx0,'build',side_effect=lambda variant:original(variant,core=0x8de0,core_limit=0x8ef7)):
            moved,_=fixture(stream,53,'fast')
        for index,(payload,raw) in enumerate(blocks):
            a=baseline.block(payload,raw,index); b=moved.block(payload,raw,index)
            for key in ('decoder_tstates','producer_tstates','sectors'):
                self.assertEqual(a[key],b[key])
            print('relocation cycles',len(raw),a['decoder_tstates'],b['decoder_tstates'])
        self.assertTrue(baseline.finish()['sectors_exact_once'])
        self.assertTrue(moved.finish()['sectors_exact_once'])


if __name__=='__main__': unittest.main()
