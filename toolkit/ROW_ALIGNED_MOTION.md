# Row-aligned motion on five-level dictionary symbols

2026-09-30. Baseline `d0e4731`; same 192 exact five-level frames (three
64-frame windows at source frames 629/2857/3855), 172-entry row dictionary
and unchanged 1152 AY records. One candidate, no full-movie sweep.

## Decision

**Reject this candidate for realtime adoption.** Aligned motion is correct
and reduces decoded volume, but the existing motion cache and residual
patching cost much more than the saved LZSA2 work. Keep the optional
experiment reproducible; the generic default and current TRD are unchanged.
The retained disk still averages 7.683025 fps and fails both timing gates.
No candidate playback rate or whole-movie capacity result was measured.

## What was tested

An index byte names four five-level logical pixels; its bit fields are not
individual pixels. The experiment searches horizontal displacements -4/0/+4
logical pixels and vertical displacements -4..+4 rows, including no motion.
These 27 choices map to existing phase-zero vectors and move whole symbols.
Black padding is index zero. Spatial predictors and sub-byte shifts are
excluded. Changed symbol count plus a one-byte motion penalty selects a
predictor; bit population is no longer treated as a visual distance.

`encode(..., fragment_byte_slack=16, row_aligned_motion=True)` keeps the
existing fragment allowance for temporal patches, but uses zero allowance
when comparing a nonzero motion vector with a whole fragment. This avoids
automatically replacing all transfers with literals. The selector is a
bounded hypothesis, **not** a cycle-aware optimizer: it does not charge the
per-frame cache cost or the actual Huffman decoder work.

The candidate emits **6540 motion commands** and enables the rolling cache
on **191/192 frames**. No new vector IDs, native instructions, buffer sizes,
resolution, quantization, dither patterns or audio changes are introduced.
Learned Huffman tables and executed instruction paths do change.

## Measurements

All CPU values are deterministic instruction T-states. The original fast
column reuses the verified frame/transport profile preceding borrowed
literals; the current disk includes those bridges. Borrowing currently
excludes motion and reuses its code RAM, so the candidate uses normal copies.

| Component | Original fast mode | Current borrowed mode | Motion candidate |
| --- | ---: | ---: | ---: |
| LZSA2 video bytes | 154956 | 154956 | 151643 |
| Video sectors | 606 | 606 | 593 |
| Decoded video bytes | 323940 | 323940 | 261389 |
| Frame reconstruction, metadata and output T | 41965760 | 43760146 | 63715325 |
| LZSA2 decoder T | 19412006 | 19412006 | 14216558 |
| Producer T | 1058423 | 1058423 | 1000444 |
| Packet copying T | 5511858 | 1950856 | at least 4182224 |

Decoded volume falls **19.31%**; compressed video falls only **2.14%**.
LZSA2 saves **5195448 T (26.76%)**, but frame stages add **21749565 T**
relative to the original fast mode. Candidate cache filling costs 8753180 T,
motion 5481126 T, and Huffman corrections 7496560 T (previously 1094356 T).
Native screen output remains 20246890 T: the exact same images still need
to be written to the same alternating screens.

The component pool including the latest borrowed bridges is 66181431 T.
The candidate pool, even with only 16 T per decoded byte for copying, is
83114551 T: **16933120 T more** in this model. The candidate copy estimate
omits bridge overhead. These sums do not replay real queue demands and are
not elapsed playback measurements. The transport harness uses fixed
256-byte demands and mocked ROM; frame execution excludes IRQ, ULA and disk.
Thirteen fewer sectors do not establish a delivery improvement. The large
CPU regression justified rejecting this candidate before another TRD build.

Native implementation changes: **0 new instructions, 0 T per-instruction
timing delta**. Existing timing-table entries are checked during execution;
aggregate path counts and absolute/delta totals are retained in the reports.

## Verification and limits

- Default fast encoding reproduces the baseline FAP3 bytes exactly.
- Independent scalar decoding verifies all compact frames and AY records.
- CPU execution verifies all 192 compact frames and both full native screens.
- Every emitted nonzero motion uses a phase-zero horizontal displacement.
- All 17 LZSA2 blocks decode exactly in the native CPU harness; byte cursors,
  banks, sector acquisition and in-place overlap proofs pass.
- Four targeted tests cover all 27 shifts, black edges, scalar reconstruction,
  unchanged frames, high-entropy scene cuts, BRIGHT, AY and input immutability.
  Eleven existing generic-converter tests also pass.
- Root TRD hash still matches the borrowed-literal report. No new TRD,
  cold-boot/real-disk run, publication timing or full-movie claim is made.

## Reproduce and evidence

Use the Python/dependency paths in [the test instructions](FIVE_LEVEL_TEST_TRD.md#evidence-and-reproduction).
The baseline FAP3 is archived in `row_lzsa_evidence/fap3-video.raw.gz`;
the baseline metadata is in `borrowed_literals_evidence/metadata.json.gz`.
The same state archive is reused. With those files extracted under `.tmp`:

```text
python -m unittest toolkit/test_row_aligned_motion.py toolkit/test_generic_converter.py
python toolkit/probe_row_aligned_motion.py --baseline .tmp/lzsa2-stages/input.fap3 --states toolkit/five_level_test_evidence/states.npz --metadata .tmp/lzsa2-stages/metadata.json --options toolkit/fast_zx0_player_build.json --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --output .tmp/row-aligned-motion
python toolkit/profile_row_cpu.py --raw .tmp/row-aligned-motion/input.fap3 --states toolkit/five_level_test_evidence/states.npz --metadata .tmp/lzsa2-stages/metadata.json --output .tmp/row-aligned-motion/frame.json
python toolkit/benchmark_row_lzsa.py --stream .tmp/row-aligned-motion/video.stream --raw .tmp/row-aligned-motion/video.raw --metadata .tmp/lzsa2-stages/metadata.json --output .tmp/row-aligned-motion/transport.json
python toolkit/summarize_row_aligned_motion.py --work .tmp/row-aligned-motion --evidence toolkit/row_aligned_motion_evidence --output toolkit/row_aligned_motion_profile.json
```

[Summary](row_aligned_motion_profile.json) records input/source identities,
per-window totals and the decision. [Archived evidence](row_aligned_motion_evidence)
contains the candidate packets, compressed stream, CPU profiles and probe.

Next: return to native screen-output cost on the retained borrowed-literal
baseline. Revisit motion only with an explicit cost for cache activation,
patched bytes and transport, or a cheaper reference-buffer design. Do not
repeat this byte-count selector or infer that all motion compensation is
unprofitable from this one fixture.
