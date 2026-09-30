# Stronger compression with the unchanged LZSA2 format

2026-09-30. User constraint: keep LZSA2 syntax unchanged; spend more host
compression time if useful. Baseline `c3d1125`, upstream compressor revision
`15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5` by Emmanuel Marty. Use the same
21 independent raw blocks, 323940 decoded bytes, from the saved 192-frame
five-level video fixture. No image/audio change or whole-movie encode sweep.

## Conclusion

**Sustained CB41 follow-up:** all 192 saved frames now pass at 25/3 fps with
zero late deadlines and exact full screens/AY. Stream 154956 -> 134349 bytes,
606 -> 525 sectors; decoder 19412006 -> 12698715 T on unchanged opcodes.
All 12 blocks pass independent decoding/IRQ checks. 392 sectors arrive during
playback. This supports full edited-movie preparation; it does not establish
its capacity or release timing. [Complete evidence](CELL_CODEBOOK_SUSTAINED.md).

**Exact ready-cell follow-up:** a separate video representation, carried by
unchanged LZSA2, now saves 17.09% compressed bytes and 38.25% decoder CPU on
one exact 64-frame window. Most ratio gain comes from direct cell deltas;
the 256-entry book further cuts raw volume/decoder work. Its full 2048-byte
table and fallback/masks are counted. Host screens and native outer-codec
checks pass. The subsequent native CB41 renderer now passes both screens,
22 edges and independent timing/IRQ checks: 7910734 T versus the old frame
component's 14295892 T. Supplied-packet ownership excludes delivery/paging
costs. The subsequent [independent window TRD](CELL_CODEBOOK_PLAYER.md) now
passes real playback: zero late deadlines at 25/3 fps, exact AY and all full
screens. Most sectors are prefetched; require 192 continuous frames next
before claiming sustained delivery or whole-movie capacity.
[Results, protocol and limits](CELL_CODEBOOK.md).

**Reset-placement follow-up:** two bounded tail candidates retain all raw
bytes and 21 blocks. Aligned cuts add 51 bytes and 2393 measured total
component T. A shifted phase saves 73 bytes, still no sector, but adds 15336
decoder/copy T before unmeasured producer/frame effects. Neither is adopted;
the variable-block copy verifier is corrected and baseline-compatible.
[Results and precise coverage](LZSA2_RESET_PLACEMENT.md). Close these reset
heuristics; the separate codebook proposal has now passed bounded host and
native feasibility, but still needs integrated playback before default use.

**Full-block distance follow-up:** retaining command positions and lengths,
an exact canonical-distance search on block 11 finds no smaller byte output
and saves only 108 decoder T (7165 bytes unchanged). All banked/native and
author checks pass; reject production integration or expansion of this pass.
The block-reset follow-up above is now complete.
[Scope, accounting and evidence](LZSA2_DISTANCE_SELECTION.md).

**Exact-oracle follow-up:** the existing compressor matches minimum size
on all 1341 bounded short inputs tested, including 63 video excerpts. No
general optimality claim. Some equal-sized alternatives differ in decoder
cost (20 faster, 24 slower); the complete-block distance follow-up above
found only a negligible saving. The short-input reference
and verification described below are now implemented.
[Results and limits](LZSA2_EXACT_ORACLE.md).

A stronger compatible compressor is possible in principle: the format does
not prescribe how the encoder finds or selects matches. The current encoder
already uses suffix-array matching, bounded dynamic programming, repeated
offsets, supplemental match searches and command reduction. `--prefer-ratio`
is already enabled. There is no unused ordinary "maximum compression" flag.

**Simply enlarging the search tables is not useful on these inputs.** Two
compiled host-only prototypes produce valid, marginally smaller streams, but
save no disk sectors and require slightly more Z80 work. Keep their sources
and results as experiments; do not make either a production default.

