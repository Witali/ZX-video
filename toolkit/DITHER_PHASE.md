# Dither phase and five levels inside each attribute cell

Investigated on 2026-09-28 after the user reported blocks with opposite
dither phase, then asked for all five 2x2 coverages inside every 8x8 cell.

## Reproduced cause

The current two-bit table always expands code 2 to `10 / 01`. With white
INK this lights the main diagonal; swapping INK and PAPER lights the other
diagonal. The palette search permits both orientations independently per
attribute cell. Its error metric averages each 2x2 group, so it cannot see
this phase difference. This explains a reproducible source of the reported
seams; without the user's exact image/scene it does not exclude other bugs.

The 4221-frame no-credits checkpoint contains:

- **549212** half-tone boundary samples with the same colour pair in opposite
  orientations, across **4121** frames (maximum **428** in one frame).
- **4204** same-location half-tone reversals between consecutive frames,
  across **448** frames.
- The unchanged Z80 cell renderer reproduces the existing Python reference
  exactly on frames **3478, 3479, 4063**, using forced dense output. Each test
  takes **154684 T**, including its normal map copy, attributes and paging,
  excluding IRQ/ULA/TR-DOS/disk. This is an isolated renderer check, not a
  replay of the user's TRD or full playback.

Counts identify phase discontinuities, not perceived-aliasing scores. See
the [before/after comparison](dither_phase_comparison.png), rendered with
nearest-neighbour scaling. The right column is a **host reference**.

## Correction while retaining the two-bit states

For darker INK, exchange the top and bottom scanlines of each 2x2 pattern.
This gives the same spatial phase for the same endpoint pair in either
orientation, retains each colour count and preserves the mean RGB of every
logical pixel. Keep endpoints and two-bit values unchanged.

This requires a corresponding native renderer change. It also makes native
bitmap pixels depend on attribute orientation. Existing dirty maps compare
only compact bitmap bytes against frame n-2. A corrected renderer must
redraw cells when that orientation changes, even with identical compact
values. On this input, **550** cells gain an exact bitmap change; after
existing dense-band promotion, **321** cells across **108** frames would
still be omitted by the old maps. The prototype regenerates the maps from
actual native bytes and tests alternating-screen replay, including changes
to attributes alone.

This fixes the identified phase mismatch, not all aliasing from resolution,
palette quantization or ordered dithering.

## Five independent coverages per cell

An 8x8 attribute cell has sixteen independent 2x2 groups. A five-level format
can choose every group freely, with fixed INK/PAPER for the whole cell:

| Level | Light pixels | Top | Bottom |
| --- | ---: | --- | --- |
| 0 | 0/4 | `00` | `00` |
| 1 | 1/4 | `10` | `00` |
| 2 | 2/4 | `10` | `01` |
| 3 | 3/4 | `11` | `01` |
| 4 | 4/4 | `11` | `11` |

Here 1 means the brighter endpoint. The sets of light pixels are nested;
all cells and frames use the same grid phase. The host prototype includes
an RGB quantizer with all five choices per cell, plus a conversion of old
compact frames that preserves their existing colour coverage. Tests show
the quantizer selecting all five levels inside a single cell. The complete
movie is **not** requantized from original RGB in this experiment.

Two bits cannot select five independent values. The tested packing stores
four samples as a radix-5 word (`125*a + 25*b + 5*c + d`, 0..624) in **10 bits**.
Four such words occupy five bytes. The Z80 would unpack bit fields and look
up precomputed top/bottom output bytes, with **no division by five**. The
simple aligned layout has two 1024-byte tables: **2048 bytes** instead of
the present **512**. No Z80 consumer or integrated RAM placement has been
implemented or timed yet; do not report this as a free runtime change.

| Full 128x96 logical frame | Current | Five-level prototype |
| --- | ---: | ---: |
| Pattern bytes | 3072 | 3840 (+25%) |
| Attribute bytes | 768 | 768 |
| Total before compression | 3840 | 4608 (+20%) |

A direct three-bit representation would increase pattern bytes by 50%.
The information bound is log2(5) = about 2.322 bits per sample, so tighter
packing exists, but its Z80 unpacking cost needs a separate measurement.

## Bounded storage comparison

Three **32-frame / 3.84-second** windows, no alternative image sets. Both
layouts use XOR against the preceding frame (including the carried frame
before the window), ZX0 v2 optimal and independent blocks up to 15872 bytes.
Sizes include four-byte block length headers. Every block independently
round-trips through the reference ZX0 decoder.

| Frames, end exclusive | Existing two-bit XOR | Five-level XOR | Difference |
| --- | ---: | ---: | ---: |
| 629..661 | 33827 | 45071 | +11244 |
| 2857..2889 | 48338 | 62106 | +13768 |
| 3855..3887 | 32330 | 41874 | +9544 |

This is **not** the existing FAP3 motion/Huffman/fragment stream. It excludes
AY, startup, sector padding and independent-disk checkpoints. It cannot
predict TRD count or playback cadence. Conversion from already quantized
frames does not measure potential quality gains of a fresh five-level
conversion from the original video. Fixed 10-bit packing is feasible, but
these preliminary results do not justify adopting it by default.

## Status and next work

- Eleven tests pass: all non-FLASH attributes, all packed byte values,
  every radix-5 word, five levels in one cell, RGB quantization, exact 2x2
  colour sums and n-2 attribute-only redraws.
- All **4221** converted frames match the aligned reference at native
  displayed-colour level. Three difficult frames were visually inspected.
- Production player, existing converter defaults and TRDs are unchanged:
  runtime instruction delta **0 T**. The new format has **no measured native
  cost**, no disk-delivery validation and no release claim.
- First implement and time the phase correction with the present four-code
  stream, including orientation-aware dirty maps and cold checkpoints.
- Compare that path with a five-level consumer in the same short windows.
  Account for lookup RAM, unpacking, predictor/cache layout, memory writes
  and extra sectors. Consider an adaptive five-level cell escape so ordinary
  cells need not pay the fixed-width overhead.
- A full five-level quality evaluation must requantize scaled original RGB,
  compare frame-level quality, then build and validate only the selected
  final set through EOF. Preserve the 50 Hz AY and exact video deadlines.

## Reproduction

```powershell
python -m unittest discover -s toolkit -p test_dither_phase.py
python -m unittest discover -s toolkit -p test_five_level_dither.py
python toolkit/audit_dither_phase.py `
  --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz `
  --output toolkit/dither_phase_audit.json `
  --preview toolkit/dither_phase_comparison.png `
  --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe `
  --cache .tmp/dither-phase-zx0
```

[Report with source/input hashes and per-frame counts](dither_phase_audit.json) ·
[Phase reference](dither_phase.py) · [Five-level prototype](five_level_dither.py) ·
[Reproducing script](audit_dither_phase.py)
