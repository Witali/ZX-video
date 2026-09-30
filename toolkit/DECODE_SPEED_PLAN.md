# Decode-speed improvement plan

Updated 2026-09-30. This is the current plan in English. Earlier proposals
and their dated results remain in the [historical plan](DECODE_SPEED_PLAN_ru.md)
and [changelog](../CHANGELOG.md).

## Objective and acceptance criteria

**Integrated CB41 window (2026-09-30):** independent 64-frame TRD now passes
real Fuse at 8.3333324 fps, zero missed deadlines, all 384 AY ticks and all
64 full published screens. Standard LZSA2 stays 42303 bytes / 166 sectors;
total file sectors 218. 130 video sectors arrive before first publication:
test the complete 192-frame fixture next for sustained delivery, then the
full edited movie and converter/volume integration. No full-movie success
claim. Core draw is unchanged; new packet/wrappers cost 23636 T and startup
book transposition 54028 T. [TRD and evidence](CELL_CODEBOOK_PLAYER.md).

**Native CB41 output (2026-09-30):** 335-byte Z80 book renderer passes both
full screens on all 64 saved frames, 22 synthetic variants and independent
instruction/IRQ checks. Supplied-packet draw costs 7910734 T, versus 14295892 T
for the old reconstruction/output component (-44.66%); ownership/paging
differ, so this is not a full delivery comparison. Book setup is 54028 T.
Book rendering costs 712149 T more than literal-only, but separate transport
savings exceed that by 779470 T. Preserve the current root image. Next
integrate one cold-bootable timing-test disk with actual packet delivery,
AY50 and six-field publication. [Accounting and evidence](CELL_CODEBOOK.md).

**Exact cell-codebook feasibility (2026-09-30):** same saved 64-frame window
with both prior screens supplied. Direct-cell deltas + a 256-entry exact
book, including table/header/masks/fallback, reduce LZSA2 51022 -> 42303 bytes
and decoder 6353724 -> 3923387 T. Control without a book isolates its raw-
volume benefit. All host screens, 22 boundaries and 17 guarded/independent
codec blocks pass. This feasibility stage did not measure native output or
fps; the follow-up above supplies native output. Retain exact brightness
before dithering and independently bootable disk requirements. [Evidence](CELL_CODEBOOK.md).

**Bounded LZSA2 reset placement (2026-09-30):** final five blocks of the saved
192-frame stream. Aligned cuts add 51 bytes and 2393 decoder/producer/copy/
frame T; shifted phase saves 73 bytes but adds 15336 decoder/copy T before
unmeasured remaining effects. Both remain 606 sectors. Author/host/native
changed-block checks pass; aligned also passes full banked transport and
all compact/native frames. Correct the copy verifier's fixed-block assumption;
do not adopt either placement or claim new fps. Next check exact ready-block
coverage and compressed cost on one window, retaining LZSA2 and applying
dither only after brightness reconstruction. [Evidence](LZSA2_RESET_PLACEMENT.md).

**Full-block LZSA2 distance selection (2026-09-30):** same literal/match
positions and lengths on complete block 11, exact canonical-offset search
within original byte budget. Payload remains 7165 bytes; decoder saves
108 T, and all 21 blocks remain 154956 bytes / 606 sectors. Model boundaries,
exhaustive tiny layouts, author, guarded banked and independent IRQ checks
pass. Reject integration/expansion: no meaningful capacity or speed gain.
Root image and last 7.683025-fps timing failure remain unchanged. Next test
a few reset boundaries on a saved window, retaining syntax and raw bytes.
[Evidence and limits](LZSA2_DISTANCE_SELECTION.md).

**Exact LZSA2 oracle (2026-09-30):** no minimum-size gap on 1341 bounded
inputs, including 63 video excerpts; 126 exhaustive command-list checks and
531 guarded/independent native cases pass. Of 232 different equal-sized
parses, 20 are faster and 24 slower; a 128-byte example saves 480 T at the
same size. These fresh-reset snippets do not predict full-block/playback
savings. The completed full-block distance test above preserves command
positions/lengths, actual reservoir state and byte budget.
Do not expand the size-only search without a counterexample. Root image
and failed timing result are unchanged. [Oracle and evidence](LZSA2_EXACT_ORACLE.md).

**Stronger standard LZSA2 search (2026-09-30):** retain format and native
decoder unchanged. On the same 21 blocks, wider host match/arrival tables
save only 2 bytes (+138 decoder T); widening the remaining supplement
limits saves 12 bytes (+760 T). Both still read 606 sectors. All guarded
and independent CPU checks pass; 27 deep-variant edges pass. No production
adoption, new disk or fps claim. Next use a small exact parser as an oracle
for pruning losses, then one bounded host-parser candidate. Keep baseline
payload fallback, nibble/EOD costs and byte/time selection. Larger runtime
history needs a separate 128 KiB bank layout and independent disk start.
[Compatible-compressor plan and evidence](LZSA2_COMPRESSION_PLAN.md).

**LZ4 analysis and short-run prototype (2026-09-30):** same 21 saved blocks,
identical compressed/decoded bytes. Inline short literal/match copies and
avoid two stack exchanges on short matches: 19847554 -> 15657014 T (-21.11%),
267 -> 280 bytes. All guarded banked blocks, 46 edge cases per variant and
independent full-flags/synthetic-IRQ checks pass. Versus current LZSA2, save
3598927 decoder/producer T but add 28492 bytes / 111 sectors. No candidate
fps or full-movie claim; root TRD unchanged. Retain as an experiment pending
actual delivery timing. Next: bounded codec selection with real disk costs,
then a Z80-cost-aware standard LZ4 parse. Unrolled copies have at most
1366050 T gross headroom. Reject simple one-or-three-byte offsets: estimated
+18092 bytes on the same parse. [Analysis and evidence](LZ4_OPTIMIZATION.md).

**Compiled row output (2026-09-30):** reject the COPY/pattern-FILL/solid-FILL
command format on the same 192 exact five-level frames. All bitmaps and
1152 suffix/boundary cases pass. Optimistic output 20246890 -> 17743885 T,
but command copies add 3231675 T and actual LZSA2/producer adds 8975251 T.
Video grows 154956 -> 211907 bytes (606 -> 828 sectors). Component regression
9703921 T, before new helper costs. No candidate TRD/Fuse run; current image
retained. Next measure native LZ4-HC as a possible selective fast block mode,
using saved blocks and counting their known capacity penalty. Do not reopen
the whole-codec sweep or adopt it on CPU alone.
[Implementation, evidence and limits](COMPILED_ROW_OUTPUT.md).

