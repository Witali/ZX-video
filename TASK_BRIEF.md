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

## Next technical milestone: decide the five-level representation

**Deliverable:** one evidence-backed recommendation for supporting all five
2x2 coverages within a cell while retaining temporal compression and fast
decoding. This milestone is a feasibility decision, not a release build.

**Starting state:**

- Commit `0ab1891` preserves INK/PAPER/BRIGHT and rejects FLASH. Existing
  attribute deltas remain in place; see [attribute storage](toolkit/ATTRIBUTE_FORMAT.md).
- Commit `5a15085` adds an optional phase-aligned Z80 renderer. It is tested
  locally but increases the stated isolated output formula by about 26.4%;
  it is not enabled in the disk builders. See [measurements](toolkit/PHASE_RENDERER.md).
- Uncommitted `toolkit/hybrid_five_level.py`, its probe and tests contain
  adaptive four/five-level cell experiments. Two saved JSON reports predate
  the latest canonical-quartet mode change: they are historical results,
  not validation of the current source. Six host tests last passed on
  September 28. No native five-level consumer or full playback is verified.

**Bounded procedure:** inspect the existing prototypes and reports; identify
which evidence is still valid. Reuse the three source windows starting at
629, 2857 and 3855, each 32 frames with a carried seed. Use existing four-code
and uniform five-level controls to assess the most promising adaptive
candidate. Recompute only invalidated comparisons. Preserve colour pairs
and BRIGHT where possible, keep FLASH=0, and retain separate attribute deltas.

**Decision evidence:** post-ZX0 bytes, per-frame image error and inspected
difficult frames, exact host reconstruction, and the proposed decoder/RAM
requirements. Distinguish measured Z80 costs from estimates or unimplemented
paths. These cell-stream controls omit parts of FAP3 and cannot establish
disk count or cadence. Record the recommendation and its tradeoffs, then
finish this milestone. Native integration and TRD rebuilding are subsequent
milestones, not implied by this feasibility task.

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
