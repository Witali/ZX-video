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

## Latest completed milestone: full movie prepared, first split exceeds volume 3

Baseline `2a9fa05`. All 4221 authorized five-level frames through source EOF
and 25326 unchanged AY ticks are prepared. Independent fixed-dither raster
matches all 29175552 host screen bytes. Original tail hold is preserved.
The movie needs 289 rows overall; equal thirds overflow the middle table
(259). A bounded row-only cut search selects 1472/2752; only that partition
is compressed: 1840522 video bytes, 185 verified LZSA2 blocks. Tables need
249/256/246 rows; resident AY 12681/13297/14467 bytes, all fit.
Exact disk totals 2425/2433/2639 sectors: first two pass dirty cold bootstrap,
third exceeds capacity by 95 sectors. Aggregate spare space is 135 sectors;
this is not a successful three-disk set. No full-movie fps claim or root TRD
update. [Full preparation, streams, evidence and preview](toolkit/CELL_CODEBOOK_MOVIE.md).

Next rebalance the cuts using saved frame costs, row constraints and bounded
boundary windows, then build one chosen complete set. Reuse
`.tmp/cell-codebook-full/{prepared.json,measured,build}`; all scripts and
hashed data are archived. Source path/tool commands are in the linked report.
Do not requantize or repeat a whole-movie codec/layout sweep. Full-volume
Fuse deadlines/screens/AY, disk switching and generic integration remain.

## Previous milestone: sustained 192-frame CB41 playback

Baseline `4006665`. Same complete three-scene fixture as the earlier
7.683025-fps player, now **8.3333331 fps with zero missed deadlines**, all
six-field intervals and 1152 exact AY ticks. All 192 full Fuse screens match
(1327104 bytes), dirty boot/progress/sector checks pass. 392 of 525 sectors
are read during playback. Video 154956 -> 134349 bytes (-13.30%); decoder
19412006 -> 12698715 T (-34.58%). All 12 independent blocks and 121 synthetic
interrupts pass. Frame-zero checkpoints are explicit; old 64-frame bytes
remain compatible. Root LFS `ZX-video-cb41-test.trd` now contains 192 frames.
Full movie, three-disk capacity and generic converter remain unverified.
[Evidence, preview and reproduction](toolkit/CELL_CODEBOOK_SUSTAINED.md).

## Previous milestone: independently bootable CB41 window

Baseline `d77b8ad`; exact 64 frames 128..191 and 42303-byte LZSA2 stream.
New root `ZX-video-cb41-test.trd` (LFS) reaches EOF in real Fuse at 8.3333324 fps:
zero late deadlines, every interval six fields, exact 384 AY ticks, no gaps,
duplicates or underruns. All 64 full published screens (442368 bytes) and
progress match. Dirty boot and integrated CPU checks pass. Total 218 sectors.
Limit: 130/166 sectors arrive before the first frame; this does not prove
long-run delivery or full-movie/three-disk success. Native draw remains
7910734 T; packet/wrapper instructions add 23636 T, book load 54028 T once.
[Disk, scripts and evidence](toolkit/CELL_CODEBOOK_PLAYER.md).

## Previous milestone: native CB41 cell output

Baseline `d1f32d3`; identical saved 64-frame payloads, rows and prior screens.
335-byte native book renderer: 7910734 frame T versus 14295892 in the old
reconstruction/output component (-44.66%). Input is supplied and target
already mapped; delivery/paging/real IRQ/ULA/disk are excluded. Transposition
costs 54028 T once. Book output adds 712149 T versus literal-only, while its
separate transport savings produce a hypothetical net -779470 T. All screens,
22 native edges, instruction timings and 106 synthetic interrupts pass.
Retain component; integrate one timing-test disk next. Current root TRD and
last measured 7.683025-fps failure remain unchanged. No candidate fps claim.
[Native ABI, provisional RAM map and evidence](toolkit/CELL_CODEBOOK.md).

## Previous milestone: exact cell-codebook feasibility

Baseline `63947dd`; saved frames 128..191, identical prior screen history.
New direct-cell representation with a 256-entry book covers 58.51% of 19303
changed cells exactly. Including its 2048-byte table: 51022 -> 42303 LZSA2
bytes (-17.09%), 200 -> 166 sectors, decoder 6353724 -> 3923387 T (-38.25%).
Literal-cell control costs 42675 bytes / 5393835 decoder T, isolating the
book's main benefit as reduced raw volume. All host full screens, 22 edges,
17 author/banked/independent blocks and 150 synthetic interrupts pass.
Promote to native implementation, not production adoption. This stage did
not include a CB41 renderer or actual playback; native follow-up is above.
[Format, scope and reproduction](toolkit/CELL_CODEBOOK.md).

## Previous milestone: bounded LZSA2 reset placement

