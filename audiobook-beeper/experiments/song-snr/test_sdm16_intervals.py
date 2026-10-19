"""Complete-domain and binary-layout checks for compact full-input tables."""
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

import numpy as np

from sdm16_intervals import DEFAULT_TABLE, HERE, q_parameters, run
from sdm16_precision import python_packet


class Sdm16Intervals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(dir=HERE.parents[2]/'.tmp',prefix='sdm16-interval-test-')
        cls.output=Path(cls.temporary.name)/'evidence'
        cls.report=run(DEFAULT_TABLE,cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_every_reachable_input_word_and_nextstate_verified(self):
        self.assertEqual(self.report['reachable_cells'],1179648)
        self.assertEqual(len(self.report['reachable_states']),18)
        self.assertTrue(self.report['blocks']['all_reachable_cells_verified'])
        self.assertTrue(self.report['hybrid']['all_reachable_cells_words_and_next_states_exact'])
        self.assertTrue(self.report['hybrid']['compact_q_raw_exact_without_clipping'])

    def test_one_low_bit_preserves_independent_eight_packet_trajectory(self):
        witnesses=self.report['hybrid']['lower_one_bit_trajectory']
        for row in witnesses:
            state=16;expected=[]
            for _ in range(8):
                word,state=python_packet(row['pcm16'],state,True);expected.append([word,state])
            self.assertEqual(row['trajectory'],expected)
        self.assertEqual(witnesses[0]['trajectory'][0][0],witnesses[1]['trajectory'][0][0])
        self.assertNotEqual(witnesses[0]['trajectory'][2][0],witnesses[1]['trajectory'][2][0])

    def test_exact_floor_parameters_preserve_q_without_source_fit(self):
        parameters=q_parameters()
        for a,(m,threshold) in enumerate(parameters):
            for u in (0,1,255,256,511,512,32767,32768,65535):
                direct=(Fraction(u,512)+Fraction(1,2)-Fraction(128*a,449)+Fraction(1,10**12)).__floor__()
                compact=(u>>9)-int(m)-int((u&511)<threshold)
                self.assertEqual(direct,compact)

    def test_reported_binary_memory_dimensions_are_exact(self):
        h=self.report['hybrid']
        self.assertEqual(h['word_intervals'],2558)
        self.assertEqual(h['recent_sign_cuts'],555)
        self.assertEqual(h['qcode_cuts'],2270)
        self.assertEqual(h['interval_body_bytes'],(self.output/'hybrid-intervals.bin').stat().st_size)
        self.assertEqual(h['compactC']['q_parameter_bytes'],744)
        self.assertEqual(h['inlineC']['word_dictionary_bytes'],4496)
        root5=next(row for row in h['root_formats'] if row['high_bits']==5)
        self.assertEqual(root5['compactC_total_bytes'],16642)
        self.assertEqual(root5['inlineC_total_bytes'],17022)
        self.assertFalse(h['selector_timing_verified'])
        self.assertFalse(h['banked_player_ram_fit_verified'])


if __name__=='__main__':
    unittest.main()
