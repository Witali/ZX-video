# Focused optimization task

Updated 2026-10-01. Use this brief to continue the project in this or a new
chat. This document scopes work; it does not start an automatic goal.

## Project objective

Fit the authorized movie edit on at most three independently bootable TRDs,
keeping resolution and 50 Hz AY. The user requested 10 fps on 2026-10-01;
prioritize exact five-field video
deadlines. All quality, fallback jitter, memory, cycle accounting, LFS and
release requirements in [AGENTS.md](AGENTS.md) remain mandatory. The generic
converter must also support other videos.

## Separate audio subproject checkpoint (2026-10-03)

Latest user clarification: allow **60 seconds** for Spectrum audio
preparation. This supersedes the earlier39.904-s limit below; retain the
old raw128 benchmark and measured results as historical evidence. The user
also permits later decoder optimization. Final PDM >=20 dB, full-source
preservation and speed within2% remain mandatory.

**Completed delivery:** the [IMA3 waveform disk](audiobook-beeper/IMA3_WAVEFORM.md)
now measures **20.07106694 dB in both full cold Fuse loops**, on the same
complete186880-sample source and unchanged comparison filter/clock.
It retains70080 compressed bytes,93440 resident bytes, all128 KiB RAM,
progress and looping playback. Native/Fuse all-bit, every preload byte,
FFmpeg IMA and normal sound capture checks pass. Both phase deltas are0 T,
speed error is-0.043271%, and normal boot to audio is27.254263 s (<60 s).
Ordinary playback remains423 T/sample, delta0; silent cycle padding adds2 T.
Use `ZX-audiobook-IMA3-waveform-test.trd` and the saved completion audit.
The 20-dB goal is satisfied for this input in Fuse, not certified on physical
hardware or arbitrary recordings. Reuse the proof; do not repeat tests or
promote the unexecuted width128 host candidate without a new task reason.

The user made **20 dB final PDM SNR mandatory** after the IMA3 preview,
then requested Speex. The [Speex audition](audiobook-beeper/SPEEX_STUDY.md)
is complete on the same full source: fixed-point decoding at 18.2/24.6k
without optional highpass/enhancement gives 24.752/27.823 dB, or
21.054/22.037 dB after the existing IMA encoder, at 6.946:1/5.155:1 with
a 32-byte framing allowance. These are **before PDM**. A verified exact
Z80 lookup product costs 111 T; synthesis products alone project58.484 s,
exceeding39.904 s before other work. Reject that strategy, not all possible
ports. Reuse the saved30 API cases,10 FFmpeg cases and1376146 arithmetic
checks. No Speex TRD has been produced. The later IMA3 waveform result above
satisfies the final20-dB objective without claiming a completed Speex port.

The earlier independently bootable IMA3 disk was integrated as a
[listening preview](audiobook-beeper/IMA3_PRELOAD.md). It expands 70080
audio bytes into the unchanged 93440-byte resident IMA allocation with
progress, then loops through the existing PDM player. Cold Fuse expansion
takes 1.935179 s; full native and two-loop cold-Fuse checks pass. The user
reported vibration in the first uncorrected test; PC timing compensation
raises fixed-clock SNR from -3.004 to 18.171/18.153 dB. Speed error is
-0.04327%; final phase deltas are -2/0 T. It remains below the 20-dB goal;
do not replace the 21-dB four-bit quality reference or claim vibration-free
physical playback. Reuse this evidence rather than rerunning the pilot.

Three optimization rounds for each selected decoder are complete. Exact
IMA3-to-IMA expansion falls from 58750730 T / 16.564 s to 6657930 T / 1.877 s;
PVQ3x512-to-PCM falls from 31352427 T / 8.839 s to 17460865 T / 4.923 s.
Full input matches independent references at every round. These are native
CPU/buffer measurements, excluding disk, ULA and final bank integration;
PVQ additionally excludes IMA re-encoding. These standalone probes did not
qualify a disk; the later IMA3 integration is described above.
Reuse [the round-by-round evidence](audiobook-beeper/DECODER_OPTIMIZATION_ROUNDS.md).
The exact IMA subset expansion was chosen for integration because it avoids
a separate PCM-to-IMA encoding stage.

Latest scope: compression of 5:1..10:1 relative to mono 8-kHz PCM16;
higher ratios are welcome when sound preservation permits. The user chose
three-bit IMA and predictive VQ for three Z80 optimization rounds each.
Keep the [research backlog](audiobook-beeper/CODEC_RESEARCH_BACKLOG.md)
for other formats. PC encoding complexity is unrestricted. The startup
budget is now60 s; the 25..30-dB codec quality target is advice.

The follow-up10:1 study is complete; no new decoder is selected for release.
The best simple VQ at11.107:1 measures14.213dB before IMA,13.744dB after,
and41.946s for the full native decode/IMA probe before ULA and final writes.
It fails the user's fidelity intent and39.904s startup limit. Encoding
complexity on PC is unrestricted. Proposed codec25..30dB / finalPDM20dB
quality gates are recommendations; preserve the same source and report
rate/quality/CPU separately. Reuse the
[measured study and primary-source shortlist](audiobook-beeper/TEN_TO_ONE_CODECS.md)
instead of repeating its dictionary/DFPWM sweep. ADPCM-XQ-style PC search
is the practical next direction; Speex11k and Opus12k are listening
references, with no verified Z80 decoder here.

In the separate `codex/lpc-ima-preload` worktree, the actual LPC-to-IMA
preloader and both progress bars pass complete native byte/RAM checks but
are **rejected**: cold Fuse conversion takes657.181 s. The corrected user
limit is twice a raw128-KiB read:19.952*2=39.904 s. The user subsequently
rejects LPC timbre changes and requests alternative waveform codecs with
10:1 compression relative to mono8-kHz PCM16; PC encoding cost is unrestricted.
Do not treat the LPC prototype as a playback release. Reuse
[its evidence](audiobook-beeper/LPC_PRELOAD.md).

The waveform-aware PC encoder retains the complete original 186880-sample
control excerpt and 93440-byte live IMA stream. Two complete cold Fuse 128
loops now measure **21.01069 dB** against the original 8-kHz PCM8 clock,
at **-0.04327%** speed error; native/Fuse bits, predictors, memory, paging,
loading and normal-speed sound capture pass. Ordinary player cost remains
423 T/sample (delta 0). This is an input-specific emulator result, not a
physical hardware test or a guarantee for every recording. The different
initial-prefix host probes remain below 20 dB and lack new execution traces.
The generic converter default and root historical disks are unchanged.
Reuse [the complete evidence and new disk](audiobook-beeper/WAVEFORM_IMA.md).

