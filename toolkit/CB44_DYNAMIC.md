# Dynamic rows and exact front-screen reuse

2026-10-01. Experimental player on `codex/cb41-10fps`; root release images
are unchanged. The four-disk goal is not achieved.

## Format and use

CB42 maintains 256 row slots (512 bytes). Control records replace selected
slots before drawing the next frame. Offline farthest-next-use eviction
excludes all rows required by that frame; slot zero stays black. Already
drawn screens and the physical 256-cell book do not refer to mutable slots.

CB44 retains those records and uses two bits per changed cell: literal four
row indices, physical book index, or exact same-position copy from the
previous front screen. The source address is destination XOR 8000h. It stays
immutable while drawing the back screen. Attributes use absolute updates.
The book is fitted to cells that cannot be copied. Spatial mode 3 remains
host-only and is rejected by the native builder. Maximum frame payload is
3168 bytes, fitting the existing fixed packet buffer.

Both `convert_video.py --video-codec cb41` and the prepared builder accept:

- `--dynamic-rows`: CB42 eviction/replacement.
- `--front-reuse`: CB44, including dynamic rows.
- `--audio-banks 2`: exact resident AYH1 segments in banks 4 and 6.

These options do not promise a disk count or timing pass. Run complete
verification for every final volume. Default CB41 bytes remain unchanged.

## Native CPU accounting

The assembler records each instruction's Z80 timing. Isolated cell routines,
including RET but excluding the outer conditional CALL and mode refill:

| Path | Previous | CB44 | Difference |
| --- | ---: | ---: | ---: |
| Book | 268 T | 281 T | +13 T |
| Literal | 304 T | 317 T | +13 T |
| Front instead of book | 268 T | 299 T | +31 T |
| Front instead of literal | 304 T | 299 T | -5 T |

Setup saves 16 T. The mode sentinel refills every four changed cells rather
than every eight; each additional refill costs 16 T. For the same cell book,
N changed cells, B front copies formerly using the book and L front copies
formerly literal, whole-renderer delta is:

`-16 + 13*N + 16*(ceil(N/4)-ceil(N/8)) + 18*(B-L)`.

This mode-reader comparison disables `fast_masks` in both kernels. The
current CB44 builder also enables the mask optimization below automatically;
add its separate delta when comparing whole renderers.

This excludes packet copying, row controls, paging, AY/IRQ, ULA contention
and disk/ROM. CB42 adds 18 T per ordinary packet and 207+74*N T per row
replacement handler, with its documented queue/dispatch exclusions.
Book refitting changes the selected paths: do not apply the formula across
different books without counting those cells again.

## Complete bounded checks

Twenty-eight tests cover existing codecs, both physical screens, counts
0/1/3/4/5/7/8/9/575/576, full-flags independent Z80 replay, input/stack/memory
guards, interrupt preservation and exact cycle deltas. Real player checks:

| Scope | Frames / AY ticks | Exact screen bytes | Nominal late | Max late |
| --- | --- | ---: | ---: | ---: |
| Synthetic dynamic fixture | 12 / 60 | 82944 | 0 | 0 fields |
| Real [4096,4352) | 256 / 1280 | 1769472 | 116 | 89 fields |

The real window has 115 misses beyond one field, 54 invalid intervals and
no AY underruns. It fails both zero-late and fallback timing. Native replay,
independent boot, complete Fuse screens, AY and all 735 sectors are exact.
An initial cut configuration failed before TRD generation because its
4096-frame first audio segment exceeded the two-bank limit; corrected cuts
preserve the actual preceding two-screen history.

One full selected four-volume partition was already host-exact. Its first
native volume now fails capacity: 2558 sectors / 2544 available, comprising
2456 video plus 102 startup/audio. Four complete images were not generated.
This is a measured failure of these cuts, not an impossibility proof.

## Actual delivery profile

`measure_fap3_fuse.py --trace-pipeline` now understands cell-player boundaries
without expecting obsolete motion reconstruction calls. It adds debugger
breakpoints only, with no player patch. `profile_cell_delivery.py` verifies
all boundaries and reports overlapping intervals explicitly.

The additional independently booted run has 117 misses (maximum 89 fields),
exact content and no AY gaps. Different bootstrap/rotation phase means its
count is not substituted for the original 116. From first packet to last
publication (95.017M elapsed T):

- Drawing: 35.103M T; mean 137120 T, maximum 274967 T.
- Disk/ROM/seek service: 19.159M T during that interval.
- LZSA2 bridge slices: 15.205M T during that interval.
- Packet acquisition: 30.452M T, overlapping disk and decode; do not add it
  to those totals. One packet waits as much as 2.035M T for queue output.
- Queue empty at 115 of 256 packet entries. All sector reads average
  31247 T; maximum 155723 T. Prefill is outside the active interval.

