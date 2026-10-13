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

    def test_transition_removes_control_jump_without_adding_oscillator_phases(self):
        data=controls(20);data['volumes'][:,0]=15;data['shapes'][:,0]=1
        data['volumes'][1::2,0]=11;data['shapes'][1::2,0]=2
        step=model.synthesize_raw(data,aligned_triangle=True)
        smooth=model.synthesize_raw(data,transition_ms=4,aligned_triangle=True)
        edges=np.arange(1,20)*3528
        before=np.diff(step)[edges-1];after=np.diff(smooth)[edges-1]
        self.assertLess(np.sqrt(np.mean(after**2)),np.sqrt(np.mean(before**2))*.05)
        # After settling, no frequency glide or second oscillator can change
        # the target waveform: it agrees with the original running phase.
        offset=np.arange(800,3528)
        for tick in range(20):
            np.testing.assert_allclose(smooth[tick*3528+offset],step[tick*3528+offset],atol=1e-12)

    def test_output_filter_rejects_unscored_square_harmonics(self):
        data=controls(100);data['volumes'][:,0]=15;data['periods'][:,0]=63
        frequency=model.CLOCK/(16*63)
        old=model.render(data)[8820:]
        filtered=model.render(data,output_bandwidth_hz=8000)[8820:]
        t=np.arange(len(old))/44100
        def projection(audio,harmonic):
            return abs(np.sum(audio*np.exp(-2j*np.pi*harmonic*frequency*t)))
        self.assertGreater(projection(old,7)/projection(old,1),.12)
        self.assertLess(projection(filtered,7)/projection(filtered,1),.001)
        self.assertAlmostEqual(projection(filtered,1)/projection(old,1),1.,delta=.003)

    def test_aligned_triangle_and_sine_have_same_fundamental_phase(self):
        data=controls(50);data['volumes'][:,0]=15
        frequency=model.CLOCK/(16*251)
        coefficients=[]
        for shape in (1,2):
            data['shapes'][:,0]=shape
            raw=model.synthesize_raw(data,aligned_triangle=True)
            t=np.arange(len(raw))/176400
            coefficients.append(np.sum((raw-.5)*np.exp(-2j*np.pi*frequency*t)))
        self.assertLess(abs(np.angle(coefficients[0]/coefficients[1])),.01)

    def test_invalid_transition_or_cutoff_fails(self):
        data=controls(2)
        for duration in (-1,21,float('nan')):
            with self.assertRaises(ValueError):model.render(data,transition_ms=duration)
        for cutoff in (0,22050,float('inf')):
            with self.assertRaises(ValueError):model.render(data,output_bandwidth_hz=cutoff)

    def test_balanced_fit_retains_quiet_independent_upper_partial(self):
        t=np.arange(441*40)/22050
        low=model.CLOCK/(16*211);high=model.CLOCK/(16*37)
        source=.25*np.sin(2*np.pi*low*t)+.004*np.sin(2*np.pi*high*t)
        for size in (512,2048):
            fitted,gain=model.fit(source,model.dictionary(size),spectral_weight_exponent=1.,band_peak_count=4)
            middle=fitted['periods'][10:30].astype(int)
            active=fitted['volumes'][10:30]>0
            self.assertGreater(np.mean(np.any((abs(middle-37)<=1)&active,axis=1)),.8)
            self.assertGreater(np.mean(np.any((abs(middle-211)<=1)&active,axis=1)),.8)
            self.assertGreater(gain,0)

    def test_invalid_spectral_fit_settings_fail_before_analysis(self):
        for exponent in (-1,2.1,float('nan')):
            with self.assertRaises(ValueError):model.fit(np.zeros(441),None,spectral_weight_exponent=exponent)
        for count in (-1,9,1.5):
            with self.assertRaises(ValueError):model.fit(np.zeros(441),None,band_peak_count=count)

    def test_dc_compensation_removes_subsonic_control_energy_and_keeps_tone(self):
        data=controls(100);data['shapes'][:,0]=2;data['volumes'][:,0]=15
        data['volumes'][1::2,0]=5
        options=dict(transition_ms=4,output_bandwidth_hz=8000,aligned_triangle=True)
        ordinary=model.render(data,**options)
        balanced=model.render(data,compensate_dc=True,**options)
        hz=np.fft.rfftfreq(len(ordinary),1/44100)
        before=abs(np.fft.rfft(ordinary))**2;after=abs(np.fft.rfft(balanced))**2
        self.assertLess(after[hz<50].sum(),before[hz<50].sum()*.01)
        self.assertAlmostEqual(after[hz>150].sum()/before[hz>150].sum(),1.,delta=.03)

    def test_short_and_long_dictionary_scales_match_direct_windowed_tone(self):
        frequency=model.CLOCK/(16*133)
        for size in (512,1024,1536,2048):
            periods,basis,_,hz,useful=model.dictionary(size)
            t=(np.arange(size)-size//2)/22050
            window=np.hanning(size)
            measured=abs(np.fft.rfft(.5*np.sin(2*np.pi*frequency*t)*window,n=2*size))/(window.sum()/2)
            prediction=basis[2,np.flatnonzero(periods==133)[0]]
            self.assertLess(abs(prediction-measured[useful]).max()/measured.max(),.008)


if __name__=='__main__':unittest.main()
