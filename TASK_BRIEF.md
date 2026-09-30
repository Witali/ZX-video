# Focused optimization task

Updated 2026-09-30. Use this brief to continue the project in this or a new
chat. This document scopes work; it does not start an automatic goal.

## Project objective

Fit the authorized movie edit on at most three independently bootable TRDs,
keeping resolution, 25/3 fps and 50 Hz AY. Prioritize exact six-field video
deadlines. All quality, fallback jitter, memory, cycle accounting, LFS and
release requirements in [AGENTS.md](AGENTS.md) remain mandatory. The generic
converter must also support other videos.

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

## Latest completed milestone: one five-level TRD, timing failure measured

After `a7cdf98`, build one 192-frame montage (64 frames at 629/2857/3855),
with original AY slices, five-level 2x2 pixels, one full-volume 172-row book
and the integrated Fast ZX0 player. The separate `05d2bf4` fix removes the
decoder's fixed Huffman-body placement assumption with 0 T cost change.
The image is independently bootable and occupies 489 file sectors.

All 192 frames reach EOF in real Fuse. AY records, sectors and sampled
pixels are exact; six full screens match all 41472 bytes. Thirteen tests
pass. **Cadence fails:** mean 6.7491 fps, 174 late frames, maximum 269 fields
of accumulated delay, an unrecovered late run through EOF. Both nominal and
fallback gates fail. Keep the root test image for visual inspection only.

Read [FIVE_LEVEL_TEST_TRD.md](toolkit/FIVE_LEVEL_TEST_TRD.md), its summary,
archived traces and per-frame quality before any additional runs. Do not
repeat the earlier isolated compression tests or infer a playback pass from
their byte/decoder savings. Full-movie capacity remains unverified.

## Next finite deliverable: locate delivery cost in the row-index prototype

If continuing optimization, profile the existing 192-frame fixture's packet
handling, reconstruction and reservoir consumption; keep deterministic CPU
separate from ROM/disk windows. The legacy sub-byte motion predictor treats
dictionary indices as old packed pixels, so its suitability is unproven.
Measure one bounded row-aware alternative against this saved baseline,
preserving the exact five-level reference and independent boot. Do not
expand into a dictionary transition or full disk set until delivery cost
supports it. The requested single-image test is complete, not a release.

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
