"""Private F00 composition and strict raw correctness gates."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT/'libraries/lzsa/src',ROOT/'libraries/zx0/src',ROOT/'libraries/tests',ROOT):
    sys.path.insert(0,str(path))

from emulator.cpu import execute_block,load_library
from next_f00_profiles import KINDS,EXPECTED_SERVICE,build
from next_f00_measure import PROTECTED,dirty,native_modes,alignment_screen
from next_e02_profiles import extra_word_cases
from lzsa import decompress


class F00Tests(unittest.TestCase):
    def test_actual_service_and_feature_union(self):
        for kind in KINDS:
            p=build(kind)
            self.assertEqual(p[2]['service_memory_bytes'],EXPECTED_SERVICE[kind])
            self.assertEqual(sum(len(blob) for _,blob in p[0])+6,EXPECTED_SERVICE[kind])
            self.assertEqual('E02CloneStart' in p[1],kind!='hot_pair')
            self.assertEqual('e03_hot_first' in p[1],kind!='hot_clone')
            self.assertEqual(p[2]['variant'],'next-f00-'+kind)

    def test_tiny_EOF_native_sixmode(self):
        library=load_library()
        for kind in KINDS:
            p,moved=build(kind),build(kind,core=0x9103)
            for payload,raw in [(bytes.fromhex('e7f0e8'),b''),(bytes.fromhex('ef41f0e8'),b'A')]:
                c=execute_block(p,payload,raw,library=library)
                modes=native_modes(p,moved,payload,raw,c['tstates'])
                self.assertEqual(len(modes),6)

    def test_legal_cloned_word_literals(self):
        for name,payload,raw,phase in extra_word_cases():
            self.assertEqual(decompress(payload,limit=len(raw)),raw)
            for kind in KINDS:
                self.assertTrue(PROTECTED(dirty(build(kind)),payload,raw)['exact'])

    def test_all_alignments_fit_cap_with_IRQ(self):
        for kind in KINDS:
            rows=alignment_screen(kind)
            self.assertEqual(len(rows),256)
            self.assertLessEqual(max(row['example_irq_inclusive_bytes'] for row in rows),10000)


if __name__=='__main__':unittest.main()