**Row-aligned motion (2026-09-30):** reject the existing-cache candidate on
the same 192 five-level frames. Correct whole-symbol shifts emit 6540 motion
commands and activate the cache in 191 frames. Decoded bytes 323940 ->
261389; LZSA2 bytes 154956 -> 151643; decoder 19412006 -> 14216558 T.
However frame stages 41965760 -> 63715325 T, including 8753180 cache and
5481126 motion T. Candidate component pool exceeds the latest borrowed
baseline by at least 16933120 T in the stated model. All compact/native CPU
frames, AY, blocks and targeted tests pass. No candidate TRD/Fuse run;
current image retained. Keep the experimental selector opt-in; return to
native output. A future motion selector must charge cache/patch costs.
[Comparison, evidence and limits](ROW_ALIGNED_MOTION.md).

**Borrowed literal suffixes (2026-09-30):** adopt the opt-in, host-validated
fragment-only mode. Same 192 frames and 606 video sectors: avoid 226819 copied
bytes in 171 packets. Copy bridges 5511858 -> 1950856 T; frame stages grow
41965760 -> 43760146 T from paging; net component saving 1766616 T.
Real Fuse 7.478465 -> 7.683025 fps, 134 -> 118 late frames, max 133 -> 99
fields. All full CPU frames, 45 copy edge cases, cold boot, AY/EOF and six
full captures pass. Both timing gates still fail. Code reuses motion RAM
only after validating that this stream cannot execute motion/spatial paths.
No compression loss or buffer reduction. Next: native pixel output.
[Implementation, timing and limits](BORROWED_LITERALS.md).

**Fresh LZSA2 stage profile (2026-09-30):** unchanged `de0a50d` test disk,
192 frames. Real elapsed stages: packet transfer 42.58%, screen output
22.87%, reconstruction 22.07%, metadata 3.63%, control/prefetch/wait 8.84%.
Separate CPU: screen 20246890 T, LZSA2 19412006 T, fragments 9090556 T,
packet-copy lower bound 5183040 T; motion/spatial/cache handlers 0 T on this
fixture. Empty queue at 153/192 packet starts; transfer max 1249405 T.
Prioritize packet-copy reduction, screen writes and decoder parsing; ideal
LDIR-repeat removal is bounded by 995975 T before new loop overhead.
Fresh full Fuse repeats 7.478465 fps and both failed timing gates. No player
or stream change. [Profile and limits](LZSA2_STAGE_PROFILE.md).

**Requested LZSA2 optimization (2026-09-30):** adopt restored upstream
S/P token dispatch, verified independently with full CPU flags. Same stream:
19844626 -> 19412006 T (-2.18%), 391 -> 384 bytes. Full Fuse publication
span improves 90904059 -> 90549516 elapsed T; fps 7.449298 -> 7.478465.
Neither timing gate passes (134 late frames, maximum 133 fields, final late
run unrecovered). Keep the updated optional test TRD and exact evidence.
No extra sector, buffer or stack cost. Return to packet-copy reduction;
unrolled match copying needs a separate bounded hypothesis. [Details](LZSA2_DISPATCH.md).

**Requested compiler comparison (2026-09-30):** same portable C LZMA1
decoder, same 21 blocks. z88dk/ZSDCC: 5359269651 T / 2344 code bytes;
SDCC: 6286416196 T / 2443 bytes; HI-TECH: 8213010715 T / 2638 bytes.
z88dk saves 14.75% versus SDCC but is 2.3242x fast ASM and 270.06x LZSA2
decoder CPU. All three are exact on the fixture and pass bounded timing,
edge and error checks. Reject realtime C LZMA integration; retain tools
for other C components and return to packet-copy reduction. Do not turn
this into an open-ended compiler-option sweep. [Evidence](Z80_C_COMPILERS.md).

**Requested native LZMA implementation (2026-09-30):** complete specialized
Z80 ASM decoder, `lc=0, lp=0, pb=2`, existing raw 21-block stream unchanged.
Unrolled EXX multiplication saves 462 T per adaptive bit: 2901892750 ->
2305838368 T (-20.5402%), code 1345 -> 1464 bytes, probabilities 3886 bytes.
All 42 video decodes, edge/error/guard/ABI tests and instruction timing checks
pass. This is still 116.19x LZSA2 decoder CPU. Reject realtime integration
of this implementation; retain the standalone source/evidence. Flat RAM and
synthetic IM1 tests do not validate production paging, 50-Hz AY or disk/ULA.
The earlier proposed LZMA feasibility probe is now resolved; return to
packet-copy reduction. [Source, measurements and limits](LZMA_Z80.md).

**Requested LZW/LZH follow-up (2026-09-30):** on the unchanged 21-block
fixture, LZW10/11/12 and standard ncompress16 grow the stream by
9.26%..24.36% versus ZX0. LH5 saves 2.18% (145725 bytes / 570 sectors).
105 independent video round trips and 33 extra cases pass. Reject tested
LZW settings for capacity; defer LH5 adoption pending native costs, bank/
overlap proof and actual deadlines. Player delta is 0 T; keep packet-copy
work priority. [Details and reproduction](LZW_LZH_ASSESSMENT.md).

**Requested modern-codec assessment (2026-09-30):** same 21 blocks/192 frames,
294 exact PC round trips. LZMA1 extreme lc=0 reaches 133084 bytes (-10.66%
versus ZX0), Brotli-11 132043 (-11.36%), Zstd-19 137607 (-7.63%). Weak LZMA
and bzip2 save only 1.26%/1.47%; LZ4-HC grows 23.14%. These are host storage
results, with 0 T change to the native player. Standard bzip2 does not fit
RAM; other new decoders require native cost, memory and overlap proofs.
LZMA lc=0 is the most interesting future small cost probe, not an accepted
replacement. Preserve the packet-copy work priority and avoid repeating the
codec sweep. [Assessment and source-backed constraints](MODERN_CODEC_ASSESSMENT.md).

**Integrated five-level transport (2026-09-30):** on the exact 192-frame
row-dictionary montage, optional fragments reduced frame work to 41965760 T.
Replacing only its outer Fast ZX0 with resumable LZSA2 now reduces decoder
25185674 -> 19844626 T; total transport CPU saves 5307621 T. Video grows
148971 -> 154956 bytes. Real fps improves 7.126866 -> 7.449298, but 135
deadlines are missed and the last late run never recovers. Keep the optional
test image; do not promote it as a release or change the generic default.
All 21 native blocks, 27 boundary cases, full test EOF, AY and six complete
captures pass content checks. Next inspect avoiding packet-buffer copies,
including cross-block ownership and IRQ paging, on this existing fixture.
See [measurement and limitations](ROW_LZSA_TRANSPORT.md).