Elapsed decoder slices include paging, IRQs and contention. Deterministic
native replay separately measures mean draw 128487 T and next packet
79695 T with mocked ROM and without sustained real AY production. Subtracting
these from elapsed times would not isolate physical disk latency.

The next bounded work should reduce native rendering/mask overhead and
producer stalls. More queued data might cover bursts, but does not prove
sustained throughput. Capacity still requires savings or better cuts.

## Reuse and reproduction

Keep prepared input `.tmp/refined-av-movie/preparation.json` and cached
streams. Do not repeat preparation or sweep whole-image variants.

```powershell
python toolkit/build_cb41_cadence_movie.py --prepared .tmp/refined-av-movie/preparation.json --output .tmp/front-native-window-fixed --volume-cuts 1158,1957,2753,3710,3902,4096,4352,4893,5066 --only-volume 7 --front-reuse --audio-banks 2 --prefix ZX-video-front --verify cpu --zx0 .worktree/compression/.tmp/ZX0/win/zx0.exe --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --trdos-rom tools/fuse-1.9.0-sdl/roms/trdos.rom
python toolkit/measure_fap3_fuse.py --fuse tools/fuse-1.9.0-sdl/fuse.exe --trd .tmp/front-native-window-fixed/ZX-video-front_part07.trd --metadata .tmp/front-native-window-fixed/ZX-video-front_part07.json --states .tmp/front-native-window-fixed/work/ZX-video-front_part07/states.npz --raw .tmp/front-native-window-fixed/work/stream.raw --trace-pipeline --output .tmp/front-pipeline-decoder/timing.json --timeout 600
python toolkit/profile_cell_delivery.py --trace .tmp/front-pipeline-decoder/timing.json --metadata .tmp/front-native-window-fixed/ZX-video-front_part07.json --cpu .tmp/front-native-window-fixed/work/ZX-video-front_part07/cpu.json --output .tmp/front-pipeline-decoder/profile.json
```

Use a new output directory if rebuilding. The analogous capacity probe uses
cuts `1312,2672,3744,5066`, `--only-volume 1 --verify none`.
[`front_native_report.json`](front_native_report.json) and its hashed evidence
preserve complete native/Fuse data, failed builds and diagnostic TRDs in LFS.

## Follow-up: skip empty groups and inline attributes

Baseline `0bb033f`. CB44 now bypasses eight bit tests for zero bitmap/attribute
mask bytes and inlines each changed attribute write. CB41/CB42 defaults and
all encoded video/AY bytes stay identical. Standalone assembly retains
`fast_masks=False` for direct baseline comparisons.

Counted body costs exclude mask fetch and the shared group tail:

| Path | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Empty bitmap group | 144 T | 39 T | -105 T |
| Empty attribute group, no E wrap | 160 T | 51 T | -109 T |
| Empty attribute group, E wraps | 160 T | 50 T | -110 T |
| Nonempty bitmap group | original body | original +14 T | +14 T |
| Nonempty attributes, k set bits | 160+45k T | 190+23k T | 30-22k T |

Per frame, with Zb/Za zero bitmap/attribute mask groups, C empty attribute
groups that wrap E, and A changed attributes, the exact delta is
`3168 - 119*Zb - 139*Za - C - 22*A`. Both renderers perform identical writes
and consume identical payloads. Sparse nonempty groups can be slower; the
formula does not claim every possible frame improves.

Ten tests pass, including 24 guarded/independent full-flags cases spanning
all 256 mask byte values, both screens, CB41/44 modes and IRQ injection.
On the same real 256-frame window every draw improves. The 255 separately
called frames average 128487 -> 122716 T (-4.49%), maximum 232322 -> 227162 T.
All 255 measured differences equal the formula; frame zero is primed by the
bootstrap and its delta is reported separately as a formula, not a call
measurement. Next-packet calls total -434 T due to the changed sector/track
alignment; those are not attributed to mask optimization.

Native code grows 348 -> 405 bytes, increasing this diagnostic image's used
sectors 797 -> 798. Video remains exactly 188005 bytes / 735 sectors, and AY
bytes are unchanged. Full Fuse playback confirms all 1769472 screen bytes,
1280 AY ticks and sector contents. Misses are 110 (108 beyond one field),
maximum 82 fields, versus 116/89 in the original baseline run. It still fails
fallback and zero-late timing. No full-movie capacity/timing claim follows.

Retain this measured rendering improvement for CB44 development. The next
constraint is producer stalls/capacity; do not rebuild all volumes merely
to repeat this test. Reuse `.tmp/front-fast-masks/` and its identical video
stream. [Per-frame/whole-player evidence](front_fast_masks_report.json),
[reproduction and exact comparison](compare_fast_cell_masks.py).
