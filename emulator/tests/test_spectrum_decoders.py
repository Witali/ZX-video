"""Actual compressed blocks on fixed/paged Spectrum RAM, contention disabled."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/'libraries/zx0/src'),str(ROOT/'libraries/lzsa/src')]

from emulator.cpu import load_library
from emulator.spectrum_runner import execute, OUTPUT_BANKS, IRQ_OVERHEAD_TSTATES


class SpectrumDecoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from zx0.maximum import build as zx_build
        from lzsa.hybrid import build as lz_build
        from zx0.tokens import Token, encode as zx_encode
        from lzsa import encode as lz_encode
        cls.library = load_library()
        cls.profiles = dict(zx0=zx_build(prefix_cap=228,shared_prefixes=True),lzsa2=lz_build(profile='fast'))
        raw = b'A'*15872
        cls.cases = (
            ('zx0',zx_encode(raw,[Token(0,1),Token(1,len(raw)-1,1)]),raw),
            ('lzsa2',lz_encode(raw,[(1,len(raw)-1,1)]),raw),
            ('lzsa2',bytes.fromhex('ef 41 f0 e8'),b'A'),
            ('lzsa2',bytes.fromhex('e7 f0 e8'),b''))

    def test_all_safe_output_banks_and_irq_cpu_formula(self):
        for codec,payload,raw in self.cases:
            before = execute(self.profiles[codec],payload,raw,codec=codec,library=self.library)
            for bank in OUTPUT_BANKS:
                for phase in (0,35,36,14361,70907):
                    with self.subTest(codec=codec,bank=bank,phase=phase,output=len(raw)):
                        result = execute(self.profiles[codec],payload,raw,codec=codec,library=self.library,
                            output_bank=bank,interrupts=True,frame_phase=phase)
                        self.assertEqual(result['tstates'],before['tstates']+IRQ_OVERHEAD_TSTATES*result['irq_acknowledgements'])
                        self.assertTrue(result['final_memory_verified'])
                        self.assertFalse(result['live_write_guard'])
                        self.assertFalse(result['compressed_overlap'])

    def test_physical_alias_output_banks_rejected_before_setup(self):
        codec,payload,raw = self.cases[0]
        for bank in (2,5,-1,8,True):
            with self.subTest(bank=bank),self.assertRaisesRegex(ValueError,'aliases'):
                execute(self.profiles[codec],payload,raw,codec=codec,library=self.library,output_bank=bank)

    def test_invalid_bank_crossing_and_code_stack_layout_rejected(self):
        codec,payload,raw = self.cases[0]
        with self.assertRaises(ValueError):
            execute(self.profiles[codec],payload,raw+b'A'*16384,codec=codec,library=self.library)
        malformed = ([(0xbfb0,b'\xc9')],{'start':0xbfb0},{'entry':'start'})
        with self.assertRaisesRegex(ValueError,'caller/IRQ'):
            execute(malformed,payload,raw,codec=codec,library=self.library)

    def test_final_bank_guard_detects_write_outside_declared_regions(self):
        # Write an unrelated physical RAM bank5 byte, then emulate the expected
        # empty-block return cursors. It must fail the final all-bank check.
        payload = bytes.fromhex('e7 f0 e8')
        program = bytes.fromhex('3e42 320060 210340 1100c0 c9')
        malformed = ([(0x8000,program)],{'start':0x8000},{'entry':'start'})
        with self.assertRaisesRegex(AssertionError,'compressed-source physical bank changed'):
            execute(malformed,payload,b'',codec='lzsa2',library=self.library)


if __name__ == '__main__':
    unittest.main()
