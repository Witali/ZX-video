"""Input fidelity, overflow protection and automatic C/Python TRD parity."""
import gzip
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import wave

import numpy as np

import convert_snr_audio as converter
from general import timeline
from ima_codec import decode


class AutomaticConverterTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / '.tmp' / 'automatic-snr-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def wav(self, values, name='исходный звук.wav', rate=8000, channels=1, width=1):
        path = self.root / name
        with wave.open(str(path), 'wb') as wav:
            wav.setparams((channels, width, rate, 0, 'NONE', 'not compressed'))
            wav.writeframes(np.asarray(values, 'u1').tobytes())
        return path

    def test_prepared_unicode_reference_is_unchanged(self):
        values = np.full(4096, 128, 'u1')
        values[:3968] = np.arange(3968) % 256
        original = values.tobytes()
        path = self.wav(values)
        source, metadata = converter.prepared_source(path)
        self.assertEqual(source.tobytes(), original)
        self.assertEqual(metadata['source_sha256'], hashlib.sha256(original).hexdigest())
        self.assertTrue(metadata['prepared_pcm_unchanged'])
        self.assertEqual(metadata['edge_fade_samples'], 0)
        self.assertEqual(metadata['short_input_repetitions'], 1)

    def test_prepared_rejects_overflow_misalignment_guard_and_bad_format(self):
        cases = [('too-large.wav', np.full(converter.MAXIMUM_SAMPLES + 512, 128, 'u1'), 8000),
                 ('unaligned.wav', np.full(513, 128, 'u1'), 8000),
                 ('wrong-rate.wav', np.full(512, 128, 'u1'), 11025),
                 ('no-silent-guard.wav', np.full(512, 127, 'u1'), 8000)]
        for name, values, rate in cases:
            with self.subTest(name=name), self.assertRaises(ValueError):
                converter.prepared_source(self.wav(values, name, rate))
        path = self.wav(np.full(512, 128, 'u1'), 'truncated-data.wav')
        path.write_bytes(path.read_bytes()[:-16])
        with self.assertRaisesRegex(ValueError, 'truncated'):
            converter.prepared_source(path)

    def test_capacity_truncation_fails_but_explicit_excerpt_is_recorded(self):
        source = np.full(512, 128, 'u1')
        metadata = dict(truncated=True, truncation_reason='resident RAM capacity',
                        short_input_repetitions=1)
        with patch.object(converter, 'prepare_source', return_value=(source, metadata)), self.assertRaisesRegex(ValueError, 'capacity'):
            converter.ordinary_source('input.wav', 'ffmpeg')
        metadata = dict(truncated=True, truncation_reason='requested duration', short_input_repetitions=1)
        with patch.object(converter, 'prepare_source', return_value=(source, metadata)):
            output, info = converter.ordinary_source('input.wav', 'ffmpeg', .01)
        np.testing.assert_array_equal(output, source)
        self.assertTrue(info['explicit_excerpt_selected'])
        self.assertTrue(info['selected_content_preserved'])
        self.assertFalse(info['original_content_preserved'])

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is required for ordinary media')
    def test_short_ordinary_input_is_not_repeated(self):
        path = self.wav(np.full(128, 128, 'u1'), 'short.wav')
        source, info = converter.ordinary_source(path, shutil.which('ffmpeg'))
        self.assertEqual(info['retained_input_samples'], 128)
        self.assertEqual(len(source), 512)
        self.assertEqual(info['short_input_repetitions'], 1)
        self.assertGreater(info['legacy_short_input_repetitions_undone'], 1)
        self.assertTrue(np.all(source[128:] == 128))

    def test_clock_matches_existing_corpus_and_uses_1024_for_full_disk(self):
        for count in (512, 16896, 186880, 720384, 969216):
            with self.subTest(samples=count):
                np.testing.assert_array_equal(converter.instruction_timeline(count), timeline(count, 'pentagon'))
        full = converter.instruction_timeline(converter.MAXIMUM_SAMPLES)
        virtual_refills = timeline(converter.MAXIMUM_SAMPLES, 'pentagon')
        self.assertNotEqual(float(full[-1]), float(virtual_refills[-1]))
        self.assertTrue(np.any(full != virtual_refills))

    def test_guard_prior_does_not_change_reference_or_discard_content(self):
        source = np.r_[np.full(384, 220, 'u1'), np.full(128, 128, 'u1')]
        original = source.copy()
        prior, coverage = converter.compensated_prior(source, converter.instruction_timeline(len(source)))
        np.testing.assert_array_equal(source, original)
        self.assertEqual(len(prior), len(source))
        self.assertTrue(np.all(prior[-128:] == 128))
        self.assertTrue(coverage['all_reference_content_precedes_settling_guard'])
        self.assertEqual(coverage['reference_last_content_edge_sample'], 384)
        self.assertGreater(coverage['prior_guard_samples_zeroed_after_lanczos'], 0)

    def test_existing_output_and_prepared_duration_are_rejected(self):
        source = self.wav(np.full(512, 128, 'u1'))
        out = self.root / 'preserved'
        out.mkdir()
        (out / 'user.txt').write_bytes(b'keep me')
        with self.assertRaisesRegex(ValueError, 'empty'):
            converter.convert(source, out, prepared_pcm=True, ffmpeg='ffmpeg')
        self.assertEqual((out / 'user.txt').read_bytes(), b'keep me')
        with self.assertRaisesRegex(ValueError, 'duration'):
            converter.convert(source, self.root / 'not-created', prepared_pcm=True, duration=.01, ffmpeg='ffmpeg')
        self.assertFalse((self.root / 'not-created').exists())

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is required for host scoring')
    def test_short_conversion_keeps_source_and_reports_insufficient_snr_scope(self):
        source = np.r_[np.full(384, 220, 'u1'), np.full(128, 128, 'u1')]
        report = converter.convert(self.wav(source), self.root / 'short-disk',
                                   prepared_pcm=True, ffmpeg=shutil.which('ffmpeg'))
        self.assertEqual(report['source_samples'], 512)
        self.assertIsNone(report['host_quality']['fixed_clock']['snr_db'])
        self.assertIsNone(report['host_quality']['change_db'])
        self.assertIn('too short', report['host_quality']['fixed_clock']['reason'])
        self.assertFalse(report['release_accepted'])

    @unittest.skipUnless(shutil.which('ffmpeg') and Path('C:/Program Files (x86)/Fuse/fuse.exe').is_file(),
                         'FFmpeg and the installed Fuse executable are required')
    def test_requested_full_fuse_verification_is_included_in_grand_total(self):
        source = np.full(512, 128, 'u1')
        report = converter.convert(self.wav(source), self.root / 'verified-short-disk',
                                   prepared_pcm=True, ffmpeg=shutil.which('ffmpeg'),
                                   verify_fuse=Path('C:/Program Files (x86)/Fuse/fuse.exe'))
        verification = report['complete_emulator_verification']
        self.assertTrue(verification['complete'])
        self.assertEqual(len(verification['native']), 4)
        self.assertEqual(len(verification['fuse']), 2)
        self.assertTrue(all(row['complete_clock_matches_host_quality_model'] for row in verification['fuse']))
        timings = report['timings']
        self.assertGreater(timings['optional_verification_seconds'], 0)
        self.assertGreaterEqual(timings['grand_total_seconds_including_requested_verification'],
                                timings['total_conversion_seconds'] + timings['optional_verification_seconds'])
        self.assertFalse(report['release_accepted'])

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is required for host scoring')
    def test_complete_unicode_c_and_python_conversions_have_identical_trd(self):
        source = np.full(4096, 128, 'u1')
        source[:3968] = np.rint(128 + 20 * np.sin(2 * np.pi * 997 * np.arange(3968) / 8000)).astype('u1')
        path = self.wav(source, 'Песня для автоматической конвертации.wav')
        reference_hash = hashlib.sha256((converter.HERE / 'ima_waveform_encoder.py').read_bytes()).hexdigest()
        reports = []
        for encoder, name in (('c', 'Диск из C'), ('python', 'Диск из Python')):
            dest = self.root / name
            report = converter.convert(path, dest, prepared_pcm=True, encoder=encoder, ffmpeg=shutil.which('ffmpeg'))
            reports.append(report)
            self.assertTrue(report['complete'])
            self.assertFalse(report['release_accepted'])
            self.assertEqual(report['source_samples'], len(source))
            self.assertEqual(report['original_python_reference_sha256'], reference_hash)
            with wave.open(str(dest / 'source-preview.wav'), 'rb') as wav:
                self.assertEqual(wav.readframes(wav.getnframes()), source.tobytes())
            packed = gzip.decompress((dest / 'soundtrack.ima.gz').read_bytes())
            pcm, indices = decode(packed)
            self.assertEqual(len(pcm), len(source))
            self.assertEqual((int(pcm[-1]), int(indices[-1])), (0, 0))
            self.assertIsNone(report['complete_emulator_verification'])
            self.assertGreater(report['timings']['total_conversion_seconds'], 0)
            self.assertGreaterEqual(report['timings']['grand_total_seconds_including_requested_verification'], report['timings']['total_conversion_seconds'])
        self.assertEqual((self.root / 'Диск из C' / 'audio.trd').read_bytes(), (self.root / 'Диск из Python' / 'audio.trd').read_bytes())
        self.assertEqual(reports[0]['packed_sha256'], reports[1]['packed_sha256'])
        self.assertFalse(reports[0]['statistics']['child_python_runtime'])
        self.assertEqual(reports[1]['statistics']['backend'], 'numpy')
        self.assertEqual(hashlib.sha256((converter.HERE / 'ima_waveform_encoder.py').read_bytes()).hexdigest(), reference_hash)


if __name__ == '__main__':
    unittest.main()