For the user's denser-compression request, the completed
[codec study](audiobook-beeper/DENSE_CODECS.md) selects predictive VQ3x1024
as the next implementation candidate: 13.38% fewer bytes including the book,
0.625-dB codec loss, 100.25 versus 131 native decoder T/sample on average.
Its 216-T boundary path needs prefetch/interleaving; the separate 8196-sample
native probe does not prove full real-time PDM playback. Do not repeat the
size/quality sweep or present the candidate as an integrated player.

## Completed delivery: four refined A/V disks

The user rejected the 15-disk count and requested at most four disks, keeping
the refined picture, new AY50 soundtrack and 10 fps. The full 5066-frame movie
now fits four independently bootable root `ZX-video-refined_part01..04.trd`
images: 2464/2476/2542/2543 occupied sectors. The dynamic dictionary replaces
rows throughout playback; every rendered RGB pixel and all 25330 AY states
remain exact. Full native, cold Fuse, actual predecessor-EOF continuation and
complete screen-byte checks pass for the entire set.

The user's explicit one-field fallback is used: cold starts have one nominal
miss (disk 3 local 933, recovered at 934); sequential playback adds disk 4 local
576, recovered at 577. Actual maxima are70907/70908 T, with no excess beyond
20 ms, invalid field intervals, drift, dropped frames or AY gaps. This is
**not zero-late playback**. The delivery report keeps `release: false` and
`preview_only: true`, with `user_authorized_delivery: true` and the explicit
fallback gate. Root parts 5..15 are retired; historical evidence and the
three-disk 25/3-fps compatibility set remain intact. See
[usage](ZX-video-refined.md), [full report](toolkit/refined_four_report.json)
and `.tmp/refined-four-candidate/`. Do not repeat complete-set measurements
without a material change. The four-disk delivery objective is satisfied;
zero-late playback and the longer-term three-disk target remain future work.

### Current checkpoint: CB46 capacity fits; timing remains open

Latest user steering (2026-10-01): improve compression at unchanged decoding
cost. Prioritize host-side encoding decisions, identical pixels/AY and the
existing player. Compare compressed bytes/sectors AND measured native cycles;
do not accept a smaller stream that increases decoding cost. Reuse one saved
window before any full-set rebuild. Dynamic row replacement is already working.

Latest encoder result: align row indices with their raster bytes and uniform
cell-book indices with the matching row index, then remove selected two-byte
LZSA2 matches only as needed to meet each original block's CPU budget.
The unchanged [4096,4352) window shrinks **185681 ->183997 video bytes**,
**726 ->719 video sectors**, **781 ->777 total occupied sectors**. Every one
of 16 blocks is no larger and no slower to decode. Independent decoder totals
are **16049945 ->15978979 T**; maximum 256-byte-quota slice 22323 ->22104 T.
Renderer code and every frame's counted renderer operations are identical.
All 256 native/Fuse screens (1769472 bytes), 1280 AY ticks and 719 runtime
sectors are exact. Timing still fails: nine late frames, all over one field,
maximum six fields, two invalid intervals; runs 123..123 and 237..244 recover
at 124 and 245. Compare with the baseline's eight misses / maximum 7 (or8)
fields / four invalid intervals. Do not describe aggregate CPU gains as an
every-frame delivery guarantee. Root images remain unchanged.

Reuse `.tmp/dictionary-numbering/budgeted/`, `.tmp/dictionary-budgeted-window/`
and [evidence](toolkit/same_cost_compression_report.json). Reproduce with
`probe_dictionary_numbering.py --variants flat`, `fit_lzsa2_cpu_budget.py`,
then `rebuild_cell_player.py --dictionary-probe <directory>/budgeted` and
the existing four flags (without `--streaming-lzsa2`). The budget fitter is
encoder-only and measures every accepted block with the independent Z80 core.
Do not rerun the unsuccessful distance-only search: exact 187-layout checking
and all 16 real blocks saved zero bytes (731 T only). General book/raster
alignment was also rejected because it increased decoder work.

Full-volume follow-up is complete and rejected: on part 4 [3744,5066), the
same numbering/fitter saves 3256 bytes and 348712 decoder T-states overall,
but blocks 2/5/17/18/32/33 exceed their original byte budgets by
9/26/22/16/52/56 bytes. Do not build this candidate or relax the block guards.
Reuse `.tmp/dictionary-part04/` and
[full-volume evidence](toolkit/full_volume_dictionary_report.json).

The existing four-slot/cache part 4 now has a complete native/Fuse timing
baseline: 1322 exact native screens, 6610 real AY ticks, 2434 exact runtime
sectors, 2543 occupied sectors. Full Fuse screen-byte capture was not run.
There are 29 nominal misses /28 beyond one field, maximum 23 fields, 23 bad
intervals. Runs 378, 588..599, 603..608 and 617..626 recover at
379/600/609/627. Reuse `.tmp/sector-cache-part04-capacity/work/part04/`
and `.tmp/sector-cache-part04-profile.json`; do not rerun this baseline.

New frame-123 diagnosis: packet acquisition has zero disk service or empty
wait, with three complete slots available. Between publications a physical
read consumes 136605 elapsed T and drawing takes 225965 T. Full part 4's
isolated frame 378 similarly has four ready slots and 156777 disk T. These
are optional-background-read admission stalls, distinct from sustained
queue depletion in the longer late runs.

Optional-read admission is now tested and rejected. On the same 256-frame
budgeted stream, a four-field margin gives 30 misses /max38 /15 bad intervals
and an unrecovered tail. A two-field margin gives 11 /max15 /7, recovered at
248; baseline 9 /max6 /2, recovered at 124 and 245. Both eliminate the isolated
frame-123 miss but starve the following burst. Both variants preserve all
256 native/Fuse screens, 1280 AY ticks, 719 runtime sectors and 777 occupied
sectors. There are 1680 admission tests plus instruction-boundary publication
race checks. Keep `--optional-read-gate` disabled; do not sweep more margins.
Reuse [evidence](toolkit/optional_read_gate_report.json),
`.tmp/optional-read-safe-window/` (four fields) and
`.tmp/optional-read-last-field-window/` (two fields).

