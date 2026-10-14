# Focused optimization task

Updated 2026-10-14. Use this brief to continue the project in this or a new
chat. This document scopes work; it does not start an automatic goal.

## Native-pixel line drawing — experimental prototype checked; release timing unresolved (2026-10-14)

The user requests the same current line-art style at true 256x192 native
resolution, retaining the current 256x144 active area if desired. The prior
open-ended accuracy goal stays paused; this is a separately authorized finite
format task. Work in`.worktree/native-lineart`, branch`codex/native-lineart`,
from`bd01d761`. Trace original256x144 RGB directly, with one-pixel native
lines, source-close solid fills and current-source dark-region rollback.
Introduce CB47 exact native8x8 bitmap cells, dictionary/front reuse and a
one-row literal; do not approximate through the old128x96/five-level plane.
Retain10 fps and unchanged50-Hz AY. First deliver a matched30-second native
test disk, comparison and fully independent cold/full Fuse timing proof.
Count native instruction paths against CB46 and actual disk allocation.
Preserve old formats and defaults, failed attempts and unrelated changes.
The current old-format progress was pushed as`bd01d761` to origin/main.
Full archive checkout failed for lack of disk space; use a sparse source
worktree and read existing authenticated inputs from main instead of copying
its large historical audio archives. Do not restart the paused broad goal.

The user additionally rejects extra outlines on thin strokes and reports
unreadable native faces/title lettering. The selected source-coherent stroke
core, bright-letter protection and grain filtering are preserved in the
CB47 prototype. All 300 native frames / 2,073,600 screen bytes pass complete
Fuse comparison, independent dirty cold boot and all 1500 original AY controls
at 50 Hz. Six old renderer variants remain byte-identical; 26 tests pass.
The final cell-only/minimum-5-match disk uses 1488 sectors, with 1056 free.
It is NOT a release: 165 nominal misses from frame 135 through 299, maximum
523 fields / 10.46 seconds of deviation, no recovery and failed one-field
fallback. Actual first-to-last publication spans 40.36 seconds. MP4s use
nominal host-reference timing, not measured TRD cadence. The raster attempt
and unsafe old buffer are rejected; the final native packet lives at
6200h..7760h, before retained 7800h helpers. Literal body 231 -> 188 T,
single-row body 93 -> 53 T, ordinary row-control dispatch -18 T; full delivery
remains data-dependent. Preserve all failed/partial attempts and the prior
qualified coarse disk. Root experimental disk:
`ZX-video-sea-foam-native-lineart-experimental.trd`.
[Readability comparisons, complete results and reproducing scripts](toolkit/analysis/native_lineart/README.md).
The format/readability experiment is reviewable. Sustained native 10-fps
delivery remains unresolved; do not call this a qualified release or resume
the stopped broad goal implicitly.

## Accuracy and compression of source-line drawings — dark-fill milestone complete (2026-10-14)

The user explicitly chooses a contour drawing with source-close coloured
fills as the target and asks to improve accuracy without ideally losing
compression. Continue on `.worktree/flat-colour`, from `78b7a7be`. The first
bounded milestone tests hardware-feasible NORMAL/BRIGHT alternatives within
the existing accepted source-colour regions. All977 frames remain identical;
reject this as an accuracy improvement. The next candidate admits coherent
dark fills within the existing RMS60/component100 colour guard, instead of
an extra max-component64 black cap. Preserve every existing source line,
classified black/colour region, paper outside the new accepted dark regions,
current-frame response and no-dither output. Every changed pixel must reduce
original RGB error.
Measure the complete qualified977-frame input with actual CB46/LZSA2 data,
including dictionaries and allocation; compare difficult scenes and motion.
Keep the previous independently qualified disk. Reject a candidate which
does not meet the image contracts or loses total compressed space. If the
host gate passes, build and fully qualify a separately named TRD before any
release claim. No new audio fit, native opcode change, neural model search
or push is requested. A qualified bounded improvement is progress toward
the active accuracy goal, not proof of a globally optimal encoder.

The optional`--lineart-dark-fills` now accepts source-close black with the
same60-RMS/100-component bound as coloured fills. Whole-source-component
rollback protects every existing coloured pixel and all source lines;
every changed pixel strictly improves original RGB error. Unguarded source
colour loss at frame460 is preserved with a regression fixture.57 tests pass.
On all977 matched frames,342,800 samples improve; RGB MSE6885.659687 ->
6025.180072. Final stream626,964 ->591,481 bytes; actual disk2541 ->2399
sectors. Complete independent dirty-RAM Fuse checks all6,753,024 screen bytes
and4885 AY records, zero nominal misses/late runs/underruns, max deviation23 T.
Native instruction delta0 T; packet/clock/cell listings are identical.
The selected LZSA2 core falls62,140,081 ->58,364,356 T, excluding disk/IRQ/ULA;
2311 actual reads replace2450. Entire original RGB/AY/model WAV remains exact.
Quiet RGB variation improves; chroma variation rises0.098%, so no universal
temporal improvement claim. Preserve154 measured files/109,149,355 bytes
plus manifest, previous disk and all failed attempts. Root disk:
`ZX-video-sea-foam-lineart-dark_part01.trd`, SHA256
`ec6fe8d13b986400dcf6b722aa5e9575ff3f3c5c0245ea4aeb2dd31a2f672dd0`.
[Usage, comparisons and full proof](toolkit/analysis/flat_colour/DARK_FILLS.md).
The scoped milestone is complete. On2026-10-14 the user requests a test disk
and explicitly stops the broader accuracy goal. Deliver this qualified test
disk and pause the goal; do not start further image, duration or codec work.
Do not claim globally optimal contours, finer-than-two-pixel geometry or a
maximum-duration disk. No push is requested.

## ZX Compressors migration plan prepared 2026-10-14

The user requests a plan for a separate `zx-compressors` repository consumed
by ZX-video through Git subtree. [ZX_COMPRESSORS_PLAN.md](ZX_COMPRESSORS_PLAN.md)
defines filtered history export, standalone test/package preparation, target
creation, in-place `libraries/` registration using split/rejoin, pinned imports,
CI/update workflow and rollback. Preserve independent `zx0`/`lzsa` packages,
31 default profiles, resource/provenance hashes, application tests and timing.
Planning snapshot main `93e93664`; freeze the latest source for implementation.
The plan is this request's deliverable; creation/migration/publication follow
only when implementation is requested. Existing movie/audio tasks stay intact.

## Source-line drawing full disk — complete (2026-10-14)

Latest steering rejects flat fills because details are lost. Stop the1005-frame
flat rebuild (219 complete host rows; partial/unqualified output is
retained). Replace it with `--colour-policy lineart`: trace source detail and
silhouettes on uniform paper, paint clear near-native black/colours only, and
sacrifice optional third-colour fill before losing outlines or tinting paper.
Inspect character/general scenes before rebuilding, then complete the original
single-disk request with this corrected image. Do not treat the superseded
flat preview as user-accepted or restart a neural/image-model sweep.

The user now requests a full disk of the shown flat/neutral-contour video.
Use the existing `.worktree/flat-colour` branch from`96fcec79`; build the
continuous sea-foam source prefix with `--colour-policy flat --colour-contours`,
no dither and no region guidance. Keep10 fps, current50-Hz AY controls, native
resolution, cold independent boot and complete nominal timing gates. Reuse
authenticated original RGB/coarse/continuous audio preparation. Select length
using actual disk sectors and resident AY capacity, not a size-only estimate.
The existing fixed forest's verified prefix ceiling is1005 frames/100.5s;
measure the new disk and report any RAM-bound unused sectors explicitly.
Deliver a separately named root TRD, full MP4, all-frame quality/actual native
proofs and preserved attempts; keep the old qualified disk. Do not change the
image model, refit the existing soundtrack or open another RAM/codec sweep
before completing this concrete disk. No push is requested.

The selected`--colour-policy lineart` now traces fine/coarse current RGB lines,
uses uniform NORMAL-white paper and source-matched normal/BRIGHT fills. Required
lines/black/paper survive; unsupported third-colour fill falls back to paper.
The strict45-RMS/75-component review accepted no colour; preserve it. Selected
60-RMS/100-component/30-degree source criteria retain matching colours without
spill.50 tests and every-frame line/fill/no-dither checks pass. Native instruction
delta0 T; default/old images and the existing AY fit remain unchanged.

Actual1005/980-frame assembly requires2589/2545 sectors and fails capacity.
The977-frame/97.7-second TRD uses2541/2544 sectors(99.8821%),three free. Complete
independent cold Fuse compares all6,753,024 screen bytes and4885 AY fields;
zero nominal misses/late runs/underruns, maximum deviation17 T. Shared900-frame
source/AY/model-WAV prefix remains exact. Full archive141 files/93,558,021 bytes
plus manifest; native proofs, all-frame metrics, previews,17 source snapshots
and failed/interrupted attempts are preserved. Root disk:
`ZX-video-sea-foam-lineart_part01.trd`, SHA256`c573cdd954f2d8cf29350c4e5092df876d7c1596fad8bdbd44fa5042c6758808`.
[Usage, full media and qualification](toolkit/analysis/flat_colour/LINEART_DISK.md).
This completes the corrected image and practical full-disk request. No further
model, maximum-duration, audio/RAM/codec search or push starts automatically.

## Solid colour and character clarity encoder — optional prototype complete (2026-10-14)

The user requests another encoder with closest source colours, solid fills,
no or very little dither, fewer attribute clashes and optional object contours.
The additional steering makes cartoon people, silhouettes and facial detail
the main visual criterion. Use `.worktree/flat-colour`, `codex/flat-colour`,
from `13819086`. Add an optional host-only CB41 palette policy; preserve source
resolution/cadence, default selector, audio and native instructions. Compare
the exact prepared sea-foam source and old qualified screens on fixed difficult
windows, including character scenes. Measure grain, actual RGB, edge/shape
retention and false seams separately; inspect native-size reference images and
motion. Record all selected and rejected trials. Deliver a runnable encoder,
tests and reproducible comparison. This is a visual prototype, not a new TRD
release; do not replace existing disks or claim unmeasured player timing. Do
not start full-cartoon/disk-capacity/audio searches in this task.

The optional `--colour-policy flat` now supports endpoint fills, source
structure/seam scoring, `--colour-dither minimal`, OpenCV source-only lost-line
contours and bounded mean-shift region guidance.96 fixed source frames in six
windows have full saved source/states, per-frame metrics, motion and character
comparisons. Flat has0% patterned samples; minimal1.094% versus65.683% before.
Neutral contours raise strong gradient retention35.408% ->44.246% over plain
flat, but the old selector retains70.066%, with lower averaged RGB/boundary
and quiet-source residual error. Region guidance worsens quiet variation.
Keep every new mode optional; none qualifies as a default quality upgrade or
semantic person recognition. Preserve both rejected/earlier trials.43 tests
plus the final8 contracts pass; all36 final compressed windows/576 host screens
roundtrip,46261 contour bytes versus69993 baseline. Native instructions stay
unchanged,0 T delta; no new TRD or Z80/Fuse timing claim. See
[evidence and usage](toolkit/analysis/flat_colour/README.md). This bounded
encoder/comparison deliverable is complete; no further model/movie search
or push starts automatically.

## YM3812 folder consolidation — complete (2026-10-14)

