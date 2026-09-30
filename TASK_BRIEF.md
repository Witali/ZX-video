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

## Latest completed milestone: lossless five-level dictionary comparison

After `37578d8`, reuse the same 96-frame packet caches on `codex/dither-4x4`.
Whole-cell dictionaries increase ZX0 bytes and are rejected. Learned row
books contain 93–114 entries and use two 256-byte native lookup pages.
Offline window selection (row books for 629/3855, hybrid for 2857) gives
68648→65294 bytes and Fast ZX0 11380407→11181994 T. Book assets are included;
install/transition/packet CPU, IRQ/ULA and physical latency are not.

The unchanged Z80 renderer passes nine synthetic dense/sparse checks on
both banks with learned tables: 154684 T dense, 27101 T sparse, 0 T delta.
Four dictionary tests pass. The pictures remain exactly the five-level
2x2 output described in [HYBRID_FIVE_LEVEL.md](toolkit/HYBRID_FIVE_LEVEL.md).
Use [FIVE_LEVEL_COMPRESSION_PLAN.md](toolkit/FIVE_LEVEL_COMPRESSION_PLAN.md)
and its three reports as the handoff. Full seed rows and unchanged retained
state were not included in book training; no integrated player is verified.

## Next technical milestone: row-table packets and one dictionary transition

**Deliverable:** bounded packet consumption and a safe dictionary transition,
with exact seed/native n-2 state, full affected CPU counts, RAM and IRQ checks.
The existing hybrid stream is the fallback and compression reference. Load
the table into the existing lookup path; keep five-byte escapes for general
inputs. Preserve the old book while pending frames reference it, or account
for translating/materializing retained state. Include seed rows when choosing
the new book; keep independent cold boot. Do not shrink the disk buffer.

Reuse windows 629, 2857 and 3855 and cached exact packets. Count all new
parsing, table installation, paging and output costs; keep ROM/drive timing
separate. Stop with an integration/cost decision and focused commit. A full
generic converter/player build and release TRDs follow a validated candidate;
the current window byte/CPU savings do not prove cadence or disk count.

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
