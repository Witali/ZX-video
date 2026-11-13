"""Check the shipped model, screen layout, and boundary-specific behavior."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from .__main__ import choose, render
from .evaluate import independent_decode, quality
from .model import load_weights
from .objective import COLOR_BUDGET, Candidates, edge_weight
from .screen import HEIGHT, WIDTH, prepare


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


if __name__ == "__main__":
    unittest.main()