The final branch-bypass variant now has complete cold/native/Fuse content
evidence for both the saved 256-frame window and full part 4. The window
improves 8 misses /max7 /4 bad intervals ->2 /max1 /0; local 123 and 232 recover
at 124/233. Actual OUT deviation reaches 70914 T (six T beyond one field), so
strict fallback does not pass. Full part 4 changes 29 /max23 /23 bad intervals
->31 /max21 /17, with late runs 378, 591..603, 614..629 and 687 recovering at
379/604/630/688. All native/Fuse screens, AY and sectors are exact; used
capacity is 2544 sectors (one extra bootstrap sector, same video bytes).
Do not select this for release or combine it with the rejected read gate.
Reuse `.tmp/streaming-lzsa2-bypass-window/`, `.tmp/streaming-bypass-part04/`
and [full evidence](toolkit/streaming_bypass_playback_report.json).

The direct header guard is now implemented as opt-in
`--streaming-lzsa2 --direct-lzsa2-header`. Independent Z80 tests confirm
96 ->46 T per available header, saving 50 T. AF is dead at token entry;
AF', HL/DE/BC and suspension remain exact. Explicit `token_guard` and
`token_body` labels replace `Token+3`. Defaults generate identical archived
decoder bytes. Three unit tests /512 AF cases, 40 component blocks and 240
independent full-flags cases pass. Forced-prefix component totals fall
25878233 ->23879878 T. See exact wait/resume path deltas in the changelog.

Both cached scopes have complete cold/native/Fuse screens, AY and sector
verification. Window [4096,4352): two isolated misses, max1, no invalid
intervals, recovered at 124/243; actual max70917 T still exceeds one field.
Full part 4: 31 ->22 misses, 30 ->20 beyond one field, max21 ->15 fields,
17 ->13 invalid intervals; runs 378, 593..601, 615..625 and 685 recover at
379/602/626/686. Streams and occupancy remain unchanged: window 781 sectors,
part 4 2544. Retain the speed improvement as opt-in; neither timing gate
passes. Reuse `.tmp/direct-lzsa2-header-window/`,
`.tmp/direct-lzsa2-header-part04/` and
[direct-header evidence](toolkit/direct_lzsa2_header_report.json).

Earlier prefix admission is tested and rejected. Starting with one completed
slot remaining costs 30 vs27 T (+3) per incomplete-input admission; decoder
instructions and complete-input bypass remain identical. Forty independent
admission cases pass. Window misses increase 2 ->14, max1 ->10 fields,
invalid intervals 0 ->6; recovered at124/252. Full part 4 misses increase
22 ->48 (47 beyond one field), max15 ->30, invalid intervals13 ->32; runs
378,585..609,611..632 recover at379/610/633. Exact media and occupancy are
unchanged. Keep `--early-lzsa2-prefix` disabled. Reuse
`.tmp/early-lzsa2-prefix-window/`, `.tmp/early-lzsa2-prefix-part04/` and
[evidence](toolkit/early_lzsa2_prefix_report.json); do not repeat this sweep.

Invisible attribute removal is implemented with future-visibility checks
and conservative per-block fallback. The bitmap/dither and every rendered
RGB pixel stay exact; only unused attribute bits differ. No later write is
added. Window: 185681 ->185605 bytes (no sector saved),16049945 ->16036695 T,
133 removed writes /5562 renderer T saved. Full part 4 first failed 8 block
budgets; freezing 238 overlapping frames and replanning histories yields
**622695 bytes /2433 video sectors**, 55 blocks individually no larger or
slower, 55754985 decoder T (-53171), 718 removed writes /33337 renderer T saved.
Reuse `.tmp/invisible-attributes-part04-guarded/round01/` and
[evidence](toolkit/invisible_attributes_report.json). Do not repeat this search.

One full direct-header playback build is at
`.tmp/invisible-attributes-playback-part04/`: 2543 occupied sectors, complete
cold/native/Fuse screens and AY checks. Actual timing still fails: 22 nominal
misses, 21 beyond one field, max 15, 11 bad intervals; runs 378,593..602,615..625
recover at 379/603/626. This is a small encoder saving, not a release fix.
Keep defaults/root images unchanged. The opt-in cached rebuilder accepts
`--invisible-attributes-probe <selected folder>` and rechecks RGB equivalence.

Generic consolidation is complete as opt-in `convert_video.py --video-codec
cb41 --guarded-cb46 --fps 10`. It selects the measured player components as
one profile and enforces per-original-block byte/CPU budgets automatically;
otherwise it keeps original packets/streams. The saved window reproduces
185605 bytes and 16036695 T exactly, with nine distinct recompressions.
The initial short-video build exposed an 8D98h decoder/renderer overlap;
build-time relocation now pins the unchanged decoder to 8D74h, preserving
public entries, producer bytes and every instruction's absolute T-state count.
The generic planner checks actual fixed AY trees/tail and the B900h cache gap.
Twenty-one tests plus five generated media cases pass: seven test TRDs,
23 frames /158976 full screen bytes, 115 AY ticks, zero nominal misses and
both modeled-ROM swaps of a three-disk fixture. These are integration checks,
not sustained movie evidence. Reuse `.tmp/generic-guarded-window/`,
`.tmp/generic-guarded-colour-fixed/`, `.tmp/generic-guarded-edge-cases/` and
[archive](toolkit/generic_guarded_cb46_report.json). Defaults/root releases
remain unchanged; do not repeat these fixture builds.

Side-only disk reads now pass the saved window and full part 4. Runtime
tracks already follow the minimum one-way cylinder path; remove redundant
same-cylinder SEEK and READ-84 settling, retaining a 717 T (>200 us) side
pause. Actual cylinder changes, FEh idle recovery, FFh dispatcher, periodic
head maintenance and short-read retry stay intact. Decoder/renderer/media
bytes are unchanged. RAM helper side paths cost 401 ->1009 T (side 1) and
391 ->999 T (side 0); cylinder-side-0 costs 391 ->456 T. These small CPU
increases replace much longer controller waits; ROM/IRQ/ULA are separate.
Helper 89 ->107 bytes, two extra stack bytes, no extra disk sector.

