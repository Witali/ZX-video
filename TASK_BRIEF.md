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

## Latest completed milestone: optional LZSA2 transport

After `c6b8475`, reuse its exact 192-frame five-level montage (64 frames at
629/2857/3855), fragment allowance 16 and original AY. Profile Fast ZX0 at
25185674 T and the producer at 1024996 T; packet-copy LDI alone costs at
least 5183040 T. Compare one outer codec with unchanged decoded bytes.

Resumable LZSA2 reduces decoder CPU to 19844626 T (-21.21%), total transport
CPU by 5307621 T, while video grows 148971 -> 154956 bytes (+4.02%). Real
Fuse improves 7.126866 -> 7.449298 fps, 145 -> 135 missed deadlines,
194 -> 137 maximum late fields. Both timing gates still fail; run 67..191
never recovers. This does not prove full-movie capacity or smooth 8 1/3 fps.

All 21 blocks, 27 boundary cases, cold boot, 192-frame EOF and AY pass.
Six full Fuse captures match all 41472 bytes. An EOD/quota corner case was
fixed and affected checks repeated; preliminary reports remain archived.
Keep `ZX-video-five-level-lzsa2-test.trd` as an optional LFS experiment;
generic encoding remains unchanged. Token-boundary yields do not provide a
universal slice-time bound on arbitrary videos.

Read [ROW_LZSA_TRANSPORT.md](toolkit/ROW_LZSA_TRANSPORT.md), its JSON and
archived evidence. Reuse [ROW_FRAGMENT_SPEED.md](toolkit/ROW_FRAGMENT_SPEED.md)
for unchanged frame CPU and FAP3 data. Do not repeat codec/allowance sweeps.

The subsequent user-requested modern-codec assessment reuses all 21 blocks:
LZMA1 extreme lc=0 saves 10.66% versus ZX0, Brotli-11 11.36%, Zstd-19 7.63%.
bzip2 saves only 1.47% and its standard decoder exceeds RAM; LZ4-HC grows
23.14%. All 294 new PC round trips pass; no new native performance claim.
See [MODERN_CODEC_ASSESSMENT.md](toolkit/MODERN_CODEC_ASSESSMENT.md).
Defer heavy-decoder integration pending a bounded Z80 cost/memory probe;
retain packet-copy reduction as the next implementation task.

## Next finite deliverable: avoid decoded packet copies

Transfer remains the largest elapsed stage (39637293 T); packet starts find
an empty queue in 153/192 cases. Inspect using slot bytes directly instead
of copying every packet into another buffer. First account for packets
crossing blocks, slot lifetime, motion/Huffman pointers and IRQ paging.
Compare one bounded candidate on the saved fixture, measuring deterministic
CPU separately from full disk/ULA/IRQ delivery. Preserve exact pixels,
AY, independent boot and every timing gate. Do not build the whole movie
or start dictionary transitions before resolving this hypothesis.

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