| Same block boundaries and decoded bytes | Baseline | Larger tables | Larger tables + deeper supplements |
| --- | ---: | ---: | ---: |
| Compressed stream bytes, including headers | 154956 | 154954 | 154944 |
| Saved bytes | 0 | 2 | 12 |
| Video sectors | 606 | 606 | 606 |
| Decoder T | 19412006 | 19412144 | 19412766 |
| Decoder delta T | 0 | +138 | +760 |
| Producer T, excluding ROM/disk | 1058423 | 1058423 | 1058423 |
| Total component T | 20470429 | 20470567 | 20471189 |

The best direct prototype saves **0.00774%**. Selecting the smallest saved
payload per block among all three would save 13 bytes, still 606 sectors;
this last number is a size-only calculation, not an integrated stream or disk.
The deeper variant worsens one block by a byte, demonstrating that a larger
heuristic search is not guaranteed to produce a monotonic improvement.

## What "larger libraries" can mean

### 1. More encoder search state on the PC

This is free of Spectrum RAM cost and does not change the format. It was
tested here. The pinned source has these limits in `src/shrink_context.h`:

| Host structure | Current | Tested |
| --- | ---: | ---: |
| Candidate matches per position | 64 | 128 |
| Arrival states in the first small-block parse | 32 | 128 |
| Arrival states in the final parse | 64 | 256 |
| Match table index shift | 6 | 7 |
| Arrival table index shift | 6 | 8 |

An arrival is an alternative way to encode the prefix ending at a given
position, including its last match offset. Retaining more alternatives can
make a later repeat-offset match cheaper. This experiment increases memory
on the compressor only; the Z80 decodes ordinary LZSA2 commands.

The two main allocation requests grow from approximately **112 MiB to
416 MiB** on MSVC x64: `65537 * 64/256 * 24` bytes for arrivals and
`65536 * 64/128 * 4` for matches. These are source-derived allocation sizes,
not measured peak working set; other tables and process overhead are extra.
Observed PC encode time was 6.92 -> 30.26 s for the wide comparison, and
10.06 -> 40.60 s for the deeper comparison. These are individual interleaved
runs including process/file overhead, not rigorous or cross-run benchmarks.

After the first result, the second prototype also changes the independent
supplement limits in `src/shrink_block_v2.c`:

- Candidate ceilings 15/46/63 become 63/95/127.
- Two supplemental insertion caps increase from 12 to 48.
- Three supplemental match-length limits increase from 16 to 64.

All other heuristics, the byte writer and both C/Z80 decoder algorithms
remain unchanged. This is still bounded search, not proof of an optimal parse.

### 2. A larger LZSA2 history dictionary at playback

