"""Check the speech candidate's pitch, register and consonant contracts."""
import unittest
import numpy as np
from pitch_aware_ay import encode,fit_weights,square_power,CLOCK
from probe_lpc2 import ay_interrupt
from verify_preview import expected_registers

LEVELS=np.r_[0.,2.**((np.arange(1,16)-15)/2)]


class SpeechTests(unittest.TestCase):
    def test_nonnote_pitch_is_preserved_and_register_packing_is_exact(self):
        pitch=137.3; t=np.arange(160*8)/8000
        signal=.1*np.sin(2*np.pi*pitch*t)+.07*np.sin(2*np.pi*7*pitch*t)
        records=[dict(mode=1,energy=20,pitch_hz=pitch)]*8
        frames,details=encode(records,signal,LEVELS)
        for f,d in zip(frames,details):
            self.assertLess(abs(CLOCK/(16*f.periods[0])/pitch-1),.001)
            self.assertGreater(f.volumes[0],0)
            self.assertEqual(d['harmonic_indices'][0],1)
        packed=b''.join(f.serialize() for f in frames)
        self.assertEqual(expected_registers(packed),b''.join(ay_interrupt.registers(f) for f in frames))

    def test_silence_and_unvoiced_frames_do_not_gain_false_pitch(self):
        records=[dict(mode=m,energy=e,pitch_hz=0) for m,e in ((0,0),(0,20),(3,20))]
        frames,details=encode(records,np.random.default_rng(4).normal(0,.1,480),LEVELS)
        self.assertEqual(frames[0].volumes,(0,0,0))
        for f in frames[1:]:
            self.assertEqual((f.volumes[0],f.volumes[2]),(0,0))
            self.assertTrue(1<=f.noise_period<=31)
        self.assertEqual([d['kind'] for d in details],['silence','noise','noise'])

    def test_fit_recovers_known_square_components(self):
        frequency=np.fft.rfftfreq(512,1/8000)[5:250]
        basis=square_power([800,267,160],frequency)
        weights=np.array([.15,.6,.25])
        fitted,error=fit_weights(basis,weights@basis)
        np.testing.assert_allclose(fitted,weights,atol=1e-8)
        self.assertLess(error,1e-15)


if __name__=='__main__': unittest.main()
