"""Both targets must reach fitting, cache identity and the final renderer."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import chip_model
import engine
import mixer_fit
import music_profile

NODE=r'C:\Program Files\nodejs\node.exe'


class ChipSelectionTests(unittest.TestCase):
    def test_scoped_target_selects_dac_and_separates_exact_cache(self):
        raw=bytes([251,0,1,0,1,0,0,0x38,12,0,0])*3
        args=(np.zeros(3*441),raw,[[12,0,0]]*3,[0.]*3,[0]*3,NODE)
        original=os.environ.get('ZX_SOUND_CHIP')
        with chip_model.select('AY-3-8910'):
            ay_key=mixer_fit.cache_key(*args)
            np.testing.assert_array_equal(music_profile.chip_levels(),music_profile.chip_levels('AY'))
        with chip_model.select('YM2149'):
            ym_key=mixer_fit.cache_key(*args)
            np.testing.assert_array_equal(music_profile.chip_levels(),music_profile.chip_levels('YM'))
        self.assertNotEqual(ay_key,ym_key)
        self.assertEqual(os.environ.get('ZX_SOUND_CHIP'),original)

    def test_engine_scope_reaches_workers_and_restores_on_failure(self):
        original=os.environ.get('ZX_SOUND_CHIP')
        def fail(*args,**kwargs):
            self.assertEqual(chip_model.current(),'YM2149')
            raise RuntimeError('fixture failure')
        with patch('engine._encode',side_effect=fail):
            with self.assertRaises(RuntimeError):engine.encode([0],NODE,'.',chip='YM2149')
        self.assertEqual(os.environ.get('ZX_SOUND_CHIP'),original)
        with self.assertRaises(ValueError):engine.encode([0],NODE,'.',chip='other')

    def test_explicit_cli_render_target_overrides_the_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);rows=np.tile([251,0,1,0,1,0,0,0x38,16,0,0,0,10,255],(15,1)).astype(np.uint8)
            rows[0,13]=14;(root/'registers.gz').write_bytes(gzip.compress(rows.tobytes(),mtime=0))
            sounds=[]
            for target,levels in (('AY',16),('YM',32)):
                subprocess.run([NODE,str(Path(__file__).with_name('render_ym2149.js')),str(root/'registers.gz'),
                    str(root/f'{target}.f32'),'50',str(root/f'{target}.json'),'14',target],check=True)
                report=json.loads((root/f'{target}.json').read_bytes())
                self.assertEqual(report['distinct_envelope_levels'],levels)
                self.assertEqual(report['dac_curve'],target)
                sounds.append((root/f'{target}.f32').read_bytes())
            self.assertNotEqual(*sounds)


if __name__=='__main__':unittest.main()