The user requests collecting all YM3812 work in a separate folder and merging
it into main. [ym3812/](ym3812/README.md) now contains all 256 relocated files
and 23 fixed shared dependency/input copies. Historical Python producers and
evidence retain exact content; paths in human-facing documentation are updated.
The AY converter's shared files remain in place. Eighteen tests and the layout
check authenticate 279 entries, 33 archived artifact manifests and 92 local
links. All 18 entrypoints start from the new layout. All 15 full song streams
are independently replayed again after relocation: 67,500 fields and every
native/output sample remain exact. [Consolidation checks](ym3812/verification.json).
This is organization scope, with no audio algorithm, native player or disk
change and no newly authorized experiment.

## YM3812 coherent-voice implementation — complete (2026-10-14)

The user now explicitly requests acting on the proposed beep-analysis plan.
Follow [the implementation scope](ym3812/analysis/ym3812_sea_foam/TRACKING_PLAN.md)
in the existing song worktree from `e22fb680`: temporal source tracking,
confidence/inactive voices, mild-FM source envelopes, then actual full-track
qualification. Use the original90-second mildly modulated baseline and fixed
source/gain/filter. Retain failed attempts and all earlier media. The prior
analysis's no-automatic-experiment checkpoint is superseded for this work.

The [selected full-track result](ym3812/analysis/ym3812_sea_foam/TRACKING_RESULT.md)
now retains all 15 measured attempts and the `soft52` audition. Source-confirmed
localized tracking and softer FM improve objective 9.444631 -> 9.358669 and
A/B/A returns 1050 -> 798, passing all original guards plus an added strict
below-50-Hz content guard. Exposed-line events improve only 1155 -> 1141;
level MAE worsens by 0.051744 dB within the saved allowance. Fourteen tests,
all 67,500 fields and every independently replayed native/output sample pass.
Keep the bounded listening classification. The requested implementation is
complete; higher-rate, physical-chip and native-player experiments remain
optional future work.

## YM3812 intermittent-tone analysis — complete (2026-10-14)

The user finds the original song rendition better and reports periodic
electronic beep/blam sounds; study source/output and propose improvements.
The [complete audit/proposal](ym3812/analysis/ym3812_sea_foam/BEEP_ANALYSIS.md)
checks all90 seconds, source/old/pure PCM, exact40,500 refitted targets and
four matched excerpts.35.87% of audible channel transitions jump>=3 semitones
per20 ms;1,050 A/B/A returns occur within40 ms. Source-diffuse regions become
isolated synthesized lines, essentially unchanged by the pure-sine update.
Large template-RMS boost is not supported. Direct auditory perception is
unavailable in this session; no perceptually labelled beep count is claimed.

Recommend the earlier mildly modulated `4b73f9ea` baseline and coherent source
partial tracking, source-tonality/inactive-voice gates and source-derived
transient behavior before testing higher target rates. Preserve the purity
attempt and all failures. This analysis/proposal request is complete; do not
start the proposed new fit, rate change or release experiment automatically.

## YM3812 generated-overtones follow-up — complete (2026-10-14)

The user hears added high harmonics, suggests mostly sines and asks the update
rate. Continue the same90-second song from `4b73f9ea`; preserve content, nine
voices,50-Hz targets, smooth register transitions, gain and playback filter.
The [pure-sine/source-cap audition](ym3812/analysis/ym3812_sea_foam/OVERTONES.md)
uses additive connection and a silent modulator from reset. Four held native
tones reduce intrinsic harmonic power33.95..40.83 dB. The selected cap changes
only72 TL targets; every pitch/multiplier/key is preserved. Extra4..8-kHz bin
power falls24.46/4.85/3.74% across three scales; the broad20%1.8..8-kHz gate
is unmet and retained. Log score worsens9.444631 ->9.897613; use the explicit
narrower sine-purity audition goal with all original content/level guards.

All six trials, rejected refits and the11-clipped-sample interruption/recovery
are preserved. Twelve tests and six complete4500-field/native/full-PCM replays
pass, with selected zero clipping and exact181-second comparison segments.
This bounded request is complete; no new fit, higher update-rate experiment,
native scheduler or physical-chip qualification starts automatically.

## YM3812 sea-foam main song — complete (2026-10-14)

Create a YM3812 soundtrack from the archived unprocessed main song, source
[133.6,223.6),90 seconds. Use `codex/ym3812-sea-foam` from `13819086` in
`.worktree/ym3812-sea-foam`. Reuse the nine sine-carrier fitter, multiplier1/2
and previously selected eight-step2-ms ordered TL exporter. Fit all4500 fields
continuously; no30-second chunk resets, beeper limiter or source PCM in the
chip output. Retain one abrupt same-target control, WAV auditions, VGM/VGZ,
spectrograms and complete state/replay/hash evidence. Preserve native players.
This bounded listening trial does not open new FM/rhythm/CSM searches or a
Spectrum delivery implementation. Finish the track before another experiment.

The [complete track and evidence](ym3812/analysis/ym3812_sea_foam/README.md)
now retain the90-second WAV,992,252-byte VGM/369,327-byte VGZ and181-second
source comparison. Smooth same-target writes reduce immediate register-effect
energy81.0822%, with a small spectral/level tradeoff. Eight tests, both4500-
field audits and full independent4,474,431-native/3,969,000-output-sample
replays pass; every command/PCM byte and comparison segment is exact, zero
clipping. Keep the bounded listening classification; no native/player change
or physical-chip delivery proof. The requested soundtrack is complete.

## Adaptive audio RAM and cover loading — complete (2026-10-13)

The user requests available RAM on Spectrum128, Scorpion256, Pentagon512
and Pentagon1024, plus a cartoon title loaded before audio and a bottom
progress bar. The adaptive sequential player now uses all distinct extra
banks as a future-sector cache, reserves base code/tables/stack/TR-DOS/screen
space explicitly, and keeps independently cold-bootable disks and128-KiB
fallback. The public converter defaults to auto RAM; legacy layouts remain
available with `--ram-cache off`. Supplied image/SCR covers survive loading.

[RAM-audio evidence](audiobook-beeper/experiments/ram-audio/README.md) qualifies
27 tests, four complete native/cold Fuse90-second song runs, eight cold IMA3
volume runs, four actual predecessor continuations/wrong-disk rejections and
all-four-model public CLI conversion. Every live pulse, predictor/index,
native hold, bank guard, loading bar and END OF AUDIO is checked. Pentagon
pacing adds26/18 T per ordinary IMA4/IMA3 sample;128/Scorpion delta0. The
original uncompensated song remains a listening preview, not a20-dB release.

The2026-10-13 `ZX-music-Sea-Foam-RAM-auto.trd` contains the main song and real
movie title. That version preloads the remaining volume on Pentagon1024, with
no subsequent floppy reads; active-part RAM copies still pause about1.9445 s
and0.7645 s. Large RAM prefetch intentionally trades longer startup for
fewer later disk reads; measured first start is96.82 s on Pentagon1024. The
continuous replacement described below supersedes this image's part handoffs.

## Continuous RAM song TRD — complete (2026-10-14)

The user clarifies that the current TRD itself should be fixed. The replacement
`ZX-music-Sea-Foam-RAM-auto.trd` now contains one continuous IMA4 stream with
shared code/tables. Audio starts in ordinary128-KiB banks, then continues
directly through detected extended physical pages. Both Pentagon512 and1024
hold the entire90-second song: zero refills, RAM copies or ROM reads between
live banks. Spectrum128 needs three refills; Scorpion256 needs one, with all
decoder/prefetch state preserved. The real title and bottom progress remain.

[Evidence and reproducer](audiobook-beeper/experiments/seamless-trd/README.md)
cover complete native and independently cold Fuse playback on all four models,
every11,526,111 source/guard pulse,720,382 predictor/index states, exact native
holds and actual output intervals. Pentagon maximum live hold is277 T,
77.288 microseconds, replacing multi-second part gaps. Ordinary423/449 T and
page extra14 T remain unchanged; new bank extras243/267 T have deltas+103/+127
from the old140 T. Preserve the original uncompensated listening-preview
classification and strict quality gate. The generic converters remain unchanged.
This completes the current image correction; no new movie optimization starts.

## Completed: sequential additional codec improvements (2026-10-14)

The user authorized working through the saved list and checking improvements.
All20 items10–29 are complete, prioritizing speed then code size, with one
complete measured/audited result per focused commit and retained failures.
Use [SECOND_PASS.md](libraries/SECOND_PASS.md) and the checklist. Preserve
defaults, wire formats, EOF/overlap/suspension/IRQ and application release gates.
Item10 is complete: optional ordinary LZSA2 near_literals saves10 T per
eligible literal and3 bytes;95 complete blocks,230 IRQs, zero slower slices,
relocation/short escaped words and13 unit tests pass. Item11 retains required
nibble/page reloads:513 native checks show safe caching +22/+8 T. Item12
retains existing direct state and live input pointers (258 checks). Item13
rejects input mutation/no indexed state site (256 checks). Item14 keeps fast
rotations and rejects unproved word narrowing (768 checks). Item15 retains
running pointers and rejects unconditional guard caching (2049 checks).
Item16 adds optional streaming word_state_init, −4 T/block/−1 byte;95 full
blocks and both42-case/six-placement guarded modes pass, unchanged waits/
sectors, dirty prior flags,252 native IRQs and14 library tests. Item17 finds
no saturating counter contract (259 checks). Item18 retains live continuations
and rejects a slower one-byte dispatch merge (513 checks). Item19 retains
compiled tables and required per-block mutable resets. Item20 adds optional
restore_compare, −5 T/demand/−2 bytes;95 blocks/230 IRQs, both42-case guarded
modes, boundary/combined-profile tests and15 unit tests pass. Item21 retains
local count/offset-role bounds and replays18 short-word blocks (55 checks).
Item22 rejects whole-run residue dispatch:95 blocks exact, but real21 +8767 T,
19 slower blocks/405 slices; +112 core/+2 stack bytes. Frozen code replays the
failed experiment without a public option. Item23 adds optional one-shot Mega:
417 native blocks (364 real), real −6.147% vs equal-ABI Fast,673 code bytes,
1305 IRQs, exact EOF/relocation/dirty offset;16 tests pass. Item24 rejects the
distance1 selector:95 exact blocks/230 IRQs, real +3816 T,51 slower blocks.
Item25 retains existing Standard stack exchanges and live DE/continuations
elsewhere (1024 native checks). Item26 rejects the guard byte-add rewrite:
22 ->52 T,863 wrong carries/32 signed-offset failures;1824 checks. Item27 retains
refill A counter/word counts and rejects CPI frontier effects (513 checks).
Item28 adds explicit resident Fast profiles: LZSA218 bytes/real −5.112%,
ZX0207/−10.986% vs same full-demand coroutine;95/417 native blocks, IRQ/
relocation/EOF,17 tests and31 default layouts pass. Item29 adds explicit137-byte
resident Small (-81 bytes, +14.948% real CPU), corrected exact EOF;95 native
blocks/235 IRQs, dirty state and1024 nibble checks pass. Final18 library/67
toolkit tests, isolated wheels/exports,31 defaults/four original resources and
both producer variants pass. See second_pass_verification.json. No further
experiment, merge/push or player/movie-release adoption is opened automatically.

## Completed: other-site Z80 speed/size survey (2026-10-14)

The user asks which further library optimizations are possible, prioritizing
speed then code size, and requests other websites. The [survey](libraries/WEB_RESEARCH.md)
inspects author articles/wiki routines, official optimizer rules and upstream
ZX0 Mega/LZSA2 small sources. Eight additional candidate groups22–29 are saved
in the checklist; seven primitive groups pass6604 native cases. An item20
LZSA2 sync proposal saves5 T/2 bytes locally, while whole-run unrolling can
beat the current16-byte prefix only on sufficiently long copies. Upstream
raw core sizes/speed claims do not have the current coroutine/streaming ABI.
All31 default profiles and four original resources remain exact; no new
codec path or release is integrated. This research deliverable is complete.
Continue from pending item10 using one fully verified experiment per commit.