**Five-level row dictionary (2026-09-30):** bounded changed-row sets fit
in two 256-byte lookup pages. Reject the tested whole-cell dictionary;
prefer row dictionaries only in windows with lower bytes and measured CPU.
Offline selection gives 68648→65294 bytes and Fast ZX0 11380407→11181994 T.
The existing renderer executes unchanged with learned table contents:
dense 154684 T and sparse fixture 27101 T, both 0 T delta in nine checks.
The fixed whole-volume dictionary, seed state and packet consumption have
since been integrated in the 192-frame fixture above. Dynamic book changes
and whole-movie five-level delivery remain unverified. See
[the compression plan and initial limitations](FIVE_LEVEL_COMPRESSION_PLAN.md).

**Five-level 2x2 decision (2026-09-30):** retain the palette-preserving
adaptive four/five-byte cell candidate. In 96 RGB frames its exact five-level
picture improves mean RGB error by 1.16–16.14%; ZX0 control bytes total
68648 versus 56146 for four-code input and 82500 for uniform-five.
The canonical three-mode alternative costs 1.80% more than adaptive hybrid;
any CPU saving remains unmeasured. Ten host tests confirm the previous
phase-aligned pattern and lossless representation changes. Next implement
and profile native expansion, IRQ/n-2/RAM contracts and sector impact before
TRD integration. [Results and reproduction](HYBRID_FIVE_LEVEL.md).

**4x4 experiment (2026-09-30):** a bounded host prototype on branch
`codex/dither-4x4` improves regional tone in 96 frames but increases logical
2x2 error by 30–38%, grain by 2.7–3.3x and cell-stream ZX0 bytes by 56.19%
overall. Do not enable this candidate. See [results and reproduction](SPATIAL_DITHER.md).
Native costs remain unmeasured; existing player code is unchanged (0 T delta).
Complete the five-level representation decision before revisiting richer
patterns; this result does not rule out every alternative 4x4 method.

**Eight-level assessment (2026-09-30):** fixed-colour 2x2 patterns have only
five area averages. Prefer an adaptive, host-generated 4x4 spatial threshold
pattern for richer gradients, retaining detail positions and fixed phase;
it does not provide eight independent tones in every 2x2 sample. Uniform
three-bit storage adds 50% pattern bytes before compression. Native fragment
delivery may avoid runtime threshold work but remains unimplemented and
untimed. See [options, arithmetic and the bounded comparison](EIGHT_LEVEL_ASSESSMENT.md).
This assessment does not authorize a new release build or replace the
pending five-level feasibility decision with an unrestricted search.

**Native dither correction (2026-09-28):** an optional Z80 implementation
now passes exhaustive attribute/byte tests, IRQ stress and 96 movie frames.
The same-map overhead is `395 + 43*bands + 61*sparse_cells + 3068*dense_bands`;
isolated full-movie output formula rises by about 26.4%. Keep this measured
[correctness baseline](PHASE_RENDERER.md), not the default player. Compare
adaptive five-level table expansion and cheaper phase preparation before
paying this overhead in the final schedule. Native-map changes are small
(251 bytes on 108 frames); full cold placement and EOF timing remain open.

**Attribute contract (2026-09-28):** keep seven colour bits (INK, PAPER,
BRIGHT), require FLASH=0. Sparse temporal attribute deltas already avoid
retransmitting unchanged colours; 98.6780% of active positions stay unchanged
between frames in the edited movie. Consider seven-bit packing only for
dense raw-attribute packets, measuring post-ZX0 sectors and unpacking costs
in local windows. See [format and audit](ATTRIBUTE_FORMAT.md).

**Automatic optimization workflow (2026-09-28):** the converter must apply
optimizations automatically. Choose compression and advance preparation in
a sliding time window, carrying the remaining disk capacity, predictor and
reservoir state forward. Do not search by repeatedly building and playing
whole alternative disk sets. Build one selected set and run complete EOF
validation as the final gate; local estimates and window tests cannot pass
that gate. Preserve original pixels/AY unless an explicitly authorized
quality policy is selected. Use the completed
[pressure-selection controls](PRESSURE_TOKEN_SELECTION.md) for calibration,
not as the production search workflow.

The first [windowed implementation](WINDOWED_OPTIMIZATION.md) is measured:
64-frame lookahead, carried producer/consumer and disk-space state, 6198
local comparisons in 3.215 seconds using cached costs. Search creates no
alternative images; the automatic prepared-stream runner builds one selected
set and checks all three disks through EOF. Actual lateness is **1186/4221**,
versus **1239** for Fast, but the model predicts only **595** late frames.
Calibrate that gap using local traces before another complete final run.
Keep the current images: both video gates fail, and generic media frontend
integration remains pending. Extend the same bounded workflow to other
measured encoder/preparation choices rather than reinstating whole-set search.

[Foreground-cost calibration](WINDOWED_MODEL_CALIBRATION.md) now corrects
metadata placement and adds measured packet transport and entry costs.
It reduces aggregate publication prediction error by **35.25%** across four
held-out archived selections, without new TRDs or Fuse runs. It still predicts
only **825** late frames for the observed **1186** of the window-selected set.
Measure queue-step control, background AY service and variable demand costs
in local windows next; do not treat this model as a release timing gate.

Fit the authorized edit in [movie_no_credits.json](movie_no_credits.json) on
at most three independently bootable TRDs. Preserve the main story and
post-credit scene through EOF, resolution, 25/3 fps and the existing 50 Hz
AY soundtrack. This fixture has 4221 frames. The converter and optimizations
must also support other videos; do not specialize player behavior to a scene.

Prepare each frame for publication at its nominal six-field deadline:
120 ms, zero late frames. Report every missed deadline. Separately check
the fallback of at most one field late, intervals of 5..7 fields and recovery
to the original schedule without dropped frames or accumulated drift.
Measure actual screen-publication OUT timing as well as field counters.
AY must update on every 50 Hz interrupt. A partial run cannot pass.

For local decoder substitutions, keep the compressed movie stream byte-for-byte
unchanged. The separately measured resident-audio format below changes
framing while preserving every video field and AY record. Count bootstrap/code size separately: a larger bootstrap can
still add disk sectors. Use all 128 KiB as useful, while accounting for both
screens, code, stack, AY/IRQ, TR-DOS workspace, tables and disk buffers.

## Current baseline and evidence

### Dither phase regression and five-level alternative (2026-09-28)

