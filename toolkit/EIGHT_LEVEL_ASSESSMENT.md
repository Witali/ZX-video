# Eight-level display feasibility

Assessed 2026-09-30. This is a design assessment, not a new codec benchmark
or release. Baseline: the current 128x96 logical/256x192 native layout,
128x72 active picture, 25/3 fps and 50 Hz AY; existing five-level experiments
remain separate and incomplete.

**Measured follow-up:** the user subsequently authorized a branch experiment.
See [the adaptive 4x4 results](SPATIAL_DITHER.md): better regional tone, but
higher fine-scale error, grain and compressed size. The tested candidate
is retained for comparison and is not recommended as the default.

## Physical limit

An 8x8 attribute cell has two endpoint colours and shared BRIGHT. FLASH is
disabled. With fixed endpoints, a 2x2 pattern can contain 0, 1, 2, 3 or 4
INK dots: only **five distinct area averages**, regardless of how those
dots are arranged. Eight code values cannot create eight independent static
averages inside that same 2x2 block. BRIGHT cannot be selected separately
for each of its sixteen logical samples.

The hardware attribute constraints are documented in the original
[Sinclair manual, chapter 16](https://worldofspectrum.org/ZXBasicManual/zxmanchap16.html).
The coverage counts and storage sizes below are arithmetic deductions.
Coverage fractions are mixtures of the two endpoint colours, not calibrated
perceptual brightness percentages or eight additional hardware greys.

## Options

| Method | Capability | Main cost or limitation |
| --- | --- | --- |
| Independent 2x4 or 4x2 logical samples | Nine possible dot counts; can select eight | Halves one dimension of the independently controlled sample grid; conflicts with the resolution target |
| Spatial threshold pattern over 4x4 native pixels | Seventeen dot counts on uniform areas; can select eight target shades | Fine contours can retain their positions, but tone accuracy is averaged over a larger area; texture/aliasing must be inspected |
| Alternate two 2x2 patterns in time | Nine time averages with equal phase duration | A 50-Hz alternation repeats at 25 Hz; flicker risk, both display banks occupied by phases and additional preparation/scheduling |
| Change palette or BRIGHT per attribute cell | More local colour choices | Does not supply eight independently selectable shades in each 2x2 sample; may introduce cell boundaries |

For spatial dithering, retain source detail on the existing logical grid;
do not first downsample the movie to one value per 4x4 block. Different
2x2 subpatterns cooperate to approximate intermediate shades on smooth
areas. This preserves sample locations, not independent eight-level tone
precision at every sample. Anchor thresholds to screen coordinates and
canonical light/dark endpoints to avoid orientation-dependent phase seams.

## Storage and decoding

Uniform eight-code storage would require 3 bits per logical sample:

| Full-frame working representation | Current | Eight-code proposal |
| --- | ---: | ---: |
| Pattern codes | 3072 B | 4608 B |
| Attributes | 768 B | 768 B |
| Total | 3840 B | 5376 B |

That is **+50% pattern data / +40% total state**, before compression. For
the active picture alone, pattern data increases **2304→3456 B**, +1152 B.
Actual sectors depend on temporal prediction and ZX0; no disk-count estimate
has been established. The enlarged state also needs a new RAM allocation.
Existing expansion tables cannot consume three-bit indices unchanged.

An alternative is to compute native patterns on the host and encode richer
cells as native fragments or dictionary references, retaining compact cells
elsewhere. A complete native 8x8 bitmap cell takes 8 raw bytes versus 4
current compact bytes (or 6 bytes of three-bit codes), excluding attributes
and command/mode overhead. This avoids runtime threshold calculation, but
fragment transport, copying, paging and extra sectors still need profiling.
Attribute deltas remain separate; untouched cells need no colour update.

## Recommendation and bounded next step

Prefer **host-generated, phase-stable spatial dithering**, applied adaptively
to smooth gradients. Retain the compact path for simple cells and sharp
details. Do not adopt temporal alternation or uniform three-bit storage by
default. Native fragments are a candidate delivery method, not an existing
integrated path or a proven speed improvement.

If implementation is requested, compare this one candidate with the best
five-level reference on the existing three 32-frame windows. First inspect
smooth gradients, silhouettes and moving edges, using both native-scale
views and spatially averaged error; a lower average error alone can hide
lost detail or flicker. Use original RGB, not only already quantized states.
Then measure actual encoded bytes and the affected Z80/IRQ/memory paths.
Reject extra shades when their quality gain does not justify delivery cost.
Retain the complete independent-boot/EOF gate for any later selected release.

**Status:** no source/movie requantization, compression run, native consumer,
new T-state measurement, TRD build or playback test in this assessment.
Production code and runtime cost are unchanged (**0 T delta**). No claim of
improved quality, eight independently accurate 2x2 shades or release fitness.
