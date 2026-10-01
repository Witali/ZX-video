# Optional soft contours before monochrome dithering

2026-10-01. Baseline `0cbfa17`. The user asked whether object outlines can
improve distinguishability. This is a bounded host prototype and visual
comparison; the existing monochrome TRD and converter defaults are unchanged.

## Method

Detect edges in the **original RGB image**, before discarding colour or
applying dither. This retains boundaries whose colours have similar luma.
Looking for edges in the dithered image would also detect the dot pattern.
The detector finds image edges, not semantic objects; shadows, leaves and
texture can be included, and some object boundaries can remain undetected.

Two candidates were measured, with one follow-up specifically addressing
the first candidate's texture amplification and row-dictionary overflow:

| Parameter | Initial, rejected | Soft candidate |
| --- | --- | --- |
| Gaussian smoothing | 5x5, sigma 0.9 | 7x7, sigma 1.4 |
| Multichannel Canny thresholds | 60 / 120 | 100 / 200 |
| Minimum connected component | 6 samples | 12 samples |
| Darkening | One quantized shade | 24/255 luma before quantization |

The soft version alters at most one output shade and only on the detected
line, approximately one logical sample (two physical pixels) wide. Constant
black/BRIGHT-white attributes, five coverages and fixed dither phase remain.
Letterbox bands are excluded from edge detection so that they do not create
false outlines. No frame-adaptive thresholds or new temporal history are used.

All contour work runs on the conversion PC. The Spectrum receives ordinary
CB41/LZSA2 data; it does not execute an edge detector or an extra drawing pass.
Data changes can still increase decoding, screen-write and disk costs.

## Measured results

Reuse the authenticated 256-frame monochrome preview. Three 32-frame
windows start at local 0, 64, 160 (prepared movie 4128, 4192, 4288). Each
starts with the same two preceding baseline screens where available, then
carries the candidate through the window. No full disk variants were built.

The initial candidate changes 11.25–19.11% of samples and strongly outlines
foliage as well as the character. Its row dictionaries require 210 / 342 /
282 entries, exceeding the native 256-entry limit in two windows. The only
encodable window grows from 9563 to 18810 bytes. Reject this candidate;
do not summarize the incomplete compression results as a whole-stream ratio.

| All 96 frames, soft candidate | Baseline | Soft contours |
| --- | ---: | ---: |
| Mean luma MSE | 337.197 | 368.405 (+9.26%) |
| LZSA2 window bytes | 58241 | 61369 (+5.37%) |
| Mean output component T-states | 113522.833 | 116020.792 (+2.20%) |
| Maximum output component T-states | 203692 | 204075 |
| Row dictionary entries per window | 95 / 158 / 117 | 111 / 171 / 140 |

Only **2.11% of active logical samples** change on average. Inspected frames
4138, 4202 and 4298: the character outline is more visible, with much less
texture tracing than the rejected version. This is a visual observation,
not an object-recognition score. Dark contours may still lose shadow detail.
Frame-to-frame mask changes are saved, but include real motion and are not
a motion-compensated flicker metric.

All 192 baseline/candidate native draws match their exact expected screens
(1327104 bytes), with instruction timings, registers, stack, tables and
inactive-bank guards checked. Twelve endpoint frame checks use a second
Z80 emulator. Eight quantizer/contour tests pass, including an equal-luma
colour boundary, constant fills, weak texture and deterministic output.

Native code is identical: **0 T instruction delta**, unchanged book loading
**54028 -> 54028 T**. Output work increases by **2497.958 T/frame** on
average because the payload changes. Component timings exclude LZSA2,
packet copies, paging, IRQ/ULA, TR-DOS and physical disk latency. No new
full-player timing or whole-volume row-capacity gate was run. The existing
monochrome disk's two late frames cannot be assumed to remain unchanged.

## Decision and visual comparison

Keep the soft selector as an optional experiment. Reject automatic strong
outlines. Full-volume row capacity and complete Fuse timing/AY/screens must
be measured before publishing a disk with the selected contours. Neither
candidate is enabled by default or added to the current TRD in this task.

- [Static source / baseline / soft comparison](monochrome_contours_evidence/soft-preview.png)
- [Animated baseline / soft comparison](monochrome_contours_evidence/comparison.gif)
- [Rejected strong comparison](monochrome_contours_evidence/strong-preview.png)
- [Metrics and archive hashes](monochrome_contours_report.json)

The animation is 32 host-rendered frames at nominal 10 fps, showing movie
frames 4288–4319. Its pixel/timing timeline is checked after GIF decoding.
It is not a recording or timing measurement of the Spectrum player.

## Reproduction

Use the existing Python environment and the saved monochrome build inputs:

```powershell
$env:PYTHONPATH='local_tools/python_packages;.tmp/lzma-z80-packages;toolkit'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest toolkit.test_monochrome_contours toolkit.test_monochrome_five_level
python toolkit/probe_monochrome_contours.py --baseline .tmp/cb41-monochrome-preview --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --output .tmp/monochrome-contours-soft --preset soft
python toolkit/profile_cell_palette_quality.py --work .tmp/monochrome-contours-soft --variants baseline contours
```

`--preset strong` reproduces the first candidate's algorithm. The evidence
archive also keeps its original source snapshots and report hashes, all
window RGB inputs/history states, raw/packed streams, row tables, per-frame
metrics, native traces, passing test output and the successful soft sources.
`archive_monochrome_contours.py` checks identities and creates the animation.
