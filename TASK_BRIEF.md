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

## Latest completed milestone: faster optional row-fragment mode

After `78541a5`, profile the same 192-frame montage (64 frames at
629/2857/3855), exact five-level states and original AY. Reconstruction was
the largest elapsed phase. Allowing two extra local bytes for existing
fragment handlers gives little gain; a subsequent 16-byte window probe
justifies one final build. No Z80 opcode changes or re-quantization.

Frame CPU drops 75788625 -> 41965760 T (-44.63%), but ZX0 grows
112364 -> 148971 bytes (+32.58%). Full real-Fuse playback improves
6.7491 -> 7.1269 fps, 174 -> 145 late frames, 269 -> 194 maximum late fields.
Both gates still fail; the final late run never recovers. AY and screen
bytes are exact, including six complete Fuse captures. Eleven converter
tests pass. Retain `ZX-video-five-level-fast-test.trd` as an optional speed
experiment; generic encoding remains byte-identical by default.

Read [ROW_FRAGMENT_SPEED.md](toolkit/ROW_FRAGMENT_SPEED.md), its JSON and
archived CPU/Fuse traces. Do not repeat the allowance comparison or rebuild
the whole movie. These results do not prove the three-disk target.

## Next finite deliverable: reduce row-fragment transport cost

Transfer is now the largest elapsed stage (45170386 T); packet starts find
an empty queue in 159/192 cases. Split it into Fast ZX0, packet copies and
ROM/disk windows using the saved fixture. Keep deterministic counts separate
from elapsed/IRQ/ULA time. Compare one bounded change that reduces transport
or decoded bytes while retaining exact pixels, AY and independent boot.
Do not start another allowance sweep or dictionary transition first.

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
