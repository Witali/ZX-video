# Faster row-index playback: bounded experiment

Maintenance, 2026-10-05: explicitly unsuccessful TRD payloads from this study were removed at the user's request. Reports, source snapshots and measurements remain historical evidence; [retirement identities and reasons](../docs/maintenance/2026-10-05-retired-trds.md) allow recovery. This does not change the original results.

2026-09-30, baseline `78541a5`. Reuse the exact 192 five-level frames and AY
from the previous test. No re-quantization, resolution or dither change.

## Result

| Measurement | Baseline | +2-byte allowance | +16-byte allowance |
| --- | ---: | ---: | ---: |
| Frame-stage CPU T | 75,788,625 | 74,872,229 | **41,965,760** |
| ZX0 video bytes | 112,364 | 113,178 | 148,971 |
| Video sectors | 439 | 443 | 582 |
| Mean observed fps | 6.7491 | 6.7875 | **7.1269** |
| Missed nominal deadlines | 174 | 172 | **145** |
| Maximum lateness, fields | 269 | 261 | **194** |
| Invalid fallback intervals | 39 | 40 | **28** |

The selected experimental mode saves **33,822,865 T (44.63%)** in frame
reconstruction/output, while growing the compressed video by **32.58%**.
Actual delivery improves by **5.60%**. Both timing gates still fail: video
can lag AY by **3.88 seconds**. This is not a release or a whole-movie capacity
result. Preserve the compact default; the faster mode remains opt-in.

[ZX-video-five-level-fast-test.trd](https://github.com/Witali/ZX-video/blob/c6b8475a3de05d9a449207c69313ab300abd09b4/ZX-video-five-level-fast-test.trd)
is a separate independently bootable visual test, stored in Git LFS. It has
633 occupied and 1911 free file sectors. The original slower test image is
retained as the baseline. Both contain the same three 64-frame windows.

## What changed

`encode_fap3.encode(..., fragment_byte_slack=16)` allows a whole fragment to
cost up to 16 more pre-ZX0 bytes than prediction plus masked Huffman values,
when prediction is nonzero or at least three byte corrections are needed.
Zero leaves the original encoder byte-identical. The existing fill, repeated
row, two-row and literal handlers reconstruct the same final bytes.

This is an optional measured tradeoff, not a claim that a byte allowance is
a cycle-accurate optimizer for arbitrary videos. All selection runs on the
host. No Z80 instruction or renderer changes; individual instruction timing
deltas are zero. Executed paths change substantially. The CPU harness checks
every executed instruction against its timing-table entry and both full
native screens after every frame. Aggregate absolute/delta counts above
exclude ZX0, packet transport, IRQ, AY, ULA and ROM/disk time.

## Why the gain is smaller in playback

The baseline real-Fuse profile spends 53,877,513 elapsed T in reconstruction,
20,845,931 in drawing, 20,142,003 in input transfer and 3,935,957 in metadata.
Its deterministic frame CPU includes 14,695,551 T in shared Huffman decoding,
9,180,764 in motion-cache filling, 6,769,003 in spatial prediction and
5,816,836 in motion. The row indices are arbitrary symbols; the original
sub-byte motion operations do not retain their old spatial meaning.

The +2-byte experiment saves only 916,396 frame T and adds four video sectors.
Its weak end-to-end gain justified one stronger probe of the same mechanism.
The +16-byte candidate was first tested for exact CPU output and compressed
size without building another disk. Its much larger CPU saving justified
the final build and full timing test.

In the final real run reconstruction falls to 20,125,309 elapsed T, but
transfer grows to **45,170,386 T**. Empty-queue waits within transfer grow
from 16,501,006 to **37,913,180 T**; the queue is empty at 159/192 packet
starts, versus 129/192 before. Transfer includes disk acquisition, ZX0 and
packet copying. It is now the largest measured foreground stage. These
elapsed windows include contention/interrupts; do not add them to CPU-only
counts or label their difference physical disk latency.

**Next bounded investigation:** replay the saved producer/consumer schedule
and split input transfer into Fast ZX0, packet copies and ROM/disk windows.
Use the saved 192 frames; reduce transport/decoded volume before another
allowance sweep or full-movie build. The earlier packed-pixel fragment
experiments in [the plan](DECODE_SPEED_PLAN.md#avoid-repeating-rejected-or-completed-experiments)
remain relevant warnings about size. This run measures the different
five-level row-index representation with actual current-player delivery.

## Verification

- Both optional variants and the default have independent scalar frame/AY
  round trips. Default encoding reproduces the old raw SHA exactly.
- CPU instruction profiling checks all 192 compact frames and both complete
  screens for each variant. The pixels are identical to the previous test.
- Cold dirty-RAM bootstrap and first-native/second-compact priming checks pass.
- Full Fuse runs reach EOF, verify all runtime sectors and 80 screen samples
  per frame. AY delivers all 1152 records exactly, without underruns, missed
  or duplicate fields. This does not fix synchronization to delayed video.
- Six additional full-screen Fuse captures of the selected image cover both
  banks and the hard cuts: all 41472 bytes match, including progress.
- Eleven generic converter tests pass, including high entropy, repeated
  frames, scene cuts, all three allowances and invalid bounds.
- Selected late runs: 43..53 recovers at 54, 57..62 recovers at 63,
  64..191 remains late through EOF. No frames dropped. Normalized to 50 Hz.

## Reproduce

Use the Python/dependency paths in [the original test instructions](FIVE_LEVEL_TEST_TRD.md#evidence-and-reproduction).
No video decoding is needed once its prepared states and raw data exist.
The image builder defaults to the optional 16-byte experiment; generic
`encode_fap3.encode` continues to default to zero.

```text
python toolkit/optimize_row_fragments.py --baseline .tmp/five-level-trd/video.raw --states .tmp/five-level-trd/prepared.npz --metadata .tmp/five-level-trd/metadata.json --options toolkit/fast_zx0_player_build.json --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe --output .tmp/row-fragments-direct --slack 16 --probe-only
python toolkit/profile_row_cpu.py --raw .tmp/row-fragments-direct/video.raw --states .tmp/five-level-trd/prepared.npz --metadata .tmp/five-level-trd/metadata.json --output .tmp/row-fragments-direct/cpu.json
```

Remove `--probe-only` to build the selected image. Use allowance 2 and output
`.tmp/row-fragments` to reproduce the conservative attempt. Run the saved
`measure_fap3_fuse.py` command with candidate TRD/metadata/raw, the same states,
and `--trace-pipeline`. `profile_row_playback.py` summarizes those boundaries;
`summarize_row_fragments.py` archives the three measurements, captures the
selected screens and copies its image to the root. Run Fuse sequentially.

Results and per-frame recovery are in [row_fragment_optimization.json](row_fragment_optimization.json).
Compressed [evidence](row_fragment_evidence) preserves CPU profiles, native
captures, exact raw packets, metadata and complete timing/debugger traces.
The previous [state archive](five_level_test_evidence/states.npz) is unchanged.
