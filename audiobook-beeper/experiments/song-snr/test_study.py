"""Independently validate bounded rendering against the existing full renderer."""
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np

from convert_mulaw_audio import filter_signal
from study import filtered,metrics
from general import catalogue,models,timeline


class WholeSongStudy(unittest.TestCase):
    def test_chunked_render_preserves_every_bin_and_filter_state(self):
        ffmpeg=shutil.which('ffmpeg');self.assertIsNotNone(ffmpeg)
        rng=np.random.default_rng(1410);values=rng.integers(0,2,8192).astype(float)
        times=np.r_[0,np.cumsum(rng.integers(18,58,len(values)))]
        # This deliberately crosses many chunk boundaries and exercises
        # irregular edges; the reference is the pre-existing whole renderer.
        expected=filter_signal(values,times,ffmpeg,768000)
        root=Path(__file__).resolve().parents[3]/'.tmp';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root,prefix='study-test-') as scratch:
            actual=filtered(values,times,ffmpeg,scratch,chunk=127)
        self.assertEqual(len(actual),len(expected))
        np.testing.assert_allclose(actual,expected,atol=1e-13,rtol=0)

    def test_metrics_use_total_error_without_fitted_gain(self):
        times=np.arange(44100)/44100
        source=np.sin(2*np.pi*440*times)
        row=metrics(source,source*.9)
        self.assertAlmostEqual(row['snr_db'],20.,places=10)
        self.assertGreater(row['error_power'],0)

    def test_source_independent_pentagon_clock_matches_complete_fuse_control(self):
        import gzip
        root=Path(__file__).parent/'evidence/study/inputs/song'
        actual=np.frombuffer(gzip.decompress((root/'verification/pentagon512/times.u32.gz').read_bytes()),'<u4')
        expected=timeline(720384,'pentagon')[:len(actual)]
        from build_pdm import CPU_CLOCK
        np.testing.assert_array_equal(expected,actual.astype(float)*CPU_CLOCK/3584000)

    def test_universal_catalogue_cannot_hide_unseen_states_or_patterns(self):
        presets=dict(models());base=catalogue(presets['legacy'])
        self.assertEqual((base['reachable_feedback_states'],base['first_patterns'],base['second_patterns']),(18,128,86))
        self.assertTrue(base['current_layout_fits'])
        self.assertEqual(sum(presets['duration_midpoint']['holds']),449)
        self.assertEqual(presets['duration_midpoint']['holds'][7],46)
        self.assertFalse(catalogue(presets['duration_zero_half_recent'])['current_layout_fits'])

    def test_silence_reports_absolute_noise_without_undefined_snr(self):
        row=metrics(np.zeros(44100),np.full(44100,.01))
        self.assertIsNone(row['snr_db']);self.assertAlmostEqual(row['error_rms'],.01)


if __name__=='__main__':unittest.main()
