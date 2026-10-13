"""Conservative noise must need both source evidence and a rendered advantage."""
import gzip
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
import noise_gate
import noise_colour

NODE=r'C:\Program Files\nodejs\node.exe'


class NoiseNecessityTests(unittest.TestCase):
    def test_added_noise_is_removed_from_a_pure_tone(self):
        count=60
        tone=np.tile([251,0,1,0,1,0,23,0x38,12,0,0],(count,1)).astype(np.uint8)
        seed=tone.copy();seed[:,7]=0x30;seed[:,8]=15
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'tone.gz').write_bytes(gzip.compress(tone.tobytes(),mtime=0))
            subprocess.run([NODE,str(noise_gate.HERE/'render_ym2149.js'),str(root/'tone.gz'),str(root/'source.f32'),
                '50',str(root/'source.json')],check=True)
            source=noise_colour.downsample(np.fromfile(root/'source.f32','<f4').astype(float))
            result,info=noise_gate.optimize(source,seed.tobytes(),NODE,noise_shares=np.full(count,.02),work_parent=root)
            self.assertEqual(info['noise_ticks_after'],0)
            rows=np.frombuffer(result,np.uint8).reshape(-1,11)
            np.testing.assert_array_equal(rows[:,6],seed[:,6])
            self.assertTrue(np.all(rows[:,7]&8))

    def test_actual_noise_with_strong_source_evidence_is_retained(self):
        count=60
        seed=np.tile([1,0,1,0,1,0,23,0x31,12,0,0],(count,1)).astype(np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'seed.gz').write_bytes(gzip.compress(seed.tobytes(),mtime=0))
            subprocess.run([NODE,str(noise_gate.HERE/'render_ym2149.js'),str(root/'seed.gz'),str(root/'source.f32'),
                '50',str(root/'source.json')],check=True)
            source=noise_colour.downsample(np.fromfile(root/'source.f32','<f4').astype(float))
            result,info=noise_gate.optimize(source,seed.tobytes(),NODE,noise_shares=np.ones(count),work_parent=root,calibration_gain=1.)
            self.assertGreater(info['noise_ticks_after'],count*.9)
            self.assertEqual(len(result),len(seed.tobytes()))


if __name__=='__main__':unittest.main()
