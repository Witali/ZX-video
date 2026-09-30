# Adaptive 4x4 spatial dither experiment

Measured 2026-09-30 on branch `codex/dither-4x4`, starting from `a3b4e4e`.
**Decision: keep the prototype for comparison; do not enable it in the
player.** Regional tone improves, but texture, temporal error and compressed
size worsen. This completes the requested bounded pattern experiment.

## Candidate and reference

- Preserve the 128x96 logical grid (128x72 active), 256x192 native screen,
  source sample positions, colour pairs, BRIGHT and FLASH=0. No temporal
  alternation, palette search or reduction to 64x48 is introduced.
- Reuse the existing converter's palette selection with attribute-change
  penalty 100000. Canonicalize the endpoints, then choose the minimum RGB
  error among **all five** 2x2 coverages for the reference. This is optimal
  for those retained colour pairs, not a globally optimal palette search.
- Project each logical source sample onto its colour pair. Choose one of
  eight dot counts `0, 2, 5, 7, 9, 11, 14, 16` per 4x4 tile, approximating
  evenly spaced coverages. A screen-anchored Bayer matrix determines the
  native dots. Every source sample independently controls its own 2x2
  portion; eight-tone precision is regional.
- Accept a candidate 4x4 tile only when the underlying four logical samples
  differ by at most 32 in every RGB channel and its mean RGB error is
  strictly below the five-level reference. Other pixels keep the reference.
  The resulting adaptive picture can mix five-level and eight-target tiles;
  it is not restricted to exactly eight global colours or means.
- Compute patterns on the host. An affected attribute cell uses eight
  native bitmap bytes; other cells retain five radix-5 bytes. Mode bits are
  separate from attributes. This is an experimental cell transport, not FAP3.

## Scope and measurements

Original source SHA-256:
`dc2146a2b1172def56730143ad80cd1825b7fad15f1fc9c23a4e7d01a741ac11`.
Three 32-frame windows start at source frames 629, 2857 and 3855, each with
a carried preceding seed: **96 measured frames + three seeds** at 25/3 fps.
Cached RGB is reused by source hash and exact FFmpeg command. Preprocessing
is 256x144 area scaling, central zoom 1.25 and 128x72 output. No release
tone-group or feedback-budget preprocessing is applied. These are source
indices, not indices after the credits edit.

Metrics use uncalibrated sRGB squared error, not perceptual fidelity
percentages. Aligned 4x4 mean error is the selection objective; the sliding
metric averages all sixteen 4x4 offsets to check benefit away from that
alignment. Logical error compares individual 2x2 native averages with the
128x96 source. Grain is variation among those averages inside 4x4 tiles.
Temporal residual error measures changes in reconstruction error between
frames; it is a temporal-instability proxy, not an emulator flicker test.

| Window | 4x4 mean error reduction | Sliding mean error reduction | 2x2 error increase | Grain ratio | Temporal error increase |
| --- | ---: | ---: | ---: | ---: | ---: |
| 629–660 | 30.68% | 23.87% | 37.90% | 2.70x | 29.28% |
| 2857–2888 | 18.75% | 15.35% | 32.74% | 3.28x | 52.64% |
| 3855–3886 | 21.49% | 18.77% | 30.35% | 3.09x | 44.14% |

Sliding mean error improves in all 96 frames. This does **not** establish
overall quality improvement: fine-scale and temporal metrics deteriorate.
Mean changed native pixels are 3.41%, 3.74% and 3.62% of the active picture,
spread across 80.75%, 80.30% and 71.51% of attribute cells respectively.

### Compression

Each temporal packet has two 96-byte change masks, nonzero attribute XOR
residuals, changed-cell payloads and a u16 packet length. The candidate adds
one mode bit per changed cell and uses five or eight payload bytes. ZX0
blocks contain at most 15872 decoded bytes, with four-byte block headers.
Window seeds are excluded from sizes. Every packet and ZX0 block round trips.

| Window | Five-level bytes after ZX0 | Adaptive 4x4 bytes after ZX0 | Increase | Native XOR control: five → 4x4 |
| --- | ---: | ---: | ---: | ---: |
| 629–660 | 31,048 | 42,449 | 36.72% | 36,200 → 45,419 |
| 2857–2888 | 27,193 | 46,547 | 71.17% | 32,720 → 50,982 |
| 3855–3886 | 24,259 | 39,860 | 64.31% | 30,295 → 42,673 |
| Total | 82,500 | 128,856 | 56.19% | 99,215 → 139,074 |

The equal-layout control XORs consecutive native bitmap bytes and attributes
before ZX0. Its increase shows that escape metadata is not the sole cause:
the new patterns also compress worse in a common representation. This is
not a universal claim about every possible spatial dither or codec.

These controls exclude FAP3 motion/Huffman/fragments, AY, n-2 update maps,
checkpoints, cold startup, disk padding and latency. They cannot determine
TRD count or sustained delivery. No native consumer or RAM layout exists.
For storage scale only, an escaped cell adds three raw bytes over five-level
storage, plus mode metadata. No CPU saving is inferred from precomputed dots.

## Validation and visual review

Seven tests pass: exact eight uniform coverages, stable static phase, all
625 four-sample combinations against the existing five-level expander,
thin-line/checkerboard/half-tone retention, endpoint orientation and BRIGHT,
mixed native/five cell and attribute delta round trips, malformed packets,
and a zero-error edge metric regression. The tests also confirm that the
adaptive output reproduces all eight uniform bars in 4x4 averages.

Reviewed [movie comparisons](spatial_dither_comparison.png), frames 653,
2886 and 3884, selected for greatest aligned tone improvement in each window,
and [the synthetic ramp, eight bars and diagonal edge](spatial_dither_synthetic.png).
The ramp has more distinct intermediate tones and its diagonal edge keeps
the reference shape. Movie areas show a coarser, more irregular texture;
existing palette limitations remain. The examples favor the candidate's
tone objective and are not a blind viewing study or full-motion review.

The first diagnostic run exposed an overstrict black-border attribute
assertion and unsigned subtraction in the edge metric. The border check
now verifies displayed RGB; gradient subtraction uses floating point and
has a regression test. The saved report was regenerated with these fixes,
reusing exact RGB and compressed-block caches. Discard the initial edge
numbers; no earlier report was committed.

**Runtime status:** existing Z80/player code is unchanged, so its change is
0 T. The prototype's native decoder, paging, RAM and disk delivery costs
remain unimplemented/unmeasured. No TRDs, playback cadence or full-EOF
release claims are made. AY is outside this host experiment and unchanged.

## Reproduce and next step

Dependencies are the project's existing NumPy/Pillow environment, FFmpeg
and ZX0. Run from the repository root with `PYTHONPATH=toolkit` plus the
existing dependency directory if needed:

```text
python -m unittest toolkit.test_spatial_dither
python toolkit/probe_spatial_dither.py --source <original.mov> --ffmpeg <ffmpeg.exe> --zx0 <zx0.exe> --cache .tmp/hybrid-five --output toolkit/spatial_dither_probe.json --preview toolkit/spatial_dither_comparison.png --synthetic-preview toolkit/spatial_dither_synthetic.png
```

[Implementation](spatial_dither.py), [probe](probe_spatial_dither.py),
[tests](test_spatial_dither.py), [per-frame report and identities](spatial_dither_probe.json).
The prototype uses no uncommitted five-level modules or stale reports.

Prefer completing the existing five-level representation decision next.
Any later 4x4 attempt should first demonstrate lower texture/temporal error
and competitive window compression; native integration is premature for
this candidate. Do not automatically start another pattern search.
