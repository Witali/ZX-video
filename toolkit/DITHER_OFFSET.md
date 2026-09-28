# One selector bit per attribute cell

Measured on 2026-09-28 after the user proposed shifting the four output
levels towards either 0% or 100%. This experiment interprets that as two
consecutive quartets. The endpoint-preserving interpretation is also covered
below; it is already represented by the existing format.

## What one shared bit provides

| Cell selector | Available bright-dot coverages |
| --- | --- |
| Lower range | 0%, 25%, 50%, 75% |
| Upper range | 25%, 50%, 75%, 100% |

The selector applies to all sixteen logical samples in an 8x8 cell. Every
sample still has two bits and can select only four levels within that cell.
The union of the two palettes has five levels, but a single cell cannot
use all five at once. Neither quartet can represent both extreme endpoint
colours simultaneously.

A separate bit for each of 768 cells costs **96 bytes per full frame** before
compression, or **72 bytes** for the 576 active cells. This experiment found
that an explicit bit is unnecessary on Spectrum: exchange INK and PAPER to
encode the selector. Both endpoints share BRIGHT, so this retains the colour
pair. With canonical lighter INK the codes mean **0/1/2/3 light dots**; with
reversed endpoints they mean **4/3/2/1**. Keep a common screen-grid phase.
For identical endpoints the selector is unnecessary and invisible bitmap
values are canonicalized to zero.

The resulting host state remains **3840 bytes**, including attributes; the
lookup shape remains four codes. The existing player does **not** implement
these new meanings. Its tables, phase-aware output and native dirty maps
would need to change together. No new native timing or integrated RAM/disk
claim is made by the host prototype.

## Measurement against current compact frames

Input: the **4221-frame** no-credits checkpoint, SHA-256
`fdabc3331ee2ce7da23a5aa0dd3e2574e4bf7bf84d07abe381c5cecd7bc1e791`.
For each cell, count the two extreme levels and choose the quartet that
alters fewer samples. Every affected sample changes coverage by exactly
one quarter. This minimizes squared mean-colour error for that fixed pair
of colours. Ties preserve the previous frame's selector. Check both
round-trip values and the per-cell minimum on every frame.

- **106275** active cell occurrences contain both endpoint colours, across
  **4136** frames.
- **231527** logical samples change, **0.59517%** of the active samples.
- Nested patterns change one native pixel per affected logical sample:
  **0.14879%** of active native pixels on average.
- Worst-frame changed logical fraction: **2.63672%**.
- Average mean-RGB MSE: **23.47648**, worst frame **107.01090**, in the
  project's 0..255 RGB palette after averaging each 2x2 group. These are
  distortion measures against the phase-aligned compact baseline, not a
  perceptual-quality percentage or a comparison with original video RGB.

The [comparison](dither_offset_comparison.png) shows the worst MSE frames
**3634, 221, 222** at nearest-neighbour scale. Additional stippling is visible
at some high-contrast details and lettering. This inspection does not
establish that every scene meets the subtle-change constraint.

## Short-window compression

Exactly the three earlier **32-frame** windows. Compare XOR n-1 frame bytes
with the preceding predictor carried into each window, optimal ZX0, blocks
up to **15872 bytes** and four-byte block headers. Every block round-trips.
The baseline bytes reproduce the previous five-level experiment.

| Frames, end exclusive | Current two-bit bytes | Shifted quartet | Difference |
| --- | ---: | ---: | ---: |
| 629..661 | 33827 | 35065 | +1238 |
| 2857..2889 | 48338 | 48692 | +354 |
| 3855..3887 | 32330 | 32719 | +389 |

The tested shifted representation is larger by **0.7..3.7%**, despite
requiring no new selector bytes. These controls exclude FAP3 motion,
Huffman, fragments, AY, startup and sector padding. They cannot estimate
TRD count, disk delivery or real playback speed. Original RGB has not been
requantized, so potential advantages for different source images remain
unmeasured.

## Endpoint-preserving interpretation

If the intended two sets are **0/25/50/100%** and **0/50/75/100%**, current
INK/PAPER orientation already selects them without another stored bit.
They retain both endpoint colours. The reported opposite checkerboard is
a separate phase problem: it needs the [phase correction](DITHER_PHASE.md),
including n-2 native map updates. Adding a bit alone does not fix it or allow
all five levels within one cell.

## Decision and coverage

Keep the shifted quartet as a measured host experiment. Do not adopt it as
the default: these bounded controls show both distortion and a size increase.
Retain the existing endpoint-preserving quartets and proceed with native
phase correction and its CPU/memory/disk accounting. No production player
code, converter defaults, AY data or TRDs changed: instruction delta **0 T**.
The new consumer remains unimplemented, and no full playback check ran.

Five offset tests plus eleven phase/five-level tests pass. Coverage includes
all 128 non-FLASH attributes and 256 packed byte values, both quartets,
all-five-in-one-cell limitations, temporal ties, scalar cost checks, exact
host round trips and the existing endpoint-preserving interpretation.

```powershell
python -m unittest discover -s toolkit -p test_dither_offset.py
python toolkit/probe_dither_offset.py `
  --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz `
  --output toolkit/dither_offset_probe.json `
  --preview toolkit/dither_offset_comparison.png `
  --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe `
  --cache .tmp/dither-phase-zx0
```

[Script](probe_dither_offset.py) · [Tests](test_dither_offset.py) ·
[Report with frame-level errors, input/source hashes and block sizes](dither_offset_probe.json)
