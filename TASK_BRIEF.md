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

## Active milestone: at most four refined A/V disks

The user rejected the 15-disk count and requested at most four disks, keeping
the refined picture, new AY50 soundtrack and 10 fps. On this goal turn they
specifically requested a dynamic row dictionary with eviction/replacement
during playback. Completion requires a full, independently bootable set of
at most four TRDs, unchanged media coverage and complete timing/content gates.
Do not substitute a short fixture, the previous soundtrack or reduced fps.

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
