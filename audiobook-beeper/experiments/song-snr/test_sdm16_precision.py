"""Exact causal checks for the standalone precision counterfactual program."""
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

import numpy as np

from sdm16_precision import (AUDIO, HOLDS, build_executable, c_cells, execute,
                             original_stream, python_packet, table_parity)


class Sdm16Precision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = build_executable()

    def stream(self, values, mode):
        with tempfile.TemporaryDirectory(dir=AUDIO.parent/'.tmp', prefix='sdm-test-') as directory:
            directory = Path(directory)
            np.asarray(values, dtype='<i2').tofile(directory/'pcm.bin')
            return execute(self.binary, 'stream', mode, directory/'pcm.bin',
                           directory/'words.bin', directory/'states.bin')

    def test_all2048_anchor_words_and_successors_match_original_and_fraction(self):
        self.assertTrue(table_parity(self.binary)['complete'])

    def test_full16bit_cells_match_independent_fraction_reference(self):
        rng = np.random.default_rng(20261019)
        cells = [(int(p),int(s)) for p,s in zip(rng.integers(-32768,32768,160), rng.integers(0,32,160))]
        cells += [(p,s) for p in (-32768,-1,0,1,32767) for s in (0,16,31)]
        words, states = c_cells(cells, 'b', self.binary)
        expected = [python_packet(p,s,True) for p,s in cells]
        np.testing.assert_array_equal(words, [row[0] for row in expected])
        np.testing.assert_array_equal(states, [row[1] for row in expected])

    def test_whole_a_stream_and_own_b_state_carry(self):
        pcm = np.random.default_rng(1616).integers(-30000,30000,96).astype('<i2')
        old_words, old_states = original_stream(pcm)
        words, states, _ = self.stream(pcm, 'a')
        np.testing.assert_array_equal(words,old_words)
        np.testing.assert_array_equal(states,old_states)
        words, states, _ = self.stream(pcm, 'b')
        expected, successor = [], 16
        for p in pcm:
            word, successor = python_packet(int(p), successor, True)
            expected.append((word,successor))
        np.testing.assert_array_equal(words,[row[0] for row in expected])
        np.testing.assert_array_equal(states,[row[1] for row in expected])

    def test_single_low_bit_changes_b_trajectory_while_a_is_unchanged(self):
        a37, _, _ = self.stream([37]*8, 'a')
        a38, _, _ = self.stream([38]*8, 'a')
        b37, s37, _ = self.stream([37]*8, 'b')
        b38, s38, _ = self.stream([38]*8, 'b')
        np.testing.assert_array_equal(a37,a38)
        self.assertEqual(int(b37[0]),int(b38[0]))
        self.assertNotEqual(int(s37[0]),int(s38[0]))
        self.assertNotEqual(int(b37[2]),int(b38[2]))

    def test_continuous_state_uses_same_initial_coordinates_and_order(self):
        pcm = [0,37,38,-128,600,8191,-16384,32767,-32768,1]
        words, states, result = self.stream(pcm,'c')
        q, recent = Fraction(0), Fraction(-1,4)
        expected = []
        for p in pcm:
            x, word = Fraction(p+32768,65536), 0
            for hold in HOLDS:
                weight = Fraction(16*hold,449)
                u = x+q/weight+recent/2
                bit = int(u>=Fraction(1,2)-Fraction(1,10**12))
                q += weight*(x-bit); recent=u-bit
                word=word*2+bit
            expected.append(word)
        np.testing.assert_array_equal(words,expected)
        np.testing.assert_array_equal(states,255)
        self.assertEqual(result['q_clip_events'],0)
        self.assertEqual(result['recent_clip_events'],0)
        self.assertEqual(int(words[0]),python_packet(0,16,True)[0])

    def test_invalid_unsigned_or_state_input_is_rejected(self):
        for cell in ((32768,16),(-32769,16),(0,32),(0,-1)):
            with self.assertRaises(ValueError):
                c_cells([cell],'b',self.binary)


if __name__ == '__main__':
    unittest.main()