Window [4096,4352): 45 ->22 read-path SEEKs, **2 ->0 nominal misses**, actual
OUT phase deviation at most16 T. Full part 4 [3744,5066), with the accepted
invisible-attribute stream: 152 ->76 SEEKs, **22 ->0 nominal misses**, max19 T,
zero bad intervals/retries/AY underruns. Full cold/native/Fuse screen-byte
checks pass for both scopes; 781/2543 occupied sectors are unchanged.
Generic `--guarded-cb46` enables this automatically; a new three-disk colour
fixture passes all ten frames, 50 AY ticks and both modeled-ROM swaps.
Reuse `.tmp/side-only-seek-window-fixed/`, `.tmp/side-only-seek-part04/`,
[method](toolkit/SIDE_ONLY_SEEK.md) and [evidence](toolkit/side_only_seek_report.json).
Eight component tests include 2560 geometry and1024 independent full-flags
cases. No physical drive was measured; standard CPU clock and the SA460
200 us side-select contract are explicit assumptions.

The coherent four-volume build and full cold/continuation gates are now
complete, as recorded above. Its media-derived common ID, independent cold
states and next-disk validation are verified. For future zero-late work, reuse
the disk 3 local 933 trace: optional cylinder acquisition crosses publication
and delays drawing, despite an available decoded slot. Avoid another whole
set sweep until a bounded scheduling change proves useful. Previously
rejected generic read gates remain disabled; do not assume they now pass.

The sector-streaming LZSA2 experiment remains unselected. Eager
prefix decoding produces 27 late frames / maximum 40 fields in the complete
256-frame window; deferring prefixes while completed slots remain gives
13 /9, versus the sector-cache baseline's 8 /7 (an earlier baseline run was
8 /8). Native screens, AY and sector sequence remain exact. The final variant
bypasses all guard branches after complete input, retaining zero per-token
overhead; its full playback follow-up is recorded above. Keep
`--streaming-lzsa2` opt-in. Reuse
[evidence](toolkit/streaming_lzsa2_report.json); root release disks are unchanged.

Latest exact mode: CB46 mode 3 stores one changed row-pair within a literal
cell, using selector 0..3 plus a row-table index. Other CB44 modes, the
mutable row table, colour attributes and LZSA2 stay unchanged. Three cached
256-frame windows save 10466 bytes (2.39%). The one selected full partition
saves 59832 video bytes, with all 5066 host screens and original AY exact.
Actual native capacity with shared AY/three video slots is now
**2464/2475/2542/2543 sectors**, all fitting 2544; all four dirty-RAM cold
loads pass. Do not rebalance or re-encode this partition just for capacity.
Reuse `.tmp/partial-row-four/` and `.tmp/partial-row-four-capacity/`.

The four-slot [4096,4352) native/cold/Fuse window verifies every screen,
1280 AY ticks and all 726 runtime sectors. Size 780 sectors. There are
31 nominal misses, 29 beyond one field, maximum 28 fields, 12 invalid
intervals; all late runs recover, last at local frame 254. Both timing
gates still fail. Reuse `.tmp/partial-row-window/`,
`.tmp/partial-row-profile.json` and [evidence](toolkit/partial_row_report.json).
Fifteen tests / 32 independent native cases pass. Exact renderer delta:
`7*book_cells - 131*partial_cells` T. No-refill partial cell 186 vs317 T;
book 288 vs281 T. Not every frame is faster; use measured total delivery.

Part 4's 1170-byte AY overflow now occupies checked fixed B398h..B82Ah;
the first 16384 payload bytes remain in bank 6. Four video slots work on this
full volume at unchanged **2543 sectors**. Twenty tests and all 6610 native
AY ticks pass; fill saves 1488 T and init 20 T versus bank-spanning shared AY.
The complete cold/Fuse volume preserves 9137664 screen bytes, all AY50 ticks
and all 2434 runtime sectors. It misses 60 deadlines (57 beyond one field),
maximum 42 fields, 34 invalid intervals; all late runs recover. Reuse
`.tmp/fixed-audio-tail-part04/` and [evidence](toolkit/fixed_audio_tail_report.json).
The smaller cached window above remains useful; do not compare its 31 misses
directly with the full volume's 60 as if the scope were identical.
All 1322 native frames pass guards on bank 6, the fixed payload and unused
RAM. `.tmp/fixed-audio-tail-profile.json` records 70 empty-queue entries;
active draw/disk/decoder elapsed 125.55M/72.02M/58.65M T within 468.51M T.
Packet stages overlap those totals. Retain the full trace for burst analysis.

Latest bounded optimization: opt-in `rebuild_cell_player.py --inline-cells`
inlines the eight CB46 cell handlers, saving exactly 17 T per changed cell.
The additional 8E80h..9000h gap is fully native-guarded; renderer ends at
93BFh, and screen state at 93C1h, leaving the 9400h audio allocation intact.
Four test methods / 28 new independent cases and all 256 native/Fuse frames
pass exact content checks. Window remains 780 sectors; misses 31 ->13,
beyond-one 29 ->13, maximum 28 ->17 fields, bad intervals 12 ->7. Local run
237..249 recovers at 250. Full part 4 remains 2543 sectors with exact cold
boot (revised full-part playback not run). Reuse `.tmp/inline-cell-window/`,
`.tmp/inline-cell-profile.json`, `.tmp/inline-cell-part04-capacity/` and
[evidence](toolkit/inline_cells_report.json). Do not rebuild from the older
window without `--inline-cells` when comparing the next player change.

The next completed opt-in is `--sector-cache`: audit bank 7 E300h..FFFFh,
then use 28 sectors at E400h..FFFFh, prefetch code E300h..E336h and fixed
helper/state B900h..B954h. When decoded slots are full, read compressed input
ahead. Cache hits copy through BC00, adding CPU work but reducing I/O stalls.
Complete window native/Fuse screens, AY, disk sequence and FIFO guards pass.
Two runs have eight late frames, all beyond one field; maximum 8 /7 fields,
four invalid intervals. Run 237..244 recovers at 245. Trace proves 112 cached
sectors, four cursor wraps and zero final occupancy. Window 781 sectors;
part 4 cold capacity remains 2543. Reuse `.tmp/sector-cache-window/`,
`.tmp/sector-cache-profile.json`, `.tmp/sector-cache-part04-capacity/` and
[evidence](toolkit/sector_cache_report.json). Keep all four flags:
`--shared-audio --four-video-slots --inline-cells --sector-cache`.

