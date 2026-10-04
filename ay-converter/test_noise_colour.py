"""Noise-fit contracts and an unseen-phase synthetic chip reference."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import numpy as np
import noise_colour as noise


class NoiseTests(unittest.TestCase):
    def test_resampling_rejects_aliases_without_moving_time(self):
        t = np.arange(44100)/44100
        low = noise.downsample(np.sin(2*np.pi*8000*t))[100:-100]
        high = noise.downsample(np.sin(2*np.pi*15000*t))[100:-100]
        self.assertGreater(float(np.sqrt(np.mean(low**2))),.69)
        self.assertLess(float(np.sqrt(np.mean(high**2))),.001)
        impulse = np.zeros(1764); impulse[882] = 1
        self.assertEqual(int(np.argmax(noise.downsample(impulse))),441)

    def test_no_noise_is_exact_and_needs_no_renderer(self):
        raw = bytes([1,0,2,0,3,0,0,0x38,4,5,6])*10
        result,info = noise.optimize(np.zeros(4410),raw,'does-not-exist')
        self.assertEqual(result,raw)
        self.assertEqual(info['changed_period_ticks'],0)

    def test_choices_preserve_tones_routing_and_other_volumes(self):
        raw = np.tile([21,1,47,2,11,3,28,0x28,12,11,10],(4,1)).astype(np.uint8)
        raw[1,6:8] = [0,0x38]
        result = noise.apply_choices(raw,np.array([0,2,3]),np.array([0,61,92]))
        np.testing.assert_array_equal(result[:,:6],raw[:,:6])
        np.testing.assert_array_equal(result[:,7],raw[:,7])
        np.testing.assert_array_equal(result[:,[8,10]],raw[:,[8,10]])
        np.testing.assert_array_equal(result[1],raw[1])
        self.assertTrue(np.all(result[[0,2,3],9]>0))

    def test_path_suppresses_weak_chatter_but_resets_at_gaps(self):
        cost = np.full((5,93),10.)
        cost[:,[0,30]] = [[0,.02],[.02,0],[0,.02],[.02,0],[5,0]]
        selected = noise.choose_path(cost,np.array([0,1,2,3,9]))
        self.assertEqual(len(set(selected[:4])),1)
        self.assertEqual(selected[4],30)

    @unittest.skipUnless(shutil.which('node'),'Node.js is required for chip validation')
    def test_digital_model_and_unseen_noise_phase(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'reference.f32'
            run = subprocess.run([shutil.which('node'),str(noise.HERE/'test_noise_colour.js'),str(source)],
                capture_output=True,text=True,check=True)
            report = json.loads(run.stdout)
            self.assertEqual(report['lfsr_states'],131071)
            raw = np.tile([0,1,0,2,0,3,31,0x37,11,0,0],(100,1)).astype(np.uint8)
            reference = noise.downsample(np.fromfile(source,dtype='<f4').astype(float))
            self.assertLess(float(np.max(abs(reference))),.5)
            result,info = noise.optimize(reference,raw.tobytes(),shutil.which('node'))
            fitted = np.frombuffer(result,dtype=np.uint8).reshape(-1,11)
            # The exact random waveform is unknowable. Recover its spectral
            # colour near period 23 at a held-out phase, retaining its level.
            self.assertLess(abs(float(np.median(fitted[10:-10,6]))-23),4)
            self.assertGreaterEqual(float(np.median(fitted[10:-10,8])),10)
            self.assertEqual(info['noise_ticks'],100)
            print(json.dumps(dict(held_out_noise_period=23,
                recovered_median_period=float(np.median(fitted[10:-10,6])),
                recovered_median_volume=float(np.median(fitted[10:-10,8])),
                reference_volume=11,core=report)),flush=True)


if __name__ == '__main__':
    unittest.main()
