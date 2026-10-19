"""Own-clock quality and automatic C/Python parity for optional448-T pacing."""
import gzip
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

import convert_snr_audio as converter
from clock_control import score
from convert_audio import pcm_wav
from general import models


class PacingConverterTests(unittest.TestCase):
    def setUp(self):
        base = converter.HERE.parent / '.tmp' / 'pacing448-converter-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_exact_clock_delta_includes_page_and_bank_boundaries(self):
        for samples in (512, 33280, 186880):
            with self.subTest(samples=samples):
                old = converter.instruction_timeline(samples)
                new = converter.instruction_timeline(samples, 448)
                # Each source sample has exactly one changed interval, slot7.
                # Page and bank additions stay in both independently counted
                # schedules and therefore cannot masquerade as a pacing fix.
                delta = np.diff(old - new) * 3584000 / converter.CPU_CLOCK
                expected = np.zeros(samples * 16)
                expected[7::16] = 1
                np.testing.assert_allclose(delta, expected, rtol=0, atol=5e-8)
                self.assertAlmostEqual((old[-1] - new[-1]) * 3584000 / converter.CPU_CLOCK,
                                       samples, places=6)
        np.testing.assert_array_equal(converter.instruction_timeline(512),
                                      converter.instruction_timeline(512, 449))

    def test_invalid_clock_fails_before_creating_output(self):
        source = self.root / 'source.wav'
        pcm_wav(source, np.full(512, 128, 'u1'))
        for value in (True, False, 448.0, np.int64(448), 447, 450):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                converter.instruction_timeline(512, value)
            dest = self.root / ('invalid-' + repr(value))
            with self.assertRaises(ValueError):
                converter.convert(source, dest, prepared_pcm=True,
                                  pentagon_ordinary_tstates=value)
            self.assertFalse(dest.exists())

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is required for own-clock scoring')
    def test_c_and_python_build_same_ui_disk_and_keep_legacy_own_clock(self):
        source = np.full(4096, 128, 'u1')
        source[:-128] = np.rint(128 + 40 * np.sin(2 * np.pi * 997 * np.arange(3968) / 8000)).astype('u1')
        path = self.root / 'source.wav'
        pcm_wav(path, source)
        reports = []
        for encoder in ('c', 'python'):
            dest = self.root / encoder
            report = converter.convert(path, dest, prepared_pcm=True, encoder=encoder,
                                       audio_progress_ui=True, pentagon_ordinary_tstates=448,
                                       ffmpeg=shutil.which('ffmpeg'))
            reports.append(report)
            self.assertTrue(report['complete'])
            self.assertFalse(report['release_accepted'])
            self.assertEqual(report['model']['pentagon_ordinary_tstates'], 448)
            self.assertEqual(report['ordinary_native_tstates']['128'], 423)
            self.assertEqual(report['ordinary_native_tstates']['pentagon1024'], 448)
            self.assertEqual(report['hot_path_instruction_delta_tstates'], -1)
            quality = report['host_quality']
            self.assertFalse(quality['baseline_reclocked_to_candidate'])
            baseline = gzip.decompress((dest / 'baseline.ima.gz').read_bytes())
            expected, _, _ = score(source, baseline, dict(models())['legacy'],
                                   converter.instruction_timeline(len(source)),
                                   shutil.which('ffmpeg'), self.root)
            self.assertAlmostEqual(quality['baseline_fixed_clock']['snr_db'], expected['snr_db'], places=11)
            self.assertAlmostEqual(quality['baseline_fixed_clock']['error_rms'], expected['error_rms'], places=13)
            self.assertEqual(report['source_sha256'], converter.sha(source.tobytes()))
        self.assertEqual((self.root / 'c' / 'audio.trd').read_bytes(),
                         (self.root / 'python' / 'audio.trd').read_bytes())
        self.assertEqual(reports[0]['packed_sha256'], reports[1]['packed_sha256'])


if __name__ == '__main__':
    unittest.main()