Previous decoder scope (parked by the steering above): remove the complete-input gate before decoding. The remaining
stall is block 14 (12492 compressed bytes) while the cache holds only 7168;
14 queue-empty entries and longest empty wait 0.81M T remain. Reuse existing
`inplace_streaming_core.py` and `streaming_slot_queue.py` as design references
(they implement ZX0, not LZSA2). `inplace_streaming_player.py` preserves AY/
drive hooks and safely remaps external queue operands. A LZSA2 variant must
guard token headers AND entire literal runs against the loaded input frontier,
preserve AF' and the suspended decoder stack, save the shared sector before
it can be overwritten, and keep explicit EOF completion. Retain existing
LZSA2 bytes and in-place proofs; first validate boundaries in a component
fixture, then reuse this complete window. The core ends at 8E6Eh and the
inline renderer starts at 8E80h, so helper placement must be checked.
Full part 4's preceding renderer's main late
run is local 577..632 (global 4321..4376), recovered at 633. Avoid re-encoding
or building a full set for each trial. Preserve exact stream bytes for
player-only changes; compare native counts separately from real disk service.
Only then build the full four-disk set and run complete cold/continuation
timing and content gates before replacing the root release images.
CB46 is currently available to the cached rebuilder via `--cell-probe`;
generic converter CLI selection still needs integration before completion.
Earlier experiments and constraints below are retained for provenance.

The CB42 implementation keeps the 256-slot / 512-byte row table, but adds
lossless replacement records. The host chooses farthest-next-use eviction
among rows not needed by the current frame; index zero stays black. Already
rendered physical screen histories and the physical cell book are independent
of row indices. Fifteen unit/regression tests pass. A 12-frame synthetic
native playback with 369 row replacements preserves both screens exactly.
Full Fuse checks of that fixture and the 64-frame real window pass: 525312
screen bytes, 380 AY ticks and zero late frames. Ordinary packet parsing
adds 18 T; drawing is unchanged. Row replacement costs 207 + 74*N T excluding
the queue body, dispatch, length read, IRQs, contention and disk latency.

One bounded real [4216,4280) comparison costs 62916 bytes static / 63118 bytes
dynamic, with exact pixels and original two-screen history. No full-size or
full-timing claim follows. Equal movie quarters need 267/271/258/261 distinct
rows and 17489/18632/19202/21012 resident audio bytes. Dynamic rows remove the
first constraint. Audio's 16-KiB bank is still a separate obstacle. Lossless
low-period-byte prediction was tested on all 25330 ticks and is insufficient:
four estimated resident sizes with a 256-byte native-code reserve are
16639/17689/18611/20468 bytes. This host prototype is not enabled in the player.
Reuse [the exact round-trip comparison](toolkit/ay_period_delta_probe/report.json).
The optional `--audio-banks 2` now uses bank 6 for a second exact AYH1
segment (AYB1 wrapper). The fixed-RAM producer changes banks without resetting
the global AY counter, FIFO or chip state; the interrupt consumer is unchanged.
Equal-quarter native bank sizes are [9984,10234], [10481,11067],
[11784,9975], [13123,10802], all within their individual 16-KiB limits.
Thirty-three tests and full Fuse playback of the dynamic-row fixture and
real 64-frame window pass: 525312 exact screen bytes, 380 exact AY ticks,
zero late frames/underruns. Reuse `.tmp/banked-audio-fixture-fixed-ram/` and
`.tmp/banked-audio-window/`; [evidence](toolkit/banked_audio_report.json).
Two incorrect helper placements were caught before acceptance and are
archived: a later producer overwrite, then a helper in pageable memory.
The final helper occupies the checked fixed gap 78A0h..7900h.
Refill overhead is 486 T (+50), switch refill 645 T (+209), EOF refill
516 T (+80), excluding the decoder body, outer service, IRQ/contention/ROM.
Initialization adds 40 T; the AY consumer and row renderer add 0 T.
Four cuts were then selected by minimax planning over 159 short CB42 windows:
[0,1312,2672,3744,5066]. Only this full partition was encoded. Video alone
uses 2558/2530/2540/2520 sectors (10148 total), leaving 28 of the four disks'
10176 sectors for all sound/startup. The first video already exceeds one
disk. Do not build this oversized candidate. All 5066 host screens and LZSA2
blocks round-trip exactly; this is not native timing or a release check.
Eleven planner/generic tests pass. Reuse `.tmp/four-dynamic-probe/` and
[the archived streams/window costs](toolkit/four_dynamic_report.json).
A host-only CB43 whole-cell replacement experiment then tested three
256-frame windows at 0/2560/4096, with exact pixels and all replacement
bytes. Static books total 453253 bytes; replacements every 32 frames cost
455017 (+0.39%), every 64 cost 452835 (-0.09%). The difficult window grows
in both cases. Fifteen tests pass, including exact old CB42 fixture bytes.
Do not implement this weak CB43 variant in the native player yet. Reuse
`.tmp/dynamic-cell-probe/` and [evidence](toolkit/dynamic_cell_report.json).
Host-only CB44 now measures exact reuse from the immutable front screen.
On the same three windows: 453253 baseline bytes, 438082 with same-position
copies, 437973 adding neighbour moves, 437906 refitting the static book to
non-reused cells. CB45 XOR attributes worsen all three windows (443312 total).
Keep only same-position reuse and book refitting for native development;
neighbour modes and XOR are prototypes, not proposed runtime requirements.
Nineteen tests pass; all compared screens are exact, including old CB42
fixture bytes. [Bounded evidence](toolkit/front_cell_report.json).

One full CB44 partition with the existing four cuts is encoded on the host:
628680/622126/637883/633641 video bytes; 2456/2431/2492/2476 sectors (9855
total). This saves 74724 bytes versus CB42, with all 5066 exact screens and
unchanged AY. Only 321 sectors remain for all boot/audio; final capacity is
not established. Reuse `.tmp/front-four/` and [exact streams](toolkit/front_four_report.json).
Native CB44 now supports exact same-position front copies; neighbour mode 3
is rejected before building. Generic and prepared conversion accept
`--front-reuse` (implies dynamic rows), `--dynamic-rows`, `--audio-banks 2`.
Twenty-eight tests pass. The 12-frame fixture is fully exact/zero-late, but
the complete 256-frame [4096,4352) window fails timing: 116 nominal misses,
115 beyond one field, maximum 89 fields. All 1769472 screen bytes and 1280
AY records are exact. Root images stay unchanged; this is not a release.
Native book/literal cells cost 281/317 T versus 268/304 T; front cells 299 T,
excluding caller/refill. Full counted formula and twenty boundary cases are
in [native evidence](toolkit/front_native_report.json).
Follow-up CB44 mask skipping and inline attribute writes reduce every draw
in this window: average 128487 -> 122716 T (-4.49%), with identical video/AY
streams. Ten tests / 24 independent component cases pass; 255 measured
frame deltas match the exact formula (frame zero is bootstrap-primed).
Full Fuse screens and AY remain exact, but 110 frames are late (108 beyond
one field), maximum 82 fields. This is an improvement, not a timing pass.
Code grows 57 bytes; this diagnostic image uses one extra startup sector
(797 -> 798), video unchanged at 735 sectors. The builder enables it for
CB44 automatically, CB41/42 defaults stay unchanged. Reuse
`.tmp/front-fast-masks/` and [evidence](toolkit/front_fast_masks_report.json).