The [phase audit](DITHER_PHASE.md) reproduces opposite checkerboards caused
by reversing INK/PAPER while retaining the same half-tone pattern. A host
reference exchanges the two output scanlines for darker INK, preserving
every logical pixel's mean colour. Native dirty maps must include attribute
orientation changes relative to n-2: otherwise 321 cells across 108 frames
in the current input would retain stale phase. Production code is unchanged.

Implement and profile that correction with the existing two-bit stream first;
include cold checkpoints, both screens, AY interruptions and actual output.
Count added selector instructions and memory accesses before integrating it.

The user also requested five independently selectable coverages inside every
8x8 cell. The tested host alternative packs four radix-5 samples in ten bits
and uses canonical endpoints with nested 2x2 patterns. It supports all five
levels in one cell without Z80 division, but needs an unimplemented native
consumer and a proposed 2048-byte lookup allocation. It grows uncompressed
pattern data by 25% and was larger in all three 32-frame XOR/ZX0 controls.
Those controls exclude the full motion/Huffman/AY pipeline and cannot predict
TRD count. Keep the alternative out of converter defaults until the native
cost, actual compression and original-RGB quality are measured. Investigate
adaptive five-level cells within the existing bounded-window workflow;
do not evaluate multiple complete image sets to choose a format.

The user's [one-bit offset proposal](DITHER_OFFSET.md) is now measured as
0/25/50/75% versus 25/50/75/100%. INK/PAPER orientation can encode that choice
without extra bytes, but each cell still has only four levels. Cells with
both extremes require clipping: 0.59517% of active logical samples changed
on average. All three bounded XOR/ZX0 controls grew (0.7..3.7%), so retain
the experiment without adopting it. If both endpoints must remain, the
existing orientation already encodes 0/25/50/100% versus 0/50/75/100%.
Continue native phase correction for those current quartets; a new stored
selector is not required. The native phase implementation is still pending.

Use the [integrated Fast ZX0 player](FAST_ZX0_PLAYER.md) as the next
experimental baseline. Full playback retains all 25326 AY records at 50 Hz
and improves late frames **1321→1239** and bad intervals **783→744** against
the [Turbo periodic-drive player](INPLACE_KEEPALIVE.md) at `a84451d`.
Retain that Turbo build for paired comparisons. Both use 2462/2463/2462
sectors, with 82/81/82 free, and exactly the same compressed stream.
Neither is a release. The earlier
[foreground resident-AY player](RESIDENT_AUDIO_PLAYER.md) at `da369e6` and
the HL-reader configuration at `074e1e7` remain historical comparisons.
Generic converter defaults and the verified root release are separate.
The new root `ZX-video-fast-preview_part01..03.trd` set contains the measured
Fast experiment and is explicitly a preview.

The [lossless token-selection experiment](FAST_TOKEN_PLAYER.md) speeds the
Fast decoder by 12.0205%, spending 61133 extra stream bytes. Full playback
reduces late frames 1239→1149 and bad intervals 744→680, with exact AY and
unchanged decoded pixels. It remains optional: disk 1 regresses slightly,
only two sectors per disk remain free, and both timing gates still fail.
Use its reserve measurements to assess where advance work is useful before
changing the queue or selecting larger streams as a default.

- Current video stream: **1,818,909 compressed bytes**, 2,965,011 video-only
  packet bytes, 188 blocks, 7106 video sectors. The older muxed stream used
  1,919,945 compressed bytes, 3,083,375 packet bytes, 378 blocks and 7501
  video sectors. Tables are per volume; each disk initializes its own
  state. A compact predictor references frame n-1 while native-screen masks
  reference n-2. Removing an intermediate buffer must preserve both.
- The full HL-reader Fuse run still fails timing: 3073 late frames, 883 AY
  underruns, 660 intervals outside the fallback range. Per-volume rates:
  8.2823025 / 7.9802956 / 7.8841952 fps. All three reach EOF.
- Streaming ZX0 input integration and its full measurements are recorded
  in `8da95ed`.
  It preserves stream bytes but increases the summed publication span from
  1,854,669,649 to 1,863,745,874 T and AY underruns from 883 to 1006.
  Keep `--streaming-input` disabled. See the
  [saved summary](streaming_player_summary.json) and
  [historical implementation report](STREAMING_PLAYER_ru.md).
- The new [full CPU-stage profile](FRAME_HOTSPOTS.md) covers all 4221 frames
  with exact compact data and both complete screens. It totals
  **1,027,719,624 T**: reconstruction 60.36%, output 32.85%, metadata 6.19%.
  This excludes ZX0, copying, queues, IRQ/AY, ULA, ROM and disk latency.
- The [compact cursor experiment](COMPACT_CURSOR.md) now completes all
  4221 frames and all three Fuse volumes. Byte updates within a stripe save
  **4,355,295 deterministic frame T-states** with unchanged compressed data,
  code size and disk layout. AY underruns fall 883→869 and summed publication
  span falls by 1,063,621 T, but bad intervals rise 660→662. Retain
  `--compact-cursor` for measured work and keep both this result and HL-only
  as comparison points; it is not a release and does not pass timing.
- The [two-byte Huffman cache prototype](CACHED_HUFFMAN_LOOKAHEAD.md) uses
  E' for lookahead and moves the motion output cursor to HL'. All 4221 CPU
  frames and both complete screens match. Against compact cursor it saves
  **5,315,088 T** (0.5194% of measured frame stages); 55 frames are slower,
  by at most 50 T. The subsequent [disk integration](LOOKAHEAD_PLAYER.md)
  now enforces a 4702-byte payload limit and two readable guards in the
  existing 4704-byte window, at zero parser CPU or stream cost. All three
  independently bootable volumes complete: 3066 late frames, 845 AY
  underruns, 644 invalid fallback intervals. The summed publication span
  improves by 1,701,794 T with unchanged disk layout. Keep the optional
  cache for measured work; all three timing gates still fail.

The subsequent [larger-slot sector-streaming experiment](INPLACE_STREAMING.md)
now has complete native-block and all-three-disk Fuse evidence. All 188
blocks decode exactly, and the same three disks retain exact 50-Hz AY.
However, decoder/producer CPU rises **201,404,859 -> 221,455,714 T** and
late frames increase **1321 -> 1457**, bad intervals **783 -> 943**. Both
video gates fail. Keep the complete-input periodic-drive player at `a84451d`
as the larger-slot baseline. Do not enable this streamed variant by default.
It reduces individual transfer peaks but increases sustained work. A future
streamed decoder should avoid routine input-page checks when enough input
is already resident, prove the lower CPU cost first, then repeat full cadence
and AY verification. Preserve the previous and current rejected experiments.

