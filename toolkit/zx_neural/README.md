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

By default the renderer uses edge-aware Floyd–Steinberg error diffusion
after a joint palette search. Use `--solid` for the previous output
without dithering, `--dither` for the previous ordered mode, or
`--smooth` for joint palette search with ordered dots.

Use `--pixel-art` for a more graphic rendering. It uses a 64-channel
CNN trained in FP32 on a palette objective that penalizes chromatic
grain. Joint palette search still enforces the Spectrum constraints.
Floyd–Steinberg sets the shading. The final pass fits the pattern of
each 2×2 tile to the source texture while preserving its average color.
It scores both the native pixels and nearby 3×3 averages and protects
strong source edges. The converter retains accurately represented color
accents and can keep details
inside the detected silhouette when `--subject-model` is supplied.
Smooth gradients retain the photo renderer's palette and fine diffusion.
The converter detects these regions by measuring source texture after
subtracting a local average, so shallow ramps can keep their shading.

The default Floyd–Steinberg and `--pixel-art` modes automatically recover
dark interior contours in saturated objects. The converter finds narrow
dark lines in the source, puts the darker palette endpoint along them,
and moves the displaced highlight to a brighter pixel of the same hue
within the 4×4 tile. This preserves the palette and local color balance.
An optional subject model restricts contour recovery to the subject and
its immediate boundary.
When a transition loses contrast in the screen preview, the converter
traces the dark side of the source brightness or saturation change.
It can place up to two extra black pixels per 4×4 tile
when the cell's existing pair includes black and the source supports the
stroke. It keeps the light endpoint in cells that use it for halftones.
See [contour measurements](evidence/inner-contours.json) for the
initial comparison and [dark edge measurements](evidence/dark-edge-strokes.json)
for the follow-up on thin boundaries.

Use `--red-line-art` to extract red objects as a black and red drawing.
The converter finds the silhouette from source color and optionally
the subject model, traces internal edges and fills deep shadows in black.
Add `--shade-line-art` for Floyd–Steinberg transitions inside the fill.
The outer contour and deep shadows stay solid in both versions.
The native screen uses a black background and a shared black/red pair.

The standard Floyd–Steinberg and `--pixel-art` modes apply a related
treatment in place when a colored object has a supported outline and
clear shadows. The converter checks for a compatible color in the
existing render. It keeps surrounding pixels exact when changing the
cell's pair and rejects a result that adds too much grid error. It
can use the optional subject mask and accepts all six Spectrum hues.
With `--pixel-art`, a fine-tuned 64-channel model provides a bounded
preference for the outline palette. The pixel mask and neighboring
color checks still determine where the selected pair can be used.
Closing gaps in the detected outline never extends the color fill.
Only pixels with matching source color evidence receive new color.

```powershell
python -m toolkit.zx_neural.train --pixel-art --outline --initialize toolkit/zx_neural/weights64-pixel-art.npz --channels 64 --epochs 50 --device cuda --workers 4 --clic-root $clic --bsds-archive $archive --weights .tmp/neural-screen/outline-trained.npz --report .tmp/neural-screen/outline-training.json
```

```powershell
python -m toolkit.zx_neural input.jpg drawing.scr --preview drawing.png --red-line-art --shade-line-art --subject-model .tmp/neural-screen/u2netp.onnx
```

```powershell
python -m toolkit.zx_neural input.jpg art.scr --preview art.png --pixel-art --subject-model .tmp/neural-screen/u2netp.onnx
```

Pixel-art training combines the 100 crops from 30 CLIC photographs
with two views from each of 90 BSDS500 training photographs and 32
synthetic screens. Six CLIC and ten BSDS500 validation photos select
the checkpoint. The same 26 holdout photos used for the earlier
photo converter are used for comparison.

```powershell
python -m toolkit.zx_neural.train --pixel-art --channels 64 --epochs 60 --device cuda --workers 4 --clic-root $clic --bsds-archive $archive --weights .tmp/neural-screen/pixel-art-trained.npz --report .tmp/neural-screen/pixel-art-training.json --cache .tmp/neural-screen/pixel-art-teacher.npz
```

See [training measurements](evidence/pixel-art.json) for the effect of
the newly trained weights and [gradient measurements](evidence/pixel-art-gradients.json)
for the comparison after adding the smooth-gradient guard.
See [texture measurements](evidence/pixel-art-texture.json) for the
comparison after replacing dot clustering with source-aware pattern fitting.

```powershell
python -m toolkit.zx_neural.compare_pixel_art .tmp/neural-screen/pixel-art-evaluation.json --clic-root $clic --bsds-archive $archive --subject-model .tmp/neural-screen/u2netp.onnx
```

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
error of its cell (RGB channels normalized to 0…1) during the initial
pair selection. The final dithered search uses a separate cost.

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
offers a similar reduction and takes longer. This comparison uses the
solid renderer. The evaluation sources were excluded from training and checkpoint
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

