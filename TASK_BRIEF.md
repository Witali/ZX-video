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

## Active deliverable: 10 fps

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
A user preference question is pending: four disks at 10 fps/unchanged quality,
retain the verified three-disk 25/3-fps set, or further compression into three.
[Evidence, limits and reproduction](toolkit/CB41_10FPS.md).

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
