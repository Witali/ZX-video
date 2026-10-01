"""Exact generic CB41 boundaries and five-level preparation regressions."""
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import five_level_dither as five
import generic_cell_codebook as generic
from convert_video import convert_frames
from probe_cell_codebook import bitmap


def frame(words, attr=71):
    levels = np.zeros((96, 128), dtype=np.uint8)
    words = np.resize(np.asarray(words, dtype=np.uint16), (72, 32))
    levels[12:84] = ((words[..., None]//np.array([125, 25, 5, 1])) % 5).reshape(72, 128)
    attrs = np.ones(768, dtype=np.uint8)
    attrs[96:672] = attr
    return np.frombuffer(five.pack_levels(levels)+attrs.tobytes(), dtype=np.uint8).copy()


class GenericCellCodebookTests(unittest.TestCase):
    def test_single_black_and_static_small_books(self):
        for words in ([0], [624], [0, 156, 312, 468, 624]):
            with self.subTest(words=words):
                frames = np.stack([frame(words)]*3)
                for start, end in ((0, 1), (0, 3), (1, 3), (2, 3)):
                    result = generic.representation(frames, start, end)
                    self.assertEqual(struct.unpack_from('<HH', result['raw'], 4), (end-start, 256))
                    self.assertEqual(len(result['book']), 2048)
                    self.assertEqual(len(result['screen_sha256']), end-start)
                    self.assertTrue(result['full_host_screens_exact'])
                    self.assertLess(result['unique_changed_patterns'], 256)
                    for detail in result['details']:
                        self.assertLessEqual(detail['packet_bytes'], 3096)

    def test_each_quarter_shade_and_bright_survive(self):
        frames = np.stack([frame([0, 156, 312, 468, 624], attr) for attr in (7, 71, 7)])
        result = generic.representation(frames, 0, 3)
        for state, source in zip(result['states'], frames):
            from row_dictionary_video import reference_tables
            import build_long_video_trd as video
            with reference_tables(result['rows']):
                self.assertEqual(video.expand_compact_screen(state.tobytes()), five.expand(source.tobytes()))
        for word, pair in zip((0, 156, 312, 468, 624), five.PATTERNS):
            symbol = result['rows']['words'].index(word)
            self.assertEqual(bitmap(bytes([symbol])*4, result['rows']['words']),
                             bytes([(pair[0]*85), (pair[1]*85)])*4)
        self.assertEqual(result['details'][1]['attribute_cells'], 576)

    def test_row_limit_includes_black_and_both_histories(self):
        self.assertEqual(generic.row_partitions([{0}]*3, 1),
                         [dict(start=i, end=i+1, rows=1) for i in range(3)])
        first, second, third = [set(range(i, i+120)) | {0} for i in (1, 121, 241)]
        sets = [first, first, second, second, third]
        parts = generic.row_partitions(sets, 10922)
        self.assertEqual([(p['start'], p['end']) for p in parts], [(0, 4), (4, 5)])
        self.assertEqual(parts[1]['rows'], 241)
        with self.assertRaisesRegex(ValueError, 'two cold histories'):
            generic.row_partitions([first, second, third], 1)

    def test_native_row_boundary_and_explicit_overflow(self):
        supported = np.stack([frame(range(256))])
        self.assertEqual(generic.representation(supported, 0, 1)['rows']['entries'], 256)
        rejected = np.stack([frame(range(257))])
        with self.assertRaisesRegex(ValueError, '257 rows'):
            generic.row_partitions(generic.row_sets(rejected), 4096)
        with self.assertRaisesRegex(ValueError, 'maximum 256'):
            generic.representation(rejected, 0, 1)

    def test_invalid_native_inputs_are_rejected(self):
        frames = np.stack([frame([0])])
        for index, value in ((3840, 0), (3936, 128), (0, 1)):
            damaged = frames.copy()
            damaged[0, index] = value
            with self.assertRaises(ValueError):
                generic.row_sets(damaged)
        for start, end in ((-1, 1), (0, 0), (0, 2)):
            with self.assertRaises(ValueError):
                generic.representation(frames, start, end)

    def test_window_and_audio_partition_keep_every_frame(self):
        import convert_cb41 as pipeline
        frames = np.stack([frame([0])]*20)
        # Controlled byte/AY constraints exercise planning only; real LZSA,
        # resident AY and final disk capacity are covered by the media suite.
        def packed(raw, codec, cache):
            count = struct.unpack_from('<H', raw, 4)[0]
            return bytes(100*count), []
        def sound(audio, lo, hi, labels):
            return bytes([lo, hi]), dict(resident_fits=hi-lo <= 4)
        with patch.object(pipeline, 'pack_blocks', side_effect=packed), \
                patch.object(pipeline, 'audio_size', side_effect=sound), \
                patch.object(pipeline, 'VIDEO_BUDGET', 700):
            parts, plan = pipeline.plan_volumes(frames, [], {}, None, None, 20)
        self.assertEqual([i for part in parts for i in range(part['start'], part['end'])], list(range(20)))
        self.assertTrue(all(0 < p['end']-p['start'] <= 4 for p in parts))
        self.assertEqual(len(plan['windows']), 1)
        self.assertEqual(plan['candidate_disk_sets_built'], 0)
        self.assertFalse(plan['final_disk_capacity_verified'])

    def test_native_options_match_verified_movie(self):
        import json
        from convert_cb41 import OPTIONS
        baseline = json.loads(Path(__file__).with_name('fast_zx0_player_build.json').read_bytes())['contract']['options']
        baseline['startup_delta'] = False
        self.assertEqual(OPTIONS, baseline)

    def test_generic_refinement_preserves_fit_and_improves_error(self):
        ramp = np.tile(np.repeat(np.array([0, 64, 128, 192, 255], dtype=np.uint8),
                                 [24, 24, 24, 24, 32]), (72, 1))
        images = np.stack([np.repeat(ramp[:, :, None], 3, axis=2)]*2)
        with tempfile.TemporaryDirectory() as tmp:
            compact, _ = convert_frames(images, Path(tmp))
            original = compact.copy()
            prepared, quality = generic.prepare_frames(images, compact, tmp)
            self.assertTrue(quality['refinement_never_increased_rgb_error'])
            self.assertLessEqual(quality['mean_mse'], quality['four_level_mean_mse'])
            self.assertEqual(set(five.unpack_levels(prepared[0, :3840].tobytes()).ravel()), set(range(5)))
            np.testing.assert_array_equal(compact, original)
            generic.row_sets(prepared)
            generic.representation(prepared, 0, 2)
            generic.write_preview(images, prepared, quality, Path(tmp)/'preview.png')
            self.assertTrue((Path(tmp)/'preview.png').is_file())
            # Windows cannot unlink a live memory map.
            del compact, prepared


if __name__ == '__main__':
    unittest.main()
