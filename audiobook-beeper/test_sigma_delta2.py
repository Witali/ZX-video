"""Exact SD2 feedback, finite-state closure, and legacy-player compatibility."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sigma_delta2 import model,tables,independent_tables,step
from ima3_direct_player import build_disk


class SigmaDelta2(unittest.TestCase):
    def test_exact_second_difference_and_continuous_packet_state(self):
        spec=model();words,nxt,proof=tables(spec)
        states={int(i):tuple(s) for i,s in proof['states'].items()}
        rng=np.random.default_rng(1977);sid=16;recent=older=0;scale=spec['dac_scale']
        for value in rng.integers(0,128,size=2000):
            x=round(scale/2+scale*spec['output_gain']*((2*int(value)+1)/256-.5))
            word=0
            for _ in range(16):
                u=x+2*recent-older;bit=int(u>=scale/2);error=u-scale*bit
                self.assertEqual(scale*bit-x,-(error-2*recent+older))
                older,recent=recent,error;word=word*2+bit
            self.assertEqual(word,int(words[value,sid]));sid=int(nxt[value,sid])
            self.assertEqual((recent-older,recent),states[sid])

    def test_exhaustive_independent_entries_and_no_state_rounding(self):
        for scale,gain in ((32,(1,2)),(64,(3,8)),(64,(1,4))):
            spec=model(scale,gain);independent_tables(spec)
            _,_,proof=tables(spec)
            self.assertTrue(proof['all_input_sequences_closed'])
            self.assertFalse(proof['state_rounding']);self.assertFalse(proof['state_clipping'])
            self.assertLessEqual(proof['exact_state_count']*6,128)
            self.assertEqual(step(scale//2,0,0,scale)[1],(0,0))

    def test_unmodified_model_rebuilds_accepted_disk_byte_exactly(self):
        root=Path(__file__).resolve().parent/'experiments/ima-quality/music3/selected'
        meta=json.loads((root/'player.json').read_bytes())
        packed=gzip.decompress((root/'soundtrack.ima.gz').read_bytes())
        with tempfile.TemporaryDirectory() as work:
            disk,_=build_disk(packed,Path(work),meta['model'],meta['hot_indices'],
                              meta['loop_idle_pairs'],meta['loop_idle_pad_tstates'])
        self.assertEqual(hashlib.sha256(disk).hexdigest(),
                         hashlib.sha256((root/'audiobook-preview.trd').read_bytes()).hexdigest())

    def test_measurement_gain_cannot_disagree_with_feedback_model(self):
        spec=model();spec['output_gain']=.5
        with self.assertRaisesRegex(ValueError,'measurement gain'):tables(spec)


if __name__=='__main__':unittest.main()