## Completed: first sequential Z80 codec trick pass (2026-10-13)

The subsequent user request asks for additional forum pages, especially a
compiler thread remembered as `x80cc`. The [bounded survey](libraries/FORUM_RESEARCH.md)
captures/screens 54 pages in 15 additional topics and records partial/unread
coverage explicitly. The actual requested compiler/thread is unidentified;
official z88dk 80cc is a naming hypothesis only. Twelve additional candidate
groups (10–21) are saved in the checklist, with 512 indexed-shift checks,
233 corrected bounded-decrement value checks and one adjacent-clear probe.
The source decrement fails at its lower bound; all corrected final flags
differ. This research deliverable is complete, with no codec/default change
or new full-codec/player qualification. Continue one codec experiment at a
time from candidate 10 when proceeding with the saved optimization queue.

The user requests a new branch, a saved list of the zx-pk.ru optimization
techniques, and sequential application/measurement/regression checking.
Work on `codex/z80-codec-tricks` in `.worktree/z80-codec-tricks`, from
`6168ba14`. Follow [the nine-item checklist](libraries/OPTIMIZATION_PLAN.md).
Finish each bounded experiment before the next, including failed/inapplicable
results. Preserve standard ZX0 v2/raw LZSA2, all decoded bytes and existing
default/release profiles. Count instructions and memory; test complete native
blocks, overlap, suspension, EOF and IRQ. Any player-default adoption still
requires complete actual delivery/Fuse/publication qualification from AGENTS.md.
Library component evidence must not be labeled a movie release. No merge/push
or unrelated audio/movie redesign is authorized by this work.

Item01 is complete: [optional long-copy LZSA2](libraries/LONG_COPY.md),
77 complete native blocks, both24-case guarded modes,12 library and66
toolkit tests. Defaults remain byte-exact. Item02 is audited: eligible register
copies already use LD; native evidence rejects replacing live saves. Next:
item03 is audited: live parity/Z/carry and multi-bit masks prevent the rewrite.
Item04 retains existing ZX0 page-aware increments and rejects unguarded
crossings in variable-position headers. Item05 rejects the jump table:
57 T versus24/31/36 T for current class selection. Item06 adds an optional
aligned ZX0 ring table (108 ->87 T, +121..245 bytes),64 full native banked
blocks/all16 profiles and AY/IM2 at every instruction pass. Next: item07
stack bulk copies reject legal overlap1/2 and violate live A/HL'/private-SP
contracts. Item08 is inapplicable to generic runtime literals; measured constant
code enlarges the sample transport. The user expanded item02 to all six
BC/DE/HL directions and nonadjacent independent instructions/calls;36864
native checks pass, but bounded-copy live saves cannot be replaced at either
endpoint. Final review corrected item01's unproved16-bit length bound: unroll
only byte forms, retain original word paths/JR cost.95 native blocks and both
42-case/six-placement streaming modes pass, with initial failures retained.
Real LZSA2 gain is now24026 T (0.124%), +87 ordinary/84 streaming bytes.
Item09 finds no cheaper carry-mask branch (direct ADC11 T versus mask15).
The first nine-item pass is complete, with two optional measured profiles and
all other decisions/evidence saved. Defaults remain exact. No merge/push or
movie release is produced; application adoption needs its complete gates.

## Reusable ZX0/LZSA libraries — complete (2026-10-13)

The user requests separate reusable ZX0 and LZSA libraries with the project's
existing improvements. [libraries](libraries/README.md) now contains two
independently installable packages, host tools, adapted Z80 generators,
licenses, configurable coroutine layouts, assembly exports and examples.
Toolkit compatibility imports share their implementations. Keep media-specific
transforms, scheduling, dictionary planning and disk queues in the application.

All31 default decoder profiles and both streaming producer variants retain
exact bytes/addresses/labels; deterministic delta0 T. Seventy-seven tests,
24 full streaming edge cases and isolated wheel/encoder/example checks pass.
[Saved report](libraries/verification.json) separates native CPU from delivery
timing. This request is complete; it does not authorize a new movie rebuild,
another codec experiment, merge or push.

## Completed bounded audio correction: periodic-noise audit (2026-10-13)

The user again reports periodic voice vibration after the preferred original
direct IMA4 disk and explicitly authorizes tracing the responsible change and
fixing the latest encoder. Compare authenticated checkpoints on identical
prepared source PCM before attributing the effect to a revision; distinguish
physical sample-clock changes from field-synchronous PDM noise and host output.
Reuse prior full traces, then completely execute each selected corrected disk
in native Z80/Fuse, including both loops and sequential transitions when used.
Preserve IMA storage, source content/bandwidth, approximately128-kHz carrier,
independent boot, and all existing timing/quality gates. Do not claim subjective
flutter eliminated solely from average SNR. Deliver the integrated correction,
audition files, regression tests and reproducible evidence; keep old releases.

The [matched audit and correction](audiobook-beeper/experiments/flutter-regression/README.md)
now qualify the current IMA4 integer PCM-origin table. On unchanged quiet
O. Henry PCM, field-noise peak falls26.525% and total error power14.483%;
the stronger speech control still passes20 dB.43 tests, full native/cold Fuse
loops, a real sequential reload/END OF AUDIO and byte-identical legacy/new
rebuilds pass. This is a periodic-noise reduction, not a subjective cure or
constant-clock implementation. The quiet excerpt remains below20 dB, and
bare-silence cyclic profile variation increases despite lower total noise.
The original full disk remains unchanged; the new looping audition is
`ZX-audiobook-IMA4-flutter-check.trd`. Reuse the saved complete evidence.

## Project objective

Fit the authorized movie edit on at most three independently bootable TRDs,
keeping resolution and 50 Hz AY. The user requested 10 fps on 2026-10-01;
prioritize exact five-field video
deadlines. All quality, fallback jitter, memory, cycle accounting, LFS and
release requirements in [AGENTS.md](AGENTS.md) remain mandatory. The generic
converter must also support other videos.

## Repository cleanup checkpoint (2026-10-05)

The user authorized repository consolidation and removal of old worktrees.
Completed AY audition, Speex/PVQ and contour research now belong to main;
volume-Huffman history is reconciled without reverting later improvements.
The [cleanup report](docs/maintenance/2026-10-05-repository-cleanup.md)
records 64 removed trees, 71 removed merged local refs, verified local recovery
archives and five intentionally retained trees. Historical paths may require
restoring an archive or supplying explicit input/tool locations. Existing
research next-step notes are checkpoints, not authorization to start another
experiment during cleanup. Current IMA/PDM playback is unchanged.

## AY speech audition checkpoint (2026-10-05)

The [O. Henry trial](ay-converter/analysis/o_henry/README.md) applies the current
AY music profile unchanged to source seconds 60..84: 1200 states at 20 ms,
persistent channels and chip-model noise fitting. Use
`ZX-audiobook-OHenry-AY50-test.trd` and the original/AY comparison WAV (AY
starts at 25 seconds). Two complete native/cold Fuse loops pass all 26400
writes /2400 fields, zero misses. Ordinary work remains 974 T, delta 0.
Full and detailed spectrograms show preserved pauses/parts of the pitch
contour but extra diffuse noise and lost upper harmonic detail. This is a
listening trial, not a speech-quality release; user acceptance is pending.
Reuse this completed evidence. No converter/player change or speech-specific
retuning was made; the accepted IMA3 speech reference remains separate.

## Completed audio request: gentle compression and normalization (2026-10-05)

After identifying vibration in `ZX-audiobook-IMA4-full-disk.trd`, the user
explicitly requests more source gain, normalization and gentle dynamic
compression. Implement this in the converter, processing the complete selected
track continuously before RAM splits. Preserve an explicit uncompressed
dynamics option and externally prepared PCM. Keep IMA/PDM timing unchanged;
validate the new complete disk and distinguish stronger signal from an actual
elimination of cyclic distortion. No merge/push requested.

The [vibration investigation](audiobook-beeper/experiments/ima4-flutter/README.md)
records all five parts through ordinary installed Fuse and speaker loopback.
It finds repeatable field-synchronous error power, not a strong simple 50-Hz
voice AM/FM component or a large host transport slip. It does not claim the
symptom fixed. The subsequent [source-conditioning change and complete disk](audiobook-beeper/experiments/audio-dynamics/README.md)
are now qualified: default gentle 2:1 compression/normalization, exact peak-only
off mode, prepared-PCM bypass and 30 passing focused tests. The new full IMA4
disk retains 113.712 seconds/all 2560 sectors; fresh complete native/cold Fuse
checks pass every bit/state, all transitions/UI and END OF AUDIO. Its SNR is
15.14..18.95 dB versus 10.33..13.53 previously; speed error is about +0.042%.
Archived streams rebuild the disk byte for byte. Cyclic error remains, and
part 3's fitted AM diagnostic increases; do not claim flutter eliminated or
20 dB achieved. No player/hot-path change, carrier reduction, merge or push.
This milestone is complete; do not open another experiment automatically.

The subsequent 2026-10-05 request authorizes cleanup of unsuccessful attempts,
merge into `main` and push. Retire intermediate candidate payloads, duplicate
traces and generated unselected builds while preserving reports, selected
streams and full release verification. See the cleanup entry in CHANGELOG.md.

## Completed audio request: audit the preferred direct IMA4 disk (2026-10-05)

The user prefers `ZX-audiobook-IMA-ADPCM-direct-test.trd` and asks when sound
quality changed and whether to restore the earlier algorithm. This steers
the active milestone to a historical comparison, not another clock design.
The [completed audit](audiobook-beeper/DIRECT_REGRESSION.md) authenticates four
complete two-loop records with identical source PCM and reconstructs them
with one float64 filter. The current assembler rebuilds the preferred disk
byte for byte; no player rollback is needed to recover that checkpoint.

The generic converter introduced in `d4a980d` dropped the old speech-specific
gain/limiter and band-pass preparation. On the same source position, the old
prepared speech is 8.332 dB louder RMS at the same peak. This is a level
difference, not an isolated measured PDM SNR gain. Modern IMA4 on the identical
old PCM has less measured waveform error; no blanket kernel regression is
established. Keep the preferred disk and reproduction guard, preserve current
converter defaults, and do not silently roll back clock corrections or apply
speech limiting to arbitrary music. No merge/push is part of this request.

## Pending audio requirement: fixed sample duration and fast conversion (2026-10-05)

The user requests equal physical duration for every audio sample, eliminating
recording-specific clock compensation. A complete disk should be generated
within the duration of the retained audio on the host PC. Shorter resident
parts are allowed; reducing PDM frequency is explicitly not allowed. Retain
approximately 128 kHz or higher and measure end-to-end quality. Do not silently
replace compressed IMA storage, reduce source bandwidth, or exempt normal
conversion stages from the speed measurement.

First audit the saved full-disk timing and benchmark the existing encoder
without repeating waveform searches. Native instruction equality alone is
insufficient: ULA port/RAM waits, page and bank transitions must all be included.
Any new player needs complete native/cold Fuse proof and explicit CPU counts;
host simulation, codec-only speed or ordinary-sample measurements cannot qualify
the requested result. Preserve the existing release while this is unverified.
The initial [audit](audiobook-beeper/FIXED_SAMPLE_CLOCK.md) is complete:
909696 measured source intervals span 423..598 T. Encoding 23.36 seconds takes
0.531 s with nearest-delta IMA or 13.517 s with the existing beam-32 encoder.
These are encoding-only results. The candidate 440-T / 16-output budget is
128978.182 PDM outputs/s; no such player is implemented or qualified yet.

