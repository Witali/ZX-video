"""Check the shipped model, screen layout, and boundary-specific behavior."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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

    def test_pixel_art_groups_dots_without_changing_tile_tone(self):
        from .pixel_art import cluster_pixels

        y, x = np.indices((HEIGHT, WIDTH))
        source = np.full((HEIGHT, WIDTH, 3), 102, dtype=np.uint8)
        attrs = np.full((ROWS, COLS), 7, dtype=np.uint8)
        screen = pack((x + y) % 2 == 0, attrs)
        before = independent_decode(screen)
        lock = (x < 32)
        changed, preview = cluster_pixels(source, (screen, before), lock)
        np.testing.assert_array_equal(preview, independent_decode(changed))
        np.testing.assert_array_equal(before[lock], preview[lock])
        np.testing.assert_array_equal(before.reshape(HEIGHT // 2, 2, WIDTH // 2, 2, 3).sum(axis=(1, 3)),
                                      preview.reshape(HEIGHT // 2, 2, WIDTH // 2, 2, 3).sum(axis=(1, 3)))
        self.assertLess(np.count_nonzero(np.diff(preview, axis=0)), np.count_nonzero(np.diff(before, axis=0)))

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
