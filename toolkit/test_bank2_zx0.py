"""Exact split-decoder cycles, suspension, input bounds and AY instruction IRQs."""
import unittest
from unittest.mock import patch
import bank_local_zx0
from bank2_zx0 import build,install_decoder,install_player
from benchmark_bank_local_zx0 import Harness
import test_bank_local_zx0 as old_tests
from zx0_speed import Token,encode


class Bank2Tests(unittest.TestCase):
    def test_layout_and_original_code_hash(self):
        regions,labels,report=build()
        self.assertEqual([len(blob) for _,blob in regions],[35,279])
        self.assertEqual(labels['end'],0x8f09)
        self.assertEqual(report['old_code_sha256'],'674e034624ad7ca6512b426183c52e6abe3bc4ac4c63588f99f7597f1ebe2021')
        self.assertEqual(report['instruction_tstate_delta'],0)

    def test_cycles_boundaries_and_slots(self):
        for size in (1,255,256,257,8192):
            raw=bytes(i%251 for i in range(size))
            tokens=[Token(0,size)] if size<=251 else [Token(0,251),Token(251,size-251,251)]
            payload=encode(raw,tokens)
            for slot in (0,1,3,4):
                hs=[Harness(dynamic_input=True,inline_literals=True) for _ in range(2)]
                install_decoder(hs[1])
                for h in hs:
                    h.begin(payload,raw,slot=slot,screen_bit=8,input_offset=255)
                    for target in sorted({min(size,n) for n in (1,127,255,256,257,4095,8191,8192)}):h.run(target)
                    h.finish();h.run(size)
                self.assertEqual(hs[0].slices,hs[1].slices)

    def test_ay_irq_after_each_instruction(self):
        def factory(**kw):
            h=Harness(**kw,inline_literals=True);install_decoder(h);return h
        with patch.object(old_tests,'Harness',factory):old_tests.LocalZX0Tests().exercise_irq(dynamic=True)

    def test_invalid_payload_bounds(self):
        raw=bytes(range(100))*5;payload=encode(raw,[Token(0,100),Token(100,400,100)])
        for bad in (payload[:-1],payload+b'!'):
            h=Harness(dynamic_input=True,inline_literals=True);install_decoder(h);h.begin(bad,raw)
            with self.assertRaises((AssertionError,RuntimeError)):h.run(len(raw));h.finish()

    def test_fallback_without_inline_huffman_leaves_ram_alone(self):
        def forbidden(*args):raise AssertionError('fallback accessed RAM')
        report=install_player(forbidden,forbidden,{'inline_huffman_patches':{'enabled':False}},None)
        self.assertFalse(report['enabled'])


if __name__=='__main__':unittest.main()
