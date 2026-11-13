# Neural ZX Spectrum screen converter

Convert a still image to a standard 256×192 Spectrum screen on a PC. The
output is a 6,912-byte `.scr` with the original bitmap layout and one
INK/PAPER pair and shared BRIGHT per 8×8 cell. FLASH is disabled.

Run from the repository root with Python, NumPy and Pillow:

```powershell
python -m pip install "numpy>=1.26" "Pillow>=10"
python -m toolkit.zx_neural input.jpg output.scr --preview output.png
python -m toolkit.zx_neural input.jpg hybrid.scr --preview hybrid.png --mode hybrid
```

The preview is an exact RGB rendering of the screen. The default fits the
whole image on a black canvas. Use `--crop` to fill the 4:3 screen. Alpha
is composited on black and EXIF orientation is honored. The checked-in
weights are loaded automatically. PyTorch is only used when training.

| Mode | Pair selection |
| --- | --- |
| `spatial` (default) | Rank pairs by local color error and refine the best eight against neighbors |
| `hybrid` | Rank pairs with the trained network and refine the best eight against neighbors |
| `neural` | Neural prediction with the same hard color error budget |
| `spatial-full` | Spatial refinement with all legal pairs inside the color error budget |
| `baseline` | Independent best-fit pairs |

The converter enumerates 56 unordered pairs (28 per brightness). Equal
colors are representable by using just one endpoint of a pair. RGB distances
use channel weights 0.25/0.60/0.15 and up to 1.75× weight at local source
edges. A candidate may add at most 0.006 to the best mean weighted squared
error of its cell (RGB channels normalized to 0…1).

The CNN sees four quadrant means and four edge means of each cell, exact
local color fits, and coarse estimates of seams against the baseline
neighbors. Two 3×3 convolutions give a 5×5-cell receptive field. A 1×1
convolution predicts corrections to the local scores. Training targets
come from five sweeps of a search that compares all eight aligned pixels on
either side of a seam. This loss penalizes the difference between the
rendered color step and the source color step, weighted towards areas
that are smooth in the source. The training loss gives more weight to
cells where changing pairs can reduce that penalty. The shortlist always
keeps the best local pair. Spatial and hybrid inference start at those best
local pairs and run two sweeps of the exact seam search over the shortlist.
They compare even and odd cells separately so each accepted edit lowers the
local-plus-seam objective.

To reproduce the training run and comparison:

```powershell
python -m pip install "numpy==2.5.4" "Pillow==13.0.0" "scikit-image==0.25.2"
python -m pip install "torch==2.15.0" --index-url https://download.pytorch.org/whl/cpu
New-Item -ItemType Directory -Force .tmp/neural-screen
$env:OPENBLAS_NUM_THREADS = "1"
python -m toolkit.zx_neural.train --weights .tmp/neural-screen/weights.npz --report .tmp/neural-screen/training.json
python -m toolkit.zx_neural.evaluate .tmp/neural-screen/evaluation --weights .tmp/neural-screen/weights.npz
python -m unittest toolkit.zx_neural.test_converter
```

The 192 training images comprise eight views each of ten photographs and
ten Expedition 33 illustrations, plus 32 generated scenes. Two distinct
sources select the checkpoint. Seven other sources supply the evaluation.
The complete split is in [corpus.py](corpus.py). The photographs come from
[scikit-image sample data](https://scikit-image.org/docs/0.25.x/api/skimage.data.html).
The project artwork requires its Git LFS objects for training and evaluation.
The retained CPU run used seed 433, 80 epochs and the best checkpoint
from epoch 6. The network has 50,296 parameters and the compressed float32
weights occupy 187,628 bytes. The inference check compares NumPy and
PyTorch logits on both validation images.

Seam RMSE measures the error in the RGB step across a cell boundary, giving
more weight to smooth source regions. Strong-edge RMSE measures the same
error at source pixel edges whose largest channel step is at least 30% of
the full range. RGB RMSE measures whole-screen per-pixel error. The evaluation
exports a comparison sheet, per-source metrics and independently decoded
previews for all five conversion modes.

On the seven evaluation images, the final comparison gives the following
mean values. Each timing is the mean of per-image medians of three CPU
measurements, including palette scoring, inference where applicable, and
screen encoding. File I/O and image loading/resizing are excluded.

| Mode | Seam RMSE | RGB RMSE | Strong-edge RMSE | Time (ms) |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 33.31 | 47.39 | 79.91 | 32 |
| Spatial | 29.87 | 47.52 | 79.61 | 94 |
| Spatial full | 29.86 | 47.52 | 79.61 | 191 |
| Neural | 33.43 | 47.39 | 79.93 | 89 |
| Hybrid | 29.87 | 47.52 | 79.61 | 110 |

Spatial refinement reduces seam RMSE by 10.3% on this set, with a 0.27%
increase in RGB RMSE and a 0.38% decrease in strong-edge RMSE. The hybrid
offers a similar reduction and takes longer. The default uses the spatial
shortlist. The evaluation sources were excluded from training and checkpoint
selection, and reused across the exploratory comparisons. The sample size
and visible posterization in the photos limit generalization. See the
[training report](evidence/training.json),
[per-source comparison](evidence/evaluation.json) and
[earlier trials](evidence/trials.json).
