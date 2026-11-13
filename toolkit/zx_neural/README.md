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

## FP32 width comparison on CLIC photographs

The wider CNN has 64 hidden channels and 118,968 parameters. To run the
checkpoint trained on the RTX 5060 Ti or the distilled 32-channel model:

```powershell
python -m toolkit.zx_neural input.jpg wide.scr --preview wide.png --mode hybrid --weights toolkit/zx_neural/weights64-clic.npz
python -m toolkit.zx_neural input.jpg small.scr --preview small.png --mode hybrid --weights toolkit/zx_neural/weights32-distilled.npz
python -m toolkit.zx_neural input.jpg dither.scr --preview dither.png --mode hybrid --weights toolkit/zx_neural/weights64-clic.npz --dither
```

The optional dither mode compares each pair after applying ordered dithering
to suitable smooth 4×4 tiles. It protects pixels at sharp source edges from
the dot pattern. Pair selection compares averaged RGB and dot contrast on
both sides of each 8×8 boundary for six sweeps, under a separate 0.022
weighted color budget. Dithering changes the available color fits and may
choose different attributes. The RGB and seam metrics averaged over 4×4
tiles describe changes in tone and the underlying grid. Pixel-level
metrics still include every visible dot. Some scenes retain false block
edges and the optional mode can increase strong-edge error.

The photo corpus is the same CLIC 2020 Professional Validation archive
used by the block-palette-compression benchmark. Its SHA-256 is
`e56568e20ead6bd215b313fed260d1c98b9ba863540039f00892ab67b1e39baf`.
The 42 full photos are split by decoded pixel hash into 30 for training,
6 for validation, and 6 for evaluation. Training uses 100 distinct
4:3 crops and 32 generated examples. Expedition 33 artwork is a visual
reference and was outside this training run. External checks use 20
photos from the BSDS500 test split. Source hashes and crop coordinates
are recorded in [width trial evidence](evidence/widths/).
See [CLIC data and license](https://archive.compression.cc/2021/tasks/index.html)
and the [BIDS BSDS500 mirror](https://github.com/BIDS/BSDS500).

Use the extracted CLIC corpus for reproduction. The CUDA run used the
PyTorch 2.15.0 cu132 build and disabled TF32 for convolutions and matrix
multiplication. The CPU build can run the same experiment with
`--device cpu`. NumPy inference runs on the CPU with either checkpoint.

```powershell
$clic = "../block-palette-compression/.benchmark-corpus/clic2020-professional-valid"
$work = ".tmp/neural-screen"
New-Item -ItemType Directory -Force $work
$env:OPENBLAS_NUM_THREADS = "1"
$common = @("--clic-root", $clic, "--device", "cuda", "--workers", "4", "--cache", "$work/clic.npz")
python -m toolkit.zx_neural.train --channels 64 @common --weights "$work/wide.npz" --report "$work/wide.json"
python -m toolkit.zx_neural.train --channels 32 @common --weights "$work/narrow.npz" --report "$work/narrow.json"
python -m toolkit.zx_neural.train --channels 32 @common --teacher "$work/wide.npz" --weights "$work/distilled.npz" --report "$work/distilled.json"
python -m toolkit.zx_neural.compare_widths "$work/comparison" --clic-root $clic --wide "$work/wide.npz" --retrained "$work/narrow.npz" --distilled "$work/distilled.npz" --training-report toolkit/zx_neural/evidence/training.json --training-report "$work/wide.json" --training-report "$work/narrow.json" --training-report "$work/distilled.json"
```

The same comparison can be run with `--bsds-archive` in place of
`--clic-root`. The BSDS mirror revision and download URL are pinned in
[photo_corpus.py](photo_corpus.py). The comparison writes exact
`.scr` files, decoded previews, side-by-side sheets and per-photo metrics.
The student uses an equal mixture of the original target loss and the
teacher's soft pair probabilities with temperature 2 and the usual
temperature-squared loss factor.

Spatial and hybrid conversion also repair false BRIGHT steps between
solid cells of the same hue. The repair joins cells only where the
source varies by at most 32 RGB levels within each cell and by at most
24 across the seam. A joined region may use one common brightness if
every changed cell stays within 0.017 extra weighted RGB squared error
(normalized channels) of its initial solid color. The repair removes
the white island in the CLIC coast photo. It can flatten a smooth
gradient because standard SCR has separate normal and bright
attributes. Use `--no-brightness-repair` in the comparison script to
reproduce the original width results below.
See [before and after measurements](evidence/widths/brightness-repair.json).

On six CLIC and 20 external BSDS photos, the hybrid seam RMSE is
26.167 / 30.954 for the original 32-channel model, 26.146 / 30.925
for 64 channels, and 26.150 / 30.929 for the distilled student.
The spatial algorithm without the network reaches 26.167 / 30.950.
The wider model lowers the network-only seam RMSE from 30.554 / 36.949
to 29.670 / 35.966 relative to the narrow model trained on the same crops.
Most of that difference disappears after the spatial refinement.

The joint dither search lowers pooled seam RMSE from 18.669 / 23.984
to 17.667 / 20.720 and pooled RGB RMSE from 38.445 / 45.261 to
30.678 / 33.065. Pooled seam RMSE improves on 3 of 6 CLIC and 19 of 20
BSDS photos. Pixel seam RMSE and strong-edge error increase. Individual
failures remain visible on smooth water and shadow transitions.
See the [CLIC results](evidence/widths/clic-comparison.json) and
[external results](evidence/widths/bsds-comparison.json).

In a paired FP32 run using the same cached inputs, four CPU threads
took 25.84 s for the 64-channel optimization loop and the RTX 5060 Ti
took 10.26 s. Separately, four preparation workers reduced cold
preparation from 42.37 s to 18.44 s and produced byte-identical arrays.
These timings exclude dependency installation and report export.
