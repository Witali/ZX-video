"""Known pitches, rests, dynamics and the unchanged nine-byte AY contract."""
import unittest

import numpy as np

import ay_fidelity as ay
import build_long_video_trd as video


class AyFidelityTests(unittest.TestCase):
    def infer(self, samples, count):
        magnitude,rms=ay.spectra(samples,22050,25/3,count)
        amplitude,explained=ay.decompose(magnitude)
        return ay.arrange(amplitude,rms,explained)

    def harmonic(self, note, t, slope=1.0, phase=.31):
        frequency=440*2**((note-69)/12)
        return sum(np.sin(2*np.pi*frequency*h*t+phase*h)/h**slope for h in range(1,9))

    def test_single_instrument_does_not_spawn_octave_voices(self):
        t=np.arange(22050*3)/22050
        for note in (45,57,69,81):
            periods,volumes,notes=self.infer(.12*self.harmonic(note,t),25)
            for ns,vs in zip(notes[3:-3],volumes[3:-3]):
                self.assertEqual([n for n,v in zip(ns,vs) if v],[note])
            self.assertTrue(np.all((periods>=1)&(periods<=4095)))

    def test_three_instruments_keep_distinct_pitches(self):
        t=np.arange(22050*3)/22050
        expected=(55,62,71)
        signal=sum(.12/(i+1)*self.harmonic(n,t,1+i*.4,.31+i)
                   for i,n in enumerate(expected))
        _,volumes,notes=self.infer(signal,25)
        for ns,vs in zip(notes[3:-3],volumes[3:-3]):
            self.assertEqual(sorted(n for n,v in zip(ns,vs) if v),list(expected))

    def test_silence_and_broadband_noise_do_not_invent_notes(self):
        for samples in (np.zeros(44100),np.random.default_rng(19).normal(0,.03,44100)):
            _,volumes,_=self.infer(samples,16)
            self.assertFalse(np.any(volumes))

    def test_note_changes_and_rests_follow_supplied_evidence(self):
        amplitude=np.zeros((18,len(ay.NOTES)))
        amplitude[2:6,69-33]=.4;amplitude[6:10,72-33]=.4
        amplitude[12:16,74-33]=.4
        periods,volumes,notes=ay.arrange(amplitude,np.ones(18)*.1,np.ones(18))
        self.assertTrue(np.all(notes[2:6,2]==69))
        self.assertTrue(np.all(notes[6:10,2]==72))
        self.assertTrue(np.all(notes[12:16,2]==74))
        self.assertFalse(np.any(volumes[[0,1,10,11,16,17]]))
        self.assertEqual(periods[10,2],periods[9,2])

    def test_dynamics_and_register_ranges(self):
        amplitude=np.zeros((40,len(ay.NOTES)));amplitude[:,69-33]=1
        rms=np.geomspace(.005,.2,40)
        periods,volumes,_=ay.arrange(amplitude,rms,np.ones(40))
        self.assertTrue(np.all(np.diff(volumes[:,2])>=0))
        self.assertGreater(volumes[-1,2]-volumes[0,2],8)
        for p,v in zip(periods,volumes):
            frame=video.AyFrame(tuple(map(int,p)),tuple(map(int,v)))
            self.assertEqual(len(frame.serialize()),9)
            self.assertTrue(all(0<=x<=15 for x in frame.volumes))

    def test_preview_preserves_phase_and_logarithmic_levels(self):
        period=round(ay.AY_CLOCK/(16*440))
        frame=video.AyFrame((period,1,1),(15,0,0))
        quieter=video.AyFrame((period,1,1),(13,0,0))
        signal=ay.render([frame]*2,25/3)
        half=ay.render([quieter]*2,25/3)
        self.assertEqual(len(signal),10584)
        np.testing.assert_allclose(half,signal*.5,atol=1e-12)
        np.testing.assert_allclose(signal,ay.render([frame],25/6),atol=1e-11)
        self.assertLess(float(np.max(np.abs(signal))),1)

    def test_measured_boundaries_preserve_phase_and_actual_duration(self):
        frame=video.AyFrame((252,500,700),(12,10,8),19)
        expected=ay.render([frame]*3,50,22050)
        np.testing.assert_array_equal(expected,ay.render([frame]*3,50,22050,sample_boundaries=[0,441,882,1323]))
        stretched=ay.render([frame]*3,50,22050,sample_boundaries=[0,400,850,1400])
        np.testing.assert_allclose(stretched,ay.render([frame],22050/1400,22050),atol=1e-12)
        with self.assertRaises(ValueError):ay.render([frame]*2,50,sample_boundaries=[0,500,400])


if __name__=='__main__':unittest.main()
