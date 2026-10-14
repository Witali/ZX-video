"""Source-line, source-fill and hardware-clash contracts for line drawings."""
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np

import lineart_colour as line
import five_level_dither as five
from cell_palette_quality import averaged


def image(rgb):
    result = np.zeros((96, 128, 3), np.uint8);result[12:84] = rgb
    return result


class LineartColourTests(unittest.TestCase):
    def test_dark_region_rollback_preserves_real_colour_and_entire_source_components(self):
        fixture = np.load(Path(__file__).parent/'analysis/flat_colour/dark-fixtures/regression460.npz')
        source = fixture['source'];old = averaged(fixture['baseline'])
        unguarded = averaged(line.render_fills(line.source_fills(source, dark_fills=True), line.source_lines(source)))
        self.assertTrue((np.mean((unguarded-source)**2, -1) > np.mean((old-source)**2, -1)).any())
        state, accepted = line.select_fills(source, dark_fills=True);new = averaged(state)
        self.assertTrue((np.mean((new-source)**2, -1) <= np.mean((old-source)**2, -1)).all())
        coloured = np.ptp(old, axis=-1) > 0
        np.testing.assert_array_equal(new[coloured], old[coloured])
        original = line.source_fills(source);proposed = line.source_fills(source, dark_fills=True)
        added = (proposed == 0) & (original != 0)
        count, labels = cv2.connectedComponents(added.astype(np.uint8), connectivity=8)
        rejected = 0
        for label in range(1, count):
            values = accepted[labels == label]
            self.assertTrue((values == 0).all() or (values == 7).all())
            rejected += (values == 7).all()
        self.assertGreater(rejected, 0)

    def test_dark_fills_use_existing_rgb_bounds_without_erasing_source_lines(self):
        source = image([190, 185, 165]);source[25:65, 35:83] = [83, 42, 10]
        source[34:38, 43:49] = source[34:38, 68:74] = 245
        old = averaged(line.encode(source));new = averaged(line.encode(source, dark_fills=True))
        changed = np.any(old != new, axis=-1)
        self.assertTrue(changed.any())
        self.assertTrue((np.mean((new-source)**2, -1) <= np.mean((old-source)**2, -1)).all())
        lines = line.source_lines(source)
        np.testing.assert_array_equal(new[lines], old[lines])
        fills = line.source_fills(source, dark_fills=True)
        added = (fills == 0) & (line.source_fills(source) != 0)
        self.assertTrue((np.mean(source[added].astype(float)**2, -1) <= 60**2).all())
        self.assertTrue((source[added].max(-1) <= 100).all())
        for rgb in ([65]*3, [100, 100, 0], [101, 0, 0]):
            self.assertTrue((line.source_fills(image(rgb), dark_fills=True)[12:84] == 7).all())
        source = image([190]*3);source[30, 40] = [90, 0, 0]
        self.assertEqual(line.source_fills(source, dark_fills=True)[30, 40], 7)

    def test_real_solid_colours_include_normal_and_bright(self):
        for colour in (0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14):
            source = image(line.COLOURS[colour].astype(np.uint8))
            np.testing.assert_array_equal(averaged(line.encode(source)), source)

    def test_unmatched_uniform_source_is_uniform_paper_without_cell_edges(self):
        source = image([100]*3)
        self.assertFalse(line.source_lines(source).any())
        actual = averaged(line.encode(source))[12:84]
        np.testing.assert_array_equal(actual, np.full((72, 128, 3), 205))

    def test_facial_lines_are_mandatory_and_not_lost_to_fill_selection(self):
        source = image([190, 185, 165]);source[25:65, 35:83] = [170, 140, 110]
        source[34:38, 43:49] = source[34:38, 68:74] = 245
        source[50:52, 48:69] = [75, 55, 50]
        mask = line.source_lines(source);state = line.encode(source)
        self.assertTrue(mask[32:40, 41:51].any());self.assertTrue(mask[47:55, 45:72].any())
        np.testing.assert_array_equal(averaged(state)[mask], np.zeros((mask.sum(), 3)))
        self.assertEqual(set(np.unique(five.unpack_levels(state[:3840]))), {0, 4})

    def test_colour_fills_cannot_spill_outside_matched_source(self):
        source = image([165, 165, 150]);source[30:66, 43:77] = [214, 182, 87]
        source[42:48, 50:59] = [170, 25, 15]
        fills = line.source_fills(source);state = line.encode(source);output = averaged(state)
        coloured = np.ptp(output, axis=-1) != 0
        self.assertTrue(coloured.any())
        np.testing.assert_array_equal(output[coloured], line.COLOURS[fills[coloured]])
        self.assertTrue((np.mean((output[coloured]-source[coloured])**2, axis=-1) <= 60**2).all())
        self.assertTrue((np.max(np.abs(output[coloured]-source[coloured]), axis=-1) <= 100).all())

    def test_three_colour_cell_keeps_lines_and_paper_before_optional_fill(self):
        source = image([110]*3);source[40:44, 60:62] = [205, 205, 0]
        source[40:44, 62] = 0
        output = averaged(line.encode(source))
        mask = line.source_lines(source)
        np.testing.assert_array_equal(output[mask], np.zeros((mask.sum(), 3)))
        paper = line.source_fills(source) == 7
        paper &= ~mask;paper[:12] = paper[84:] = False
        np.testing.assert_array_equal(output[paper], np.full((paper.sum(), 3), 205))

    def test_deterministic_current_frame_and_native_border_contract(self):
        source = image(np.random.default_rng(4).integers(0, 256, (72, 128, 3), dtype=np.uint8))
        state = line.encode(source)
        old_source = image([205, 0, 0]);old = line.encode(old_source)
        self.assertEqual(line.encode(source, old, old_source), state)
        self.assertEqual(state[3840:3936], bytes([1])*96)
        self.assertEqual(state[4512:], bytes([1])*96)
        self.assertFalse((np.frombuffer(state[3840:], np.uint8) & 128).any())
        with self.assertRaises(ValueError):line.encode(source.astype(float))
        with self.assertRaises(ValueError):line.encode(source, state)

    def test_generic_cli_policy_produces_exact_packet_roundtrip(self):
        from convert_video import convert_frames
        from generic_cell_codebook import prepare_frames, row_sets, representation
        source = image([160]*3);source[27:66, 43:77] = [205, 205, 0]
        images = np.stack([source[12:84]]*2)
        with tempfile.TemporaryDirectory() as tmp:
            compact, _ = convert_frames(images, Path(tmp))
            prepared, report = prepare_frames(images, compact, tmp, colour_policy='lineart')
            try:
                self.assertEqual(prepared[0].tobytes(), line.encode(source))
                self.assertEqual(report['dither'], 'none')
                self.assertTrue(report['colour_comparison']['contours'])
                self.assertFalse(report['colour_comparison']['semantic_person_model'])
                row_sets(prepared)
                self.assertTrue(representation(prepared, 0, 2)['full_host_screens_exact'])
            finally:del compact, prepared

    def test_generic_dark_option_metadata_and_exact_screen_roundtrip(self):
        from convert_video import convert_frames
        from generic_cell_codebook import prepare_frames, representation
        source = image([180]*3);source[30:55, 43:77] = [83, 42, 10]
        with tempfile.TemporaryDirectory() as tmp:
            compact, _ = convert_frames(np.stack([source[12:84]]*2), Path(tmp))
            states, report = prepare_frames(np.stack([source[12:84]]*2), compact, tmp,
                colour_policy='lineart', lineart_dark_fills=True)
            try:
                self.assertEqual(states[0].tobytes(), line.encode(source, dark_fills=True))
                self.assertTrue(report['lineart_dark_fills'])
                self.assertEqual(report['colour_comparison']['parameters']['black_max_component'], 100)
                self.assertTrue(representation(states, 0, 2)['full_host_screens_exact'])
            finally:del compact, states
        with self.assertRaises(ValueError):
            prepare_frames([source[12:84]], np.zeros((1, 3840), np.uint8), '.',
                colour_policy='flat', lineart_dark_fills=True)


if __name__ == '__main__':unittest.main()
