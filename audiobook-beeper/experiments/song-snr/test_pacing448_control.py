"""Independent scope and timing checks for the frozen 448-T host control."""
import unittest
from pathlib import Path

import numpy as np

from build_pdm import CPU_CLOCK
from general import timeline
from pacing448_control import (FREQUENCIES, generated_source, instruction_timeline,
                               model_for, verify_archived_score)
from probe_reconstruction_error import wav8


class Pacing448Control(unittest.TestCase):
    def test_449_matches_independent_historical_schedule(self):
        np.testing.assert_array_equal(instruction_timeline(131584, 449),
                                      timeline(131584, 'pentagon'))

    def test_448_changes_only_slot_seven_by_one_tstate(self):
        before = instruction_timeline(131584, 449) * 3584000 / CPU_CLOCK
        after = instruction_timeline(131584, 448) * 3584000 / CPU_CLOCK
        # Renderer units are fractional reference T states. Recover their
        # independently integral native ticks before subtracting two intervals;
        # cancellation of four large f64 timestamps otherwise costs two ulps.
        np.testing.assert_allclose(before, np.rint(before), rtol=0, atol=1e-7)
        np.testing.assert_allclose(after, np.rint(after), rtol=0, atol=1e-7)
        delta = np.diff(np.rint(before).astype('i8')) - np.diff(np.rint(after).astype('i8'))
        np.testing.assert_array_equal(delta[7::16], 1)
        delta[7::16] = 0
        np.testing.assert_array_equal(delta, 0)
        self.assertAlmostEqual(before[-1]-after[-1], 131584, places=7)

    def test_table_weights_remain449_for_timing_only_candidate(self):
        before, after = model_for(449), model_for(448)
        self.assertEqual(before['holds'], after['holds'])
        self.assertEqual(sum(after['holds']), 449)
        self.assertTrue(after['audio_progress_ui'])
        self.assertEqual(after.pop('pentagon_ordinary_tstates'), 448)
        self.assertEqual(before, after)

    def test_long_sources_retain_original_waveform_prefix_and_guard(self):
        for name in ('silence','quiet440','loud3000','steps','quiet997','multitone'):
            short = generated_source(name, 16384)
            long = generated_source(name)
            self.assertEqual(len(long), 131584)
            np.testing.assert_array_equal(long[:16384], short[:16384])
            self.assertTrue(np.all(long[-512:] == 128))
        self.assertGreater((len(long)/8000-.2)*FREQUENCIES[0], 3)

    def test_long_waveform_prefix_matches_authenticated_existing_inputs(self):
        root = Path(__file__).parent / 'evidence' / 'general' / 'inputs'
        for name in ('silence','quiet440','loud3000','steps','quiet997','multitone'):
            original = wav8(root / (name + '.wav'))
            self.assertEqual(len(original), 16896)
            np.testing.assert_array_equal(generated_source(name)[:16384], original[:16384])

    def test_archived_score_guard_rejects_gain_or_clock_reclassification(self):
        score = dict(snr_db=20.25031588676249, error_rms=.0331307606696652)
        self.assertTrue(verify_archived_score(score, score)['passed'])
        with self.assertRaises(ValueError):
            verify_archived_score(dict(score, snr_db=20.3), score)
        with self.assertRaises(ValueError):
            verify_archived_score(dict(score, error_rms=.033), score)
        with self.assertRaises(ValueError):
            verify_archived_score(dict(score, snr_db=None), score)

    def test_invalid_timelines_rejected_before_encoding(self):
        for samples, pace in ((513,448),(512,447),(512,448.),(512,True)):
            with self.assertRaises(ValueError):
                instruction_timeline(samples, pace)


if __name__ == '__main__':
    unittest.main()
