"""Masking must preserve audible errors; register feedback must improve sound."""
import gzip
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import fast_mixer
import noise_colour
import psychoacoustic as psycho
import simulation_refine as fit

NODE = r'C:\Program Files\nodejs\node.exe'


class PerceptualFeedbackTests(unittest.TestCase):
    def test_neighbour_masking_and_candidate_cannot_hide_its_own_error(self):
        hz=np.array([800,1000,1100,5000.])
        reference=np.tile([.001,1.,.001,.001],(3,1))
        threshold=psycho.thresholds(reference,hz)
        weights=psycho.error_weights(reference,reference,threshold)
        self.assertLess(weights[0,2],weights[0,3])
        candidate=reference.copy();candidate[:,2]=.5
        self.assertGreater(psycho.error_weights(reference,candidate,threshold)[0,2],.95)

    def test_forward_masking_decays_without_suppressing_new_sound(self):
        reference=np.array([[1.],[0.],[0.]])
        threshold=psycho.thresholds(reference,np.array([1000.]))
        self.assertGreater(threshold[1,0],threshold[2,0])
        self.assertAlmostEqual(float(threshold[2,0]/threshold[1,0]),10**(-8/10),places=6)
        self.assertEqual(float(psycho.error_weights(reference,np.ones_like(reference),threshold)[2,0]),1.)

    def test_real_chip_levels_and_periods_improve_detuned_dynamic_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=np.tile([246,0,1,0,1,0,0,0x38,9,0,0],(80,1)).astype(np.uint8)
            target[40:,8]=14
            (root/'target.gz').write_bytes(gzip.compress(target.tobytes(),mtime=0))
            subprocess.run([NODE,str(fit.HERE/'render_ym2149.js'),str(root/'target.gz'),str(root/'source.f32'),'50',str(root/'source.json')],check=True)
            samples=noise_colour.downsample(np.fromfile(root/'source.f32','<f4').astype(float))
            seed=target.copy();seed[:,0]=251;seed[:,8]=12
            result,info=fit.optimize(samples,seed.tobytes(),NODE,work_parent=root)
            rows=np.frombuffer(result,np.uint8).reshape(-1,11)
            self.assertLess(info['final']['objective_db'],info['baseline']['objective_db'])
            self.assertLess(info['final']['level_mae_db'],info['baseline']['level_mae_db'])
            self.assertGreater(info['changed_volume_registers'],0)
            self.assertGreater(info['changed_tone_periods'],0)
            self.assertTrue(np.all(rows[:,8:]<=15))
            np.testing.assert_array_equal(rows[:,6:8],seed[:,6:8])

    def test_zero_source_emits_mute_registers_instead_of_hiding_sound_with_gain(self):
        seed=bytes([251,0,1,0,1,0,0,0x38,12,0,0])*3
        result,info=fit.optimize(np.zeros(3*441),seed,NODE)
        self.assertFalse(np.frombuffer(result,np.uint8).reshape(-1,11)[:,8:].any())
        self.assertEqual(info['fixed_model_gain'],1.)

    def test_fast_cache_is_exact_and_separate_from_full_search(self):
        seed=bytes([251,0,1,0,1,0,0,0x38,12,0,0])*3
        samples=np.zeros(3*441)
        controls=dict(tone_volumes=[[12,0,0]]*3,noise_shares=[0.]*3,carriers=[0]*3)
        with tempfile.TemporaryDirectory() as directory, patch('fast_mixer._optimize',return_value=(seed,{'model':'fixture'})) as optimize:
            first,info=fast_mixer.optimize(samples,seed,NODE,cache_dir=directory,**controls)
            second,reused=fast_mixer.optimize(samples,seed,NODE,cache_dir=directory,**controls)
            self.assertEqual(first,second);self.assertTrue(reused['cache_hit']);self.assertEqual(optimize.call_count,1)
            samples[0]=.001
            fast_mixer.optimize(samples,seed,NODE,cache_dir=directory,**controls)
            self.assertEqual(optimize.call_count,2)


if __name__=='__main__': unittest.main()