The [cost-selected fast-fragment experiment](RESIDENT_FRAGMENTS.md) now also
fits all three independent disks, with 19/34/37 sectors free. All 4221 compact
frames and both complete native screens match; no frame-stage CPU regression
occurs. It saves 29,444,903 frame T, but adds 11,781,649 producer/ZX0 T and
151 video sectors. Complete Fuse playback retains exact 50-Hz AY and has
1237 late frames / 747 invalid intervals, versus 1321 / 783. Both video
gates still fail, and volume 1's maximum lateness grows 64 -> 72 fields.
Keep this optional data variant as a comparison, while retaining the roomier
`a84451d` baseline and unchanged release/defaults. Compare changes against
the same input policy so data and decoder benefits are not double-counted.

The [native-mask remeasurement](NATIVE_MASK_SELECTION.md) now builds and
plays all three disks too. It revisits the older capacity-rejected
`gray_optimal` rule under the current layout. Exact pixels and 50-Hz AY
are preserved. Frame CPU saves 6,373,807 T, but producer/ZX0 adds 1,774,469 T
and video adds 110 sectors. Full Fuse has 1268 late frames / 761 invalid
intervals; total publication span grows 141,810 T and volume 2's maximum
lateness grows 260 -> 262 fields. Do not adopt this global mask policy.

The [resumable optional-reader experiment](RESUMABLE_PACKET.md) is also
complete. It preserves all compressed video bytes and occupied sectors,
and 33 native draws now begin before the interrupted packet finishes.
Nevertheless, full Fuse worsens **1321 -> 1337 late frames**, **783 -> 797
invalid intervals**, and summed publication span by **425,442 T**. AY stays
exact at 50 Hz. Keep this implementation experimental and retain `a84451d`.

## Method: replace indexed access when the whole path is faster

Inspect the generated machine code and measured execution frequency.
Compare IX/IY memory operations with ordinary registers, `(HL)` or direct
addressing. Include address setup, cursor advances, all saves/restores,
branches, code size and extra stack depth. Check live flags and both register
sets across IRQ, calls and paging.

