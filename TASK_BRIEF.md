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

## Latest completed milestone: five levels with the previous 2x2 pattern

The user requested this follow-up on `codex/dither-4x4`, after `b7604ab`.
Retain colour pairs and add the missing quarter shade only on lower local
RGB error. Adaptive four/five-byte cells restore all five coverages exactly
with the established phase-aligned 2x2 pattern. In three 32-frame RGB windows,
mean error improves 1.16–16.14% with no worse frame. ZX0 control bytes are
56146 for four-code input, 82500 for uniform-five, 68648 for adaptive hybrid,
and 69887 for explicit canonical modes. Ten host tests pass.

Use [HYBRID_FIVE_LEVEL.md](toolkit/HYBRID_FIVE_LEVEL.md) and the current
`hybrid_five_level_canonical_probe.json` as the handoff. The two older
reports are historical: retained-palette control hashes match the new run;
the broader palette search was not rerun and has four worse-error frames.
The earlier [4x4 candidate](toolkit/SPATIAL_DITHER.md) remains rejected as
the default. No native five-level consumer, timing or release is verified.

## Next technical milestone: native adaptive five-level expansion

**Deliverable:** one bounded native implementation/profile of the chosen
adaptive cell representation, with exact equivalence to the saved host
2x2 patterns. Adaptive hybrid is the compression reference. Canonical modes
cost 1.80% more in these windows and are an alternative only if avoiding
endpoint-orientation work justifies the extra data.

Use the existing four-code renderer and its optional phase-aligned version
as baselines; [PHASE_RENDERER.md](toolkit/PHASE_RENDERER.md) records the
optional path's substantial overhead. Count absolute and delta T-states,
account for tables/code/state/IRQ/paging and native n-2 changes, and verify
both output banks and interrupts. Preserve seven attribute bits and FLASH=0.
Reuse source windows 629, 2857 and 3855 with carried state; do not repeat
host palette searches. Report unmeasured disk/ROM effects separately.

Finish with the native cost/RAM decision and focused commit. Integrating
the format into the generic converter/player and building release TRDs
remain subsequent work; host byte counts do not prove disk count or cadence.

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
