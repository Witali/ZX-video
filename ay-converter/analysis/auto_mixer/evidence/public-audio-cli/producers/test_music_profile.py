"""Music-profile regressions: rests, repeat attacks, chip levels and polyphony."""
import unittest
import numpy as np
import ay_fidelity as ay
import ay_square_fit as fit
import music_profile as music
import spectrogram


class ProfileTests(unittest.TestCase):
    def test_calibration_is_local_and_cache_is_curve_specific(self):
        nominal = ay.LEVELS.copy()
        ym = music.chip_levels()
        self.assertEqual((len(ym), ym[0], ym[-1]), (16, 0, 1))
        old = fit.volume_candidates((10, 12, 14)).copy()
        fitted = fit.volume_candidates((10, 12, 14), tuple(ym))
        ratio = np.sum(ym[fitted]**2, axis=1)/np.sum(ym[[10,12,14]]**2)
        self.assertTrue(np.all(abs(10*np.log10(ratio)) <= .25000001))
        np.testing.assert_array_equal(old, fit.volume_candidates((10, 12, 14)))
        np.testing.assert_array_equal(nominal, ay.LEVELS)

    def test_note_lifetimes_and_repeated_attack(self):
        paths = np.tile([60, 64, 67], (8, 1))
        periods = np.tile([200, 170, 140], (8, 1))+np.arange(8)[:, None]
        volumes = np.full((8, 3), 10)
        volumes[3] = 7
        volumes[6] = 0
        onset = np.zeros(8, bool)
        onset[4] = True
        result, events = music.hold_note_pitch(periods, volumes, np.zeros(8, int), paths, onset)
        voice = [e for e in events if e['voice'] == 0]
        self.assertEqual([(e['start_tick'],e['end_tick']) for e in voice], [(0,4),(4,6),(7,8)])
        for e in events:
            self.assertTrue(np.all(result[e['start_tick']:e['end_tick'], e['voice']] == e['period']))

    def test_envelope_does_not_cross_rests_or_new_notes(self):
        paths = np.array([[69,69,69], [69,69,69], [-1,-1,-1], [72,72,72]])
        amplitude = np.ones((4, len(ay.NOTES)))
        amplitude[1:] *= .01
        value = music.envelopes(paths, amplitude, amplitude, np.zeros(4,bool), .5)
        np.testing.assert_array_equal(value[2], 0)
        np.testing.assert_allclose(value[3], .01)
        self.assertGreater(value[1, 0], .01)

    def test_joint_path_keeps_three_distinct_chord_notes(self):
        amplitude = np.zeros((10, len(ay.NOTES)))
        amplitude[:, np.array([48,64,76])-33] = [1,.7,.9]
        seed = np.tile([48,64,76], (10,1))
        result = music.joint_paths(amplitude, np.ones(10), np.ones(10), seed, np.zeros(10,bool))
        np.testing.assert_array_equal(result, seed)

    def test_silence_and_held_tone_end_to_end(self):
        for silent in (True, False):
            t = np.arange(22050)/22050
            samples = np.zeros(len(t)) if silent else .2*np.sin(2*np.pi*440*t)
            features = music.analyse(samples)
            p,v,paths,noise,_,meta = music.arrange(features)
            self.assertEqual(len(p), 50)
            self.assertEqual(meta['update_rate_hz'], 50)
            if silent:
                self.assertFalse(v.any())
                self.assertFalse(noise.any())
            else:
                active = v[10:40]>0
                frequencies = ay.AY_CLOCK/(16*p[10:40][active])
                self.assertGreater(len(frequencies), 20)
                self.assertTrue(np.all(abs(1200*np.log2(frequencies/440)) < 12))
                self.assertFalse(noise[10:40].any())

    def test_spectrogram_identity_gain_and_wrong_octave(self):
        t = np.arange(8820)/22050
        original = np.sin(2*np.pi*440*t)*.1
        reference = spectrogram.features(original)
        same = spectrogram.compare(reference, spectrogram.features(original*2))
        wrong = spectrogram.compare(reference, spectrogram.features(np.sin(2*np.pi*880*t)*.1))
        for size in same:
            self.assertAlmostEqual(same[size]['magnitude_cosine'], 1)
            self.assertLess(same[size]['log_magnitude_mae_db'], 1e-10)
            self.assertLess(wrong[size]['magnitude_cosine'], .2)


if __name__ == '__main__':
    unittest.main()
