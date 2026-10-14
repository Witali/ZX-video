"""Calibration of independently reported modulation, hum and clock metrics."""
import unittest
import json
import numpy as np

from artifact_diagnostics import (RATE,clock_diagnostics,cyclic_fit,error_spectrum,
                                  tone_diagnostics,waveform_diagnostics)


class ArtifactDiagnostics(unittest.TestCase):
    def setUp(self):
        self.t=np.arange(2*RATE)/RATE
        self.x=.4*np.sin(2*np.pi*317*self.t)+.2*np.sin(2*np.pi*937*self.t)

    def test_am_delay_and_hum_are_separated(self):
        d=np.gradient(self.x)*RATE
        y=1.2*(self.x+.02*self.x*np.cos(2*np.pi*50*self.t)+20e-6*d*np.sin(2*np.pi*50*self.t))
        y+=.003*np.cos(2*np.pi*50*self.t)+.002*np.sin(2*np.pi*100*self.t)
        row=cyclic_fit(self.x,y,50)
        self.assertTrue(row['small_signal_applicable'])
        self.assertAlmostEqual(row['am_peak_percent'],2,places=7)
        self.assertAlmostEqual(row['linearized_delay_peak_us'],20,places=7)
        self.assertAlmostEqual(row['linearized_speed_peak_percent'],.6283185307179586,places=7)
        self.assertAlmostEqual(row['fitted_hum_peak']['50'],.003,places=8)
        self.assertAlmostEqual(row['fitted_hum_peak']['100'],.002,places=8)

    def test_static_gain_delay_are_not_periodic_modulation(self):
        y=1.2*self.x+10e-6*np.gradient(self.x)*RATE
        row=cyclic_fit(self.x,y,50)
        self.assertLess(row['am_peak_percent'],1e-7)
        self.assertLess(row['linearized_delay_peak_us'],1e-7)
        result=waveform_diagnostics(self.x,y,frequencies=(50,))
        self.assertGreater(result['error_rms'],.01)
        self.assertLess(result['fixed_clock_snr_db'],20)

    def test_silence_has_absolute_noise_not_infinite_snr(self):
        noise=.003*np.cos(2*np.pi*50*self.t)
        result=waveform_diagnostics(np.zeros(len(noise)),noise)
        self.assertTrue(result['silence_reference'])
        self.assertIsNone(result['fixed_clock_snr_db'])
        self.assertAlmostEqual(result['error_rms'],.003/np.sqrt(2),places=8)
        self.assertAlmostEqual(result['coherent_unfitted_error_components'][0]['peak'],.003,places=8)
        self.assertFalse(result['modulation'][0]['available'])

    def test_drift_does_not_pass_small_signal_fit(self):
        y=.4*np.sin(2*np.pi*317*1.003*self.t)+.2*np.sin(2*np.pi*937*1.003*self.t)
        row=cyclic_fit(self.x,y,50)
        self.assertFalse(row['small_signal_applicable'])

    def test_clock_separates_mean_drift_and_periodic_disturbance(self):
        n=16000;cpu=3584000
        starts=np.arange(n)/8000
        dt=(1+.01+.002*np.cos(2*np.pi*50*starts))/8000
        sample=np.r_[0,np.cumsum(dt)]
        pulse=np.concatenate([np.linspace(sample[i],sample[i+1],17)[:-1] for i in range(n)]+[sample[-1:]])*cpu
        row=clock_diagnostics(pulse,cpu_hz=cpu)
        self.assertAlmostEqual(row['average_speed_deviation_percent'],(1/1.01-1)*100,places=8)
        self.assertAlmostEqual(row['accumulated_time_drift_ms'],20,places=7)
        uniform=clock_diagnostics(np.arange(n*16+1)*cpu/(8000*16),cpu_hz=cpu)
        self.assertLess(uniform['drift_removed_time_excursion_us'],1e-6)
        self.assertLess(max(r['peak_percent'] for r in uniform['periodic_interval_deviation']),1e-10)
        self.assertGreater(row['drift_removed_time_excursion_us'],10)

    def test_tone_phase_track_recovers_average_speed(self):
        carrier=997
        x=.2*np.sin(2*np.pi*carrier*self.t)
        y=.2*np.sin(2*np.pi*carrier*1.0002*self.t)
        row=tone_diagnostics(x,y,carrier,frequencies=(5,50))
        self.assertTrue(row['phase_tracking_reliable'])
        self.assertAlmostEqual(row['average_speed_shift_percent'],.02,places=5)

    def test_true_small_phase_modulation_is_detected(self):
        x=.3*np.sin(2*np.pi*997*self.t)
        y=.3*np.sin(2*np.pi*997*(self.t+10e-6*np.sin(2*np.pi*50*self.t)))
        row=cyclic_fit(x,y,50)
        self.assertTrue(row['small_signal_applicable'])
        self.assertAlmostEqual(row['linearized_delay_peak_us'],10,delta=.04)
        self.assertLess(row['am_peak_percent'],.01)

    def test_idle_whistle_is_visible_beyond_mains_hum(self):
        noise=.02*np.sin(2*np.pi*3991*self.t)
        result=error_spectrum(noise)
        peak=result['strongest_error_bins'][0]
        self.assertAlmostEqual(peak['hz'],3991,delta=result['bin_width_hz'])
        self.assertGreater(peak['three_bin_error_power_fraction'],.95)
        self.assertAlmostEqual(result['bands'][4]['rms'],.02/np.sqrt(2),places=6)

    def test_length_mismatch_is_not_silently_trimmed(self):
        with self.assertRaises(ValueError):waveform_diagnostics(self.x,self.x[:-1])
        with self.assertRaises(ValueError):clock_diagnostics([0,0,1],cpu_hz=3584000)

    def test_inserted_transport_pause_is_not_discarded(self):
        cpu=3584000;n=4096
        pulse=np.arange(n*16+1,dtype=float)*cpu/(8000*16)
        pulse[40001:]+=cpu*.005
        row=clock_diagnostics(pulse,cpu_hz=cpu)
        self.assertGreater(row['largest_actual_pulse_hold_us'],5000)
        self.assertGreater(row['accumulated_time_drift_ms'],4.99)

    def test_diagnostics_are_strict_json_and_short_period_is_inconclusive(self):
        row=waveform_diagnostics(self.x,self.x)
        self.assertFalse(row['modulation'][0].get('small_signal_applicable',False))
        json.dumps(row,allow_nan=False)
        x=.2*np.sin(2*np.pi*997*self.t)
        json.dumps(tone_diagnostics(x,x,997),allow_nan=False)
        edges=np.arange(4096*16+1)*3584000/(8000*16)
        json.dumps(clock_diagnostics(edges,cpu_hz=3584000),allow_nan=False)


if __name__=='__main__':unittest.main()