Baseline `8b03511`; last five blocks, affecting saved frames 151..191.
Aligned packet boundaries: +51 bytes, same 606 sectors, +2393 total
decoder/producer/copy/frame T. Shifted phase: -73 bytes, same sectors,
+15336 measured decoder/copy T; producer/frame effects not remeasured.
All changed blocks pass author/host/native/IRQ checks. Aligned also passes
full banked transport and all 192 exact compact/native frames. The copy
verifier now uses actual block bounds and reproduces the old baseline.
Reject both tested placements; retain current root TRD and 7.683025-fps
failure. [Evidence and coverage](toolkit/LZSA2_RESET_PLACEMENT.md).

## Previous milestone: full-block LZSA2 distance search

Baseline `ca95df5`; block 11 of the unchanged 21-block five-level fixture.
Fixed command positions/lengths, exact canonical distance DP under original
byte limit. Minimum size remains 7165 bytes; decoder saves only 108 T
(944426 -> 944318), with unchanged 154956-byte stream / 606 sectors.
3214 cost boundaries, 187 exhaustive layouts / 2716 serialized alternatives,
all author/banked/independent slices and 184 synthetic interrupts pass.
Reject integration or broader distance-only search; keep prototype/evidence.
Root TRD unchanged; last actual 7.683025 fps still fails both timing gates.
[Details and reproduction](toolkit/LZSA2_DISTANCE_SELECTION.md).

## Previous milestone: exact LZSA2 oracle

Baseline `a63043a`. No size gap on 1341 short inputs, including 63 video
excerpts; 126 independent complete-command enumerations and 531 guarded/
independent native cases pass. Of 232 changed equal-size parses, 20 are faster,
24 slower; a video excerpt saves 480 T (8784 -> 8304) at unchanged size.
These independently reset short cases cannot be spliced into the full
stream or treated as a playback improvement. Root TRD unchanged; goal still
fails at last measured 7.683025 fps. Reuse the
[oracle, exact evidence and limits](toolkit/LZSA2_EXACT_ORACLE.md).

## Previous milestone: stronger standard LZSA2 search

Baseline `c3d1125`, same 21 archived blocks. A larger host match/arrival
search saves 2 bytes (+138 decoder T); a follow-up expanding supplemental
limits saves 12 bytes (+760 T), still 606 sectors. All byte/overlap/bank/
sector/cycle/independent IRQ checks and 27 deep-variant edges pass. Reject
these changes as production defaults; preserve standard format and root TRD.
[Prototypes, evidence and next parser plan](toolkit/LZSA2_COMPRESSION_PLAN.md)
are saved. Simple table growth is not a meaningful capacity optimization.

## Previous milestone: LZ4 analysis and fast short runs

Baseline `e681055`; unchanged 21 LZ4-HC12 blocks and 192-frame decoded input.
Direct short copies and fewer stack exchanges reduce decoder 19847554 ->
15657014 T (-21.11%), with identical compressed bytes and 13 extra code bytes.
Independent full-flags/IRQ runs, guarded banked decoding and 46 edge cases
per variant pass. Versus current LZSA2, decoder/producer saves 3598927 T but
video grows by 28492 bytes / 111 sectors. Retain experimental component;
no new disk or candidate playback claim. Root TRD unchanged. Reuse
[analysis, plan and evidence](toolkit/LZ4_OPTIMIZATION.md), not a codec sweep.

## Previous milestone: compiled row output feasibility

Baseline `42bcc0f`, unchanged 192-frame five-level fixture. Native generated
COPY/FILL runs pass all bitmaps and 1152 boundary cases. Their optimistic
output saving is 2503005 T, but command copying adds 3231675 T and measured
LZSA2/producer adds 8975251 T. Compressed video grows 154956 -> 211907 bytes.
Reject this command format; no new disk or actual cadence claim. Root image
unchanged; exact scripts and [evidence](toolkit/COMPILED_ROW_OUTPUT.md) saved.
Next bounded deliverable below measures a faster selective block decoder.

## Previous milestone: row-aligned motion feasibility

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

## Next finite deliverable: rebalance full-movie CB41 disk capacity

Keep root images and LZSA2 syntax. The full five-level preparation is complete;
reuse its hashed caches/streams and existing AY50. The chosen cuts 1472/2752
produce 2425/2433/2639 occupied sectors, with 95 excess sectors in volume 3.
Use saved frame/block costs and exact per-volume row unions (including two
checkpoints) to select nearby boundary windows. Measure those windows before
building one new chosen set; do not search by repeatedly encoding full sets.
Account for resident AY and actual bootstrap/player overhead as well as video.
Preserve all 4221 frames, resolution, raster and soundtrack. If capacity
passes, verify actual EOF playback/deadlines/screens/AY on every independent
disk, including disk switching, then integrate the generic converter.
See [full evidence and reproduction](toolkit/CELL_CODEBOOK_MOVIE.md).

## Release gate and handoff

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it.

After a completed milestone, replace the starting-state section with a short
handoff: baseline commit/input, decision and key measurement, evidence links,
remaining work or limitations, and the single next deliverable. Keep this
brief compact; detailed history belongs in the changelog and reports.
