"""Source-conditioning safety, true compression, streaming parity and CLI routing."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from audio_dynamics import normalize, normalize_file, PEAK


class Dynamics(unittest.TestCase):
    def test_off_is_exact_previous_gain_and_silence_is_exact(self):
        x = np.linspace(-.7, .6, 3001)
        y, info = normalize(x, 'unused', 'off')
        self.assertTrue(np.array_equal(y, x*(PEAK/max(abs(x)))))
        self.assertEqual(info['rms_gain_over_peak_only_db'], 0)
        for mode in ('off', 'gentle'):
            y, info = normalize(np.zeros(101), 'unused', mode)
            self.assertFalse(np.any(y))
            self.assertEqual(len(y), 101)
            self.assertEqual(info['output_rms'], 0)

    def test_invalid_source(self):
        for x in ([], [float('nan')], [float('inf')]):
            with self.assertRaises(ValueError): normalize(x, 'unused')
        with self.assertRaises(ValueError): normalize([1], 'unused', 'invalid')

    def test_public_cli_modes(self):
        from convert_audio import main
        for codec, target in (('ima4', 'convert_audio.convert'), ('ima3', 'convert_ima3_audio.convert'),
                              ('mulaw', 'convert_mulaw_packet.convert')):
            for flags, expected in (([], 'gentle'), (['--dynamics','off'], 'off')):
                with patch(target, return_value={'quality_gate_passed':True}) as convert:
                    try:
                        main(['input.wav','--codec',codec,'--output','unused','--ffmpeg','ffmpeg','--fuse','fuse']+flags)
                    except SystemExit as done:
                        self.assertEqual(done.code, 0)
                    self.assertEqual(convert.call_args.args[0].dynamics, expected)

    @unittest.skipUnless(os.environ.get('TASK_FFMPEG'), 'set TASK_FFMPEG for real filter integration')
    def test_compression_peak_timing_and_streaming_parity(self):
        ffmpeg = os.environ['TASK_FFMPEG']
        t = np.arange(32000)/8000
        x = (np.sin(2*np.pi*400*t)*np.where(t<2, .02, .75)).astype('<f4')
        old, _ = normalize(x, ffmpeg, 'off')
        new, info = normalize(x, ffmpeg)
        self.assertEqual(len(new), len(x))
        self.assertAlmostEqual(float(max(abs(new))), PEAK, places=12)
        self.assertGreater(np.std(new[8000:15000]), np.std(old[8000:15000])*1.5)
        self.assertLess(np.std(new[24000:31000])/np.std(new[8000:15000]),
                        np.std(old[24000:31000])/np.std(old[8000:15000]))
        # A compressor changes gain, never the sample timing or polarity.
        self.assertTrue(np.all(new*x >= 0))
        self.assertAlmostEqual(info['output_rms'], float(np.sqrt(np.mean(new*new))))
        with tempfile.TemporaryDirectory() as directory:
            src, dst = (Path(directory)/name for name in ('raw.f32','conditioned.f32'))
            src.write_bytes(x.tobytes())
            gain, stream_info = normalize_file(src, dst, ffmpeg)
            streamed = np.frombuffer(dst.read_bytes(), '<f4').astype(float)*gain
            self.assertTrue(np.array_equal(new, streamed))
            self.assertEqual(info, stream_info)
            gain, _ = normalize_file(src, dst, ffmpeg, 'off')
            self.assertEqual(dst.read_bytes(), src.read_bytes())
            self.assertTrue(np.array_equal(old, np.frombuffer(dst.read_bytes(),'<f4').astype(float)*gain))

    def test_prepared_pcm_bypasses_dynamics(self):
        from convert_audio import prepared_ima4_source, pcm_wav
        from convert_mulaw_audio import prepare
        x = np.full(8192, 128, dtype='u1')
        x[100:7000] = np.arange(6900, dtype='u1')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'prepared.wav'
            pcm_wav(path, x)
            kept, _ = prepared_ima4_source(path)
            self.assertTrue(np.array_equal(kept, x))
            mu, _ = prepare(path, 'unused', prepared=True, dynamics='gentle')
            self.assertTrue(np.array_equal(mu, (x.astype(np.int16)-128)*256))


if __name__ == '__main__':
    unittest.main()
