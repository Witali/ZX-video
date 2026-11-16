"""Check the shipped model, screen layout, and boundary-specific behavior."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from .__main__ import choose, convert, render
from .dither import DitherCandidates
from .evaluate import independent_decode, quality
from .halftones import restore_halftones
from .model import load_weights
from .objective import COLOR_BUDGET, Candidates, edge_weight
from .screen import ATTRIBUTES, COLS, HEIGHT, ROWS, WIDTH, pack, prepare, to_cells
from .subject import LUMA, box_mean, protect_thin_parts, restore_color_accents
from .subject_continuity import continue_thin_parts, fit_part, replace_cells
from .subject_gaps import keep_open_gaps


class ConverterTests(unittest.TestCase):
    def test_cell_alignment_corrects_a_grid_offset_and_moves_its_subject_mask(self):
        from .alignment import align_cells
        from .screen import Framing, PALETTE

        y, x = np.indices((160, WIDTH))
        pattern = ((x + 3) // 8) % 2 + 2 * (((y + 3) // 8) % 2)
        source = PALETTE[np.array([2, 4, 1, 7])[pattern]]
        image = Image.fromarray(source)
        mask = Image.fromarray(source[..., 0])

        def render_input(rgb, probability):
            np.testing.assert_array_equal(probability, rgb[..., 0].astype(np.float32) / 255)
            return convert(rgb, "spatial", None, floyd=True, repair=True)

        framing, (screen, preview) = align_cells(image, False, render_input, mask)
        self.assertEqual(framing, Framing(dy=3))
        np.testing.assert_array_equal(independent_decode(screen), preview)

    def test_cell_alignment_respects_fit_and_crop_boundaries(self):
        from .screen import Framing, placement

        self.assertIsNone(placement((256, 192), False, Framing(dx=1)))
        self.assertIsNone(placement((256, 192), True, Framing(dx=1)))
        box, rect = placement((256, 192), True, Framing(scale=1.03125, dx=3, dy=-3))
        self.assertEqual(rect, (0, 0, WIDTH, HEIGHT))
        self.assertGreaterEqual(min(box), 0)
        self.assertLessEqual(box[2], WIDTH)
        self.assertLessEqual(box[3], HEIGHT)
        # This height yields a crop origin just below zero in floating point.
        crop = prepare(Image.new("RGB", (256, 94), (12, 34, 56)), True, framing=Framing(dx=1))
        self.assertTrue((crop == (12, 34, 56)).all())

    def test_dark_ramp_removes_false_palette_steps_and_keeps_a_real_highlight(self):
        from .dark_ramps import quiet_seam_error, restore_dark_ramps

        shades = np.arange(30, 80, 50 / WIDTH)
        gradient = shades[:, None] * np.array([.08, .18, 1])
        source = np.broadcast_to(gradient, (HEIGHT, WIDTH, 3)).astype(np.uint8)
        source[72:120, 120:128] = 205
        attrs = np.full((ROWS, COLS), 1, dtype=np.uint8)
        attrs[:, 8:15] = 5
        attrs[:, 16:24] = 7
        attrs[9:15, 15] = 7
        y, x = np.indices(source.shape[:2])
        bits = (x + y) % 3 == 0
        bits[72:120, 120:128] = True
        baseline = pack(bits, attrs)
        old = independent_decode(baseline)
        screen, preview = restore_dark_ramps(source, (baseline, old))

        np.testing.assert_array_equal(independent_decode(screen), preview)
        np.testing.assert_array_equal(preview[72:120, 120:128], old[72:120, 120:128])
        self.assertTrue((preview[:64, :, :2] == 0).all())
        self.assertGreater(preview[:64, 224:, 2].mean(), preview[:64, :32, 2].mean())
        all_cells = np.ones((ROWS, COLS), dtype=bool)
        self.assertLess(quiet_seam_error(source, preview, all_cells), .65 * quiet_seam_error(source, old, all_cells))

    def test_pale_blue_ramp_keeps_blue_and_uses_density_for_the_gradient(self):
        from .dark_ramps import quiet_seam_error, restore_dark_ramps

        shades = np.linspace(46, 118, HEIGHT, dtype=np.float32)[:, None]
        source = np.broadcast_to((shades * [.52, .67, 1])[:, None], (HEIGHT, WIDTH, 3)).astype(np.uint8)
        y, x = np.indices(source.shape[:2])
        bits = (x + y) % 5 < (source[..., 2] / 41).astype(int)
        attrs = np.ones((ROWS, COLS), dtype=np.uint8)
        attrs[:, COLS // 2:] = 7
        baseline = pack(bits, attrs)
        old = independent_decode(baseline)
        screen, preview = restore_dark_ramps(source, (baseline, old))

        np.testing.assert_array_equal(independent_decode(screen), preview)
        self.assertTrue((preview[..., :2] == 0).all())
        self.assertGreater(preview[-24:, :, 2].mean(), preview[:24, :, 2].mean())
        cells = np.ones((ROWS, COLS), dtype=bool)
        self.assertLess(quiet_seam_error(source, preview, cells), quiet_seam_error(source, old, cells))

    def test_ramp_coverage_fits_quiet_neighbors_and_keeps_a_source_edge(self):
        from .dark_ramps import fit_ramp_coverage

        source = np.full((HEIGHT, WIDTH, 3), (25, 45, 80), dtype=np.float32)
        source[:, :64, 2] = 160
        preview = np.full_like(source, (0, 0, 50))
        ink = np.full_like(source, (0, 0, 205))
        level = np.full((HEIGHT, WIDTH), .4, dtype=np.float32)
        cells = np.zeros((ROWS, COLS), dtype=bool)
        cells[:, 8:13] = True
        adjusted = fit_ramp_coverage(level, source, preview, cells, ink)

        self.assertAlmostEqual(adjusted[64, 64], .4, delta=.01)
        self.assertLess(adjusted[64, 100], .36)

    def test_balanced_ramp_tiles_preserve_quiet_borders(self):
        from .dark_ramps import safe_ramp_tiles

        source = np.full((HEIGHT, WIDTH, 3), (12, 34, 60), dtype=np.uint8)
        before = np.full_like(source, (0, 0, 52))
        candidate = before.copy()
        candidate[0:4, 4:8, 2] = 104
        self.assertFalse(safe_ramp_tiles(source, before, candidate)[0, 4])
        source[:, :8, 2] = 112
        self.assertTrue(safe_ramp_tiles(source, before, candidate)[0, 4])

    def test_pale_highlight_removes_an_artificial_bright_boundary(self):
        from .tonal_repair import restore_pale_highlights

        ramp = np.linspace(194, 219, WIDTH, dtype=np.uint8)
        source = np.broadcast_to(ramp[None, :, None], (HEIGHT, WIDTH, 3))
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        attrs[:, COLS // 2:] |= 64
        baseline = pack(np.ones((HEIGHT, WIDTH), dtype=bool), attrs)
        screen, preview = restore_pale_highlights(source, (baseline, independent_decode(baseline)))

        np.testing.assert_array_equal(independent_decode(screen), preview)
        self.assertLess(np.abs(np.diff(preview.astype(int), axis=1)).max(), 50)

    def test_subject_tones_recover_clipped_midtone_detail_inside_the_mask(self):
        from .tonal_repair import restore_subject_tones

        y, x = np.indices((HEIGHT, WIDTH))
        mask = (y >= 40) & (y < 136) & (x >= 56) & (x < 184)
        tone = np.where(mask, np.where((x >= 112) & (x < 128), 155, 182), 205)
        source = np.repeat(tone[..., None], 3, axis=-1).astype(np.uint8)
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        baseline = pack(np.ones((HEIGHT, WIDTH), dtype=bool), attrs)
        prior = independent_decode(baseline)
        current = baseline, prior
        screen, preview = restore_subject_tones(source, current, mask.astype(np.float32))

        self.assertIs(restore_subject_tones(source, current, None), current)
        self.assertIs(restore_subject_tones(prior, current, mask.astype(np.float32)), current)
        self.assertEqual(screen[6144:], baseline[6144:])
        np.testing.assert_array_equal(independent_decode(screen), preview)
        np.testing.assert_array_equal(preview[~mask], prior[~mask])
        self.assertLess(preview[48:128, 116:124].mean(), preview[48:128, 132:140].mean() - 12)
        before = quality(source, prior)
        after = quality(source, preview)
        self.assertLess(after['pooled_rgb_rmse'], before['pooled_rgb_rmse'])
        self.assertLessEqual(after['pooled_seam_rmse'], before['pooled_seam_rmse'])

    def test_weak_subject_edge_follows_source_and_preserves_cell_colors(self):
        from .subject_edges import restore_weak_subject_edges

        y, x = np.indices((HEIGHT, WIDTH))
        mask = (y >= 48) & (y < 144) & (x >= 62) & (x < 194)
        light = np.where(mask, 104, 147).astype(np.uint8)
        source = np.repeat(light[..., None], 3, axis=-1)
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        bits = (x + y) % 3 != 1
        baseline = pack(bits, attrs)
        before = independent_decode(baseline)
        original = baseline, before

        repaired, after = restore_weak_subject_edges(source, original, mask.astype(np.float32))
        np.testing.assert_array_equal(independent_decode(repaired), after)
        self.assertEqual(repaired[6144:], baseline[6144:])
        np.testing.assert_array_equal(after[~mask], before[~mask])
        self.assertLess(after[52:140, 62].mean(), before[52:140, 62].mean() - 10)
        self.assertLessEqual(quality(source, after)['pooled_seam_rmse'], quality(source, before)['pooled_seam_rmse'])
        flat = np.full_like(source, 135)
        self.assertIs(restore_weak_subject_edges(flat, original, mask.astype(np.float32)), original)
        self.assertIs(restore_weak_subject_edges(source, original, None), original)

    def test_subject_strokes_recover_a_narrow_diagonal_inside_the_subject(self):
        from .subject_strokes import restore_subject_strokes

        y, x = np.indices((HEIGHT, WIDTH))
        mask = (x > 60) & (x < 130) & (y > 30) & (y < 145)
        line = (x == 62 + y // 3) & (y >= 38) & (y < 134)
        source = np.repeat(np.where(line, 95, 166)[..., None], 3, axis=-1).astype(np.uint8)
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        screen = pack((x + y) % 5 != 0, attrs)
        before = independent_decode(screen)
        original = screen, before

        repaired, after = restore_subject_strokes(source, original, mask.astype(np.float32))
        np.testing.assert_array_equal(independent_decode(repaired), after)
        np.testing.assert_array_equal(after[~mask], before[~mask])
        self.assertEqual(repaired[6144:], screen[6144:])
        self.assertLess(after[line].mean(), before[line].mean() - 20)
        self.assertLessEqual(quality(source, after)['pooled_seam_rmse'], quality(source, before)['pooled_seam_rmse'])
        self.assertIs(restore_subject_strokes(np.full_like(source, 166), original, mask.astype(np.float32)), original)

    def test_outline_palette_keeps_black_where_a_stroke_is_required(self):
        from .line_art import fit_outline_palette
        from .screen import to_cells

        rgb = np.full((HEIGHT, WIDTH, 3), (240, 45, 45), dtype=np.float32)
        shape = np.zeros((HEIGHT, WIDTH), dtype=bool)
        shape[32:40, 48:64] = True
        fill = shape.copy()
        fill[32:40, 55] = False
        bright = np.zeros((ROWS, COLS), dtype=np.uint8)
        cells = to_cells(shape).any(axis=(2, 3))
        attrs, coverage, paper, ink = fit_outline_palette(
            rgb, 2, bright, to_cells(shape), fill, to_cells(~shape), cells, np.full(shape.shape, .94),
        )
        self.assertEqual(attrs[4, 6], 64 | 2)
        np.testing.assert_array_equal(paper[4, 6], (0, 0, 0))
        np.testing.assert_array_equal(paper[4, 7], (255, 0, 0))
        self.assertTrue(np.all(ink[4, 7] >= paper[4, 7]))
        tint = coverage[32:40, 56:64]
        self.assertTrue(np.all((tint > 0) & (tint <= .20)))
        self.assertLess(tint[4, 0], tint[4, 4])

    def test_softer_outline_keeps_the_previous_render_if_a_strong_edge_degrades(self):
        from . import line_art

        middle = WIDTH // 2
        source = np.full((HEIGHT, WIDTH, 3), 60, dtype=np.uint8)
        source[:, middle:] = 190
        reference = (b"reference", np.zeros_like(source))
        previous = (b"previous", source - 60)
        softened_image = source.copy()
        softened_image[:, middle - 1:middle + 1] = 125
        softened = (b"softened", softened_image)

        with patch.object(line_art, "draw_outline_subjects", side_effect=(reference, previous, softened)):
            self.assertIs(line_art.outline_subjects(source, reference), previous)

    def test_outline_subjects_uses_source_hues_and_keeps_incompatible_cells(self):
        from .line_art import outline_subjects

        source = np.full((HEIGHT, WIDTH, 3), 205, dtype=np.uint8)
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        for x, hue, channels in ((32, 2, (1, .25, .12)), (112, 4, (.10, 1, .18)), (184, 1, (.12, .18, 1))):
            color = np.asarray(channels)
            source[48:112, x:x + 40] = np.arange(145, 241, 1.5)[:, None, None] * color
            source[68:91, x + 12:x + 24] = color * 100
            attrs[6:14, x // 8:x // 8 + 5] = hue
            source[48:56, x:x + 3] = 205
            source[93:103, x + 18:x + 19] = 205
            attrs[6, x // 8] = (hue << 3) | 7
        bits = np.ones((HEIGHT, WIDTH), dtype=bool)
        bits[:, :8] = False
        bits[96:, 8:16] = False
        bits[48:56, 35:40] = False
        bits[48:56, 115:120] = False
        bits[48:56, 187:192] = False
        bits[93:103, (50, 130, 202)] = False
        screen = pack(bits, attrs)
        prior = independent_decode(screen)
        outlined, preview = outline_subjects(source, (screen, prior))
        np.testing.assert_array_equal(preview, independent_decode(outlined))
        for x, channel in ((32, 0), (112, 1), (184, 2)):
            np.testing.assert_array_equal(preview[48:56, x:x + 8], prior[48:56, x:x + 8])
            self.assertGreater(np.count_nonzero((preview[74:84, x + 14:x + 21] == 0).all(axis=-1)), 45)
            self.assertGreater(np.count_nonzero(preview[93:105, x + 8:x + 32, channel]), 150)
            self.assertTrue((preview[94:102, x + 18] == 0).all())
        np.testing.assert_array_equal(preview[:48], prior[:48])

    def test_red_line_art_extracts_shapes_and_fills_shadows_black(self):
        from .line_art import red_shapes, render_red_line_art

        source = np.full((HEIGHT, WIDTH, 3), (30, 82, 91), dtype=np.uint8)
        source[48:108, 76:148] = (232, 60, 38)
        source[63:91, 100:124] = (118, 30, 18)
        source[26, 38] = (246, 50, 32)
        fill, silhouette = red_shapes(source)
        self.assertTrue(silhouette[70:84, 108:116].all())
        self.assertFalse(fill[70:84, 101:104].any())
        self.assertTrue(fill[54:58, 84:94].all())
        self.assertFalse(fill[48, 76:148].any())
        self.assertFalse(silhouette[26, 38])

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source_path, screen, preview = (folder / name for name in ("in.png", "out.scr", "out.png"))
            Image.fromarray(source).save(source_path)
            subprocess.run([sys.executable, "-m", "toolkit.zx_neural", str(source_path), str(screen),
                            "--red-line-art", "--preview", str(preview)], check=True)
            data = screen.read_bytes()
            self.assertEqual(set(data[6144:]), {66})
            decoded = independent_decode(data)
            self.assertEqual(set(map(tuple, decoded.reshape(-1, 3))), {(0, 0, 0), (255, 0, 0)})
            with Image.open(preview) as image:
                np.testing.assert_array_equal(decoded, np.asarray(image))
            shaded_screen, shaded = render_red_line_art(source, shaded=True)
            np.testing.assert_array_equal(shaded, independent_decode(shaded_screen))
            self.assertEqual(shaded_screen[6144:], data[6144:])
            self.assertTrue(np.all(shaded[..., 0] <= decoded[..., 0]))
            self.assertLess(np.count_nonzero(shaded[..., 0]), np.count_nonzero(decoded[..., 0]))

    def test_cli_and_independent_screen_decoder(self):
        source = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        source[8:56, 48:128] = (255, 0, 0)
        source[64:128, 128:208] = (0, 205, 205)
        source[128:191, 1:47] = (255, 255, 255)
        source[57, 5:250] = (255, 255, 0)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            original, screen, preview = (directory / name for name in ("in.png", "out.scr", "out.png"))
            Image.fromarray(source).save(original)
            for extra in ([], ["--mode", "hybrid"], ["--pixel-art"]):
                with self.subTest(options=extra):
                    subprocess.run([sys.executable, "-m", "toolkit.zx_neural", str(original), str(screen),
                                    "--preview", str(preview), *extra], check=True)
                    decoded = independent_decode(screen.read_bytes())
                    np.testing.assert_array_equal(decoded, source)
                    with Image.open(preview) as image:
                        np.testing.assert_array_equal(decoded, np.asarray(image))

    def test_pixel_art_fits_texture_without_changing_tile_tone(self):
        from .pixel_art import mean_rgb, refine_texture

        y, x = np.indices((HEIGHT, WIDTH))
        shade = np.where((x + y) % 2 == 0, 71, 134).astype(np.uint8)
        source = np.repeat(shade[..., None], 3, axis=-1)
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        screen = pack(y % 2 == 0, attrs)
        before = independent_decode(screen)
        lock = (x < 32)
        changed, preview = refine_texture(source, (screen, before), lock)
        np.testing.assert_array_equal(preview, independent_decode(changed))
        np.testing.assert_array_equal(before[lock], preview[lock])
        self.assertEqual(screen[6144:], changed[6144:])
        np.testing.assert_array_equal(before.reshape(HEIGHT // 2, 2, WIDTH // 2, 2, 3).sum(axis=(1, 3)),
                                      preview.reshape(HEIGHT // 2, 2, WIDTH // 2, 2, 3).sum(axis=(1, 3)))
        target = mean_rgb(source, 3)
        old_error = np.mean((mean_rgb(before, 3) - target) ** 2)
        new_error = np.mean((mean_rgb(preview, 3) - target) ** 2)
        self.assertLess(new_error, .85 * old_error)

        source[10:30, 48:64] = 255
        _, edge_preview = refine_texture(source, (screen, before), lock)
        np.testing.assert_array_equal(edge_preview[10:30, 47:49], before[10:30, 47:49])

    def test_inner_contours_move_highlights_without_changing_palette_or_shading(self):
        from .inner_contours import restore_inner_contours

        source = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        source[48:112, 48:112] = (228, 96, 63)
        source[52:108, 73:75] = (137, 47, 28)
        attrs = np.zeros((ROWS, COLS), dtype=np.uint8)
        attrs[6:14, 6:14] = (2 << 3) | 7
        bits = np.zeros((HEIGHT, WIDTH), dtype=bool)
        bits[48:112, 73:75] = True
        screen = pack(bits, attrs)
        before = independent_decode(screen)
        result, preview = restore_inner_contours(source, (screen, before))
        np.testing.assert_array_equal(preview, independent_decode(result))
        self.assertEqual(result[6144:], screen[6144:])
        self.assertLess(preview[56:104, 73:75, 1].mean(), before[56:104, 73:75, 1].mean() * .20)
        np.testing.assert_array_equal(before.reshape(HEIGHT // 4, 4, WIDTH // 4, 4, 3).sum(axis=(1, 3)),
                                      preview.reshape(HEIGHT // 4, 4, WIDTH // 4, 4, 3).sum(axis=(1, 3)))
        self.assertEqual(restore_inner_contours(source, (screen, before), np.zeros(bits.shape))[0], screen)

    def test_dark_edge_strokes_use_existing_black_without_erasing_halftones(self):
        from .inner_contours import trace_dark_edges

        source = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        source[48:112, 48:96] = (115, 41, 26)
        source[48:112, 96:144] = (229, 92, 58)
        bits = np.ones((HEIGHT, WIDTH), dtype=bool)
        attrs = np.zeros((ROWS, COLS), dtype=np.uint8)
        attrs[6:14, 6:12] = 2
        attrs[6:14, 12:18] = (2 << 3) | 7
        bits[48:112, 96:144] = (np.indices((64, 48)).sum(axis=0) % 2) == 0
        screen = pack(bits, attrs)
        prior = independent_decode(screen)
        result, preview = trace_dark_edges(source, (screen, prior), None)
        np.testing.assert_array_equal(preview, independent_decode(result))
        self.assertEqual(screen[6144:], result[6144:])
        mark = (prior != preview).any(axis=-1)
        self.assertTrue(mark[56:104, 94:96].any())
        self.assertFalse(mark[56:104, 52:90].any())
        np.testing.assert_array_equal(prior[56:104, 100:136], preview[56:104, 100:136])
        self.assertLessEqual(mark.reshape(HEIGHT // 4, 4, WIDTH // 4, 4).sum(axis=(1, 3)).max(), 2)

    def test_pixel_art_protects_smooth_ramp_and_keeps_texture_eligible(self):
        from .pixel_art import preserve_photo_details

        y, x = np.indices((HEIGHT, WIDTH))
        checker = (x + y) % 2 == 0
        shade = np.where(y < 96, 40 + x // 2, np.where(checker, 65, 165))
        source = np.broadcast_to(shade[..., None], (HEIGHT, WIDTH, 3)).astype(np.uint8)
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        photo = pack(checker, attrs)
        style = pack(~checker, attrs)
        original, stylized = independent_decode(photo), independent_decode(style)
        (screen, preview), locked = preserve_photo_details(
            source, (photo, original), (style, stylized), probability=None,
        )
        np.testing.assert_array_equal(preview, independent_decode(screen))
        np.testing.assert_array_equal(preview[:80], original[:80])
        np.testing.assert_array_equal(preview[112:], stylized[112:])
        self.assertTrue(locked[:80].all())
        self.assertFalse(locked[112:].any())

    def test_smooth_ramp_seams_and_real_edges(self):
        y, x = np.indices((HEIGHT, WIDTH))
        source = np.stack([60 + x // 2, 40 + x // 2 + y // 4, 50 + y // 2], axis=-1).astype(np.uint8)
        candidates = Candidates(source)
        layers = load_weights()
        baseline = choose(source, candidates, "baseline")
        hybrid = choose(source, candidates, "hybrid", layers)
        _, original = render(candidates, baseline)
        _, reduced = render(candidates, hybrid)
        self.assertLess(quality(source, reduced)["seam_rmse"], quality(source, original)["seam_rmse"])
        regret = np.take_along_axis(candidates.regret, hybrid[..., None], axis=-1)
        self.assertLessEqual(regret.max(), COLOR_BUDGET)
        self.assertGreater(edge_weight(np.array([.01, .01, .01])), .98)
        self.assertLess(edge_weight(np.array([.8, .6, .4])), 1e-6)

    def test_narrow_transparent_image(self):
        source = Image.new("RGBA", (1, 1000), (255, 0, 0, 128))
        native = prepare(source)
        self.assertEqual(native.shape, (HEIGHT, WIDTH, 3))
        self.assertEqual(np.count_nonzero(native[..., 0]), HEIGHT)
        self.assertEqual(native[..., 0].max(), 128)

    def test_subject_recovery_targets_a_vanished_thin_part(self):
        source = np.full((HEIGHT, WIDTH, 3), 166, dtype=np.uint8)
        probability = np.zeros((HEIGHT, WIDTH), np.float32)
        probability[40:100, 50:150] = 1
        probability[100:140, 121:127] = 1
        source[probability == 1] = 137
        visible = source.copy()
        invisible = visible.copy()
        invisible[100:140, 121:127] = 166
        target = protect_thin_parts(source, invisible, probability)
        self.assertLess(target[120, 124, 0], 110)
        np.testing.assert_array_equal(target[65, 75], source[65, 75])
        self.assertIsNone(protect_thin_parts(source, np.where(probability[..., None], 90, 166)
                                             .repeat(3, axis=-1).astype(np.uint8), probability))
        uncertain = np.full(probability.shape, .2, dtype=np.float32)
        old, _ = convert(source, "spatial", None, floyd=True)
        result, _ = convert(source, "spatial", None, floyd=True, probability=uncertain)
        self.assertEqual(old, result)

    def test_green_cells_are_restored_in_the_native_screen(self):
        bits = np.ones((HEIGHT, WIDTH), dtype=bool)
        before = np.full((ROWS, COLS), 7, dtype=np.uint8)
        before[2, 3] = 4
        after = np.full((ROWS, COLS), 7, dtype=np.uint8)
        after[2, 4] = 2
        old, candidate = pack(bits, before), pack(bits, after)
        original = np.full((HEIGHT, WIDTH, 3), (190, 190, 190), dtype=np.uint8)
        original[16:24, 24:32] = (95, 119, 73)
        corrected, preview = restore_color_accents(original, (old, independent_decode(old)),
                                                     (candidate, independent_decode(candidate)))
        np.testing.assert_array_equal(preview, independent_decode(corrected))
        np.testing.assert_array_equal(preview[16:24, 24:32], independent_decode(old)[16:24, 24:32])
        np.testing.assert_array_equal(preview[16:24, 32:40], independent_decode(candidate)[16:24, 32:40])

    def test_connected_detail_recovers_source_tone_across_cells(self):
        source = np.full((HEIGHT, WIDTH, 3), 166, dtype=np.uint8)
        foreground = np.zeros((HEIGHT, WIDTH), dtype=bool)
        foreground[40:96, 64:144] = True
        foreground[96:146, 108:114] = True
        source[foreground] = 135
        bitmap = np.ones_like(foreground)
        bitmap[112:130, 108:114] = False
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        attrs[12:19, 13:15] = 55
        attrs[14:17, 13:15] = 7
        screen = pack(bitmap, attrs)
        old = independent_decode(screen)
        mask = foreground.astype(np.float32)
        result, preview = continue_thin_parts(source, (screen, old), (screen, old), mask, mask)
        np.testing.assert_array_equal(preview, independent_decode(result))
        core = np.s_[100:140, 108:114, 0]
        self.assertLess(abs(preview[core].mean() - 135), abs(old[core].mean() - 135))
        np.testing.assert_array_equal(preview[:96], old[:96])

    def test_detail_dither_stays_inside_its_mask(self):
        source = np.full((HEIGHT, WIDTH, 3), (202, 160, 105), dtype=np.uint8)
        part = np.zeros((HEIGHT, WIDTH), dtype=bool)
        part[16:40, 27:30] = True
        source[part] = 109
        # Some background is already white and some comes from a cell
        # with a red endpoint. Both should stay solid through the refit.
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        attrs[2:4, 3] = 2
        bitmap = np.ones_like(part)
        bitmap[38, 24] = False
        screen = pack(bitmap, attrs)
        prior = independent_decode(screen)
        cells = to_cells(part).any(axis=(2, 3))
        patterns, rendered, _, _ = fit_part(source, (screen, prior), part, cells, part, -1)
        pair = np.flatnonzero(ATTRIBUTES == 7).item()
        result, preview = replace_cells((screen, prior), cells, pair, patterns, rendered)
        np.testing.assert_array_equal(preview, independent_decode(result))
        self.assertEqual(set(preview[part][:, 0]), {0, 205})
        self.assertTrue(np.all(preview[16:32, 24:27] == 205))
        np.testing.assert_array_equal(preview[32:40, 24:27], prior[32:40, 24:27])

    def test_flat_primary_shading_recovers_luma(self):
        y, x = np.indices((HEIGHT, WIDTH))
        source = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        source[..., 0] = 160 + x // 3
        shade = np.rint(28 + 20 * (1 + np.sin((x + y) / 3))).astype(np.uint8)
        source[..., 1] = shade + 16
        source[..., 2] = shade + 6
        source[32:72, 16:48] = (0, 205, 0)
        attrs = np.full((ROWS, COLS), 2, dtype=np.uint8)
        attrs[4:9, 2:6] = 4
        screen = pack(np.ones((HEIGHT, WIDTH), dtype=bool), attrs)
        before = independent_decode(screen)
        result, preview = restore_halftones(source, (screen, before))
        np.testing.assert_array_equal(preview, independent_decode(result))
        np.testing.assert_array_equal(preview[32:72, 16:48], before[32:72, 16:48])
        target = box_mean(source @ LUMA, 3)
        before_error = np.mean(abs(box_mean(before @ LUMA, 3) - target))
        after_error = np.mean(abs(box_mean(preview @ LUMA, 3) - target))
        self.assertLess(after_error, .65 * before_error)

    def test_source_gap_breaks_a_flat_join_without_changing_attributes(self):
        source = np.full((HEIGHT, WIDTH, 3), 160, dtype=np.uint8)
        source[24:104, 32:48] = 112
        source[24:104, 53:70] = 112
        probability = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
        probability[24:104, 32:70] = .9
        probability[24:104, 48:53] = .6
        bits = np.ones((HEIGHT, WIDTH), dtype=bool)
        bits[24:104, 32:70] = np.indices((80, 38)).sum(axis=0) % 2 == 0
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        screen = pack(bits, attrs)
        before = independent_decode(screen)
        result, preview = keep_open_gaps(source, (screen, before), probability)
        np.testing.assert_array_equal(preview, independent_decode(result))
        self.assertEqual(screen[6144:], result[6144:])
        self.assertGreater(preview[30:98, 48:53, 0].mean(), before[30:98, 48:53, 0].mean() + 12)
        np.testing.assert_array_equal(preview[:, :28], before[:, :28])

    def test_default_floyd_preserves_gradient_tones(self):
        x = np.broadcast_to(np.linspace(0, 1, WIDTH), (HEIGHT, WIDTH))
        source = np.stack((80 + 90 * x, 125 + 35 * x, 180 - 45 * x), axis=-1).astype(np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            original = directory / "input.png"
            Image.fromarray(source).save(original)
            decoded = {}
            for mode in ("default", "floyd", "solid"):
                output = directory / f"{mode}.scr"
                flag = [] if mode == "default" else [f"--{mode}"]
                subprocess.run([sys.executable, "-m", "toolkit.zx_neural",
                                str(original), str(output), *flag], check=True)
                decoded[mode] = independent_decode(output.read_bytes())
        np.testing.assert_array_equal(decoded["default"], decoded["floyd"])
        self.assertLess(quality(source, decoded["default"])["pooled_rgb_rmse"],
                        quality(source, decoded["solid"])["pooled_rgb_rmse"])

    def test_adaptive_dither_preserves_hard_edge_pixels_and_legal_screen(self):
        source = np.full((HEIGHT, WIDTH, 3), 112, dtype=np.uint8)
        source[47:52] = 255
        candidates = Candidates(source)
        black_white = np.flatnonzero(ATTRIBUTES == 0x47)[0]
        labels = np.full((ROWS, COLS), black_white)
        _, original = render(candidates, labels)
        dither = DitherCandidates(candidates)
        screen, dithered = render(dither, labels)
        np.testing.assert_array_equal(independent_decode(screen), dithered)
        np.testing.assert_array_equal(original[46:53], dithered[46:53])
        self.assertLess(quality(source, dithered)["pooled_rgb_rmse"],
                        quality(source, original)["pooled_rgb_rmse"])

    def test_brightness_step_removed_on_ramp_but_kept_at_real_edge(self):
        ramp = np.linspace(218, 240, 32).round().astype(np.uint8)
        source = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        source[8:16, :32] = ramp[None, :, None]
        source[32:40, :16] = 205
        source[32:40, 16:32] = 255
        candidates = Candidates(source)
        labels = candidates.unary.argmin(axis=-1)
        _, before = render(candidates, labels, repair=False)
        screen, after = render(candidates, labels, repair=True)
        self.assertEqual(set(before[8, :32, 0]), {205, 255})
        self.assertEqual(len(set(after[8, :32, 0])), 1)
        np.testing.assert_array_equal(after[32:40], before[32:40])
        np.testing.assert_array_equal(independent_decode(screen), after)


if __name__ == "__main__":
    unittest.main()
