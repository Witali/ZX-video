# Joint colour and dither coverage with monochrome error bounds

2026-10-01. Baseline `756ecd0`. The user requested colour that brings the
picture closer to the source, with dither chosen again for the selected
colours. This is a completed bounded prototype, not a new disk release.

## Method and meaning of the guarantee

For each 8x8 physical cell, evaluate all 56 canonical PAPER/INK/BRIGHT pairs,
including normal white. For each pair, search all five coverages separately
for every logical 2x2 sample: 0/25/50/75/100%. The density is recomputed from
the source RGB, rather than retaining the monochrome density after changing
the endpoints. Fixed dither phase and the existing five-pattern ABI remain.

For coverage `q`, the average is `PAPER + q*(INK-PAPER)`. The within-pattern
RGB variance is `q*(1-q)*mean((INK-PAPER)^2)`. This distinguishes a close
average colour from a high-contrast mixture of very different dots.

The reference is the monochrome quantization of the **same scaled source**.
The selected candidate enforces:

1. Each logical 2x2 sample has no higher average RGB MSE than monochrome.
2. Each sample has no higher physical RGB MSE under the model where the
   source sample is constant over its 2x2 footprint. This error equals
   average RGB MSE plus within-pattern variance. Variance alone is not
   individually bounded, although its measured average decreases.
3. Summed Rec.709 luma error in each character cell is no higher than
   monochrome. Individual samples may trade brightness error within that
   cell; this is not a pointwise luma guarantee.

The initial candidate applied condition 3 per sample too. That retained
little colour in many scenes. One targeted follow-up uses the cell-wide
luma bound while keeping both pointwise RGB bounds. Its search objective
is RGB MSE + 2*luma MSE + 0.03*pattern variance. A previous colour pair is
retained only within 4 score units/sample of the best eligible pair.
The exact monochrome state is always an explicit feasible fallback.

This is a bounded search, not an exhaustive optimizer over all combinations
of sixteen five-level samples. Every selected output is checked against the
three bounds. Bounds use encoded RGB and the project's 205/255 Spectrum
palette model; they are not perceptual percentages, calibrated display
measurements or guarantees against unsampled high-resolution source detail.
Contours and global contrast stretching are not applied in this experiment.

## Results on four cached 32-frame windows

Prepared movie starts: 0, 704, 3392, 4288. Source/chunk hashes are checked.
Each method includes two source-derived histories where available. Joint
palette history starts there; this is not a full-movie temporal-history run.

| Active image, 128 frames | Old colour | Monochrome reference | Joint colour/coverage |
| --- | ---: | ---: | ---: |
| Mean average RGB MSE | 638.461 | 1218.566 | **584.912** |
| Mean luma MSE | 455.836 | 372.521 | **240.085** |
| Mean physical RGB MSE in the stated model | 10139.957 | 12024.326 | **9605.304** |
| Mean pattern variance | 9501.496 | 10805.760 | **9020.392** |
| Cell-boundary residual MSE | 466.763 | 300.853 | **493.336** |
| LZSA2 window bytes | 39467 | 44018 | **52489** |

Average RGB error falls **52.00% versus monochrome**, and **8.39% versus
old colour**. The strict pointwise-luma candidate was more conservative;
both attempts, parameters and per-frame results are archived. All selected
pointwise RGB/physical-RGB and cell-luma checks pass on all 128 frames.
The old colour output is a comparison, not the reference for these guards:
some cells and windows can have higher RGB error than that older colour path.

**Spatial boundaries remain a limitation.** Their residual-error proxy
increases versus both references despite the better colour and luma errors.
Inspection of frames 10, 714, 3402 and 4298 confirms more appropriate tones
in some regions, but visible cell transitions and chromatic dither remain.
Do not present these error bounds as a guarantee that every region looks
better. The hardware still shares only two colours/BRIGHT across an 8x8 cell.
Keep neutral output where no eligible colour pair helps; colour restoration
is partial, not arbitrary full-colour reproduction.

Solid black coverage stays 8.29% versus monochrome. BRIGHT-white coverage
changes 11.36 -> 10.01%; normal white adds 3.54%. These are active logical
sample areas, not counts of physical white/black dots. No extra endpoint
boost is used to reverse a source-error improvement.

## Cost and verification

Window bytes increase **19.24% versus monochrome**, or **32.99% versus old
colour**. Row dictionaries use 64/105/91/133 entries and fit the 256-entry
limit locally; this does not prove whole-volume capacity or disk count.

Native code/format are unchanged (**0 T instruction delta**, book loader
**54028 -> 54028 T**). Data-dependent CB41 output mean rises from
**88292.625 to 93924.086 T/frame**, +5631.461 T (**6.38%**). Sample maximum
changes from 199451 to 217610 T. These are output-component timings, excluding
LZSA2, packet copies, paging, IRQ/ULA, TR-DOS and drive latency.

All 256 baseline/joint native draws and 1769472 screen bytes match. Every
executed instruction timing and memory/register guard passes; 16 endpoint
frame checks use an independent emulator. Nine tests cover colour recovery,
all five gray levels, normal white, stale palette rejection, both luma bounds
and the physical-error identity against expanded pixels. The comparison GIF
is decoded and checked pixel-for-pixel on its complete 100-ms timeline.

## Decision and next gate

Retain the cell-luma version as the preferred **optional prototype** for
source-faithful colour/coverage selection. Do not enable it by default or
replace the current TRDs: block boundaries and the byte/CPU cost remain
material. The next bounded step is to constrain boundary error within the
same RGB bounds, then verify the chosen whole-volume row capacity and complete
Fuse timing/AY/screens. No full-player timing claim follows from this probe.

- [Source / monochrome / old colour / joint comparison](faithful_colour_evidence/selected-preview.png)
- [Animated monochrome / joint comparison](faithful_colour_evidence/comparison.gif)
- [Summary and authenticated archive index](faithful_colour_report.json)
- [Encoder](faithful_colour.py), [tests](test_faithful_colour.py)

The GIF shows host-rendered movie frames 4288–4319, not an emulator timing
recording. Defaults, root disk images, frame cadence and AY are unchanged.

## Reproduce

```powershell
$env:PYTHONPATH='local_tools/python_packages;.tmp/lzma-z80-packages;toolkit'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest toolkit.test_faithful_colour toolkit.test_monochrome_five_level
python toolkit/probe_faithful_colour.py --prepared .tmp/cb41-10fps-movie/prepared/preparation.json --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --output .tmp/faithful-colour-cell --luma-guard cell
python toolkit/profile_cell_palette_quality.py --work .tmp/faithful-colour-cell --variants baseline joint
```

`--luma-guard sample` reproduces the initial stricter constraint. Its original
source snapshots are also archived. `archive_faithful_colour.py` preserves
both attempts, RGB/state windows, streams, native checks and source hashes,
and creates the checked animation. The final rerun reused compressed blocks
after clarifying the module's guarantee documentation; it was not a new
parameter search or disk-image sweep.
