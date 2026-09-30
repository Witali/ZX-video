# Current LZSA2 playback: where the time goes

2026-09-30, baseline `de0a50d`. Fresh profiling of the unchanged optional
`ZX-video-five-level-lzsa2-test.trd`: 192 frames, three 64-frame source windows
at 629/2857/3855, 21 LZSA2 blocks, 154956 video bytes, 606 runtime sectors,
original 50 Hz AY. **Input delivery is the largest elapsed stage; screen
output and LZSA2 are the largest individual CPU components. Motion handlers
are not executed on this fixture.** No player or encoded data was changed.

## Real Fuse elapsed time

The denominator is 91220166 elapsed T from the first packet read, after
initial queue prefill, through the last publication OUT. This is 25.7292 s
at 70908 T per 50 Hz field. The rows are disjoint and sum to 100%.

| Stage | Elapsed T | Share | Mean ms/frame |
| --- | ---: | ---: | ---: |
| Get packet: disk service, LZSA2, queue and copy | 38845163 | 42.58% | 57.07 |
| Write reconstructed image to native screen | 20858966 | 22.87% | 30.64 |
| Reconstruct compact frame | 20133887 | 22.07% | 29.58 |
| Control, background prefetch and waiting between stages | 8068220 | 8.84% | 11.85 |
| Packet metadata | 3313930 | 3.63% | 4.87 |

The mixed control/prefetch/wait row is **not idle time that can all be
removed**. The full driver-entry-to-finished interval, including prefill,
is 98355897 T; bootstrap before driver entry is another 11418106 T.
The first-to-last publication span is 90549516 T, exactly equal to the prior
run, yielding **7.478465 fps**. These scopes have different endpoints.

The queue is empty at **153/192 packet starts**. Empty-queue service windows
total 31641452 elapsed T inside packet transfer. The producer is doing work
during these waits; this is not 31.6 million T of idle spinning.
The largest single transfer takes 1249405 T, approximately 352.4 ms, far
beyond a 120-ms frame budget. The p99 is 1220853 T.

Disk read/seek service windows occupy **16280668 T (17.85%)** of the same
chart interval: 13925467 T inside transfer and 2355201 T in the mixed gaps.
They are already included in the rows above. Across the whole traced run,
including prefill, read windows total 18972412 T and seek windows 421824 T.
These are ROM/drive/IRQ/ULA elapsed windows, not isolated physical latency.
Do not add them again to the chart or subtract CPU counts to infer latency.

## Deterministic CPU components

Independent component execution excludes IRQ, ULA contention, ROM and
physical drive timing. Frame reconstruction uses the actual encoded frame
commands. LZSA2 uses fixed 256-byte output demands across the entire stream,
including bytes prefetched before the elapsed chart starts. Its scheduling
differs from the real queue. The following counts must not be added to the
elapsed chart; packet copying is a lower bound, not a complete queue model.

| Component | CPU T | Interpretation |
| --- | ---: | --- |
| Native screen output | **20246890** | Largest individual CPU component |
| LZSA2 decoder | **19412006** | Almost as expensive as all screen output |
| Fragment reconstruction | 9090556 | Fill/repeated rows/literals into compact frame |
| Reconstruction control, unchanged blocks and patches | 7449756 | Includes handoff/static edges |
| Copy decoded packets | **at least 5183040** | 323940 bytes times 16 T per LDI, excluding bridge overhead |
| Compiled metadata | 2656588 | Counted once, not again inside packet transport |
| Attribute reconstruction | 1427614 | Attribute pass and grouping |
| Huffman corrections | 1094356 | Shared and inline paths together |
| Input producer | 1058423 | Deterministic service code, ROM mocked |
| Motion, spatial prediction and motion cache handlers | **0** | No executions on these encoded frames |

The frame model totals 41965760 T, identical to its prior archived result.
Within screen output, dense pixel writes cost 10340352 T and cell pixel
writes 4009664 T: together **14350016 T, 70.88% of the output stage**.
Cell address computation adds 1894464 T. These are better candidates than
small paging costs (14784 T in this output model).