The first complete selected volume before mask optimization fails capacity:
2558 sectors versus 2544,
including 2456 video and 102 startup/audio sectors. No full-set TRDs were
emitted. Reuse `.tmp/front-four-native-capacity/` and the exact cached video.
The complete real Fuse pipeline trace finds drawing 35.10M T, active disk
service 19.16M T and active LZSA2 bridge slices 15.21M T within 95.02M T
from first packet to last publication. Decoder slices include paging/IRQs/
contention; these are not deterministic CPU counts. Packet intervals overlap
disk/decode and must not be added again. An independently booted trace has
117 misses, same maximum 89; report both runs rather than replacing the
original result. Queue empty at 115/256 packet entries. Next reduce native
mask/render overhead and inspect producer scheduling on this cached window;
an extra buffer alone does not establish sustainable delivery. See
[implementation, cycles and reproduction](toolkit/CB44_DYNAMIC.md).
The next completed step retires old reconstruction at 8000h..8D74h in this
layout (derive the upper bound from decoder metadata, never hardcode it).
Guarded native execution of 268 frames makes zero reads/writes/fetches in
those 3444 bytes. Cold Fuse screens/AY are exact for the real 256-frame
window and two six-frame fixture disks; actual predecessor-EOF continuation
also passes at zero late frames for the fixture. The real window remains
late: 113 misses, maximum 82 fields, reflecting changed disk alignment.
Active instructions/draw T-states and video/AY streams are unchanged.
Diagnostic capacity improves 798 -> 796 sectors. The first full selected
volume now needs 2556 / 2544 sectors (12 over); still no four-disk release.
Reuse `.tmp/front-retired-core/`, `.tmp/front-retired-fixture/`,
`.tmp/front-retired-capacity/` and [guarded evidence](toolkit/retired_cell_report.json).
`rebuild_cell_player.py` reuses existing metadata/scaffold/raw/LZSA2/AY;
use it for player-only changes instead of preparing/encoding again.

Shared fixed-RAM AY is now implemented behind `rebuild_cell_player.py
--shared-audio`. The B100h..B700h gap passes a full native access guard.
Seventeen tests pass; all 25330 selected-volume ticks are native/chip exact.
Fixed storage is 3860/3940/3932/4053 bytes. Payloads are
14137/16118/12516/17554 bytes, with only part 4 using a 1170-byte bank-6 tail.
AY fill costs 69212242 -> 70408859 T (+1196617); this saves storage, not CPU.
Real 256-frame cold/Fuse content is fully exact; size 796 -> 793 sectors.
Timing still fails: 108 misses, all beyond one field, maximum 82 fields.
Complete four-volume capacity is 2543/2541/2588/2588 sectors: 84 sectors
(21504 bytes) over the total available 10176. The first two volumes pass
dirty-RAM cold loading; no four-disk release or whole-movie timing claim.
Reuse `.tmp/shared-audio-window/`, `.tmp/shared-audio-four-capacity/` and
[the saved evidence](toolkit/shared_audio_report.json).
Four video slots are now opt-in for one-bank AY: cached rebuild flags
`--shared-audio --four-video-slots`. Move AY to bank 6 and restore video
banks [0,1,3,4], using their original mapper and in-place layout. Spanning
audio is rejected. Capacity 47616 -> 63488 decoded bytes; cursor cost
39/47 -> 11 T; admission and AY relocation add 0 T. Eighteen tests pass.
Complete native/cold/Fuse checks preserve all 256 screens and 1280 AY ticks.
Real-window timing improves 108 -> 37 misses (36 beyond one field), maximum
82 -> 43 fields, 15 invalid intervals; size stays 793 sectors. Still fails
both timing gates. Reuse `.tmp/four-video-slots-window/` and
[the evidence](toolkit/four_video_slots_report.json); do not repeat builds.
Next scoped step: inspect the remaining 41 empty-queue packet entries and
late runs in the full saved pipeline profile, and handle full part 4's
1170-byte audio overflow. Protect it from BOTH compressed input and output,
or first audit further fixed RAM (B700h..BA00h is not yet audited). The old
plan's suggested video map [0,1,3,6] would require new paging code; the
implemented one-bank case instead retains the original [0,1,3,4] mapper.
In parallel capacity work, target the remaining total sector excess;
moving volume cuts alone cannot remove it. Do not reduce media quality.
Retain full image/AY, 10 fps and the entire edit; do not rebuild all four
TRDs until a bounded test and complete capacity checks support the candidate.
Reuse `.tmp/dynamic-rows-probe/`, `.tmp/dynamic-rows-fixture/` and
`.tmp/dynamic-rows-window/`; do not rebuild the previous 15-image set.
Saved [native/Fuse proof and archives](toolkit/dynamic_rows_report.json).
An initial full-capture gate caught a build-only placeholder hash overwriting
the correct five-level reference hash. The parent-volume metadata override
is fixed; recovered checks preserve the original failed metadata. This did
not change any generated player/data bytes or relax the pixel comparison.

## Earlier deliverable: 10 fps

Develop this track on **`codex/cb41-10fps`**, as requested on 2026-10-01.
The branch retains `5ae85fc` and `d2d7e1b`, including all tests, LFS fixtures
and failed-capacity evidence. Local `main` stays at `a878583`: the verified
25/3-fps implementation plus its read-only cadence assessment. Keep further
10-fps changes on this branch; merge only when requested. The working
directory and ignored preparation caches remain in the repository root.