The format supports positive reference distances up to **65535 bytes**;
the encoded offsets are negative 16-bit displacements. It also provides
compact offset encodings and reuse of the previous offset. See the
[official block specification](https://github.com/emmanuel-marty/lzsa/blob/master/BlockFormat_LZSA2.md).
An arbitrary 128 KiB reference dictionary cannot be addressed by this format.

Our current player uses independent blocks of at most **15872 output bytes**
inside bank-local 16 KiB slots. Thus the actual available history grows only
within each block; it is much smaller than the format's maximum. Increasing
a host search table does not restore previous blocks' discarded history.

The upstream `-D` option can seed a dictionary without changing token syntax,
but the decoder must have the exact same bytes at the corresponding reference
addresses. Adding that option alone would make our current player invalid:
its bank-local source-address calculation and guard assume within-block history.
Retaining history would require an explicit memory layout, bank-copy/paging
costs and input-buffer tradeoff. A seed dictionary stored on disk costs bytes
and boot time too. Every disk must carry or reconstruct its own starting
history, preserving independent boot. This possibility is **not measured**
or implemented by the present experiment.

### 3. More video fragments in the earlier dictionary layer

The row/fragment dictionary belongs to the video representation before LZSA2.
It may reduce bytes presented to LZSA2, but it is a separate optimization:
dictionary assets, indices, installation and lookup all have costs. More
entries do not inherently improve the outer compressor. Keep that work
separate from this fixed-input, unchanged-format encoder comparison.

## Separate video-layer proposal: table-driven inverse transforms

2026-09-30, analytical follow-up at `a977f1d`; no new encoder, Z80 kernel,
disk or measurement. A simplified IDCT is feasible in principle, but it
belongs to the video representation. LZSA2 only restores literal bytes and
back-references; its [standard token syntax](https://github.com/emmanuel-marty/lzsa/blob/master/BlockFormat_LZSA2.md)
has no image or transform operation. New video commands can still be carried
by unchanged LZSA2, but existing video decoders would need a new mode/version.
Keeping both layers unchanged permits only host-side analysis/selection of
images that the existing video commands already represent.

### Two distinct table approaches

1. **Tables of basis contributions.** The PC precomputes each allowed
   coefficient's contribution to a 4x4 logical block. The Z80 adds selected
   tables, then scales/clamps/quantizes to five levels and produces bitmap
   bytes. Example storage: four basis functions * 16 amplitudes * 16 samples
   * two signed bytes = 2048 bytes. This replaces multiplication, not the
   accumulation, rounding, prediction or output work. An illustrative direct
   sum with DC initialization and three AC contributions needs 48 additions
   per block. Using `ADD HL,DE` at 11 T gives 528 T for additions alone;
   768 blocks of a full 128x96 logical frame would require 405504 T before
   table loads/stores and other stages, against a total six-field budget of
   425448 T. This is an estimate for that deliberately simple implementation,
   not a bound on factored IDCTs or a measured native routine. Unchanged blocks
   should be skipped and the black fields retained.
2. **Tables of complete reconstructed blocks.** Restrict coefficient
   combinations and precompute their final five-level, phase-correct dither
   output on the PC. A 4x4 logical block becomes one aligned 8x8 Spectrum
   cell: eight bitmap bytes. A 256-entry table costs 2048 bitmap bytes and
   each selected block needs a one-byte index, before command/position costs.
   Attributes, including BRIGHT, stay separate. The Z80 only selects and
   writes the prepared bitmap; no runtime IDCT or amplitude summation is
   needed. This is a codebook/vector-quantization scheme whose entries may
   be generated by IDCT, not a general JPEG/H.263 transform decoder.

The second approach is the more plausible speed-oriented hypothesis.
Current [row tables](row_dictionary_video.py) already use 512 bytes to map
one index to two bitmap scanlines. Four row indices describe the same
4x4 logical area, so the proposed index can replace four literal indices
where the chosen pattern is suitable. **This does not predict a fourfold
file-size or rendering-speed improvement:** existing temporal reuse, row
runs and LZSA2 already compress those indices, and the new dictionary,
mode/mask, fallback commands and screen writes all have costs. There is
no established free 2 KiB; account for the existing row table and the full
128 KiB layout before allocating another table or shrinking disk buffers.

### Quality and compatibility constraints

- User-confirmed ordering: reconstruct brightness (and add any predicted
  residual), round/clamp and quantize to the five brightness levels, then
  apply the fixed-phase dither as the final display step. A lookup table
  may fuse these steps only if its result is identical to that ordering.
  Never dither separate basis contributions before adding them: dithering
  is nonlinear. A runtime level-to-pattern lookup also preserves this order.
- Transform logical brightness values before dithering, never dictionary
  index numbers or the binary dither texture. Preserve cell attributes and
  the fixed screen phase; do not let a block choose the opposite phase.
- A small low-frequency coefficient set cannot reproduce arbitrary sharp
  cartoon outlines or all five-level block arrangements. Restrict use to
  suitable blocks, with the existing exact literal/fragment mode as fallback.
  Keeping five output levels alone is not evidence of preserved quality.
- Compare decoded blocks/frames to the accepted five-level reference and
  inspect contours, thin details, ringing, block seams and temporal shimmer.
  Any temporal predictor must use reconstructed history to avoid drift.
- Keep each disk independently bootable by including its starting codebook.
  Dictionary bytes and updates count toward capacity and loading cost.
- If explored, begin with one saved 32-64-frame window and 256 full patterns.
  Measure total compressed bytes, metadata, native render/paging cycles and
  actual deadlines before expansion. A ratio estimate is not an adoption gate.

Small transforms are real techniques: [IJG-related reduced-IDCT derivations](https://jpegclub.org/jidctred/)
show a 2x2 sum/difference transform and a factored 4x4 transform. Their
reduced-output examples do not justify lowering our existing logical
resolution or establish Z80 performance. Keep this as a separate candidate;
the reset-placement task is now complete. The bounded exact codebook
probe in [CELL_CODEBOOK.md](CELL_CODEBOOK.md) is promising and native output
is next; current production runtime formats remain unchanged.

## Plan for a meaningfully stronger compatible compressor

### Priority 1: identify actual parser losses before another large search

Build a small exact reference optimizer for short inputs and compare it with
the current compressor. Use deliberately constructed repeat-offset and
literal-boundary cases, plus short slices from a difficult saved window.
This gives reproducible examples of lost bytes and an attainable lower bound
for those small inputs, rather than assuming larger constants must help.

The stronger parser should account for:

- The current byte position, previous offset, and pending literal-run length.
  The upstream optimizer often merges alternatives by offset. Audit whether
  arrivals with different literal tails can be discarded safely before
  calling the parse exact; no correctness defect is claimed here.
- Actual literal thresholds 3/18/256 and match thresholds 9/24/256, repeat
  offsets, offset cost classes 32/512/8704/65535 and the raw-block EOD command.
- Nibble sharing and final byte rounding. The current encoder already uses
  four-bit costs; do not "improve" it by rounding every nibble up to a byte.
  Nibble phase may be explicit or derived from the cumulative exact cost.
- Future offset reuse: the longest current match need not lead to the smallest
  complete output. Keep useful alternatives by offset and future state.

Use the exact short-input oracle to validate any new pruning rule. Extend
only proven opportunities to a bounded beam/Pareto parser on 15.5 KiB blocks.
Keep the current writer and decoder until independent compatibility tests
prove a replacement writer necessary. Updating `libdivsufsort` by itself
changes suffix-array construction speed, not the available input history or
the format's reference range; it offers no automatic compression gain.

### Priority 2: choose reset boundaries in a bounded temporal window

Move existing block boundaries, keeping every output block at most 15872
bytes and retaining the same raw-block/header syntax. A reset just before
related data can lose useful history; a reset at a scene transition may lose
less. Compare a small set of cuts near packet boundaries, including header,
carry, in-place overlap and sector costs. Smaller blocks introduce more
resets, so this is not a guaranteed gain. Do not sweep complete disk sets.

### Priority 3: evaluate history only with a concrete RAM design

First measure the byte potential of a fixed seed or retained history using
the author decoder. If it is substantial, draw the full 128 KiB allocation
and prototype reference access in banked Z80. A host size result alone cannot
justify shrinking disk buffers or adding frequent paging. Preserve ordinary
LZSA2 commands and independent disk boot throughout.

### Selection and acceptance

Always retain the existing compressed payload as a fallback. A new compressor
may choose its candidate only after standard decoder verification and the
configured byte/time objective. For speed-neutral compression, measure total
native work as well as bytes; 2-byte matches can reduce storage but add
dispatch work. If sizes tie, prefer measured lower decode cost rather than
an arbitrary token-count heuristic. Never claim more compression from a
postprocessed format or a lossy change to the decoded video.

Before adoption, require unchanged decoded bytes, original-author C and
independent host/Z80 round trips, in-place proof, complete bank/sector checks,
instruction counts and relevant edge cases. Then measure actual publication
and AY with real disk/ROM/ULA behavior. Full edited-movie capacity and EOF
deadline checks on every independently bootable volume remain the release gate.

## Verification of the completed probes

- All 21 baseline recompressions reproduce the archived payloads exactly
  in both comparisons. No compiler/source-version difference is hidden.
- Both new streams pass original-author decoder round trips, independent
  parser checks, per-write cursor/overlap proofs, guarded banked Z80 decoding,
  sector order/exact EOF and independent full-flags per-slice cycle checks.
- Each candidate passes a separate 184-interrupt synthetic IM1 run.
  This verifies state preservation, not actual AY cadence.
- The deeper compressor passes 27 non-video native boundary cases, including
  small/long lengths, literal-heavy input, offset thresholds, overlapping
  runs, maximum native block size and a short-sector retry.
- The assembled player code is identical to the baseline. Changed instruction
  paths produce the +138/+760 T deltas above; no instructions were optimized.
- Current root TRD hash is unchanged. No new TRD, Fuse playback rate or
  full-movie capacity estimate was produced. Both broadening probes are
  completed but rejected for production adoption.

## Reproduction and evidence

[probe_lzsa2_search.py](probe_lzsa2_search.py) checks the pinned source revision
and clean tracked files, copies sources/licenses into a temporary output
directory, marks its altered files and uses the existing MSVC build script.
It does not alter upstream checkout files or download/run a third-party EXE.
Add `--deep` for the supplemental-search variant, using a different output
directory. The helper is a research compressor prototype, not a converter
default. Raw fixture/metadata remain in `row_lz4_evidence` and the original
stream in `row_lzsa_evidence/video.stream.gz`.

```powershell
$env:PYTHONPATH='local_tools/python_packages;.tmp/lzma-z80-packages;toolkit'
python toolkit/probe_lzsa2_search.py --source .worktree/three-disk-quality/.tmp/codec_sources/lzsa --baseline-exe .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --vs 'C:/Program Files/Microsoft Visual Studio/18/Community' --output .tmp/lzsa2-wide-search --raw .tmp/lzsa2-stages/video.raw --stream .tmp/lzsa2-stages/video.stream
python toolkit/probe_lzsa2_search.py --deep --source .worktree/three-disk-quality/.tmp/codec_sources/lzsa --baseline-exe .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --vs 'C:/Program Files/Microsoft Visual Studio/18/Community' --output .tmp/lzsa2-deep-search --raw .tmp/lzsa2-stages/video.raw --stream .tmp/lzsa2-stages/video.stream
python toolkit/benchmark_row_lzsa.py --stream .tmp/lzsa2-deep-search/wide.stream --raw .tmp/lzsa2-stages/video.raw --metadata .tmp/borrowed-literals/metadata.json --output .tmp/lzsa2-deep-search/cpu.json
python toolkit/verify_lzsa2_search.py --stream .tmp/lzsa2-deep-search/wide.stream --raw .tmp/lzsa2-stages/video.raw --cpu .tmp/lzsa2-deep-search/cpu.json --output .tmp/lzsa2-deep-search/verification.json
python toolkit/test_row_lzsa.py --lzsa .tmp/lzsa2-deep-search/build/lzsa.exe --output .tmp/lzsa2-deep-search/edges
```

Run the same CPU/independent verification commands for the wide variant.
Then archive the reports and payloads:

```powershell
python toolkit/summarize_lzsa2_search.py --wide .tmp/lzsa2-wide-search --deep .tmp/lzsa2-deep-search --evidence toolkit/lzsa2_search_evidence --output toolkit/lzsa2_search_profile.json
```

The [summary](lzsa2_search_profile.json) includes exact hashes, allocation
estimates and coverage. [Evidence](lzsa2_search_evidence) includes compiler
manifests/logs, per-block sizes, both new streams, native and independent CPU
reports and edge results. Executables and temporary source copies stay out
of Git. Original LZSA source remains under its upstream zlib/CC0 licenses.