## Full IMA4 disk through the public script — complete (2026-10-05)

The user requests a complete disk in IMA4 and explicitly requires our
existing conversion script. Extend `convert_audio.py --codec ima4` with
sequential RAM-sized parts, reusing the existing encoder, calibrated player
and disk controller. Use the supplied O. Henry audiobook. Account for each
part's recording-dependent decoder tables; shorten the final part to fill
the remaining sectors. Preserve the looping preview and IMA3 behavior.
Verify every final part, actual cold disk playback, automatic transitions,
loading UI, speed within 2% and measured quality. Keep loading pauses explicit.
Deliver one independently bootable TRD with source ranges and saved evidence;
do not open unrelated codec experiments or merge/push without a new request.

The [completed disk and evidence](audiobook-beeper/experiments/ima4-full-disk/README.md)
retain 113.712 source seconds in five parts, using all 2560 sectors. Complete
native and cold Fuse checks pass every bit, state, memory/paging check, four
automatic transitions, loading UI and END OF AUDIO. Speed error is about
+0.042%; measured loading pauses are 21.03–22.79 seconds. The fixed-clock
float64 SNR is 10.33–13.53 dB: the 20-dB target is not met, so the report
explicitly marks the otherwise verified output as a quality preview.

Twenty-five focused tests pass. Live timing remains 423 T/sample, delta 0.
The full disk's pulse timings match independently qualified references
exactly; the unchanged 8-T limit still includes every startup sample.
Natural HALT-phase qualification and optional phase-search failure handling
are now automatic. Original failures, exact producers, authenticated full
trace reuse and corrected native timing labels are preserved. Ordinary
looping preview binaries remain byte-identical. No physical-hardware or
multi-disk swap execution is claimed for this IMA4 milestone. Further
quality experiments, merge and push require a new request.

## Two-bit G.726 implementation — feasibility experiment complete (2026-10-05)

The user requests an implementation of G.726 at two bits/sample. Implement
and cross-check the exact16-kbit/s,8-kHz codec, retain the same reference
speech for quality comparisons, and measure a concrete Z80 implementation
before claiming live PDM playback. Keep IMA/mu-law defaults and releases.
Standard G.726 has a substantially larger adaptive predictor than IMA;
do not label a simplified IMA subset or a PC-transcoded disk as native
G.726 playback. The deliverable must include executable code, listening
output, tests, timing evidence and a documented integration decision. If
the measured decoder cannot fit the live budget, preserve that result
without weakening the2% speed requirement or claiming a qualified TRD.

The complete codec, PC converter/audition and separately compiled Z80
decoder now pass exact FFmpeg, cross-optimization and native PCM/state tests.
Three rounds reduce the matched-prefix cost127115.239 ->70442.908 T/sample;
the full186880-sample run averages70415.970 against a443.3625-T live budget.
Its CPU-only preparation time3710.095 s also fails the60-second limit.
The23.36-s payload is46720 bytes/8:1; codec-only filtered SNR17.077649 dB.
Retain this [tested research implementation and evidence](audiobook-beeper/experiments/g726-2bit/README.md),
without adding a misleading native G.726 TRD or changing IMA/mu-law defaults.
This requested bounded implementation is complete; further handwritten
optimization is a separate milestone, not an automatic open experiment.

## All active audio codecs — bounded quality follow-up complete (2026-10-05)

The later request to maximize all active audio codecs authorizes the bounded
[quality follow-up](audiobook-beeper/experiments/quality-max/README.md): finish
the pending speech IMA3 comparison, try the third IMA search for both bit
depths, and add waveform-aware mu-law encoding on the PC. This supersedes
the earlier pause for this milestone. Keep resident capacity, formats and
Z80 kernels unchanged; retain every verified fallback. Run full two-loop
checks for each new stream and preserve rejected prototypes. No new movie,
LPC/Speex/AY study, merge or push is part of this request.

Completed results: IMA3 fixed-clock/f64 minimum20.431992 ->20.655388 dB;
IMA4 keeps22.174535 after rejecting a9.849028-dB candidate. Mu-law's joint
two-clock search yields10.295781 dB versus6.533228 for its timing-only
control; its historical9.672027 metric used a different reference clock.
All new streams pass full native/cold Fuse two-loop verification and the
three selected images have normal-speed recordings. Fifteen tests and a
complete short public CLI conversion pass. Z80 costs and RAM are unchanged.

The subsequent **128-kHz eight-bit milestone is also complete**:
[packet algorithm, timing and full evidence](audiobook-beeper/experiments/mulaw128/README.md).
Compact mu-law remains one byte/sample. Sixteen-pulse table dispatch costs
423 T/sample versus432 (−9), with page/bank extras41/112 T versus35/116;
guard reset adds7 T once. All128 KiB are accounted for; tables reduce the
prefix to97024 bytes/12.128 nominal seconds without PCM/PDM expansion.
The public mu-law CLI defaults to `--pdm-rate 128000`;64000 preserves the
old exact-accumulator control. IMA3 remains the overall codec default.

Selected `ZX-audiobook-mulaw-128-test.trd` measures127927.577 useful outputs/s,
tempo−0.056580%, and25.244120 dB on both complete cold Fuse loops. The same
PCM16 reference gives11.927962 dB with64-kHz `best`. All3107833 bits and194049
feedback states, native RAM, paging, startup UI and repeat phase pass;
normal-speed Fuse capture is complete. Twenty-one tests pass. The30-dB
target is not met; no physical-hardware proof, exact full-precision SD2,
sequential mu-law volumes, merge or push is claimed. Finish this milestone
without opening another codec/model sweep.

## IMA4 overlapping PDM search — requested follow-up complete (2026-10-05)

The user chooses IMA3 for duration and IMA4 for quality and authorizes the
overlap transfer/experiment. Inspection confirms it already exists in
`--codec ima4 --quality best`. Complete only the previously paused speech4
refinement and a matched commit128 no-overlap control; other paused cases
remain paused. [Saved comparison](audiobook-beeper/experiments/ima4-overlap/README.md).
No production encoder/player changes are needed: all extra search remains
on the PC, IMA4 ordinary423 T/sample, delta0, page/bank extras14/140 T.

Both new streams pass complete two-loop native/cold Fuse, every bit and
predictor/index, memory/paging/UI and phase checks. However, the refined
commit64 stream's22.552121-dB host estimate becomes8.126727 dB on its own
clock; the matched commit128 control yields20.922286 dB. Keep the earlier
verified22.164431-dB overlap result. Separate consistent float64 audits
give22.174535 /8.126934 /20.928543 dB respectively. There is no new quality
improvement to claim. Data-dependent ULA waits matter despite unchanged
instruction counts. The final disk is a byte-identical copy of the prior
winner with a new normal-speed recording. Source/stage hashes and search
AST checks authenticate the reused host candidate; no mismatched resume
identity or interrupted Fuse proof is accepted. IMA3 stays default.

## Compact mu-law TRD control — complete, not a quality upgrade (2026-10-05)

The user now authorizes the real eight-bit mu-law converter and asks about
second-order quality. `convert_audio.py --codec mulaw` (`ulaw` alias) builds
an independently bootable looping RAM prefix with standard G.711 bytes,
512-byte inverse companding and all decoded 16 bits retained. No PCM/PDM
audio expansion; all 128 KiB are accounted for, holding121088 bytes/15.136 s.
The [first-order control and PC comparison](audiobook-beeper/experiments/mulaw-trd/README.md)
are complete. Native/cold Fuse verify every bit/level/error across two full
loops, full memory, paging, progress and loading UI; normal-speed audio is
recorded. Average PDM64119.013 Hz, speed+0.185958%, ordinary432 T/sample
(+4.625 versus IMA3); page/bank extras35/116 T. Seven tests pass.

Actual total SNR9.672027 dB is poor despite codec-only approximately39 dB.
Retain as a functional format/control preview; **do not replace IMA3** or
claim the 30-dB target. On the identical new PCM16 prefix, ideal PC SD2
at128 kHz gives27.185326 dB versus SD1's17.130225; at64 kHz11.536644 versus
10.053453. These numbers differ from the previous longer PCM8 study.
No second-order Z80 port or physical-hardware validation is established.
Further SD2 work needs an explicit next milestone; the older IMA quality
study remains paused. No merge or push requested for this deliverable.

## Compact mu-law/A-law audio — PC simulation complete (2026-10-05)

The user subsequently authorized eight-bit mu-law/A-law instead of IMA and
requires inverse companding inside modulation, keeping one stored byte per
sample and no expanded PCM audio buffer. The PC-first instruction remains.
[The new study](audiobook-beeper/experiments/xlaw-pc/README.md) selects mu-law:
30.920091 dB at768-kHz numerical integration,30.917095 dB at1536 kHz, both
using stable float64 filtering and128000-Hz PDM. Same source and filter
frequencies/order; all formats are compared under identical conditions.
A-law gives30.221673 dB; linear PCM8 control32.248227 dB. Old float32 scores
are retained separately after high-rate numerical instability was exposed.
Do not mix these numbers with historical measurements without rescoring.

Both payloads are186880 bytes for23.36 s, with512-byte inverse-companding
tables. The full model input exceeds Spectrum RAM: at the old94458-byte
audio budget it would hold11.80725 s, before new layout tradeoffs. Every
direct-byte pulse matches the expanded control; full independent decoder,
integer recurrence and stable finer-grid checks pass. WAVs and raw bytes
are archived. No Z80 port/TRD/default converter switch has been done or
authorized by this PC-only stage. Real timing, RAM layout and loops still
require proof. The earlier paused IMA quality milestone remains paused.

## 30-dB audio target — PC simulation complete (2026-10-05)

The user requires current IMA compression/duration and requested simulation
before another Z80 port. [The bounded study](audiobook-beeper/experiments/snr30-ima/README.md)
keeps the full 186880-sample speech reference, listening filter and 128-kHz
decision rate. Best ideal-clock total SNR is 21.227136 dB for IMA3 and
24.639507 dB for IMA4; 30 dB is not reached. The modulator alone exceeds
30 dB, but the IMA losses remain. Twenty-four configurations include two
overload rejections; the extra filtered-error encoder is worse. Save all
results and the independent PCM/bit checks. No new Z80 code/TRD/defaults or
hardware claim belong to this simulation. Do not port a candidate solely
because its modulator-only score passes 30 dB. This is not an impossibility
proof for another joint encoder/output algorithm. The older paused study
remains paused.

## Second-order audio experiment — completed, rejected (2026-10-05)

The separate [exact SD2 experiment](audiobook-beeper/experiments/sigma-delta2-128/README.md)
executes at 127652.961 Hz average with unchanged ordinary 427.375 T/sample.
It is noisier: 11.179067 dB after a silent-guard repeat fix, against the
accepted IMA3 reference's 20.436321 dB. Keep the old damped model as default.
All bits, predictor/index states, memory, paging and phase pass two complete
native/cold Fuse loops; normal-speed recording is saved. The guard reset
costs 7 T once per loop, offset by 7 T less calibrated filler. Bank-2 tables
grow by 2816 bytes. Preserve the failed initial candidates and use the
archived evidence instead of repeating this experiment. No physical test.
The user subsequently requested 30 dB while retaining current IMA compression
and duration; this is a separate error-budget investigation, not permission
to replace IMA with precomputed PDM or shorten the excerpt.

## IMA3 / IMA4 quality checkpoint — paused (2026-10-04)

