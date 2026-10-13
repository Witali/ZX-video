"""Independent harmonic/phase checks for the hypothetical six-voice renderer."""
import unittest
import numpy as np
import experimental_six_voice as model


def controls(ticks):
    return dict(periods=np.full((ticks,6),251,np.uint16),volumes=np.zeros((ticks,6),np.uint8),
        shapes=np.zeros((ticks,6),np.uint8),modes=np.zeros((ticks,6),np.uint8),noise_periods=np.full(ticks,16,np.uint8))


class SixVoiceTests(unittest.TestCase):
    def test_rendered_harmonics_agree_with_independent_fourier_ratios(self):
        data=controls(100);data['volumes'][:,0]=15
        frequency=model.CLOCK/(16*251)
        for shape,ratio in ((0,1/3),(1,1/9),(2,0)):
            data['shapes'][:,0]=shape
            audio=model.render(data)[44100//5:]
            t=np.arange(len(audio))/44100
            # A direct Fourier projection, independent of the template builder.
            fundamental=abs(np.sum(audio*np.exp(-2j*np.pi*frequency*t)))
            third=abs(np.sum(audio*np.exp(-6j*np.pi*frequency*t)))
            self.assertAlmostEqual(third/fundamental,ratio,delta=.012)

    def test_phase_does_not_restart_at_twenty_ms_or_when_muted(self):
        data=controls(20);data['volumes'][:,0]=15;data['shapes'][:,0]=2
        audio=model.render(data,oversample=4)
        # Direct constant-frequency source plus independently implemented AC
        # coupling and the same documented output filter, without field loops.
        rate=176400;n=20*3528;t=np.arange(n)/rate
        raw=.5+.5*np.sin(2*np.pi*model.CLOCK/(16*251)*t)
        dc=np.convolve(raw,np.ones(4096)/4096,'full')[:n]
        offset=np.arange(-252,253);kernel=.225*np.sinc(.225*offset)*np.hanning(505);kernel/=kernel.sum()
        expected=np.convolve(np.pad(raw-dc,(252,252)),kernel,'valid')[::4]
        np.testing.assert_allclose(audio,expected,atol=2e-12)

    def test_shared_noise_is_one_generator_and_invalid_controls_rejected(self):
        one=controls(10);one['modes'][:]=1;one['volumes'][:,0]=10
        two={k:v.copy() for k,v in one.items()};two['volumes'][:,1]=10
        np.testing.assert_allclose(model.render(two),2*model.render(one),atol=1e-12)
        self.assertEqual(len(model.noise_cycle()),131071)
        one['volumes'][0,0]=16
        with self.assertRaises(ValueError):model.render(one)

    def test_sine_template_can_recover_an_off_note_frequency_and_silence(self):
        t=np.arange(441*20)/22050;frequency=model.CLOCK/(16*347)
        pcm=.2*np.sin(2*np.pi*frequency*t);pcm[-441*5:]=0
        state,gain=model.fit(pcm,model.dictionary())
        active=state['volumes'][:10]>0
        self.assertTrue(np.any((state['shapes'][:10]==2)&active))
        self.assertTrue(np.any((abs(state['periods'][:10].astype(int)-347)<=1)&active))
        self.assertFalse(state['volumes'][-5:].any())
        self.assertEqual(model.validate(state),20)
        self.assertGreater(gain,0)


if __name__=='__main__':unittest.main()
