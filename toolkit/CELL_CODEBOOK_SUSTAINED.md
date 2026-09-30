# CB41 sustained playback: complete 192-frame fixture

2026-09-30, baseline `4006665`. One book and one continuous pipeline now cover
all three saved scenes, starting at frame zero. Resolution, five-level
quantization, fixed-phase dither and AY records are unchanged. This is
**23.04 seconds of selected scenes**, not the complete authorized movie edit.

## Result

| Same 192 saved frames | Previous borrowed-literal FAP3 | CB41 |
| --- | ---: | ---: |
| Mean real-Fuse fps, normalized to 50 Hz | 7.6830252 | **8.3333331** |
| Missed nominal deadlines | 118 | **0** |
| Maximum late fields | 99 | **0** |
| Invalid actual fallback intervals | 24 | **0** |
| Compressed video bytes | 154956 | **134349 (-13.30%)** |
| Video sectors | 606 | **525 (-81)** |
| Total occupied file sectors | 653 | **572** |
| LZSA2 blocks | 21 | **12** |
| Decoder CPU T | 19412006 | **12698715 (-34.58%)** |
| Producer CPU T, excluding ROM/disk latency | 1058423 | **855775** |

All 191 field intervals are six fields. Actual publication span is
**81260570 T**, phase relative to first publication **-1..19 T**, intervals
**425434..425468 T** around nominal 425448 T. No late runs, dropped frames
or schedule-origin shifts. All **1152 AY records** match, with zero field
gaps, duplicates or underruns. Progress reaches 100% at EOF.

Only **133/525 sectors** finish loading before first publication; **392**
are read during playback, none cross the first OUT. This exercises repeated
slot turnover and both scene changes beyond the startup reserve. Every
runtime sector is verified in order, with zero retries. This finite fixture
on one emulator configuration is not a full-movie or hardware guarantee.

## Verification and costs

- Dirty-RAM cold boot, all 192 native CPU frames and all progress steps pass.
  Separate Fuse captures check **every complete published screen**, **1327104
  bytes**, including attributes, black fields and progress. The uninterrupted
  timing run checks 80 samples per frame and every AY write/tick independently.
- Both host representations match every screen. All 22 boundary variants
  pass. New history tests cover starts 0/1 and prove that changing future
  frames cannot change the initial two encoded packets.
- All 12 blocks pass author/host overlap proofs, guarded banked transport
  and independent full-flags decoding with exact per-slice timing. **121
  synthetic interrupts**, zero unavailable events. Maximum fixed-demand
  decoder slice: **21537 T**. Actual scheduling is measured separately.
- Native renderer, decoder and packet/IRQ opcodes are unchanged: instruction
  delta **0 T**. Only input/table data, startup history, counts and progress
  intervals change. Native draw on this data costs **24524522 T**; packet/
  wrapper instructions **70740 T** (`192*252 + 84 + 192*116`), book load
  **54028 T** once, priming clock **81 T**. Histogram total: **24649371 T**.
  Queue/copy/service bodies, disk/IRQ/ULA are outside that subtotal.
- Old reconstruction/output costs 43760146 T versus 24524522 T for native
  draw, delta -19235624 T; ownership/paging scopes differ. Use actual playback
  for total-delivery conclusions. Decoder/producer save **6915939 CPU T**.
- Fuse bootstrap **11490799 T**, runtime driver through EOF including
  prefill **90718720 T**, combined **102209519 T**. These include ROM, emulated
  drive latency, IRQ and ULA; exclude BASIC loading PLAYER and human swaps.
  Nested disk-service windows must not be added again to elapsed totals.

The 256-entry book covers **31837/60489 changed cells (52.63%)**, with exact
four-row fallback. Raw volume is 188881 bytes including header/table. All
eight banks keep the [verified allocation](CELL_CODEBOOK_PLAYER.md#full-ram-allocation).
The 512-byte row table has 172 used entries. Source states remain SHA-256
`47b062996f9445403e6fc4c400c5d7be5666c6b46ee568fefc5a1b3d3081dbb0`.

## Cold start, compatibility and image review

`history_state()` supplies black row symbols and first-frame attributes for
indices -2/-1, stored by the independent bootstrap. Encoder, host decoder,
builder and CPU verifier use this explicit rule. Negative NumPy indices no
longer risk borrowing the clip's final frames. No first frames are omitted.
The old 64-frame window reproduces identical raw and compressed hashes.

[Preview](cell_codebook_sustained_preview.png) compares saved source images
with actual Fuse frames 31/95/159/191. Inspected bunny edges, branches,
grass/tree textures, black fields and progress. Output remains identical
to the accepted five-level reference; existing Spectrum colour-cell and
quantization limits remain. No pixel changes were introduced for speed.
The first preview attempt used the states-only archive, which lacks RGB
images; the full preparation cache was then used after matching its state hash.

## Artifact and reproduction

Updated LFS [ZX-video-cb41-test.trd](../ZX-video-cb41-test.trd), SHA-256
`1d7eb8d0291887f8c47c953c305526100b78677620d0eb14baad96d0e27a6847`.
It replaces the 64-frame CB41 test at the same path. Its previous version
and evidence remain in commit `4006665`; other root images are unchanged.
[Summary](cell_codebook_sustained_profile.json) and
[hashed evidence](cell_codebook_sustained_evidence/) retain inputs, build,
CPU/independent checks, complete timing trace and every full screen/trace.

Reuse the [window commands/tool setup](CELL_CODEBOOK_PLAYER.md#artifact-reproduction-and-next-step):

1. Run `probe_cell_codebook.py --start 0 --count 192 --candidate-only` with
   the same states/metadata/video/author, output `.tmp/cell-codebook-192`.
   Run `test_cell_codebook.py` on this probe. No codec/layout sweep is repeated.
2. Build with `build_cell_codebook_trd.py`, using the new `--probe`,
   `--cell-raw` and `--output .tmp/cell-codebook-192/player`.
3. Run `benchmark_row_lzsa.py` / `verify_lzsa2_search.py` on new raw/stream
   files. Run `measure_fap3_fuse.py` / `capture_cell_codebook_fuse.py` on the
   actual disk, with the unchanged full source states and FAP3 AY input.
4. Archive with `summarize_cell_codebook_player.py`, supplying `--transport`,
   `--independent`, `.tmp/lzsa2-stages/transport.json` as `--baseline-transport`
   and `toolkit/borrowed_literals_profile.json` as `--baseline-profile`.
   `--extra-evidence NAME PATH` retains probe, tests, compatibility, raw/stream.
   The archiver supports variable lengths and reports timing failures honestly.
5. [preview_cell_codebook.py](preview_cell_codebook.py): `--captures
   <player>/captures.json --prepared .tmp/five-level-trd/prepared.npz --output
   toolkit/cell_codebook_sustained_preview.png`.

## Next deliverable and release scope

Prepare the **entire 4221-frame authorized edit**, preserving source mapping,
the post-credit scene through EOF and existing AY50. Use the same five-level
quantizer, then measure full-data row-book requirements and selected CB41
capacity before building one chosen volume set. Each volume needs its own
tables/checkpoints and independent boot. Do not infer three-disk fit from
this montage or drop frames/resolution. Integrate the path into the generic
converter and verify every volume through EOF, pixels/AY, nominal deadlines
and fallback recovery. The full goal remains active.