Resample the original at 10 fps, retain the authorized edit and all existing
AY ticks, and publish every frame on five-field deadlines. First validate
short fixtures and a difficult movie window; build one selected complete
set using window-based planning. Confirm full EOF timing, screen bytes,
sound and cold boots before replacing the verified root images. The prior
three-disk 25/3-fps set remains the compatibility baseline until this passes.
Record actual disk count; do not label an oversized or late candidate a
release. Avoid unrelated codec experiments.

Implemented in `5ae85fc`: `convert_video.py --video-codec cb41 --fps 10`,
five-field video and independent AY50. All 23 short fixture frames pass.
The 256-frame difficult window `[4128,4384)` also passes full Fuse timing,
all 1769472 screen bytes and 1280 AY ticks, zero nominal misses or underruns.
Full preparation is complete: 5066 frames, all 25326 original AY ticks plus
four silent tail ticks. Reuse `.tmp/cb41-10fps-movie/prepared/` and the saved
reports; do not redo quantization or compression probes without a reason.

One selected three-volume plan `[0,1808,3408,5066]` failed actual capacity:
first volume 2782 sectors / 2544 maximum. No new full-movie TRD was emitted;
later volumes were not encoded. All 159 window costs are cached in
`.tmp/cb41-10fps-full/partition.json`. This is not an impossibility proof.
The earlier disk-count preference is resolved: on 2026-10-01 the user
authorized additional disks for the refined colour and sound rebuild,
retaining the new image, new AY soundtrack and 10 fps. Do not reduce these
to enforce the earlier three-disk cap on this rebuild.
[Evidence, limits and reproduction](toolkit/CB41_10FPS.md).

## Latest scoped result: cell colours and contrast

The user reported conspicuous coloured cells and fewer solid black/white
areas. The completed 128-frame probe on `codex/cb41-10fps` reproduces the
baseline and confirms lower endpoint coverage. A palette repair improves
RGB error but costs 18.79% more bytes and worsens dark-scene cell seams.
An endpoint-only bias restores coverage at +6.52% bytes, +2.38% measured
output CPU and +4.16% RGB MSE. Seventeen tests and 256 native frame draws
pass. These are experimental selectors; defaults/root images are unchanged,
and full playback for their data is unverified. Reuse the saved RGB windows,
states, streams and metrics. [Decision and next bounded milestone](toolkit/CELL_PALETTE_QUALITY.md).

## Monochrome visual preview completed

At the user's request, root `ZX-video-monochrome-preview.trd` contains the
256-frame `[4128,4384)` window with fixed black/BRIGHT-white attributes and
five dither coverages, 10 fps and original AY50. Full screens, AY, sector
reads and independent boot pass; 669 sectors used. Two frames (80/115) are
one field late, recovering on 81/116. The authorized fallback passes but
zero-late timing does not. This is a visual preview, not the complete movie
or a replacement release. The prepared builder accepts `--monochrome`;
ordinary colour defaults are unchanged. [Evidence and reproduction](toolkit/MONOCHROME_PREVIEW.md).

## Optional contour experiment completed

Source-RGB contours were compared on 96 cached monochrome frames. Strong
tracing overdraws texture and exceeds the 256-row limit in two windows;
reject it. A softened pre-dither variant changes 2.11% of samples, costs
5.37% more window bytes and 2.20% more native output T-states, and fits all
three window dictionaries. All 192 baseline/soft native draws and eight
tests pass. Keep this as an optional prototype: no new TRD/default change,
full-player timing or full-volume capacity claim. A host comparison GIF is
saved. [Evidence and next gate](toolkit/MONOCHROME_CONTOURS.md).

## Joint colour and grain prototype completed

At the user's request, compare joint colour/coverage selection against the
monochrome source reference on 128 cached frames. The selected version guards
average and physical-model RGB error per 2x2 sample and luma error per cell.
RGB MSE drops 52.00% versus monochrome / 8.39% versus old colour, but boundary
residual error increases. Bytes +19.24% and output CPU +6.38% versus mono;
local row tables fit. All 256 native draws and nine tests pass. Keep this
optional prototype; defaults/TRDs remain unchanged and full-player timing
is unverified. Next address boundaries within these RGB bounds before a
release gate. [Comparison and evidence](toolkit/FAITHFUL_COLOUR.md).

## Audio conversion integrated: square harmonics and quieter noise

On 2026-10-01 the user authorized audio changes and requested flexible frequency
selection inside the converter. `convert_video.py` now automatically fits
integer AY periods and nearby volume levels against odd square harmonics,
recovers isolated off-grid tones and lowers noise by one nominal 3 dB step.
AY remains 50 Hz. Three eight-second source windows improve spectral/chroma
and onset proxies; 27 tests, 2400 isolated native AY ticks and one complete
five-frame CLI/CPU fixture pass. Audio bytes +75.79%, audio CPU +27.42% in
these windows. No full-film timing/capacity claim; root TRDs and cached AY stay
at the verified baseline. Reuse [audio evidence and reproduction](toolkit/AY_SQUARE_FIT.md).

## Refined full-movie rebuild completed (fallback preview)

The user requested new root TRDs with the joint colour/grain selector and
square-aware AY fitting. Full preparation is cached in
`.tmp/refined-av-movie/`: 5066 frames, 25330 AY ticks, 506.6 seconds including
120 ms of silent tail padding. The authorized credits cut retains the
post-credit scene through source EOF. Mean frame RGB MSE is 692.855 versus
743.070 for the former colour selector; all per-sample RGB and per-cell luma
guards pass. This is a numerical comparison, not a perceptual percentage.

An eight-disk complete Fuse run had 207 missed nominal deadlines and failed
the one-field fallback on three volumes. A targeted 64-frame probe with
the final series identity and real preceding histories passed with zero
misses. Explicit timing-driven cuts preserve every frame and AY tick; they
do not claim a minimum disk count. Reuse
[the archived failed run and probe](toolkit/refined_av_attempt_report.json).
The selected complete rebuild is now published as root LFS
`ZX-video-refined_part01..15.trd`. Extra disks are authorized for this set.
All 5066 frames / 35016192 screen bytes, 25330 AY ticks and 10126 runtime
sector reads pass cold Fuse playback. All 15 independent boots, 14 prompt
transitions and 14 actual-predecessor-EOF snapshot continuations pass.
Both cold and sequential runs have four isolated late frames: disk 1 frame
1040, disk 3 frame 159, disk 8 frames 92/95 (zero-based). Every late frame
recovers on the next frame. Maximum phase is 70916 T cold / 70915 T resumed,
one 70908-T field plus instruction-level variation. AY has no missing or
duplicate fields or underruns. The one-field fallback passes; nominal
zero-late timing does not, so this is a full-movie preview, not a strict
release. Keep the verified three-disk 25/3-fps compatibility set.

