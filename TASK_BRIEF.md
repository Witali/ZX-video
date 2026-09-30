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

## Latest completed milestone: row-aligned motion feasibility

Baseline `d0e4731`, same 192 exact five-level frames. Whole-symbol shifts
produce 6540 motion commands, with cache active in 191 frames. Decoded
volume drops 19.31%, LZSA2 size 2.14%, decoder CPU 26.76%. Existing cache
and residual patches outweigh those savings: frame stages 41965760 ->
63715325 T. Component model is at least 16933120 T worse than the current
borrowed mode. Reject this selector for realtime adoption; retain its
explicit experimental flag, scripts and [evidence](toolkit/ROW_ALIGNED_MOTION.md).
All 192 compact/native CPU frames, AY and 17 blocks pass; no candidate TRD
or actual cadence claim. Default encoding/root TRD unchanged. Return to
native output below; any later motion selection must charge cache/patch CPU.

## Previous milestone: borrowed literal suffixes

Baseline `dacb24f`, unchanged 192-frame/21-block five-level fixture. Opt-in
`build_row_lzsa.py --borrow-literals` copies packet prefixes and reads retained
literal bytes directly from slots. Host validation requires temporal/whole
fragments and no motion cache; other streams retain the normal builder.
Copy bridges save 3561002 T; frame paging adds 1794386 T, net -1766616 T.
Real Fuse improves 7.478465 -> 7.683025 fps, 134 -> 118 missed deadlines,
maximum 133 -> 99 fields. Final run 76..191 stays late. All 192 full CPU
frames, 45 copy edge cases, host contract checks, cold boot, AY/EOF and six
full captures pass. Same compressed bytes / 606 sectors, updated optional
LFS test TRD. Both timing gates still fail; full movie remains unverified.
Reuse [implementation, evidence and reproduction](toolkit/BORROWED_LITERALS.md).

## Previous milestone: fresh LZSA2 stage profile

User-requested profiling of unchanged `de0a50d`, same 192 frames/21 blocks.
Elapsed Fuse: transfer 42.58%, draw 22.87%, reconstruction 22.07%, metadata
3.63%, control/prefetch/wait 8.84%. Separate CPU: output 20246890 T, LZSA2
19412006 T, fragments 9090556 T; packet-copy lower bound 5183040 T. Motion,
spatial and motion-cache handlers execute zero times on this fixture; retain
generic support. Empty queue at 153/192 packets, worst transfer 1249405 T.
Fresh EOF/AY/pixel checks pass; playback still 7.478465 fps, 134 late frames,
maximum 133 fields and final run unrecovered. No player/stream change.
Reuse [profile, caveats and reproducer](toolkit/LZSA2_STAGE_PROFILE.md).
Next: remove decoded packet copies; screen writes and LZSA2 parsing follow.

## Previous milestone: LZSA2 flag dispatch

User-requested LZSA2 optimization: restore upstream parity/sign dispatch
and extend the component verifier. Same 21 blocks: 19844626 -> 19412006 T
(-432620, -2.18%), 391 -> 384 bytes, unchanged 154956-byte runtime stream.
Full 192-frame Fuse: 7.449298 -> 7.478465 fps; missed nominal deadlines
135 -> 134, maximum lateness 137 -> 133 fields. Both timing gates still fail;
late run 67..191 does not recover. All bytes, sectors and AY pass; six full
captures are exact. Independent full-flags CPU agrees on every old/new slice,
including additional interrupted runs. Updated optional LFS test TRD; no
full-movie release. Reuse [evidence](toolkit/LZSA2_DISPATCH.md).

C LZMA remains rejected for realtime use; retain [its comparison](toolkit/Z80_C_COMPILERS.md)
and [security record](toolkit/Z88DK_SECURITY_CHECK.md). Next: packet copies.

## Previous milestone: native LZMA feasibility

The user-requested optimized Z80 ASM implementation is complete. Reuse
[LZMA_Z80.md](toolkit/LZMA_Z80.md) and its benchmark: same 21 archived blocks,
all native bytes exact, 2901892750 -> 2305838368 T (-20.5402%). Compressed
size remains 133084 bytes, but decoder CPU is 116.19x LZSA2. Reject realtime
integration of this implementation; keep the tested standalone decoder.
No new TRD or production RAM/paging/AY/disk verification. The finite LZMA
probe supersedes its earlier deferral below; return to packet-copy work.

## Playback baseline: optional LZSA2 transport

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

The requested LZW/LZH follow-up finds LH5 at 145725 bytes (-2.18% versus
ZX0); tested LZW limits produce 162770..185256 bytes (+9.26%..+24.36%).
All 105 video round trips plus 33 extra cases pass independent decoders.
No native speed/memory/cadence claim. See
[LZW_LZH_ASSESSMENT.md](toolkit/LZW_LZH_ASSESSMENT.md); keep the same next task.

## Next finite deliverable: reduce native pixel output cost

Packet-copy reduction is implemented and verified for the eligible mode.
Native output still costs 20246890 deterministic T: dense/cell pixel writes
14350016 T and cell address computation 1894464 T. Inspect the generated
row-table renderer for one exact-byte improvement, then compare with the
borrowed-literal baseline in CPU and complete Fuse playback. Preserve both
screen histories, 50-Hz AY, five levels and the nominal/fallback gates.
Use the saved difficult windows; progress to complete-movie volumes when
the candidate meets timing. The goal remains smooth 25/3 fps, not a passing
component or average-speed result.

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
