"""Off-grid pitch recovery, odd harmonics, envelope and converter contracts."""
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import ay_fidelity as ay
from ay_square_fit import refine, square_templates
from build_long_video_trd import AyFrame


class SquareFitTests(unittest.TestCase):
    @staticmethod
    def signal(periods, levels, seconds=1):
        t = np.arange(round(seconds*22050))/22050
        # Independent time-domain square wave, including its full harmonic train.
        return sum(level*np.where(np.sin(2*np.pi*(ay.AY_CLOCK/(16*p))*t+.31)>0, 1., -1.)
                   for p, level in zip(periods, levels))

    def test_actual_square_spectrum_matches_odd_template(self):
        signal = self.signal([251], [.1])
        spectrum, _ = ay.spectra(signal, 22050, 50, 50)
        template = square_templates([251])[0]
        observed = spectrum[25]
        cosine = observed @ template/(np.linalg.norm(observed)*np.linalg.norm(template))
        self.assertGreater(cosine, .99)
        frequency = np.fft.rfftfreq(8192, 1/22050)
        fundamental = ay.AY_CLOCK/(16*251)
        peaks = [template[np.argmin(abs(frequency-fundamental*h))] for h in (1,2,3,5)]
        self.assertLess(peaks[1]/peaks[0], .001)
        self.assertAlmostEqual(peaks[2]/peaks[0], 1/3, delta=.02)
        self.assertAlmostEqual(peaks[3]/peaks[0], 1/5, delta=.02)

    def test_recovers_detuned_integer_periods_and_stable_pitch(self):
        for actual in (246, 258):
            spectrum, _ = ay.spectra(self.signal([actual], [.1]), 22050, 50, 50)
            old = np.tile([252, 800, 1300], (50, 1))
            volumes = np.tile([12, 0, 0], (50, 1))
            periods, fitted, stats = refine(spectrum, old, volumes, np.zeros(50, int))
            self.assertTrue(np.all(periods[8:-8, 0] == actual))
            np.testing.assert_array_equal(fitted, volumes)
            self.assertGreater(stats['fit_spectral_cosine_sum_after'], stats['fit_spectral_cosine_sum_before'])

    def test_joint_chord_does_not_reinterpret_partials_as_other_notes(self):
        actual, seeds = [494, 310, 246], [504, 318, 252]
        spectrum, _ = ay.spectra(self.signal(actual, [.15, .08, .06]), 22050, 50, 50)
        old = np.tile(seeds, (50, 1))
        volumes = np.tile([13, 11, 10], (50, 1))
        periods, fitted, _ = refine(spectrum, old, volumes, np.zeros(50, int))
        np.testing.assert_allclose(np.median(periods[10:-10], axis=0), actual, atol=1)
        power = np.sum(ay.LEVELS[fitted]**2, axis=1)/np.sum(ay.LEVELS[volumes]**2, axis=1)
        self.assertTrue(np.all(np.abs(10*np.log10(power)) <= .25+1e-12))

    def test_silence_noise_and_inputs_are_preserved(self):
        magnitude = np.zeros((4, 4097))
        periods = np.tile([1, 4095, 252], (4, 1))
        volumes = np.array([[0,0,0], [0,15,0], [0,1,0], [0,0,0]])
        noise = np.array([0,31,1,0])
        before = [x.copy() for x in (magnitude, periods, volumes, noise)]
        p, v, _ = refine(magnitude, periods, volumes, noise)
        np.testing.assert_array_equal(v[:,1], [0,14,0,0])
        np.testing.assert_array_equal(p, periods)
        for actual, expected in zip((magnitude, periods, volumes, noise), before):
            np.testing.assert_array_equal(actual, expected)
        _, unattenuated, _ = refine(magnitude, periods, volumes, noise, noise_steps=0)
        np.testing.assert_array_equal(unattenuated, volumes)
        for pp, vv, nn in zip(p, v, noise):
            frame = AyFrame(tuple(map(int, pp)), tuple(map(int, vv)), int(nn))
            self.assertEqual(frame, AyFrame.deserialize(frame.serialize()))

    def test_disabled_tuning_and_range_validation(self):
        spectrum, _ = ay.spectra(self.signal([246], [.1]), 22050, 50, 50)
        periods = np.tile([252, 100, 1], (50,1))
        volumes = np.tile([12,0,0], (50,1))
        fitted, _, _ = refine(spectrum, periods, volumes, np.zeros(50, int), tuning_cents=0)
        np.testing.assert_array_equal(fitted, periods)
        for kw in (dict(noise_steps=2), dict(tuning_cents=-1), dict(tuning_cents=101)):
            with self.assertRaises(ValueError):
                refine(spectrum, periods, volumes, np.zeros(50, int), **kw)

    def test_full_analysis_recovers_off_grid_pure_tone_without_false_noise(self):
        t = np.arange(22050)/22050
        samples = .12*np.sin(2*np.pi*(ay.AY_CLOCK/(16*246))*t)
        spectrum, rms = ay.spectra(samples, 22050, 50, 50)
        p, v, _, noise, _, fit = ay.arrange_for_chip(spectrum, rms)
        self.assertGreater(fit['recovered_isolated_tone_ticks'], 0)
        self.assertTrue(np.all(p[10:-10, 2] == 246))
        self.assertTrue(np.all(v[10:-10, 2] > 0))
        self.assertFalse(np.any(v[10:-10, :2]) or np.any(noise[10:-10]))
        from ay_square_fit import recover_isolated_tones
        for samples in (np.zeros(22050), np.random.default_rng(331).normal(0, .1, 22050)):
            m, rms = ay.spectra(samples, 22050, 50, 50)
            self.assertEqual(recover_isolated_tones(m, rms, np.ones((50,3), int),
                np.zeros((50,3), int), np.full((50,3), -1, int)), 0)

    def test_generic_audio_uses_new_fit_and_keeps_50_hz_and_tail(self):
        from convert_video import convert_audio
        pcm = self.signal([246], [.1], seconds=.2).astype('<f4').tobytes()
        with tempfile.TemporaryDirectory() as folder, patch('convert_video.run', return_value=pcm):
            directory = Path(folder)
            frames, report = convert_audio(Path('fixture.mov'), 'ffmpeg', directory,
                dict(start_time='0'), dict(index=1), 5, Fraction(10), noise_steps=0)
            self.assertEqual(len(frames), 25)
            self.assertEqual(len((directory/'ay.bin').read_bytes()), 25*9)
            self.assertEqual(report['chip_fit']['model'], 'ay_square_register_fit_v2')
            self.assertEqual(report['chip_fit']['noise_attenuation_register_steps'], 0)
            self.assertTrue(any(p == 246 and v > 0 for f in frames for p, v in zip(f.periods, f.volumes)))
            self.assertTrue(all(f.volumes == (0,0,0) for f in frames[-5:]))
            silent, quiet = convert_audio(Path('silent.mov'), 'ffmpeg', directory, {}, None, 5, Fraction(10))
            self.assertEqual(len(silent), 25)
            self.assertTrue(quiet['silence'])


if __name__ == '__main__':
    unittest.main()