Reuse `.tmp/refined-av-final/`, the 544-file
[final archive and report](toolkit/refined_av_movie_report.json), and the
[integrity/LFS check](toolkit/refined_av_archive_check.json). The failed run
and probe have another 268 authenticated artifacts. All 35 relevant tests
pass. [Finalization](toolkit/finish_refined_av.py) verifies actual EOF
continuations before publishing, and
[archive verification](toolkit/verify_refined_av_archive.py) checks hashes,
source identities and staged LFS pointers. No physical floppy drive test
or minimum-disk-count claim follows. This deliverable is complete; further
disk-count or zero-late optimization is a separate milestone.

## Working method

1. **Define one deliverable.** State the problem, baseline, hypothesis and
   completion criterion briefly. An explanation request should produce an
   explanation with proportionate evidence. An implementation request should
   complete the authorized change. Do not expand either into adjacent work.
2. **Reuse evidence.** Begin with Git status, this brief and the relevant
   source/report. Check input and source identities before reusing results.
   Read targeted sections of [the plan](toolkit/DECODE_SPEED_PLAN.md), not
   the entire history or every report. Preserve unrelated working changes.
3. **Run one comparison first.** Compare the baseline with one candidate.
   Add another only to resolve a specific uncertainty revealed by that
   comparison. Close a hypothesis when evidence supports adoption,
   rejection or deferral; do not keep polishing an unpromising candidate.
4. **Use bounded experiments.** Reuse representative 32–64-frame windows,
   including a difficult scene and relevant boundary cases. Carry required
   predictor, back-screen and producer/consumer state. Select locally;
   build one selected final disk set instead of searching with full sets.
5. **Verify according to risk.** Documentation needs a diff review. Codec
   changes need independent round trips and relevant edge cases. Native
   changes need instruction timings and affected RAM, paging, screen and IRQ
   contracts. Retain required checks; repeat them only when a relevant
   change, failure or unresolved risk invalidates prior evidence.
6. **Keep tool output small.** Search names first; read the relevant function
   or JSON fields. Prefer summaries and failure details over raw reports,
   full listings or repeated source dumps. Save reproduction scripts and
   evidence in the repository; use caches keyed by relevant inputs/options.
7. **Finish the deliverable.** Fix defects needed to complete the authorized
   change. Record each meaningful attempt in the changelog and commit each
   completed logical change separately. Report result, evidence, limitations
   and one next step. A failed experiment can be a completed decision; it
   does not complete the overall project goal. Do not automatically open a
   new research branch after that decision.

No routine confirmation is needed for authorized, reversible work. Ask only
when missing information or a genuine permission boundary prevents a sound
decision. These scope controls must not reduce verification or hide failures.

## Current state: five-level playback and generic integration verified

The full authorized movie edit is verified at 25/3 fps with five brightness
levels on three independently bootable root LFS images:
`ZX-video-five-level_part01..03.trd`. All 4221 frames meet their nominal
six-field deadline, all 25326 AY ticks remain exact, and all 29175552 screen
bytes match. Disk usage is 2475/2505/2511 sectors. Both prompt transitions
and actual-predecessor-EOF snapshot continuations pass. Physical drive swaps
were not measured. Reuse [the complete movie evidence](toolkit/CELL_CODEBOOK_BALANCED.md).

`convert_video.py --video-codec cb41` now connects the same native player to
ordinary video inputs, without movie-specific paths or cuts. It retains
aspect ratio, EOF, audio offsets/tail and silence; refines to five levels;
selects row/cell books and the verified native options; plans with 32-frame
windows; checks resident AY and actual disk capacity; and verifies independent
volumes. Native table/capacity failures are explicit without dropping frames
or reducing quality. FAP3 remains the default for compatibility.

Five generated cases (single, portrait, moving colour/sound split across
three disks, non-square pixels, audio tail) pass complete Fuse playback:
20 frames, 120 AY ticks, seven disks, 138240 exact screen bytes, zero late
nominal deadlines. Both prompt transitions pass; 19 unit/regression tests
pass. The generic representation reproduces every saved CB41 byte and screen
hash for all 4221 movie frames. Root disk identities and all 84 full-movie
archive hashes were checked. Renderer/packet code is identical; LZSA2
relocation within bank 2 preserves every instruction and absolute T-state
cost (0 T instruction delta).

[Generic command, evidence and reproduction](toolkit/GENERIC_CB41.md) ·
[Saved report](toolkit/generic_cb41_profile.json) ·
[Detailed experiment history](CHANGELOG.md)

## Completion evidence and practical limits

| Requirement | Current evidence |
| --- | --- |
| Complete authorized edit, five levels, unchanged resolution/AY | Saved full-movie preparation, exact generic CB41 reproduction, unchanged root hashes |
| At most three independent disks | Actual sector counts, dirty cold boots and complete individual Fuse runs |
| Every frame on its original six-field deadline | All 4221 frames and 4218 intra-disk intervals; zero late runs, drift or dropped frames |
| Exact displayed screens and progress | Full 29175552-byte movie screen verification; full generic fixture screens |
| 50-Hz AY and sustained disk delivery | All 25326 movie AY ticks and 7187 sectors exact; most sectors read during playback |
| Disk continuation | Both prompt/identity/bootstrap checks plus movie runs from actual predecessor EOF RAM |
| Generic converter | Five complete input cases, exact row/AY/native-capacity gates, 19 tests, one selected final set |
| Reproducibility and cycles | Committed scripts/reports/hashed evidence; native instruction tables and 0 T delta; TRDs in LFS |

The requested movie playback objective and generic integration milestone are
complete. Arbitrary new videos still require their own full timing/content
gate; no universal cadence, three-disk limit or perceptual 95% claim follows
from these fixtures. A local size estimate that fails final capacity can
require a smaller --max-frames-per-disk on retry. These limits are reported,
not hidden by quality loss. No further codec sweep is part of this milestone.

## Release gate for a future changed candidate

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it. Reuse
the passing root movie set and archives when their identities are unchanged.
