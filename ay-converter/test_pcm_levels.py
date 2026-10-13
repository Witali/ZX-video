"""Bounded compression preserves silence/timing and reduces level spread."""
import unittest
import numpy as np
import pcm_levels
from audio_input import mono_filter


class PcmLevelTests(unittest.TestCase):
    def test_quiet_passage_gets_closer_without_clipping_or_filling_silence(self):
        t=np.arange(22050*6)/22050
        amplitude=np.r_[np.full(22050*2,.7),np.full(22050*2,.02),np.full(22050*2,.3)]
        source=amplitude*np.sin(2*np.pi*440*t)
        source=np.r_[source,np.zeros(22050)]
        original,a=pcm_levels.process(source,dynamics='original')
        compact,b=pcm_levels.process(source,dynamics='compact')
        self.assertLess(b['processed_levels']['p90_minus_p10_db'],a['processed_levels']['p90_minus_p10_db']-5)
        self.assertEqual(b['clipping_samples'],0)
        self.assertAlmostEqual(float(abs(compact).max()),10**(-1/20))
        np.testing.assert_array_equal(compact[-22050:],0)
        self.assertEqual(len(compact),len(original))
        # Compression changes amplitude, never the zero crossings of a tone.
        np.testing.assert_array_equal(np.signbit(original),np.signbit(compact))

    def test_context_and_invalid_options(self):
        source=np.r_[np.zeros(441),np.ones(441)*.2,np.ones(441)*.8]
        processed,info=pcm_levels.process(source,start_tick=1,ticks=1)
        self.assertEqual(info['source_peak'],.2)
        self.assertEqual(info['processed_levels']['active_ticks'],1)
        self.assertFalse(processed[:441].any())
        with self.assertRaises(ValueError):pcm_levels.process(source,dynamics='other')

    def test_five_point_one_uses_an_explicit_centre_priority_mix(self):
        self.assertIn('0.40*c2',mono_filter(6,'5.1'))
        self.assertEqual(mono_filter(6,'5.1'),mono_filter(6,'5.1(side)'))
        self.assertIsNone(mono_filter(2,'stereo'))
        self.assertIsNone(mono_filter(1,'mono'))


if __name__=='__main__':unittest.main()