Representative instruction costs, excluding waits and IRQ, from the
[Zilog Z80 CPU manual](https://www.zilog.com/docs/z80/um0080.pdf):

| Operation | Alternative | T before → after |
|---|---|---:|
| `LD r,(IX+d)` | `LD r,(HL)`, address already prepared | 19 → 7 |
| `LD A,(IX+d)` | `LD A,(nn)`, constant address | 19 → 13 |
| `INC IX` | `INC HL`, equivalent cursor | 10 → 6 |
| `LD IX,(nn)` | `LD HL,(nn)` | 20 → 16 |
| Repeated indexed load | Reuse an ordinary register | 19 → 4 |

Do not sum these instruction savings without their surrounding code.
HL already addresses Huffman tables. SP must remain usable by IRQ; treating
input data as a stack risks corruption or long interrupt-disabled periods.

The completed HL-reader substitution is the reference example:
68 repetitions of `LD A,(IX+0); INC IX` (29 T) became
`EXX; LD A,(HL); INC HL; EXX` (21 T). Preserving HL' and setting up cursors
adds 45 T per call: **68 * -8 + 45 = -499 T/frame**, measured for every
frame, **-2,106,279 T** total. Compressed bytes and video sectors are unchanged.
See [the saved verification](hl_mask_reader_summary.json).

## Prioritized work

The user's advance-preparation proposal is recorded in
[Frame preparation reserve](FRAME_PREPARATION_RESERVE.md). A fresh audit of
the complete Fast traces confirms median decoded reserves **30148/9840/4 B**;
the hardest disk-2/3 windows still have **0..6 B** at every packet start.
The two-byte Huffman cache, 47616-byte decoded packet reservoir and one
compact-frame lookahead are different resources. First improve refill speed;
then assess a queue of predecoded changes with explicit n-1/n-2 dependencies,
expanded-command capacity, paging/copy cost and full cadence verification.

0. **Decouple AY delivery with a complete resident soundtrack.** The
   [resident-audio prototype](RESIDENT_AUDIO.md) stores each volume's exact
   AY records, tables and initial state in 13279/12262/12080 bytes. Video-only
   ZX0 plus that audio totals **1869817 bytes**, **50128 fewer** than the
   existing mux; all 4221 packets and 25326 ticks round-trip. Estimated free
   sectors with old fixed overhead were 71/66/63. The
   [actual integrated TRDs](RESIDENT_AUDIO_PLAYER.md) now leave **68/65/65**
   sectors free, with dirty-RAM boot and mocked swaps verified. The
   [Z80 decoder and paging bridge](RESIDENT_AUDIO_Z80.md)
   execute all 25326 records exactly. Code, expanded tables and data fit
   in **14230/13215/13037 B**, leaving at least **2154 B** in bank 4.
   The integrated format uses the audio-free parser, three video slots in
   banks 0/1/3, fixed bridges in retired code and bounded startup sections.
   Queue-only six-record service failed with 3830 AY underruns. Adding
   foreground service and increasing the batch limit to 31 eliminates all
   sound gaps through EOF on all three disks: **25326 exact ticks at 50 Hz**.
   The ISR is unchanged. The six-record CPU fixture still reports producer
   **9150603→52600652 T (+43450049)**; it is not the new scheduling total.
   Actual video sectors fall **7501→7158** and summed publication spans fall
   **1851904234→1816733868 elapsed T**. There are still **1745 late frames**
   and **1047 invalid fallback intervals**. Maximum lateness is 103/291/291
   fields; late runs recover 5/3/6 times, but disks 1/2 end late. Average
   8.333333 fps on disk 3 does not establish smooth playback.
   Obtain a complete new CPU replay and retain read/seek intervals separately.
   The [half-row cache integration](HALF_ROW_PLAYER.md) now completes all
   CPU frames and all three disks: frame stages save **15980003 T**, parser
   copies add **333459 T**, and ZX0 adds **7583 B / 30 runtime sectors**.
   Actual occupied sectors grow by 40; 53/52/53 remain free. Sound stays
   exact at 50 Hz, but late frames improve only **1745→1740**, with 1043
   fallback interval violations. Keep it optional and preserve the smaller
   baseline. The subsequent [uncontended half-row body experiment](UNCONTENDED_HALF_COPY.md)
   moves the sixteen LDIs into 33 of the old selector's 38 unused bank-2
   bytes. CALL/RET adds 27 T per half-row, **2659824 T** across all 4221
   fully pixel-checked CPU frames. Complete Fuse playback leaves
   each publication span unchanged, increases late frames **1740→1741**
   and bad intervals **1043→1048**, with byte-exact streams and identical
   disk usage. Reject this placement as a speed improvement; preserve its
   evidence. Capacity and AY cadence pass; both video timing gates fail.
   The frozen-producer FIFO model does not establish that resizing the
   existing AY queue fixes starvation; do not infer missing byte availability
   from a queue call's end timestamp alone.
1. **Reduce repeated reconstruction state work.** Use the bank-aware
   histogram to inspect cache maintenance (112,146,097 T), control
   (66,807,315 T) and no-op traversal (74,830,741 T). Identify redundant
   address reloads and saves; retain the existing fast no-op and selective
   cache paths. Low-byte tile/run cursor updates are now implemented and
   verified; do not count their saving again. Record useful work separately
   from removable overhead. Prioritize larger remaining costs over repeated
   one-instruction changes with a small measured whole-player effect.
2. **Audit remaining Huffman indexed loads and call boundaries.** There are
   1,203,077 indexed memory loads in the profile. A hypothetical 19→7 T
   substitution saves 14,436,924 T before setup costs. Use this as a gross
   ceiling for those loads, not a promised saving. Keep cached-byte and
   inline-patch optimizations already present. The two-byte cache now has
   complete CPU and integrated disk measurements: short symbols save
   7..11 T, long symbols add 18 T and setup adds 46 T/frame. Its packet
   contract, cold-installed inline code, bootstrap sectors and complete
   three-volume delivery are checked. Preserve that work and do not count
   the saving again. For other videos, reject an oversized optional
   configuration or retain the old decoder. Future register-allocation
   changes must preserve the two-readable-byte limit and IRQ state.
3. **Optimize pixel conversion and addressing.** Dense pixel work alone
   costs 136,520,064 T. Try reuse of addresses/lookup results while retaining
   the exact dither output and alternate-screen dependencies. Count writes,
   row/page transitions and ULA effects, not just dispatch instructions.
   Dense-output dispatch and whole-row fill tests have already been
   rejected below. Avoid a runtime scan for uniform rows in this stream;
   successful rows are too rare even under a zero-cost-fill bound.
4. **Revisit producer scheduling only with a cheaper input guard.** The
   streaming prototype shortens some disk bursts but adds too much CPU.
   Preserve EOF handling, unloaded-page protection, one-sector steps and
   IRQ safety. Measure the complete producer/consumer schedule before
   accepting a changed disk buffer or queue policy.
   The two-byte-cache trace has 460/397/619 frames whose foreground stages
   exceed six fields, and no late frames already native-ready at least
   1000 T before the nominal deadline. Empty-input waits total 134,642,123
   elapsed T, including producer work and disk service. Use these traces
   to distinguish burst buffering opportunities from sustained CPU cost;
   do not label all wait time removable overhead or fix only publication.
   The [in-place ZX0 reservoir experiment](INPLACE_ZX0_RESERVOIR.md) now traces
   all bytes of all three resident-video streams at 8/12/15.5/16 KiB block
   sizes. **15872-byte blocks** safely increase decoded packet capacity from
   **24576 to 47616 bytes**, with minimum sector-placement margins of
   **255/257/255 bytes**. Video shrinks **1832196→1818909 B**, runtime sectors
   **7158→7106**. Full 16-KiB output is rejected: **180/183 blocks** overwrite
   unread input, even with exact-end placement. The old 16-KiB compression
   study used another stream and separate input storage and does not prove
   this layout. Preserve both results.
   All 364 old and 188 new blocks also pass native turbo decoding in separate
   and overlapping memory, with identical read/write traces and zero layout
   instruction delta. Larger blocks increase naked-decoder cost
   **160653056→162913389 T (+2260333)**. This excludes the coroutine, queue,
   carry copies, IRQ/ULA and disk waits; only integrated delivery can decide
   whether the reserve and sector savings repay that cost.
   The [integrated larger-slot experiment](INPLACE_SLOT_PLAYER.md) now builds
   and completes all three independent TRDs: **2461/2463/2462 sectors** used,
   **83/81/82 free**. It changes the output base and queue bias, handles split
   headers and the shared tail, and preserves live LZ history. The disk
   adapter advances regions at FFFF/0000, not E000; the new producer restores
   its owned slot. Full native producer/coroutine execution checks every
   packet byte and counts **200004910 -> 201404951 T (+1400041)** with a frozen
   idle clock, excluding ROM/IRQ/ULA and actual queue quotas.
   The first complete run exposes long-idle disk failures: 15 read retries,
   252 AY underruns. A 64-field pre-read SEEK/HLD check removes all retries,
   but successful reads can still wait about 0.64 seconds. The corrected
   complete run has **1496 late frames**, **914 invalid intervals**, and
   **24 AY underruns**, versus 1745/1047/0 in the smaller resident baseline.
   Preserve both attempts; neither is a release or cadence pass.
   [Periodic drive maintenance](INPLACE_KEEPALIVE.md) now runs during queue
   waits and foreground frame work. All three volumes finish with **zero
   AY underruns, record gaps/duplicates and missing/duplicate IRQ fields**;
   50-Hz AY delivery passes again. The 185 SEEK/HLD calls consume 76670
   elapsed ROM-service T; maximum sector read falls to about 43.9 ms.
   Video improves to **1321 late frames and 783 invalid intervals**, still
   failing both timing gates. All video/AY bytes and 7106 reads are unchanged;
   actual occupied sectors are 2462/2463/2462. Retain the maintenance hook
   in this experimental path; common checks add 279 CPU T each, and their
   actual total call count is not replayed. All tested path counts are saved.
   Next target **block-acquisition bursts and usable reserve**: worst packet
   transfers still approach 1.9 million elapsed T despite short individual
   reads. Compare earlier acquisition or consumption of partially acquired
   compressed input, preserving overlap safety, live history, slot ownership
   and AY. Keep the earlier streaming-input regression as a comparison and
   measure sustained CPU/disk delivery before adoption. Larger decoded
   packet storage is not extra native-screen buffering and cannot establish
   cadence on its own.

   The first **resumable optional packet acquisition** experiment is
   [complete and rejected as a default](RESUMABLE_PACKET.md). The earlier
   [trace analysis](NATIVE_MASK_SELECTION.md) found 64 baseline read-ahead
   calls that span publication while the following compact frame is already
   prepared; 16 are followed by a late frame. The largest post-publication
   transfer tail is 1,542,815 elapsed T. These are blocking intervals, not
   CPU savings. The implemented two-byte parser state resumes at existing
   queue boundaries; actual full traces verify 33 earlier draws. Exact
   packets, split length fields, slot EOF and IRQ preservation pass, but
   global checks add 54 T per mandatory queue gate and 27 T per mandatory
   demand dispatch. Smaller optional ZX0 quanta also add work. Both timing
   gates still fail and total delivery worsens. A next variant should keep
   the original mandatory path, using an optional-only consumer entry or
   safely restored temporary routing. Count its setup/restoration, preserve
   partial header/body state and original deadlines, then repeat complete
   delivery measurements. Do not repeat the current global-gate policy or
   infer a sustained speedup from its isolated responsiveness improvement.

   The subsequent [separate optional consumer](OPTIONAL_PACKET.md) now
   completes that proposed comparison. Its 324-byte bank-7 helper retains
   the original required consumer bytes, with zero extra stack or data
   buffers. Required queue/demand overhead is zero; resumable parser
   dispatch still adds 245 T per fresh packet in the direct-entry fixture.
   Full EOF playback reports **1329 late frames / 790 bad intervals**,
   better than global gating (1337/797), worse than the original (1321/783).
   Capacity and all AY bytes/50-Hz timing pass, both video gates fail.
   Do not enable it by default or repeat this completed variant. Future
   scheduling work must reduce difficult-scene work or prepare more of it
   before those runs; account for reservoir capacity and overlapping stages.

   The [complete decoded-reserve analysis](LATE_RESERVOIR.md) now confirms
   sustained depletion: median reserve is 30092/9263/4 bytes by volume.
   The hardest 32-frame windows on disks 2/3 have at most six bytes ready at
   every packet start; transfer accounts for more than half their elapsed
   foreground work. Next remeasure short-match removal in the unchanged ZX0
   format with the present 82/81/82-sector headroom. The old adaptive search
   had only 275/58/746 spare bytes and does not settle this larger-budget case.
   Verify overlap across sector alignments, native coroutine work, added
   reads and complete selected playback. The saved free-input projection is
   hypothetical, not a feasibility proof or a substituted release criterion.

The [direct alternate-HL target-load hypothesis](DIRECT_MOTION_TARGET.md)
is now **verified as a CPU prototype**. Replacing
`LD HL,(target); PUSH HL; EXX; POP HL; EXX` (**45 T**) with
`EXX; LD HL,(target); EXX` (**24 T**) and moving the common load to phase
zero saves exactly **21 T** on each of **28,773** nonzero-phase entries.
Setup totals are **1,294,785→690,552 T**; all 4221 exact compact/native
frames confirm **-604,233 T**, or **0.059352%** of measured frame CPU.
There are no slower frames. Five tests cover vectors/edges, mixed frames
and real AY/publication IRQs, including EXX boundaries. The earlier DE'
allocation's 489,141-T estimate remains historical.

The prototype adds **3 code bytes**, leaving five bytes before the 8FC0h
helper. It changes primary HL after phases 2/6; current callers overwrite
it immediately, and the installer checks that contract. Integration must
relocate the retired patch region reused by bank-2 ZX0 from
8DF2h..8F09h to 8DF5h..8F0Ch and rebuild all metadata/references. The movie
stream is unchanged; compressed bootstrap size and actual disk timing are
not measured. Keep it optional until independent boot, sector budget and
all three full playback runs pass. This small saving alone does not resolve
the remaining publication deadlines.

## Priorities after complete player profiling

The [2026-09-27 profiling report](PLAYER_PROFILING.md) combines fresh
instruction profiles with all seven archived three-volume playback variants.
Its [auditor](profile_player_comparison.py) partitions elapsed time without
double-counting disk calls or drawing during a suspended packet acquisition.
No player/stream changes are made by this analysis (0 T / 0 bytes).

- Fresh current-frame CPU totals **1,017,445,008 T**: reconstruction
  **59.96%**, native output **33.19%**, metadata **6.25%**. Dense/sparse
  pixel operations cost **217,109,804 T**, Huffman **125,825,146 T**, and
  cache filling **112,146,097 T**. Remaining indexed memory loads cost
  **9,586,716 T (0.94%)**, so prioritize register substitutions by their
  complete path cost rather than expecting them to dominate the result.
- In the retained player's publication window, reconstruction takes
  35.69%, native output 19.07%, disk service 11.85%, transfer outside disk
  calls 9.94%, and metadata 4.33%. The remaining 19.13% contains background
  work, audio, control and waits; do not treat it as measured idle time.
- The fresh full required-reader fixture spends **190,422,888 T in ZX0**,
  **50,177,846 T in packet copying** and **11,366,156 T in queue control**.
  It has mocked ROM and a frozen clock. Its 63,590,055 metadata T are also
  in the frame fixture: never count them twice or call the combined
  fixtures a complete integrated CPU measurement.
- Only **58,959,456 T (30.96%)** of ZX0 is the actual LDIR copy; the other
  **131,463,432 T** goes to parsing, setup, boundaries and suspension.
  Mean match/literal copies are **4.2901 / 4.8065 bytes**. Prioritize
  short-run dispatch and demand-boundary costs before a blanket long-copy
  unroller. Preserve the stream for runtime-only substitutions. Keep the
  separate short-match-removal/sector-headroom encoder experiment above.
- Keep native pixel conversion, Huffman, motion-cache filling and patch
  dispatch high in the CPU work list. Rank both complete-movie and
  difficult-scene costs using the saved per-frame profiles. Do not present
  already active unrolled packet/cache copies or black-border omission as
  new optimizations. Respect compact n-1 and native n-2 dependencies.
- A zero-copy packet proposal must save enough of its measured copy cost
  to pay for any extra paging/table accesses and preserve slot ownership.
  The current transfer already uses 16-T LDI for each decoded byte.
- Add paired audio-service, background-producer and wait trace points in
  the next actual changed-player measurement to resolve the unclassified
  elapsed bin. Existing archive traces do not isolate all those costs.

The best late-frame count among the seven configurations is still
**1237/4221** (fast fragments), with **747** invalid fallback intervals;
it adds 151 video reads and worsens disk 1's peak. Neither CPU ranking nor
mean fps replaces the complete nominal/fallback/AY gates. Keep the retained
baseline and release unchanged while developing the next measured candidate.

## Unchanged-stream ZX0: measured CPU candidates

The unchanged-stream [faster ZX0 CPU experiment](FASTER_ZX0.md) is now
complete on all 188 retained blocks. Adapted Fast costs **183,122,436 T**
versus **189,573,555 T**, saving **6,451,119 T (3.403%)**; producer+decoder
saves **3.203%**. Tuned Turbo saves **2,300,609 T (1.214%)**. Both keep
all **1,818,909 stream bytes and 7106 sector reads**, improve every complete
block and preserve exact in-place input/output. Fast has 62 of 11584 calls
slower by at most 69 T; tuned Turbo has none. Four test groups, including
real AY IRQ code after every instruction and arbitrary demand targets, pass.

The [Fast disk integration](FAST_ZX0_PLAYER.md) now completes all three
independently bootable volumes with unchanged stream/occupied sectors and
exact 50-Hz AY. Late frames fall **1321→1239**, invalid intervals **783→744**.
The publication-span reduction is only **850900 T / 0.0469%**; both video
gates still fail. Keep Fast as the next experimental baseline and tuned
Turbo as the smaller CPU-only alternative. Fast occupies **401 code/state bytes
(+87)**: 7C00h..7C7Dh helpers and 8DF2h..8F06h hot core. It reuses retired
RAM without shrinking buffers or requiring prior-disk state. Both variants
assume non-wrapping C000h..FDFFh output; they are not replacements for the
old wrapping half-bank decoder. The installed build remaps 22 external
operands, verifies the rebuilt producer and updates the cold bridge overlay.
Dirty-RAM boot and mocked disk swaps pass. Account for the direct-HL
prototype's shifted core bounds if combined in a later experiment.

The baseline executes 2253636 decoder T from bank 5; Fast executes 4530562.
Full ULA/ROM/disk/publication/AY measurements are now saved; do not apply the
CPU percentage to whole-player speed or declare a release. The
[saved auditor](audit_faster_zx0.py) verifies code,
streams and all CPU sums. Preserve these results before further branch,
gamma or Mega experiments; the latter remain unmeasured.

## Avoid repeating rejected or completed experiments

- [Positional no-op run tags](TAGGED_NOOP_RUNS.md) now use the existing
  fast-fragment dispatch and exclude static edge stripes. This removes the
  old experiment's per-motion-tile test, but still costs 43,634 extra ZX0
  bytes / 172 video sectors. Three actual TRDs fit with 7/32/32 sectors free.
  Complete Fuse playback has 1315 late frames versus 1321, but 786 bad
  intervals versus 783; the total publication span falls by only 70,914 T.
  Do not adopt this format as the default. Preserve the separate CPU and
  disk results: the 481 frames whose baseline work exceeds six fields
  actually add 173,339 frame-stage T, despite the aggregate CPU saving.
- The September 25 [cost-selected fast-fragment experiment](FRAGMENT_COST_SELECTION_ru.md)
  used an older 8-KiB-block/bootstrap budget. Its 64-bit local allowance saved
  8,898,970 frame-stage T across all 1300 frames of volume 3, but added 11,616
  ZX0 bytes and exceeded that disk's capacity. Capacity has since changed.
  Its [remeasurement with resident AY](RESIDENT_FRAGMENTS.md) is now complete
  on all three volumes, retaining 15872-byte blocks, exact pixels and original
  checkpoints. Volume 3 reproduces the old candidate bytes, but its current
  frame-stage saving is 8,545,530 T. All-volume measured component CPU saves
  17,663,254 T; final ZX0 grows 38,682 bytes. Use the complete reports for
  future selection work, including the grouping by baseline foreground work.
  The 150-T/symbol ranking term is historical, not a lower bound for today's
  134-T short decoder. Do not repeat only the local pre-ZX0 estimate.
- The current stream already rounds bands with at least 18 changed cells
  to all-FF masks. A new nearly-dense test admits no extra bands and would
  add 531,846 T. A full-eight-cell helper with a new test on every nonzero
  group is estimated to add 1,056,003 T. Both are rejected; see
  [the probe and assumptions](FRAME_HOTSPOTS.md).
- Changing the encoder's density threshold is a separate stream-size
  experiment. The [complete native-mask remeasurement](NATIVE_MASK_SELECTION.md)
  now checks host-selected sparse/full maps, zero groups, band parity, every
  compact/native byte, actual ZX0/capacity and full delivery. All three disks
  fit with 49/38/48 sectors free, but a 4,599,338-T net measured component
  saving does not compensate the complete delivery result: summed publication
  span grows 141,810 T. Do not adopt the global CPU-optimal maps or repeat
  their stage-only projection. Keep the prior 8-KiB `gray_optimal` and
  `compact_16` records; the current larger-slot result does not test the
  latter size-first rule or a targeted mix of policies.
- Whole-row zero/uniform detection was measured on all 83,652 dense rows.
  Only 90 are zero and 332 uniform. Charging just immediate failures while
  making every other test and successful fill free still adds at least
  **1,314,132 / 1,022,816 T**. Reject these two dispatch strategies; this
  does not rule out partial-row methods or precomputed hints. See the
  [complete input profile and lower-bound calculation](FLAT_DENSE_ROWS.md).
- Uncontended compact/cache, compiled masks, cached Huffman bytes, inline
  ZX0 literals/matches, demand decoding, AY-wait prefetch, fast IM2 return,
  Gray-order sparse cells and black-border omission have already been
  investigated. Preserve measured benefits; do not present them as new.
- Removing zero-mask writes alone has a small gross bound and adds state
  checks. Packet-ready guards and current streaming input failed to improve
  the full delivery results. Keep their reports and disabled options.
- RLE, LZSA2 or other block codecs do not automatically retain ZX0's size.
  Reuse the [adaptive-codec results](ADAPTIVE_CODECS_RESULTS_ru.md) before
  proposing another format. Vector encoding remains deferred.

## Verification required for each implementation

1. Save the old and new generated instruction paths, their absolute Z80
   T-states, delta, assumptions, RAM layout and stack requirements.
2. Test meaningful boundaries and IRQ interruption points. Execute all
   frames and compare compact data, both complete screens, AY, cursors,
   buffer ownership and independent-volume startup. Verify stream hashes.
3. Build independently bootable images and check bootstrap size, total
   sectors and LFS rules. Do not replace release TRDs with an unverified
   experiment. Never require retained RAM from the preceding disk.
4. Run all volumes through EOF in Fuse. Report CPU separately from ROM,
   disk acquisition and contention. Check actual nominal deadlines,
   fallback bounds, recovery of late runs, AY continuity and sector order.
   State limitations of emulator timing and any missing physical-drive run.
5. Keep scripts, reports and unsuccessful attempts in the same focused
   commit as their changelog entry. Write maintained documentation and
   agent instructions in English; add Russian translations only on an
   explicit request for that document or task.
