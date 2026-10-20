"""S01 private Small layout, tag-boundary and exact-EOF checks."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT/'libraries/lzsa/src',ROOT/'libraries/zx0/src',ROOT/'libraries/tests',ROOT):
    sys.path.insert(0,str(path))

from next_s01_lzsa_profiles import KINDS,EXPECTED_CODE,EXPECTED_STACK,build
from next_s01_lzsa_measure import state_exhaustion,Observer,model,PROTECTED,dirty,extra_cases
from emulator.cpu import load_library,execute_block


class SmallTests(unittest.TestCase):
    def test_actual_storage(self):
        for kind in ('baseline',)+KINDS:
            p=build(kind)
            self.assertEqual(sum(len(b) for _,b in p[0]),EXPECTED_CODE[kind])
            self.assertEqual(p[2]['service_memory_bytes'],EXPECTED_CODE[kind]+EXPECTED_STACK[kind])
            self.assertEqual(len(p[2]['patched_addresses']),2)
            self.assertEqual(p[2]['per_block_setup_tstates'],24)
            self.assertEqual(p[2]['external_initialization_tstates'],0)

    def test_all_tags_and_flag_values(self):
        self.assertEqual(state_exhaustion()['token_phase_nibble_flag_states'],256*256*16)

    def test_native_tiny_eof_and_word_literals(self):
        library=load_library();baseline=build()
        cases=[('empty',bytes.fromhex('e7f0e8'),b''),('one',bytes.fromhex('ef41f0e8'),b'A')]
        cases += list(extra_cases())
        for name,payload,raw in cases:
            observer=Observer(baseline)
            old=PROTECTED(dirty(baseline),payload,raw,watch=observer.watch)
            counts=observer.finish()['counts']
            for kind in KINDS:
                p=build(kind);got=execute_block(p,payload,raw,library=library)
                self.assertEqual(got['tstates'],old['tstates']+model(kind,counts),(kind,name))
                self.assertLessEqual(got['stack_bytes'],EXPECTED_STACK[kind])


if __name__=='__main__':unittest.main()