The user requested saving progress and pausing. **Do not resume automatically.**
All study processes are stopped. See the exact
[checkpoint and resume instructions](audiobook-beeper/experiments/ima-quality/CHECKPOINT.md)
and [study](audiobook-beeper/experiments/ima-quality/README.md).

Both converters now offer a shared bounded `--quality best` waveform search,
measured-candidate selection, and verified fallbacks. IMA4 additionally
refines on the winner's measured clock. Fourteen tests pass; both short CLI
paths execute successfully and mark below-target previews correctly.
Ordinary Z80 costs remain IMA3 427.375 /IMA4 423 T/sample, delta 0 T.

Three new root TRDs and recordings are complete: Entertainer IMA3
19.031203 ->19.165090 dB, Entertainer IMA4 17.237725 ->19.897558 dB,
speech IMA4 21.010690 ->22.164431 dB. Music remains below 20 dB.
Speech IMA3 has one complete trace-qualified candidate at 20.659504 dB
(baseline 20.436321), but the other candidate and final recording remain
unfinished. Speech IMA4's final refinement has completed host encoding,
but its own Fuse verification was interrupted. Keep the earlier verified
speech IMA4 disk until the new stream proves better. Host scores are not
release scores. Preserve/reuse completed host searches and all saved traces.

This is a saved partial milestone, not a completed four-case release. The
worktree/branch is `C:/Work/ZX-video/.worktree/lpc-ima-preload` /
`codex/lpc-ima-preload`; no merge or push is part of this checkpoint.

## Exact PC encoder acceleration (2026-10-04)

The user requested faster audio encoding after the long normalized music
build. [Waveform search acceleration](audiobook-beeper/experiments/waveform-speed/README.md)
is complete. Keep beam widths, horizons and quality settings unchanged.
Reuse scratch arrays, parent backpointers and retained-state propagation;
replace full sorting with exact state merging and bounded selection.
An optional C kernel is built automatically with installed MSVC x64 or cc,
cached locally, and covered by producer hashes. No downloads. A compiler-free
NumPy fallback remains. The standalone encoder exposes `--backend` controls.

Three comparable 2048-sample repeats measure median 22.766993 s before,
12.571314 s with optimized NumPy (1.811x), and 5.589146 s with the native
kernel (4.073x). All three complete 186880-sample Entertainer search outputs
match the old bytes: new search times 102.094716/170.451387/652.329028 s.
Previous full CLI times include preparation/scoring and are not an exact
end-to-end comparison. Five new test methods and nine converter tests pass.
Reuse existing complete Fuse/quality evidence for the unchanged streams and
players; both published music disks are unchanged. Z80 delta is 0 T, ordinary
IMA3 cost remains 427.375 T/sample and page/bank extras +14/+140 T. The
28-artifact archive authenticates the comparison; no further sweep is needed.

## Normalized Entertainer pair (2026-10-04)

The requested [normalized music pair](audiobook-beeper/experiments/entertainer-normalized/README.md)
is complete. Use `ZX-music-Entertainer-normalized-IMA3.trd` and
`ZX-music-Entertainer-normalized-IMA4.trd`. Both loop the same first 23.344 s
of music, plus a 128-sample silent guard, from exactly the same PCM8/8-kHz
reference. Two-pass loudness preparation measures -17.89 LUFS /-1.97 dBTP,
1.95 LU above the same prefix of the earlier prepared example, without
clipped quantized samples. IMA4's new explicit `--prepared-pcm` preserves it.

All three IMA3 searches and two IMA4 compensation passes are complete.
Selected full-Fuse minimum SNR is 19.031203 /17.237725 dB, with speed errors
-0.299133% /-0.043272%. Both remain listening previews below 20 dB under the
user's permission to retain the best bounded music result. These compare
the existing different pipelines, not bit depth alone. Both cold boots,
two complete native/Fuse loops, paging/memory checks and normal-speed FMF
recordings pass. The 219-artifact audit authenticates the saved pair.
IMA3/IMA4 ordinary hot paths remain 427.375/423 T/sample, each delta 0 T;
no physical hardware or new user listening acceptance is claimed. Reuse
these reports; no further search is part of this completed deliverable.

## Direct IMA3 / automatic converter checkpoint (2026-10-04)

The [IMA3 and IMA4 comparison](audiobook-beeper/IMA3_IMA4_COMPARISON.md)
records the common recurrence, distinct packing/timing/memory and proposed
transfers. First candidate: automatic IMA4 waveform search with overlapping
windows on its existing player. This is a documented proposal, not a new
implementation or release. Local acceleration/prepared-PCM checkpoints are
identified separately from the inspected main baseline; reuse that work.

The latest AY follow-up is [chip-model noise colour fitting](ay-converter/analysis/noise_colour/README.md).
The music profile searches 31 noise periods and three bounded shared-level
choices using valid-rate Ayumi simulation, retaining all tone/channel IDs,
noise events/routes and the 20-ms grid. On the complete Entertainer example,
both cold Fuse loops improve unpooled spectral error at all three resolutions;
noisy-state error falls about 9–12%. Most benefit is level correction; colour
adds a small, mixed incremental gain. Full 34232 writes /3112 fields pass,
zero misses; 19 tests pass. Player binary unchanged, 974 T ordinary /delta 0.
Use `ZX-music-Entertainer-AY-noise-colour-test.trd` and the saved normal WAV,
matched spectrograms and complete evidence. Early invalid-rate model drafts
are explicitly rejected and archived; do not reuse them as quality evidence.
Default legacy remains byte exact; `--profile music --noise-fit heuristic`
reproduces the preceding tracked50 arrangement. Physical hardware and listening
acceptance remain unclaimed. Reuse the completed proof rather than retuning.

The preceding AY follow-up is [persistent components + mixed noise](ay-converter/analysis/tracked50/README.md).
The user requires continued sounds to stay on their original channels despite
small pitch/amplitude changes. The current optional `--profile music` tracks
three dominant fundamentals by pitch, with 289 component lifetimes /zero
migrations in the full Entertainer excerpt. Separately detected noise is mixed
on 415 ticks without disabling an active tone. All changes remain on the
20-ms grid. Full cold Fuse passes 34232 writes /3112 fields, zero misses;
14 regression tests pass. Player binary unchanged, 974 T ordinary /delta 0.
Cosine spectral similarity improves, but weak-spectrum error and some rhythm
proxies regress. Reuse the complete plots, every-state audit and normal WAV.
Previous listening disk: `ZX-music-Entertainer-AY-tracked50-test.trd`. The AY9
mixer extension needs the standalone reader; old legacy bytes remain exact.

The [50-Hz AY music improvement](ay-converter/analysis/music50/README.md) is
complete as an optional `--profile music` in the standalone converter.
The user fixes the sound quantum at 20 ms and excludes 100-Hz playback.
Seven bounded host variants select joint voice allocation, held note pitch,
short-window envelopes, YM2149 volume calibration and transient-limited noise.
The full 31.12-s Entertainer preview passes two cold Fuse loops: 34232 register
writes /3112 fields, no missing fields, unchanged player binary and 974 T
ordinary work (delta 0). Spectrogram error improves modestly; long-window
cosine and some other proxies regress. All measured tradeoffs, figures,
normal Fuse WAV and complete proofs are archived. Use
`ZX-music-Entertainer-AY-music50-test.trd` for listening. Keep the earlier AY
disk and default `legacy` profile. Reuse this bounded evidence; subjective
acceptance and physical hardware testing are not claimed.

The user accepted the actual interactive playback of the overlap speech
TRD in **Program Files Fuse 1.9.0** and requested it as the main algorithm.
`convert_audio.py` now defaults to the accepted packed IMA3/direct-PDM
pipeline; select `--codec ima3` or `--codec ima4` explicitly. IMA3 defaults
to one sequential TRD; the older IMA4 mode remains a looping RAM preview.
The separate IMA3 entry point stays compatible. See [converter usage](audiobook-beeper/CONVERTER.md).
The accepted setup is Spectrum 128 + Beta 128, 100% speed, 44.1-kHz/16-bit
host sound, visible window and no recording/debugger. No Z80 or disk changes.
This closes the pending acceptance of that control, without establishing
the cause of the earlier vibration or claiming all arbitrary inputs pass.

Previously, neither short modeled WAV had audible vibration, while the
user reported it in an earlier Program Files session.
The [host-output study](audiobook-beeper/experiments/fuse-host-output/README.md)
tests that native DirectSound build and `tools/fuse-1.9.0-sdl/fuse.exe` with
real WASAPI speaker-loopback capture. Their interior 19.8 seconds of generated
speech are byte-exact after identical resampling. Both valid 44.1-kHz runs
have only a two-sample (0.042-ms) range in coarse 100-ms-window alignment;
a clean 48-kHz control has a one-sample range and no clear improvement.
Windows output changes frequency balance and level; registered Realtek
effects are a hypothesis, not a confirmed cause. No settings were changed.
One small-buffer 48-kHz capture reported discontinuities and is rejected;
the enlarged-buffer repeat is clean. The user also hears **no vibration in
the actual Windows-output WAV**. Thus the reported symptom was not reproduced
in this controlled run. No stored Fuse config or active process was found;
the user's former unsaved settings remain unknown. A manual launcher with
the measured audio/machine options is available in the study for a visible
run without recording/debugger. That visible launch has now been performed
and accepted by the user. Do not resume blind codec tuning.
The earlier `host_audio_muted: true` FMF metadata was incorrect for native
Win32 (the SDL environment flag is ignored); the recorder is corrected.

The earlier vibration report prompted the historical
[residual study](audiobook-beeper/experiments/ima-3bit-residual/README.md), which
records seven bounded host controls and diagnostic WAVs: four-bit coding on
the same saved PDM clock improves a 4.096-s control from 21.600309 to
23.899006 dB, but is not a new executable disk or proof that flutter is gone.
Other three-bit controls are rejected as worse or immaterial. The subsequent
user comparison found no flutter in either short modeled control, and the
subsequent interactive run is now accepted. No new player or
TRD is released. Reuse these reports instead of repeating the same probes.

The narrower boundary-error correction is complete: [overlapping waveform search](audiobook-beeper/experiments/ima-3bit-overlap/README.md)
commits 64 samples of each 128/256-sample horizon. The automatic converter
uses it by default. On the unchanged sequential speech fixture, boundary
noise/interior noise falls from 1.835..1.840 to 0.999; both final parts measure
20.436046 dB, speed -0.271723%. Every native/Fuse output through EOF passes;
normal Fuse WAV is saved. Player/table binaries are unchanged, 427.375
T/sample, delta 0 T, unchanged RAM/payload/capacity. Use
`ZX-audiobook-IMA3-overlap-test.trd` as the accepted listening reference. This removes
the measured periodic boundary excess; residual IMA/PDM noise remains and
the user has accepted the interactive reference. Reuse its complete evidence.

The [sequential converter](audiobook-beeper/IMA3_SERIES.md) now defaults to
one TRD; `--disk-mode all` retains the whole selected track on numbered,
independently bootable volumes, and `--disk-mode preview` keeps the old
looping RAM demo. It loads/plays successive RAM-sized parts with audible
disk pauses. The 57-byte exit fits existing padding: no extra RAM, no new
per-sample cost, unchanged 94458-byte /251888-sample capacity. Five full
parts hold 157.35 seconds of source on one disk. Full native/Fuse tests cover
automatic loading, both cold disk boots, actual-RAM continuation, wrong disk,
all seven banks and CLI defaults. The root
`ZX-audiobook-IMA3-sequential-test.trd` deliberately plays the same 23.36-s
reference twice; measured 20.161979/20.161096 dB and a 19.798231-s load pause.
The synthetic full-capacity fixture is a correctness test below 20 dB,
not a longer quality release. Reuse the [archived evidence](audiobook-beeper/experiments/ima-3bit-series/README.md).

