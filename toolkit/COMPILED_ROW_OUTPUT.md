# Compiled COPY/FILL row output: bounded feasibility check

2026-09-30; baseline `42bcc0f`, retained `d0e4731` borrowed-literal image.
Same 192 five-level frames, 172-entry row table and LZSA2 input fixture.

## Decision

**Reject this command format for player integration.** Native bitmap output
is correct, but commands add 56951 compressed bytes / 222 sectors. Their
decoding and copying exceed the optimistic renderer saving by 9703921 T.
Keep the current TRD unchanged. No new TRD, Fuse run or cadence claim.

This closes one output-layout hypothesis. It does not prove every finer
update format unprofitable, or complete the smooth 25/3-fps objective.

## Hypothesis and implementation

The current two-row dictionary lookup needs 43 T per sparse symbol, or
51 T with horizontal/source advances. The lookup uses ordinary registers,
not indexed loads. All 192 native maps redraw 296000 row symbols, but only
166533 differ from frame n-2. Finer row runs could reduce wasted drawing.

[The prototype](probe_compiled_row_output.py) generates native Z80 commands
on the host, then calls unrolled suffixes of three 32-column routines:

| Run | Setup plus CALL/RET | Per symbol | Command bytes |
| --- | ---: | ---: | ---: |
| COPY from compact row through the two lookup pages | 54 T | 51 T | 11 |
| FILL with different upper/lower bytes | 51 T | 26 T | 10 |
| FILL with equal upper/lower bytes | 44 T | 22 T | 8 |

Each command frame also ends with a 10-T RET. Odd-length suffixes start
with the lower pixel row, selecting the correct dictionary page/register
and screen address. The routines occupy 579 bytes in the isolated fixture;
their addresses have **not** been allocated in the production player.

One dynamic-programming policy selects spans from n-2 changes, optionally
drawing intervening unchanged symbols. Its objective is native T plus 81 T
per command byte: 60 estimates the old decoder cost, 21 charges an LDIR
copy. This is a ranking heuristic; the actual new LZSA2 cost is measured.
It selects 13577 COPY, 370 pattern-FILL and 87 solid-FILL runs. To limit
command overhead it ends up drawing 317464 symbols, more than the old map.

The proposed packet replaces the native map with a command length/padding
and appends command bytes. An inverse rewrite verifies every reconstruction,
attribute, header and other payload byte outside that field. The current
player does not support these packets. The largest is 3632 bytes, below its
4704-byte workspace limit. No audio payload is changed by this video-only
probe; actual integrated AY/IRQ operation remains untested.

## Measurements

| Measurement | Current format | Candidate |
| --- | ---: | ---: |
| LZSA2 video bytes | 154956 | 211907 |
| Video sectors | 606 | 828 |
| Decoded video bytes | 323940 | 477875 |
| LZSA2 decoder T | 19412006 | 27976642 |
| Producer T | 1058423 | 1469038 |

Commands total 153935 bytes. Executing them and the run routines costs
16931839 T for all bitmaps. Keeping the baseline attribute, paging and
shared-control costs while removing every old bitmap dispatch cost gives
an optimistic complete-output estimate of **17743885 vs 20246890 T**:
2503005 T saved. Copying commands with LDIR alone adds **3231675 T**.
The measured transport component adds **8975251 T**, giving the stated
**9703921-T regression** before new helper overhead and changed queue copies.

These are component counts, not elapsed playback. The LZSA2 harness uses
fixed 256-byte demands, mocked ROM and no IRQ/ULA/disk latency. The prototype
host installs commands directly before executing output, so command-copy
costs are separately labelled estimates. Extra disk sectors are measured;
their real latency has not been measured. No candidate fps is inferred.

## Verification

- All 192 bitmaps and both alternating screen histories match exactly.
  Compact input, command code, stubs and lookup tables remain unchanged.
- Each executed opcode matches its Z80 instruction timing; all run formulas
  equal measured totals. Every COPY/pattern/solid suffix length 1..32 is
  tested on both screens at six Spectrum address boundaries: 1152 cases.
- All 31 LZSA2 blocks round-trip on host and Z80 CPU, with input/output
  cursors, bank/sector bounds and in-place overlap proofs checked.
- Root TRD hash matches the retained borrowed-literal image. Native image
  quality, 50-Hz AY and boot are not re-certified by this component probe.
- Initial import/cache-directory setup failures were fixed before the
  completed measurements; neither preliminary run produced a playback result.

## Reproduce

Reuse the Python/dependency paths in [the test instructions](FIVE_LEVEL_TEST_TRD.md#evidence-and-reproduction)
and baseline video/metadata in the preceding LZSA2/borrowed archives.

```text
python -m unittest toolkit/test_compiled_row_output.py
python toolkit/probe_compiled_row_output.py --states toolkit/five_level_test_evidence/states.npz --metadata .tmp/borrowed-literals/metadata.json --video .tmp/lzsa2-stages/video.raw --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --output .tmp/compiled-row-output
python toolkit/benchmark_row_lzsa.py --stream .tmp/compiled-row-output/video.stream --raw .tmp/compiled-row-output/video.raw --metadata .tmp/borrowed-literals/metadata.json --output .tmp/compiled-row-output/transport.json
python toolkit/summarize_compiled_row_output.py --work .tmp/compiled-row-output --evidence toolkit/compiled_row_output_evidence --output toolkit/compiled_row_output_profile.json
```

[Summary](compiled_row_output_profile.json) and [evidence](compiled_row_output_evidence)
retain identities, every frame, packets and the native transport report.

Next bounded question: could a faster outer decoder meet difficult-window
deadlines without this command expansion? Reuse the existing LZ4-HC blocks
from the [codec assessment](MODERN_CODEC_ASSESSMENT.md), measure actual Z80
cost, and charge their known size increase. The earlier capacity rejection
still rules out blindly replacing the whole stream. A selective block mode
would need a measured total-delivery win and remain within the disk budget.
