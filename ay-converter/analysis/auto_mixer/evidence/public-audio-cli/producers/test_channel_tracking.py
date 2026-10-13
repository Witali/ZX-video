"""Channel identity and actual AY mixer regressions, independent of the song."""
import unittest
import numpy as np
from ay_format import AyFrame,registers
from verify_preview import expected_registers
from verify_preview import extract_player,native_check
from music_player import build_disk
import channel_tracking as tracking
import music_profile as music
import ay_fidelity as ay


class TrackingTests(unittest.TestCase):
    def test_every_mixer_value_through_native_z80(self):
        frames = [AyFrame((251,731,1977),(8,11,14),1+i%31,i) for i in range(64)]
        raw = expected_registers(b''.join(frame.serialize() for frame in frames))
        disk,meta = build_disk(raw)
        result = native_check(extract_player(disk),meta,raw)
        self.assertTrue(result['registers_exact'])
        self.assertEqual(result['register_writes'],64*22)

    def test_mixer_extension_and_all_legacy_noise_periods(self):
        for n in range(32):
            legacy = AyFrame((1,2048,4095),(1,9,15),n)
            self.assertEqual(AyFrame.deserialize(legacy.serialize()),legacy)
            self.assertEqual(expected_registers(legacy.serialize()),registers(legacy))
            self.assertEqual(legacy.serialize()[5] & 128,0)
            for mixer in range(64):
                frame = AyFrame(legacy.periods,legacy.volumes,n,mixer)
                self.assertEqual(len(frame.serialize()),9)
                self.assertEqual(AyFrame.deserialize(frame.serialize()),frame)
                self.assertEqual(expected_registers(frame.serialize()),registers(frame))

    def test_amplitude_swaps_and_small_pitch_motion_never_move_channels(self):
        notes = np.array([[48.,64.,76.],[76.1,48.2,63.9],[64.2,75.9,48.1]])
        strengths = np.array([[.9,.6,.3],[.95,.2,.6],[.1,.8,.9]])
        out,values,ids = tracking.assign_channels(notes,strengths)
        np.testing.assert_allclose(out,[[48,64,76],[48.2,63.9,76.1],[48.1,64.2,75.9]])
        np.testing.assert_array_equal(ids,np.tile([1,2,3],(3,1)))
        np.testing.assert_allclose(values,[[.9,.6,.3],[.2,.6,.95],[.9,.1,.8]])

    def test_rest_releases_only_its_channel(self):
        notes = np.array([[48,64,76],[76,-1,48],[69,48,76]])
        out,_,ids = tracking.assign_channels(notes,np.ones((3,3)))
        np.testing.assert_array_equal(out,[[48,64,76],[48,-1,76],[48,69,76]])
        np.testing.assert_array_equal(ids,[[1,2,3],[1,0,3],[1,4,3]])

    def test_noise_mixes_without_disabling_or_moving_active_tones(self):
        volumes = np.array([[10,11,12],[12,10,9],[12,0,9],[9,10,11]])
        period = np.array([8,8,8,0])
        mixed,mixer,route = tracking.add_noise(volumes,period,np.full(4,.25),music.chip_levels())
        self.assertEqual(len(set(route[:3])),1)
        for tick in range(3):
            self.assertFalse(mixer[tick] & (1 << (route[tick]+3)))
            for voice in range(3):
                if volumes[tick,voice]:
                    self.assertFalse(mixer[tick] & (1 << voice))
        self.assertEqual(mixer[3],0x38)
        np.testing.assert_array_equal(mixed[3],volumes[3])

    def test_free_channel_noise_and_independent_noise_detection(self):
        mixed,mixer,route = tracking.add_noise(np.array([[10,0,12]]),np.array([4]),np.array([.2]),music.chip_levels())
        self.assertEqual(route[0],1)
        self.assertTrue(mixer[0] & 2)
        self.assertFalse(mixer[0] & 16)
        self.assertGreater(mixed[0,1],0)
        rng = np.random.default_rng(325)
        t = np.arange(22050)/22050
        for noisy in (False,True):
            source = .15*np.sin(2*np.pi*440*t)
            if noisy:
                source += .12*rng.standard_normal(len(t))
            mag,rms = ay.spectra(source,22050,50,50)
            period,level,share = tracking.noise_component(mag,rms,np.ones(50))
            if noisy:
                self.assertGreater(np.count_nonzero(period[5:-5]),35)
                self.assertGreater(np.median(share[5:-5]),.18)
            else:
                self.assertFalse(period[5:-5].any())


if __name__ == '__main__':
    unittest.main()
