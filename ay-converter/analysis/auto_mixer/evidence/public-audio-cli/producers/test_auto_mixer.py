"""Actual mode selection, phase-aware final evaluation and cache identity."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import ay_fidelity as ay
import mixer_fit as mix
import noise_colour
import spectral_patterns as patterns

NODE = r'C:\Program Files\nodejs\node.exe'


class AutomaticMixerTests(unittest.TestCase):
    def test_spectral_reuse_scales_intensity_and_matches_uncached_fit(self):
        patterns.reset()
        t = np.arange(22050)/22050
        shape = ay.spectra(.1*np.sin(2*np.pi*440*t),22050,50,50)[0][25]
        data = np.array([shape,shape*.25,shape*2,shape,shape*.5])
        expected = ay.decompose(data)
        actual = ay.decompose(data,pattern_cache=True)
        np.testing.assert_allclose(actual[0],expected[0],rtol=1e-5,atol=1e-9)
        np.testing.assert_allclose(actual[1],expected[1],rtol=1e-8,atol=1e-10)
        self.assertEqual(patterns.stats()['reused'],4)
        different = data.copy(); different[0,100] += .01
        ay.decompose(different,pattern_cache=True)
        self.assertGreater(patterns.stats()['entries'],1)

    def test_exact_cache_checks_context_and_saves_registers(self):
        raw = bytes([251,0,1,0,1,0,0,0x38,11,0,0])*4
        samples = np.zeros(4*441)
        kwargs = dict(tone_volumes=[[11,0,0]]*4,noise_shares=[.2]*4,carriers=[0]*4)
        with tempfile.TemporaryDirectory() as folder, patch('mixer_fit._optimize',return_value=(raw,{'model':'fixture'})) as fit:
            a, info = mix.optimize(samples,raw,NODE,cache_dir=folder,**kwargs)
            b, reused = mix.optimize(samples,raw,NODE,cache_dir=folder,**kwargs)
            self.assertEqual(a,b)
            self.assertFalse(info['cache_hit']); self.assertTrue(reused['cache_hit'])
            self.assertEqual(fit.call_count,1)
            samples[0] = .001
            mix.optimize(samples,raw,NODE,cache_dir=folder,**kwargs)
            self.assertEqual(fit.call_count,2)

    def test_three_modes_from_an_unseen_phase_and_final_real_render(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run([NODE,str(mix.HERE/'test_auto_mixer.js'),str(root/'source.f32')],check=True)
            source = noise_colour.downsample(np.fromfile(root/'source.f32','<f4').astype(float))
            seed = np.tile([251,0,0,2,0,3,31,0x31,11,0,0],(120,1)).astype(np.uint8)
            result,info = mix.optimize(source,seed.tobytes(),NODE,
                tone_volumes=np.tile([11,0,0],(120,1)),noise_shares=np.full(120,.3),
                carriers=[0]*120,work_parent=root)
            rows = np.frombuffer(result,np.uint8).reshape(-1,11)
            self.assertEqual(info['final_decision'],'automatic')
            self.assertGreater(np.count_nonzero(rows[10:30,7] & 8),15)
            self.assertGreater(np.count_nonzero((rows[50:70,7]&9)==0),15)
            self.assertGreater(np.count_nonzero((rows[90:110,7]&9)==1),15)
            np.testing.assert_array_equal(rows[:,:6],seed[:,:6])
            self.assertLess(info['final_multiresolution_log_mae_db']['automatic'],
                            info['final_multiresolution_log_mae_db']['seed'])


if __name__ == '__main__':
    unittest.main()
