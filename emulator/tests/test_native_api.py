"""Public Python entry points execute changed decoders and native Spectrum bus."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/'libraries/zx0/src'),str(ROOT/'libraries/lzsa/src')]
from emulator.cpu import CPU, Spectrum128, execute_block, load_library


class NativeAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = load_library()

    def test_both_codecs_guarded_and_single_tick_equivalence(self):
        from zx0.maximum import build as zx_build
        from zx0.tokens import Token, encode as zx_encode
        from lzsa.hybrid import build as lz_build
        from lzsa import encode as lz_encode
        raw = b'A'*4096
        for profile,payload in (
                (zx_build(prefix_cap=228,shared_prefixes=True),zx_encode(raw,[Token(0,1),Token(1,4095,1)])),
                (lz_build('fast'),lz_encode(raw,[(1,4095,1)]))):
            with self.subTest(codec=profile[2]['entry']):
                fast = execute_block(profile,payload,raw,library=self.lib)
                original = execute_block(profile,payload,raw,library=self.lib,fast=False)
                self.assertEqual(fast['tstates'],original['tstates'])
                self.assertEqual(fast['registers'],original['registers'])
                self.assertEqual(fast['ula_wait_tstates'],0)

    def test_live_guards_and_allocation_errors(self):
        profile = ([(0x8000,bytes.fromhex('3e 42 32 00 60 c9'))],{'start':0x8000},{'entry':'start'})
        with self.assertRaisesRegex(AssertionError,'native memory guard'):
            execute_block(profile,b'\0',b'',library=self.lib)
        with self.assertRaisesRegex(ValueError,'Overlapping allocations'):
            execute_block(profile,b'\0',b'A',source=0xc000,library=self.lib)

    def test_spectrum_mapping_program_uses_native_bus(self):
        # LD BC,7FFD; LD A,3; OUT(C),A; LD A,5A; LD(C000),A; RET.
        code = bytes.fromhex('01 fd 7f 3e 03 ed 79 3e 5a 32 00 c0 c9')
        with CPU(self.lib) as cpu,Spectrum128(library=self.lib) as spectrum:
            spectrum.attach(cpu)
            spectrum.load(0x8000,code)
            spectrum.load(0xbfee,b'\x00\x01')
            spectrum.load_rom(0,b'\0',offset=0x100)
            cpu.set_registers(pc=0x8000,sp=0xbfee)
            status = cpu.run()
            self.assertEqual(status['cpu_tstates'],59)
            self.assertEqual(spectrum.read(0xc000,1),b'Z')
            self.assertEqual(spectrum.state()['paged_bank'],3)
            self.assertEqual(spectrum.state()['cpu_tstates'],59)
            self.assertEqual(spectrum.state()['ula_wait_tstates'],0)
            spectrum.out(0x7ffd,0)
            self.assertEqual(spectrum.read(0xc000,1),b'\0')
            with self.assertRaisesRegex(RuntimeError,'banked memory'):
                _ = cpu.memory

    def test_unqualified_contention_and_bad_setup_rejected(self):
        with CPU(self.lib) as cpu,Spectrum128(library=self.lib,contention=True) as spectrum:
            with self.assertRaises(NotImplementedError):
                spectrum.attach(cpu)
            with self.assertRaises(ValueError):
                cpu.set_registers(halt=1)
            with self.assertRaises(ValueError):
                spectrum.load(0x2000,b'\0')
            with self.assertRaises(ValueError):
                spectrum.set_phase(70908)


if __name__ == '__main__':
    unittest.main()
