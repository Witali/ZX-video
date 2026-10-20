"""Geometry and format gates for the three rejected E02 constructions."""
import unittest

from next_e02_profiles import KINDS,build,extra_word_cases,ROOT
from lzsa.hybrid import build as public
from lzsa import decompress
from profile_branch_mix import instructions


class ContinuationTests(unittest.TestCase):
    def test_emitted_service_delta_and_stack_contract(self):
        baseline=public('fast',cold_match_extension=True)
        for name,delta in (('direct-hl',79),('hot-clone',30),('shared-tail',-2)):
            profile=build(name)
            self.assertEqual(profile[2]['service_memory_bytes']-baseline[2]['service_memory_bytes'],delta)
            self.assertEqual(profile[2]['caller_stack_bytes'],6)
            self.assertEqual(profile[2]['service_memory']['external_state_bytes'],0)
            self.assertEqual(profile[2]['nominal_aligned_service_bytes'],profile[2]['service_memory_bytes'])
            self.assertTrue(profile[2]['variant'].startswith('next-e02-'))
        self.assertEqual(set(KINDS),{'direct-hl','hot-clone','shared-tail'})

    def test_three_exit_and_continuation_geometries(self):
        for kind,returns in (('direct-hl',0),('hot-clone',3),('shared-tail',1)):
            profile=build(kind);origin,blob=profile[0][0];labels=profile[1]
            first=min(value for key,value in labels.items() if key.startswith('token_') and key[6:].isdigit())
            code=dict(instructions(blob[labels['LongLiterals']-origin:first-origin],labels['LongLiterals']))
            self.assertEqual(sum(op==b'\xc9' for op in code.values()),returns)
            if kind=='direct-hl':
                self.assertEqual(sum(op==b'\xe9' for op in code.values()),3)
                for token in range(256):
                    if (token>>3)&3==3:self.assertEqual(blob[labels['token_'+str(token)]+4-origin],0xd9)
            if kind=='shared-tail':
                self.assertEqual(blob[labels['long8_complete']-origin:labels['long8_complete']-origin+2],b'\x18\xf4')
                self.assertEqual(blob[labels['long16_complete']-origin:labels['long16_complete']-origin+2],b'\x18\xee')

    def test_supplemental_word_literals_are_valid(self):
        rows=list(extra_word_cases());self.assertEqual(len(rows),4)
        for case,payload,raw,phase in rows:
            self.assertEqual(decompress(payload,limit=len(raw)),raw,case)


if __name__=='__main__':unittest.main()