## Smooth color transitions

The new palette search uses up to 13 candidates per cell and alternates
row and column optimization for up to three passes. Each strip is solved
with dynamic programming while its neighbors are held fixed. The cost
compares 4×4 mean colors and dot contrast on opposite sides of each seam.
A soft penalty also favors matching pair endpoints on smooth source
transitions. Source edges increase the local pixel fidelity weight and
gradually reduce dithering. Cells that can reproduce the source exactly
retain only exact candidates.

The default then scans the whole image in alternating directions with
Floyd–Steinberg weights 7/16, 3/16, 5/16 and 1/16. It transfers the
component of the quantization error that the receiving pair can represent.
The local contrast limits diffusion near real edges. The search uses
ordered patterns to estimate the pair costs, so it does not guarantee
that the final error-diffused bitmap has the same seam score.

Reproduce the comparison with the same photos as the width experiment:

```powershell
python -m toolkit.zx_neural.compare_gradients .tmp/neural-screen/gradients-clic --clic-root $clic
python -m toolkit.zx_neural.compare_gradients .tmp/neural-screen/gradients-bsds --bsds-archive "$work/BSDS500-mirror.zip"
```

The command writes side-by-side sheets, final SCRs for both new modes,
and per-photo metrics. It independently decodes each SCR before
measuring it. See [CLIC results](evidence/gradients/clic.json) and
[BSDS results](evidence/gradients/bsds.json).

## Automatic subject contours

Pass `--subject-model` with the local U²-NetP ONNX weights to protect
low-contrast silhouettes during conversion. The detector finds salient
regions automatically from the source photo. A candidate pass increases
local brightness separation for thin parts that disappeared in the
first render. Another pass can draw a one-pixel contour where the other
color in the existing pair improves the boundary. Both passes use the
original source and the predicted silhouette. There are no object-specific
rules or hand-drawn masks in the converter.

For a narrow connected detail spanning several cells, the converter
also tests a common pair across those cells. It keeps the source
shading in the interior and adds a small contrast increase on the
inside edge. Only pixels inside the detected detail receive the new
dither pattern. Outside it, the converter keeps existing colors that
the pair can represent and maps incompatible colors to one of its
endpoints using the source and the previous render. The pass accepts a
pair only if the detail's local tone gets closer to the photo, weak
contrast is retained or improved, and the extra grid error stays bounded.
Cells with faithfully reproduced color accents are protected.

The subject pass also checks narrow background openings between darker
source edges. Small openings may be partially filled by the predicted mask.
The converter uses the source brightness and the surrounding saliency to
recover these gaps by changing individual pixels within the existing pair.

With Floyd–Steinberg enabled, the final render can recover shades in
primary-colored areas that lost source brightness variation. It fits a
compatible highlight and contains diffusion within the detected color
region. A proposal must improve the local color fit and stay within the
grid error budget. This pass works with or without the subject model.

The converter restores baseline cells that lose a correctly represented
dominant source channel. It accepts an adjusted screen only when its
silhouette contrast improves, its pooled seam error stays within the
allowed increase, and important saturated patches remain visible.
Strong accents can still limit how much of a contour can be recovered.
The model can also miss subjects or include parts of the background.

Install the optional runtime and download the pinned model once. The
command verifies its SHA-256 before loading it. Inference uses CPU
ONNX Runtime and reads only the local input photo.

```powershell
python -m pip install "onnxruntime==1.32.0"
New-Item -ItemType Directory -Force .tmp/neural-screen
curl.exe --fail --location --output .tmp/neural-screen/u2netp.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx
python -m toolkit.zx_neural input.jpg output.scr --preview output.png --mode hybrid --weights toolkit/zx_neural/weights64-clic.npz --subject-model .tmp/neural-screen/u2netp.onnx
```

Add the same `--subject-model` argument to `compare_gradients` to
compare the standard Floyd–Steinberg render with automatic contour
recovery. The experiment uses the same six CLIC and 20 BSDS photos
as the gradient comparison. The model weights are 4,574,861 bytes
and come from the [rembg distribution](https://github.com/danielgatis/rembg)
of [U²-NetP](https://github.com/xuebinqin/U-2-Net).
See [CLIC results](evidence/subjects/clic.json) and
[BSDS results](evidence/subjects/bsds.json).
The follow-up compares those screens against the continuity pass.
See [the follow-up measurements](evidence/subjects/continuity.json).
See [the detail dither measurements](evidence/subjects/bounded-dither.json)
for the comparison after restricting the pattern to the detail mask.
See [the shading and gap measurements](evidence/subjects/detail-shading.json)
for the comparison against that version.