The [compact IMA3 table layout](audiobook-beeper/IMA3_MEMORY.md) is complete.
It reuses 352 code-gap bytes and removes excess padding, reclaiming 1024
physical RAM bytes with all decoder/PDM states retained. Fixed reservation
is 13312 bytes; automatic capacity is 94458 packed bytes /251888 samples /
31.486 s. Pulse instructions and 427.375 T/sample are unchanged, delta 0 T.
Two full cold Fuse reference loops have exactly the old 5981841 bits and
relative timestamps, preserving the existing 20.159645/20.159651-dB result.
Native and cold Fuse verify the new full seven-bank capacity with a synthetic
tail (8060417 outputs), not a longer real recording. Use
`ZX-audiobook-IMA3-compact-tables.trd`; retain earlier disks as baselines.
Reuse this proof instead of repeating the encoder search or quality checks.

The user also requested a movie-style AY version of the same music. The
[generic AY converter](audiobook-ay/CONVERTER.md) and separately assembled
looping player are complete. The 31.12-s The Entertainer example uses 17116
resident bytes; full cold Fuse checks cover 34232 writes / 3112 fields over
two repeats with no missed fields, loading-message hiding and a normal WAV.
Ordinary cost stays 974 T (delta 0); loop restart adds 105 T once per repeat.
Use `ZX-music-Entertainer-AY.trd`. The chip arrangement's musical similarity
metrics are not comparable to PDM waveform SNR; listening acceptance remains
with the user. Reuse this evidence instead of repeating the conversion.

The AY converter is also preserved as a [standalone source folder](ay-converter/README.md).
It includes the analyser, AY formats, TRD helpers, assembly player, renderer,
native/Fuse verifier and FMF parser. It runs without imports from the movie
or beeper projects. Original experiment sources and evidence remain available.

The separate [public-domain music example](audiobook-beeper/experiments/ima-3bit-entertainer/README.md)
uses The Entertainer by Scott Joplin, performed by IE. The user explicitly
accepts the best found music result below 20 dB. Three automatic searches
select a 31.128-s excerpt at 17.837011/17.836344 dB in complete cold Fuse
loops, with -0.328930% speed error and 0/0-T phase errors. The full 93432-byte
audio capacity now contains real music. This remains a listening preview
under the converter's unchanged 20-dB gate; no global optimum or physical
hardware claim is made. Use `ZX-music-Entertainer-IMA3.trd`. The player hot
path is unchanged, delta 0 T. Do not replace the audiobook reference below.

The direct packed-IMA3 implementation now passes the same complete original
186880-sample reference at **20.159645 /20.159651 dB** in two cold Fuse loops,
without Spectrum-side IMA3-to-IMA4 expansion. Resident audio is70080 bytes,
no PCM/PDM buffer; speed error-0.299133%, phase0/0 T, mean PDM127652.961 Hz.
Native427.375 T/sample is+4.375 T from the expanding player's423 T; page/
bank extras stay+14/+140 T. All5981841 outputs and373760 predictor/index
samples pass native/Fuse checks;32 loading progress steps and message hiding
pass. Normal cold boot to sound is22.815238 s; actual two-loop WAV and
completion audit are saved. Full93432-byte /249152-sample capacity is native-tested across seven
banks with a synthetic tail, not a longer real-source release.

Use [the automatic converter and evidence](audiobook-beeper/IMA3_DIRECT.md).
It handles FFmpeg input, preparation, separate assembly, calibration,
waveform search, complete quality checks, TRD and normal WAV automatically.
The selected width256 /128-sample /weight0.03 horizon scores20.159645 dB
on the pilot schedule and passes the newly executed disk. Default four-bit
encoding remains unchanged. A25-dB target is supported but not achieved
by this full-source IMA3 delivery; below-target runs return exit2 and remain
previews. Reuse the saved complete checks and hashed pilot rather than
repeating tuning experiments. The previous expanding20.071-dB disk remains
historical. New disk: `ZX-audiobook-IMA3-direct-test.trd`.

## Separate audio subproject checkpoint (2026-10-03)

Active throughput goal clarified on 2026-10-04: consecutive sample writes
are permitted; do not spend further work on output pacing. Exact Speex
default is now pure-r40: 1487605573 T / 7960.218 T/sample, 40.751%
fewer T than round09, but still 18.195x over the average 437.5-T budget.
Round17 reconciles nested costs with unchanged OUT traces; round18 selects
combined-register multiplication after comparing three candidates. All
1074400 PCM16/PCM8 samples and 589824 extra product/cycle cases pass.
Rounds19/20 replace the seven-bit excitation shift and retain innovation
table state in registers; 396800 isolated shifts and all 64 table energies
pass. Round21 rejects unprofitable zero guards; round22 selects zero-feedback
state copy and removes an unread store, saving exactly 11359020 T. All
4650 arbitrary-history checks per variant pass. Round23 inlines products,
holds offsets in index halves and borrows SP for first-part reads. It saves
98139844 T versus round22 including setup; 7719 arbitrary histories and 128
filter calls per variant pass. Round24 adds a pre-negated table step and saves
12603144 T; all 65536 coefficients and 262144 negations pass after fixing
an initial borrow bug. Code/state 10527/1041 bytes, useful tables 14140 bytes within 16 KiB;
fresh default build matches and every playback code write is forbidden.
The below-10000 intermediate target is met. Round25 reconciles the full
profile with identical PCM/OUT traces: inline feedback 35.880%, decoder
body 16.470%, preparation 13.728%, 44692 observed changed pages. Round26
then saves exactly 16205909 T by keeping the pitch sum in alternate registers;
200187 sum and 589824 helper-preservation cases pass. Round27 shares a history
cursor for pitch >=41, saving 43983608 T; all 81920 address cases per variant
and 1094880 complete-stream samples pass. General path adds one T/sample.
Round28 selects 65 constant pitch-gain routines using same-size pointer
triples: -96923613 T, all 4259840 products per candidate and 1094880 complete
samples pass. Generic energy multiplication and the table arena stay unchanged.
Round29 returns A:HL directly, saving 12976212 T and 325 code bytes:
**below-9000 intermediate target met**. All 4259840 products, 200187 sums,
163840 history cases per variant and 1094880 complete samples pass.
Round30 confirms the 93-T synthesis shift, saving exactly 27 T/sample;
every OUT delta agrees. Both versions pass 393216 isolated shifts, 1572864
rounding boundaries and 128 filter calls; selected 1094880 full samples pass.
Round31 selects two unsigned partials for signed16x16: -40455507 T, code -39.
All 16777216 unsigned and 2228224 signed products, actual operand/cost
reconciliation, instruction/memory guards and 1094880 complete samples pass.
Round32 shares Q14 coefficient normalization: -5359215 T, code +179.
All 1343488 Q14 cases, 1179648 unsigned products and 1094880 complete samples
pass. Full fixtures improve; 40193 individual speech calls regress. Fresh
default identity matches. Round33 removes that double sign reversal and
uses sign-specific combination: -11022228 T, code +8. Every Q14 input saves
30..211 T; 1343488 arithmetic cases and 1094880 complete samples pass.
Round34 removes 64 cancelling EXX pairs per changed page: exactly
-22882304 T, code -128. All 65536 coefficient pages per variant, 1024 page
masks and 1094880 complete samples pass; registers/flags/BSS match. The
44692-page count and preparation/full saving reconcile with identical inputs.
Round35 retains 16*step in BC/BC' and uses aligned group-end addresses:
exactly -7999868 T, code -27. All 65536 coefficients, 10240 address cases,
1024 page masks and 1094880 complete samples pass; every OUT delta matches
179 T per preceding changed page. The below-8500 intermediate target passes.
Round36 selects direct aligned cosine words and an exact polynomial fallback:
-21301571 T, code -2, table bytes -1870. All 25737 angles per binary, 720896
P13 cases and 1094880 complete samples pass; every OUT delta reconciles.
All speech calls align; random packets exercise two fallback calls. All full
fixtures improve, but unaligned individual calls are slower.
Round37 fuses Q14 and its caller negate: -8467830 T, code +153, state/tables
unchanged. All 1343488 arithmetic cases and 1094880 full samples pass;
caller instruction audits and every OUT delta reconcile. All full fixtures
improve, but 6773 individual speech calls regress.
Round38 reads Q14 arguments directly: exactly 45 T/call, -4204800 T, code +2.
All 1343488 arithmetic cases, 18384 pointer cases per binary and 1094880
full samples pass; every OUT delta reconciles. State/tables unchanged; the
retired upper argument bytes are write-protected.
Round39 omits zero top feedback partials: -35432446 T, code +581, state/
tables unchanged. Eligible samples save 653 T, other nonzero samples pay
21 T and zero samples are unchanged. Both binaries pass 196608 feedback
cases and 128 arbitrary-state filter calls; all 1094880 complete samples,
all fixture cost predictions and every OUT delta pass. No full fixture
regresses.
Round40 selects small signed magnitude products with subtractive updates:
-31084822 T, code +902, no extra state/tables. The below-8000 target is met.
All 196608 feedback cases per binary, 327680 negate cases and 1094880 full
samples pass after fixing an intermediate-byte borrow bug. Every fixture
and OUT delta reconciles; two tone fixtures regress by about 0.15%, while
other full streams improve or stay unchanged. Next inspect negative 12-bit
magnitude/subtraction, retaining -4096/general fallbacks; not implemented
or measured. The next intermediate target is below 7800 T/sample.
The average real-time goal is still unmet.
The broader goal remains active. Use the
[throughput worklist](audiobook-beeper/speex-port/THROUGHPUT_TODO.md) and
[round40 report](audiobook-beeper/speex-port/rounds/40/REPORT.md), not the
historical PVQ scheduling milestone, to select the next optimization.

Latest optimization milestone on 2026-10-04: selected PVQ round13 retains
round12 sound and all 80974 stored bytes, while reducing complete unpaced
CPU from 16897348 to 15651480 T (83.7515 T/sample, 7.373% fewer T).
Every 437/438-T port interval and 25 short-length checks pass. Conditional
round14 reaches 62528 bytes / 2.98874:1 and 69.3130 T/sample, but loses
3.6550 dB raw SNR and is rejected against the declared one-dB gate. Keep
round13 selected; exact Speex remains pure-r9. Table RAM remains 4614 bytes;
ULA/hardware timing remains unverified. Both experiments and reproduction
are linked from the [completed target](audiobook-beeper/speex-port/NEXT_TARGET.md).

Further follow-up on 2026-10-04: all six items in the
[new audio worklist](audiobook-beeper/speex-port/FOLLOWUP_TODO.md) are closed
in the same `codex/speex-port` worktree. Exact default `pure-r9` costs
2510789186 T / 13435.302 T per sample, 9.00% less than round04, but still
30.71x over budget. 1074400 exact PCM16/PCM8 checks pass; code/state are
6624/1039 bytes and the table arena remains 16 KiB. Reduced-precision Speex
and periodic waves were tried and not selected. A separate assembly
PVQ3x1024 player now verifies the complete 186880-sample control with exact
437/438-T output intervals including banks and tail; 90.418 T/sample before
pacing, 80974 stored bytes (2.308:1 versus PCM8), 4614 table bytes. Raw source
SNR is 23.510 dB. This changes the format; it is not real-time Speex.
ULA/physical timing, particularly contended input banks, remains unverified.
Reuse [current code, reports and reproduction](audiobook-beeper/speex-port/README.md).

