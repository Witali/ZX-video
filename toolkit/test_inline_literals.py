"""Literal fallthrough: exact cycles, token suspension, slots and AY interrupts."""
from hashlib import sha256
import unittest
from unittest.mock import patch

import bank_local_zx0
from benchmark_bank_local_zx0 import Harness
from benchmark_direct_slot_input import Harness as Producer
import test_bank_local_zx0 as local_tests
import test_direct_slot_input as input_tests
import test_slot_queue as queue_tests
from zx0_speed import Token,encode


class InlineLiteralTests(unittest.TestCase):
    def test_default_code_unchanged(self):
        self.assertEqual(sha256(bank_local_zx0.build()[0]).hexdigest(),
            '0f9e6c25f57b654887e742bb5e13bea2c80d11559447c1e3b3cbdbe4da75c455')
        self.assertEqual(sha256(bank_local_zx0.build(dynamic_input=True)[0]).hexdigest(),
            '48d391d1c135ba78497b3690e5e2aae89f15e73bdbe1a10b2ecd4f7544ab2bd2')

    def test_exact_delta_suspension_wrap_and_input_offset(self):
        for dynamic in (False,True):
            for size in (1,255,256,257,8192):
                raw=bytes(i%251 for i in range(size))
                tokens=[Token(0,size)] if size<=251 else [Token(0,251),Token(251,size-251,251)]
                payload=encode(raw,tokens)
                for slot in ((0,1,3,4) if dynamic else (1,3,4)):
                    hs=[Harness(dynamic_input=dynamic,inline_literals=x) for x in (False,True)]
                    for h in hs:
                        h.begin(payload,raw,slot=slot,screen_bit=8,input_offset=255 if dynamic else 0)
                        for target in sorted({min(size,n) for n in (1,127,255,256,257,4095,8191,8192)}):
                            h.run(target)
                        h.finish();h.run(size)
                    self.assertEqual(hs[1].total-hs[0].total,-17-27*sum(not t.offset for t in tokens))
                    self.assertEqual([(s['target'],s['produced']) for s in hs[0].slices],
                                     [(s['target'],s['produced']) for s in hs[1].slices])
                    self.assertEqual(len(hs[1].code)-len(hs[0].code),-16)

    def test_specialized_stored_input_rejected_and_truncation_detected(self):
        with self.assertRaisesRegex(ValueError,'ZX0 blocks only'):
            Harness(inline_literals=True).begin(b'!',b'!',stored=True)
        raw=bytes(range(100))*5;payload=encode(raw,[Token(0,100),Token(100,400,100)])
        for bad in (payload[:-1],payload+b'!'):
            h=Harness(inline_literals=True);h.begin(bad,raw)
            with self.assertRaises((AssertionError,RuntimeError)):
                h.run(len(raw));h.finish()

    def test_ay_irq_after_each_instruction(self):
        def factory(**options):return Harness(**options,inline_literals=True)
        with patch.object(local_tests,'Harness',factory):
            local_tests.LocalZX0Tests().exercise_irq(dynamic=True)

    def test_disk_sector_crossings_and_slot_ownership(self):
        def factory(*args,**options):return Producer(*args,**options,inline_literals=True)
        with patch.object(input_tests,'Harness',factory):
            input_tests.DirectSlotTests().test_header_crossings_and_first_track_layout()
            input_tests.DirectSlotTests().test_many_blocks_sharing_one_sector_and_short_read_retry()
            queue_tests.QueueTests().test_full_empty_wrap_partial_and_zero_consumption()
            queue_tests.QueueTests().test_shared_sector_with_more_blocks_than_slots()


if __name__ == '__main__':unittest.main()
