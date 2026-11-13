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
from .model import load_weights
from .objective import COLOR_BUDGET, Candidates, edge_weight
from .screen import ATTRIBUTES, COLS, HEIGHT, ROWS, WIDTH, pack, prepare
from .subject import protect_thin_parts, restore_color_accents
from .subject_continuity import continue_thin_parts


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
            for extra in ([], ["--mode", "hybrid"]):
                with self.subTest(options=extra):
                    subprocess.run([sys.executable, "-m", "toolkit.zx_neural", str(original), str(screen),
                                    "--preview", str(preview), *extra], check=True)
                    decoded = independent_decode(screen.read_bytes())
                    np.testing.assert_array_equal(decoded, source)
                    with Image.open(preview) as image:
                        np.testing.assert_array_equal(decoded, np.asarray(image))

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