Initial follow-up on 2026-10-04: the separate `codex/speex-port` worktree contains a
complete assembly Speex narrowband mode-3 decoder with direct PCM8 port
output. Its six-item optimization worklist is complete, with a report and
focused commit for every item. The selected `pure-r4` is 1.644x faster than
the original assembly, at 14764.861 T/sample, but **not real time** against
the 437.5-T budget at 3.5 MHz/8 kHz. The table arena is exactly 16 KiB (16010
useful bytes); code/state are 6152/1356 bytes. All 1074400 tested PCM16/PCM8
samples match, including speech, signal/capacity and random mode-3 packets,
with arithmetic/LPC, memory and instruction-timing checks. Reuse the
[implementation and evidence](audiobook-beeper/speex-port/README.md).
At that initial checkpoint the sine-table suggestion was an unimplemented
approximate alternative; a 388-T four-oscillator kernel estimate excluded
parameter extraction, noise, scheduling and ULA contention. It is not a
verified Speex playback result. Prefer assembly for further Z80 programs.

### Earlier preload and codec studies (2026-10-03)

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

## Shared automatic AY sound engine — complete (2026-10-13)

The user requests automatic tone/noise/mixed selection, closer PCM matching,
shared movie/audio conversion and repeated-pattern reuse. Both public entry
points now use `ay-converter/engine.py`, defaulting to `auto` with the previous
music/legacy profiles retained. Five complete eight-second excerpts improve
selected mean log-spectral error; auditions and regressions remain explicit.
The exact-repeat mixer cache passes byte identity; strict spectral reuse has
zero hits in these recordings. No playback grid, RAM layout or Z80 instructions
change. Sixty-six relevant tests, native two-loop excerpts, three cold Fuse
sound auditions and a complete five-frame 10-fps movie fixture pass. Both
public commands produce identical sound states. This does not rebuild or
qualify the complete movie with the changed soundtrack. Reuse
[the method and saved evidence](ay-converter/analysis/auto_mixer/README.md).


### AY phrase dictionary experiment — complete, rejected (2026-10-13)

The requested repeat-code idea was measured separately on eight exact streams.
AYP1 has correct lossless round trips but uses more bytes than existing AYH1
and increases gzip size. Keep the measured host prototype and report; retain
the release codec. No native decoder or subsequent experiment is authorized
by this completed milestone. See the automatic-mixer report's phrase section.

## First five minutes of Big Buck Bunny AY audio — complete (2026-10-13)

From `e7450386`, convert source 0..300 seconds with the shared default `auto`
engine, preserving all 15000 states on the 20-ms grid. Analyse the timeline
continuously, render one complete listening WAV, and package independently
bootable resident audition disks (three 100-second parts with hardware envelopes). The source has no movie edit.
Complete native and cold Fuse checks for every state on all disks; save
listening artifacts and a reproducible report. Count and verify any resident player
instruction changes needed for the authorized hardware envelopes. Independent candidate rendering may
be scheduled concurrently after byte-equivalence checks; do not open another
codec/quality sweep or rebuild the video releases as part of this request.

The user subsequently authorizes shared analytic proposals, PCM normalization,
complete simulation feedback for levels/frequencies, relative psychoacoustic
masking, and hardware envelopes configured across multiple 20-ms fields.
Finish this sound deliverable with actual envelope-aware native/cold playback
proofs; report any changed resident disk count. Full movie release remains
outside this milestone; preserve its current qualified disks.

The subsequent requests authorize an explicit AY-3-8910/YM2149 target,
source-evidenced sparse noise, bounded smooth dynamic-range compression and
centre-priority 5.1 downmixing shared by both public entry points. The final
300-second host/native set is built, with zero strong level-hole fields under
the documented source-audibility check. All three complete cold runs now pass 15000 fields and 195145 exact bus
writes, with zero missing/duplicate fields or runtime disk reads. The complete
listening set and proofs are archived in ay-converter/analysis/bbb_5min/evidence.
This authorized sound deliverable is complete; do not open another quality sweep. Current audio format is
AY12/14 registers; ordinary resident work increases 974 ->1166/1206 T.

## Thirty-second O. Henry listening follow-up — complete (2026-10-13)

The requested source[60,90) WAV uses the current shared auto engine, AY-3-8910
and compact dynamics. All1500 packed/control states, source/producer hashes
and30-second WAV/headroom checks pass; listen in
[the retained audition](ay-converter/analysis/o_henry/README.md). No converter
or native instruction changes, new Fuse qualification or broader search.

## Hypothetical six-voice waveform experiment — complete (2026-10-13)

The user authorizes a bounded script/WAV experiment with six AY-like voices
and square/triangle/sine selection on the same O. Henry source[60,90) prepared
reference. Complete selectable and square-only controls-only WAV replays,
four independent tests and exact source/producer/artifact checks pass.
Selected spectral objective8.18696 versus old AY9.24885, with worse short-field
level MAE2.03192 versus1.36731 dB; no listening grade or isolated voice-count
claim. [Code, auditions and evidence](ay-converter/analysis/six_voice/README.md).
No real-chip, Z80, release, full-film or subsequent model search is part of this
completed request.

## YouTube sea-foam one-disk excerpt — complete (2026-10-13)

From `7f9206ed`, deliver a beginning-of-source excerpt of the user's
`WGc7ptKfA9c` video with the existing guarded CB46 and real AY-3-8910 pipeline.
The selected source[0,50.7) interval has507 frames at10 fps and2535 AY fields
at50 Hz, on one independently bootable TRD. Complete dirty-RAM cold Fuse,
all native screen bytes, every AY record and all nominal publication deadlines
pass; zero missed deadlines, no late runs, maximum in-field deviation17 T.
The MP4 preview, source/producer hashes, complete proofs and the superseded
longer attempt are retained in [the archive](toolkit/analysis/sea_foam/README.md).
The resident audio forest bounds the conservative selected part; no maximum
single-disk duration or full-cartoon qualification is claimed. The prerequisite
checkpoint fix changes startup by+255 T and runtime by0 T. Finish this authorized
excerpt; no new RAM/codec sweep or existing movie rebuild is part of it.

## Source-matched stable colour for the sea-foam excerpt — complete (2026-10-13)

The user requests colours closer to the original and less attribute flicker.
From `7886808a`, add bounded source/output comparison to host CB41 preparation,
including all legal colour pairs and temporal feedback among close candidates.
Preserve resolution, fixed dither phase, the exact50.7-second RGB source and
2535 existing AY fields. Compare every frame against the retained legacy
reference, inspect difficult scenes and provide source/old/new previews.
Rebuild and fully cold-Fuse qualify the same excerpt, including every screen,
AY field and nominal deadline, before replacing its root TRD. Native ABI and
instructions remain unchanged; record0 T delta. Keep old measured evidence.
Do not expand to the full cartoon, audio memory optimization or unrelated
colour/model sweeps as part of this requested correction.
The user additionally requires current-frame colour without trailing changes:
history is disabled in every cell with any source component delta above4 codes.
Add a public `--monochrome` option for explicit black/white spatial gray output;
retain unchanged audio/cadence and check both supported host formats.
The user identifies artificial8x8 cell-border blocks in smooth source areas.
Add current-frame spatial coherence across attribute boundaries, comparing
source-relative edge steps and protecting actual contours with source contrast.
Keep sample-level actual RGB/chroma guards; temporal history must not delay
meaningfully changed cells. Complete the same selected excerpt qualification.

The final `df44dac2` selector meets the requested correction on all507 frames:
boundary residual231.36326 ->151.03494, temporal chroma58.44063 ->43.06844,
quiet pooled luma18.12883 ->13.68272. Synthetic smooth-gradient grid error
falls97.72%; moving-source colour and real-contour tests pass. Twenty-seven
tests and both monochrome CLI CPU/content smoke checks pass. The rebuilt
one-disk excerpt fully passes dirty cold Fuse, all3504384 screen bytes, every
2535 AY record and all nominal deadlines; maximum in-field deviation19 T,
zero late runs. Actual sector count1436. Preserve old evidence and all measured
draft outcomes; use [the comparison/archive](toolkit/analysis/sea_foam/README.md).
No source/AY change, native instruction change, full-cartoon or subsequent
model search is part of this completed request. Actual two-colour-per-cell
limits remain; do not claim perfect gradients, source gamut or zero artifacts.

## Six-voice clicks/ringing follow-up — candidate delivered (2026-10-13)

The user reported clicks and periodic ringing and authorized continuation in
a separate worktree. Use `.worktree/six-voice-clicks`, branch
`codex/six-voice-clicks`, from `bd2a5be2`. On the same prepared O. Henry[60,90)
reference, diagnose large control-boundary and DC jumps plus output harmonics
outside the 8-kHz fitting band. CLI defaults now explicitly model a 4-ms
raised-cosine level/shape/route transition, aligned triangle fundamental and
8-kHz output filter. Six continuous phases, 16 target levels and 50-Hz controls
remain; smooth transitions extend the hypothetical model, not real AY writes.

Nine full same-control ablations and complete final feedback are retained.
Selected boundary derivative power falls72.3%, boundary/interior ratio
1.863759 ->1.120837, and power above9 kHz is negligible. Objective slightly
worsens8.186964 ->8.281203 dB; level MAE improves2.031917 ->2.002794 dB.
Inside-band excess-tone fields remain12; complete ringing removal or speech
intelligibility is not established. Eight tests, old/new exact controls-only
WAV replays, all1500 states, zero clipping and complete source/producer/media
hash checks pass. [Candidate, before/after, evidence and reproduction](ay-converter/analysis/six_voice_clicks/README.md).
Listening acceptance is pending. The bounded deliverable is ready; do not
start another search automatically. Existing native players/releases unchanged.

## Six-voice source/output spectrogram follow-up — complete (2026-10-13)

The user requests spectrogram comparison and closer spectral reconstruction.
Continue `.worktree/six-voice-clicks` from `15d01878` on the same prepared
O. Henry[60,90) reference. Common-scale full/detail maps expose weak upper
partials, 2..4-kHz power0.315397 of source and29.008758% of output power below
50 Hz. Six-voice CLI defaults now use512-sample analysis, source-only inverse
magnitude weighting exponent1, four extra peaks per band, and explicit
control-only DC compensation in a balanced hypothetical mixer. Retain six
phases, 50-Hz/16-level targets, shapes, shared noise, 4-ms morph and8-kHz FIR.

Sixteen complete trials are retained and replayed. Select the lowest objective
that improves both cosines, log error and convergence on all three scales,
level MAE and subsonic power. Reject exponent1.5/window512 despite its lower
scalar objective because long-window dominant-partial agreement worsens.
Actual saved-WAV objective8.281245 ->6.771566 dB, level MAE2.002844 ->0.789174,
cosines0.820376/0.823144/0.852582 ->0.899120/0.848475/0.864305. Sub50-Hz power
29.008758% ->0.137689%; 2..4-kHz relative power0.315397 ->0.846484, with
remaining bin-wise errors above4 kHz. [Figures, new WAV, all trials and reproduction](ay-converter/analysis/six_voice_spectral/README.md).
Twelve tests, full1500-state/1323000-sample candidate and all16 trial replays,
previous-WAV replay, zero clipping and source/producer/artifact hashes pass.
Balanced DC compensation explicitly extends the hypothetical model; no real
AY/Yamaha/Z80/release proof or global optimum is claimed. Listening acceptance
is pending. The bounded deliverable is complete; no further search opens
automatically. Existing native players/releases are unchanged.

## Six-voice compressed-command size — complete (2026-10-13)