Zero motion-handler time does **not** mean all temporal reuse is disabled:
unchanged blocks still cost 2086154 T in `reconstruct/noop_control`, and the
compact frame retains previous contents. It also does not justify deleting
motion support from a generic converter. The result applies to the current
row-dictionary stream with the 16-byte fragment allowance; other encodings
can execute those handlers. All executed frame instructions are attributed,
and the stage sum is checked against the complete frame count.

### Inside LZSA2

| Work | CPU T | Share of decoder |
| --- | ---: | ---: |
| Token/length/offset parsing and copy setup | 11588591 | 59.70% |
| Copy matches from history | 5117297 | 26.36% |
| Demand checks and yielding | 1083424 | 5.58% |
| Copy literals | 1061718 | 5.47% |
| Resume wrapper | 560976 | 2.89% |

The decoder copies 265217 match bytes and 58723 literal bytes. Repeated
LDIR iterations cost 21 T, versus 16 T for LDI/final LDIR (Zilog UM0080,
the same timing table used by the decoder verifier). Removing *all* such
5-T repeat costs would save at most **995975 T**: 873825 in matches and
122150 in literals. This is only an ideal upper bound; a real unrolled
implementation needs selection/tail handling and code space. Packet-copy
instructions alone cost over five times that bound. No new optimization
or measured speedup is claimed here; player instruction delta is **0 T**.

## Priority from this profile

1. **Avoid the second decoded-packet copy.** Explore consuming slot bytes
   directly, accounting for cross-block packets, bank lifetimes, frame/Huffman
   pointers and IRQ paging. The 5183040-T lower bound is an opportunity, not
   a promised net saving; any replacement overhead must be measured.
2. **Reduce screen-output and fragment-write work.** Native pixel writes
   dominate output. Investigate direct expansion into the hidden screen or
   fewer writes while preserving the compact predictor and both screen
   histories. Do not assume double buffering eliminates reconstruction.
3. **Target LZSA2 token/offset/setup paths before a large copy-loop expansion.**
   Preserve compression, overlap safety, the AF' reservoir and demand limits.
4. **Improve lookahead to hide disk-service bursts.** An empty queue in 80%
   of packets and 350-ms transfer outliers matter more than averages. This
   requires a producer/consumer delivery test; changing buffer size alone
   is not evidence of improvement. Keep AY service on every 50 Hz interrupt.

Motion and further Huffman tuning have low priority for this exact fixture.
These are ranked proposals, not implementations or permission to start a
new codec sweep. The next finite task remains decoded-packet copy reduction.

## Verification, scope and reproduction

Fresh runs check all 21 decoder blocks, every instruction timing, input/output
cursors, bank bounds and sectors; all 192 compact frames and both native
screens in the frame CPU model; and a complete unmodified cold-boot Fuse run
through EOF with all 606 runtime sectors, all 1152 AY ticks and 80 pixel
samples per frame. No audio underruns, missing or duplicate ticks. Full Fuse
screen captures from the previous unchanged-image run remain archived; no
new full captures or physical-hardware test are claimed.

Both release timing gates still fail: **134 missed nominal deadlines**,
maximum lateness **133 fields (2.66 s)**, 24 invalid actual fallback intervals.
Runs 43..49 and 56..57 recover at 50 and 58; run 67..191 remains late at EOF.
No frames are dropped. The phase occupied at a missed nominal deadline is
transfer in 66 cases, draw in 29, prepare in 26, metadata in 12 and control
in one. This shows where execution was, not sole responsibility for earlier
accumulated delay. A montage is not a full-movie release test.

Run [profile_lzsa2_stages.py](profile_lzsa2_stages.py) from the repository root
with the existing Python environment (`PYTHONPATH=local_tools/python_packages;.tmp/lzma-z80-packages;toolkit`).
The default command extracts hash-checked archived inputs, runs three probes
and saves the report. `--prepare-only` prints the independent probe commands;
`--summarize-only` validates and summarizes completed runs. Run only one Fuse
instance at a time. [JSON](lzsa2_stage_profile.json) includes per-stage stats,
window summaries and source/evidence hashes; compressed raw reports and
traces are in [lzsa2_stage_evidence](lzsa2_stage_evidence).