The user accepts the overall spectral candidate sound with residual
squeaking/ringing and requests storage size. Reuse its exact30-second/1500-
update controls from `593301b6` in `.worktree/six-voice-clicks`; no new fit.
All18 combinations of packed/columnar/delta layouts, DEFLATE/XZ/ZX0, and
30-second/1-second blocks are measured and recover every control/model setting.
Complete1,323,000-sample recovered-control WAV replay is byte-identical.

Raw aligned commands24,036 bytes including header; columnar ZX017,897 for
one30-second block or19,853 for independent1-second blocks, versus XZ16,180.
Absolute columns beat deltas. ZX0 gives estimated35.8..39.7 KB/minute or
2.15..2.38 MB/hour by linear scaling of this excerpt; longer audio unmeasured.
[Streams, full report, format limits and reproduction](ay-converter/analysis/six_voice_storage/README.md).
This is the hypothetical six-voice model, not a native AY format; no real
chip, Z80 decoder timing or release proof. Native code/releases unchanged.
The bounded size deliverable is complete; do not open another search.

## Six-voice real-time decoding — complete (2026-10-13)

The user authorizes real-time decoder verification after storage commit
`b6d8badc`. Reuse the exact19,853-byte one-second ZX0 control stream without
refitting. Native Standard/Turbo decoders plus an IM2 double-buffer consumer
pass all60 actual block timing checks,60 varying-phase interrupt injections,
and two full1500-field schedules with two-field preparation. Turbo additionally
passes a full one-field schedule; Standard's one-field underflow at field400
is retained as a rejected partial run. All actual commits/values are checked.

Worst decode21.849/17.362 ms Standard/Turbo for each second of commands;
including IRQs22.714/17.795 ms. CPU including every command IRQ4.059/3.679%.
Flat output1168 T ->columnar1268 T (+100); IRQ1505/1605 +29 entry/vector T.
Working RAM3938 bytes; minimum two-field ready margins17.297/22.216 ms.
Commit lag<=0.422059 ms, intervals70808..71008 T with no origin drift.
[Full traces, report, code and reproduction](ay-converter/analysis/six_voice_realtime/README.md).
This establishes instruction-table throughput for the hypothetical19-register
device. Disk/ROM/video/contention, actual AY/hardware audio and release playback
remain unmeasured; native release instructions are unchanged. The requested
decoder check is complete; no further experiment opens automatically.

## YM3812 nine-channel speech simulation — complete (2026-10-13)

The user authorizes a YM3812/OPL2 reconstruction of the same accepted sound.
Use `.worktree/ym3812-speech`, branch `codex/ym3812-speech`, from `86b959f9`.
Reuse the exact prepared O. Henry[60,90) source,1500 targets at50 Hz. Compare
nine carrier-sine channels, all four real OPL2 carrier waveforms, and a bounded
two-operator FM patch bank; one FM comparison may ramp TL through real writes.
Render actual YM3812 register streams with pinned ymfm-py0.2.0, export VGM,
retain all trials, source/output figures and an audition. Check complete
controls/VGM/audio replay, chip constraints and no source PCM in output.
Do not modify the six-voice model or release/native players, or open another
hardware/CSM/voice-count search. This is emulator evidence, not a real-chip
qualification or a promise of better listening quality.

All eight1500-field streams replay exactly via real OPL2 VGM writes; five
independent tests pass. Keep multiplier1 and multiplier1/2 banks. Select
`mult12/sine`: magnitude cosines0.944152/0.899093/0.903570, level MAE0.304720
dB, sub50 power0.030281%, peak0.892415/no clipping. Combined log score7.242039
is worse than six-voice6.771566; short root cosine also worsens. Strict
all-root/cosine guard has no eligible trial; deliver the explicitly narrower
dominant/level/subsonic audition choice. Four-waveform log winner6.593306 has
10.912983% sub50 power. Selected VGM161158/VGZ61653 bytes; all native/output
samples and states checked. [WAVs, metrics and reproduction](ym3812/analysis/ym3812/README.md).
The core's unused wave-disable-gating limitation is recorded; streams enable
the bit. Physical chip/Z80/release proof and listening acceptance remain
pending. Existing native code/releases unchanged. Simulation complete;
do not open another experiment automatically.

## YM3812 frame-boundary clicks — complete (2026-10-13)

The user likes the YM3812 audition but hears clicks and suspects audio-frame
boundaries. Reuse exact1500 targets/gain from `60e8bb3e` in the same worktree;
do not refit spectra. Carrier TL accounts for95.42% of the measured immediate
register-effect squared sum. Eight full trials compare real TL ramps and
split pitch-register ordering. Select eight-step raised-cosine nominal2-ms
TL transitions plus pitch order minimizing temporary frequency excursions.
Actual serial bus completion is<=4.217687 ms; all exact20-ms targets remain.

Squared immediate write effect6.984949 ->1.398379 (-79.9801%); largest effect
0.286625 ->0.069429. Dominant cosines0.944361/0.899641/0.904923 slightly improve;
level MAE0.304720 ->0.424978 dB and log/level7.242039 ->7.376224 worsen. Root
cosines worsen too. Eight unit tests and all8*1500 states/full native replays
pass; old media and revised CLI replay byte-exactly, zero clipping. Selected
82,166 writes,337,171 VGM /134,200 VGZ bytes. Keep all trial streams/reports.
[Audio, comparison, figures and reproduction](ym3812/analysis/ym3812_clicks/README.md).
Diagnostics include legitimate pitch/envelope changes; do not claim perceptual
click elimination. Listening acceptance pending. No native/player/release
changes or physical-chip/Z80 proof. This bounded deliverable is complete.

## Pattern/solid cell-boundary correction and full-disk extension — complete (2026-10-13)

The user still sees character-cell rectangles and sharp patterned/solid borders.
From `0085a116`, inspect actual native texture, not just averaged RGB. Fit palette
and fractional density together with globally anchored coordinates, source-edge
texture continuity and current-frame palette coherence. Preserve true contours,
frame cadence, resolution and the existing2535 AY fields. Use the same507-frame
sea-foam source and retain `db07319e` evidence. Compare visible native patches and
defined texture metrics before accepting the host candidate; fully cold-Fuse
qualify every final screen/AY field and nominal deadline before replacing TRDs.
Native ABI/2x2 lookup phase remains unchanged, instruction delta0 T. Work on
`codex/attribute-pattern` to preserve concurrent codec-library edits on main.

The user rejects the whole-image fractional-density draft for visible noise
and identifies the false red rectangle on frame259. Supersede it with the
crisp baseline quantizer, a source-relative20-degree opponent-colour cone and
four-native-pixel local gray seam feathering. Keep real contours and all other
dither samples; do not retexture entire smooth regions. Archive the rejected
draft as an interrupted host attempt, never as a native-qualified release.

The final local selector additionally handles source-smooth NORMAL/BRIGHT solid
steps. All507 final screens and2535 AY fields pass complete cold Fuse with zero
nominal misses and maximum deviation17 T. Preserve its qualified checkpoint.
The user now requests a video occupying one full disk: extend the continuous
source prefix toward actual single-TRD capacity with these image settings,
10 fps and unchanged50-Hz AY. Measure real resident memory, actual disk sectors
and complete native timing; do not silently reduce quality/cadence or publish a
size-only estimate. Reuse verified cached preparation when all source bytes
and selector parameters match. The fixed AY forest permits1005 leading frames,
not the conservative507-frame bisection. Disk capacity is the remaining gate.

The practical full-disk result is900 frames/90 seconds,4500 unchanged AY fields
and one TRD with2529 used/15 free data sectors(99.4104%). The1005- and940-frame
attempts require2704 and2602 sectors and remain failed size probes. The final
disk completely passes independent cold Fuse, all6220800 screen bytes, every
AY record and all nominal deadlines; zero late runs, maximum deviation22 T.
Archive the full media, all-frame source metrics, matching507-frame old/new
comparison, complete native proofs and failed attempts; replace the root disk
only after qualification. Native instructions remain unchanged,0 T delta.
The authorized image correction and practical one-disk fill are complete.
No full-cartoon rebuild, further model/codec/RAM experiment or push is opened.

## AY spectral transfer — complete (2026-10-13)

The user requests saving the transfer plan, a new worktree, implementation and
measured outcomes. Branch `codex/ay-spectral-transfer` starts from `6168ba14` at
`.worktree/ay-spectral-transfer`. Follow [the saved plan](docs/ay-spectral-transfer-plan.md):
direct integer-period spectral fitting; inverse weighting/band peak candidates;
transition-aware selection; then a separately qualified subframe DAC-ramp
probe. Use the exact prepared O. Henry[60,90) reference and1500 current states,
including envelopes; avoid double source conditioning. Retain all trials and
failed guards, figures, streams and exact auditions. Preserve default/release
code until evidence admits a change. The subsequent user steering adds source
verification of the installed Fuse sound model and explicit AY/YM comparison.
Finish each milestone before opening the next; do not treat a model-only
subframe experiment as native scheduler or release qualification.

Fuse-source steering is complete: official1.9.0 source uses AY-3-8912 masks,
16-level envelope and its own DAC; static Ayumi curve MAE1.928268 dB AY versus
3.328873 YM. Default AY is retained. Optional standalone `psg_probe.asm` uses
R1=1Fh, validates used-bit reads and restores R1;30 native fixtures pass,
265/279 T AY/YM excluding CALL. Current player unchanged. [Proof](ay-converter/analysis/ay_spectral_transfer/FUSE_SOUND.md).
Continue the original ordered encoder plan; source checks do not finish it.

Stage1 direct-period fitting is complete with two rejected trials:512/2048
objectives10.112593/10.711803 versus9.248850, with improved dominant cosines
but worse weak-bin log error. Keep baseline and both full trials. Three tests,
all2*1500 states and exact full WAV replays pass; native/default code unchanged.
[Evidence](ay-converter/analysis/ay_spectral_transfer/README.md). Continue stage2
inverse weighting and regional peaks, then transition and subframe milestones.

Stage2 is complete: exponent1 gives9.926241; regional peaks9.913041 versus
baseline9.248850. Long dominant cosines0.728756/0.730898 fail the saved guard;
both rejected. All four full stream/WAV checks pass. Continue stage3 and the
separate subframe probe without changing the default encoder or guard.

Stage3 is complete: continuity0.02/0.05/0.1 objectives9.900928/9.901714/9.874857;
existing feedback plus envelope reaches9.667439, still worse than9.248850.
All four final streams/WAVs replay exactly, including AY12 state decoding.
All rejected under saved guards, default/native code unchanged. Continue the
separate timed-DAC probe on retained baseline; no native scheduler claim.

All four bounded milestones are now complete. Timed eight-step2/4/8-ms
real-DAC ramps reduce same-state step energy21.88..22.15%, below their25%
integration threshold;19,574 ->25,707 writes and67,644 ->88,122..89,953 gzip
bytes. Scalar timed-baseline9.338099 ->9.326758/9.302608/9.264055; spectral and
dynamic tradeoffs retained, no native scheduler added. Seven tests pass; nine
unique50-Hz streams execute27,000 total native fields/two full loops each,
exact values/banks/stack. General CLI reproduces AY stream/WAV byte exactly;
explicit YM variant9.814675 does not make Fuse a YM model. Default remains
the current9.248850 encoder; best new full pipeline9.667439 is rejected.
[Completion, auditions and all results](ay-converter/analysis/ay_spectral_transfer/README.md).
No physical-chip/Fuse-audio/movie-release claim; no hot-path change, delta0 T.
No further sweep, native scheduler, merge or push starts automatically.
