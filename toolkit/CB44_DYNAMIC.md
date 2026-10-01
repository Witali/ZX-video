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

## Follow-up: retire old fixed reconstruction

Baseline `e747b02`. CB44 clears the old motion/patch code from 8000h to the
current LZSA2 core origin, obtained from metadata. In this build the origin
is **8D74h**, freeing 3444 bytes. Earlier planning mentioned a different
origin; it is not a valid hardcoded allocation boundary. Active render,
packet and clock listings remain identical (0 T instruction delta).

`build_cell_codebook_trd.py` now rejects every read, write and instruction
fetch in the retired range after player entry. Complete 256-frame replay
and two six-frame disks pass with zero accesses. All 255 separately called
draws have identical CPU costs. Disk-start alignment changes packet/ROM
paths, so their differences are recorded separately.

Complete Fuse cold playback compares 1852416 screen bytes and 1340 AY ticks
across the three diagnostic images. The two-disk fixture's actual EOF
snapshot continuation also passes, zero nominal misses or AY gaps. This
does not simulate a physical floppy swap. The real window has 113 misses
(110 beyond one field), maximum 82 fields and 51 invalid intervals. It
still fails timing; do not infer a speedup from startup code removal.

The real diagnostic disk shrinks 798 -> 796 used sectors. First-volume
capacity of the full selected partition is now **2556 / 2544**, still 12
sectors too large. Video and AY are byte-identical. No new root release set.

Rebuild from caches with `rebuild_cell_player.py --metadata OLD.json
--output NEW --zx0 PATH --lzsa PATH --verify cpu`; this reuses global
histories, raw/LZSA2 video and sound. `--verify none` is suitable only for a
capacity probe. No preparation or video recompression is performed.
The continuation verifier now accepts the generic converter's `volumes.json`
as well as its older capacity layout. The movie publication wrapper requires
movie-specific metadata and initially rejected the synthetic fixture; direct
generic continuation verification avoids fabricating those fields.

[`retired_cell_report.json`](retired_cell_report.json) archives all guarded
replay, cold/full-screen playback, actual EOF continuation and capacity data.

### Next audio-memory candidate (host estimate only)

`probe_shared_resident_audio.py` recodes the exact four AYB1 streams with one
AYH1 model per volume. All 25330 tick records and initial states are exact.
Trees+payload shrink 83674 -> 74373 bytes before startup compression. The
single payloads use 14137/16118/12516/17554 bytes, so only volume 4 needs
1170 bytes beyond one bank. Native table trees plus a **reserved, unmeasured**
512-byte decoder allowance need 3946/4026/4018/4106 bytes. The newly freed
3444-byte interval is insufficient by itself.

The proposed additional B100h..B700h gap after book/popcount needs a guard
audit. Fixed tables plus a bank-spanning reader could free most/all bank 6
for a fourth video slot. Native paging/bit-reader changes, slot-specific
in-place bounds, sustained timing and actual startup size are unverified.
This is the next bounded implementation, not an accepted four-disk result.

## Shared fixed-RAM AY implementation (2026-10-01)

Baseline `9893f79`; `rebuild_cell_player.py --shared-audio` opts in for CB44.
Decode an existing AYB1 to its exact initial state and records, encode one
AYH1 model, and place code at 8000h, roots at 8200h and four-byte tree nodes
up to the actual LZSA2 origin, then B100h..B700h. A full 256-frame guarded
replay proves that the additional tail was unused in the baseline. Payload
resides in bank 4; at most 1536 additional bytes may reside at the top of
bank 6. Reject larger streams rather than silently overflowing. Original
source audio hashes and records remain available in build metadata.

At a payload-byte refill, the baseline `LD B,(IX+0); INC IX; RL B` costs
19+10+8 = 37 T. Spanning adds `LD A,IXH; OR A; JR NZ; SCF`, 28 T on the
ordinary path: 65 T total. SCF restores the bit-reader sentinel carry.
The first bank-4 wrap adds 214 T (251 total), including the 92-T paging
body, preservation of BC and loading the overflow pointer. Final bank-6
wrap adds 55 T (92 total); remaining records prevent reading beyond EOF.
One-bank compilation omits all these additions. Spanning init adds 20 T.

The direct fixed bridge costs 436 T (one bank) / 442 T (spanning), versus
the previous two-segment bridge's 486 T ordinary / 645 T switch / 516 T
EOF. These include caller preservation, resident CALL, two 92-T page calls
and RET, excluding resident body and outer CALL. For one identical global
model, each spanning refill's measured delta is
`6 + 28*bytes_read + 186*bank4_wraps + 27*bank6_wraps` T. Independent
full-flags Z80 tests validate every boundary and all preserved registers.
IRQs, contention, TR-DOS and physical disk are excluded from CPU counts.

All 25330 native AY records/chip updates are exact. Against the original
two-model volumes, fill totals are 69212242 -> 70408859 T (+1196617), since
global Huffman distributions and wrap checks change decoding work. This
layout saves space; it is not an AY speed optimization. Seventeen tests
pass, including IRQs after every instruction and exact 16-bit clock wrap.

The complete real 256-frame window preserves 1769472 Fuse screen bytes,
1280 AY records and all runtime sectors. It shrinks 796 -> 793 sectors but
still misses 108 nominal deadlines, all beyond one field, maximum 82.
Selected full-volume capacity is 2543/2541/2588/2588 sectors, 84 sectors
over four disks in total. The first two pass dirty-RAM cold startup.

Full-movie playback, integrated overflow playback and EOF continuation
remain outstanding. The video queue still has three slots. Future reuse of
bank 6 must protect the audio tail from compressed input as well as output,
or first prove another fixed allocation for the tail. No root release image
has been replaced. [Evidence](shared_audio_report.json),
[verifier](verify_shared_audio.py), [capacity script](measure_shared_audio_capacity.py).

## Fourth video slot for one-bank AY (2026-10-01)

`rebuild_cell_player.py --shared-audio --four-video-slots` adds an explicit
bounded experiment. Move the coded AY payload to bank 6, leaving the fixed
decoder/trees where they were. Restore original queue capacity and cursors
for video banks **0,1,3,4**. Both producer and copy/disk paging already use
this map; no new bank mapping helper or block format is necessary. Audio
requiring two banks is rejected before image generation.

Memory: four slots of up to 15872 bytes, 63488 vs 47616 decoded bytes.
Admission `CP 3` -> `CP 4` stays 7 T at both sites. Cursor `CALL helper`
(17 + 22/30 = 39/47 T) -> `INC A; AND 3` (4+7 = 11 T), saving 28/36 T
at each producer/consumer advance. AY bridge's `LD A,14h` -> `LD A,16h`
stays 7 T. All other active code remains identical. Earlier component
metadata records the previous installation; the final queue listing and
`four_video_slots.patches` carry these exact overrides.

Eighteen tests pass. Full-flags independent CPU checks verify all caller
registers, exact AY records and zero cycle delta for relocation. Complete
native replay additionally guards bank 6 against every runtime write.
Complete cold/Fuse playback verifies all 1769472 screen bytes, 1280 AY
ticks and 735 sector contents. Same difficult [4096,4352) window, same
793 sectors. Nominal misses fall 108 -> 37, beyond-one-field misses
108 -> 36, maximum 82 -> 43 fields. Fifteen intervals remain invalid.
This is a significant bounded improvement, not a zero-late/fallback pass.

The full trace has 41 empty-queue packet entries. Active elapsed 91.66M T
includes draw 33.37M, disk service 17.92M and decoder bridges 14.37M;
packet intervals overlap these and must not be summed again. Reuse this
trace to diagnose remaining stalls. Part 4's 1170-byte audio overflow is
still incompatible with this four-slot allocation. No full-movie timing,
continuation or release-image claim follows. [Evidence](four_video_slots_report.json),
[guard and archive script](verify_four_video_slots.py).

## CB46: one changed row-pair per literal cell (2026-10-01)

Mode 3 now has an explicitly different wire header, CB46. Its two bytes
are a row selector 0..3 and one index into the current mutable row table.
Write the two corresponding physical scanline bytes and retain the other
six bytes of that back-screen cell. Modes 0/1/2 retain CB44 meanings.
The host uses this only when exactly one of the four logical rows differs
from frame n-2, and the cell otherwise uses a four-index literal. Never
apply a partial update against the front screen or a previous table index.
The builder rejects out-of-range selectors and wrong packet extents.

The existing book branch adds `JR C,partial_row`: 7 T for a book cell,
12 T when taken. The partial body loads selector, advances HL, doubles A,
adds D, sets D, loads table page and index, expands the two table bytes
with one B/D increment, then jumps to the unchanged cell return. Its body
cost is 93 T; the original four-row literal body costs 231 T. Mode dispatch
adds 7 T relative to a literal, hence **-131 T**. No-refill cell costs:
book 288, literal 317, front 299, partial 186 T. Same bitmap masks/mode-byte
count mean the whole-renderer delta is exactly
`7*book_cells - 131*partial_cells`. Exclude outer services, IRQs, ULA and
disk latency. Thirty-two independent full-flags component cases verify all
selectors, both screens, mode-byte boundaries and IRQ preservation.

On the three cached windows: 121912/127989/188005 ->
117701/124058/185681 compressed bytes (10466 saved, 2.39%), with exact
screens. Full selected partition: 608061/604926/626506/623005 video bytes,
59832 fewer bytes; all 5066 host screens match. With the actual shared-AY
bootstrap and three slots, capacities are 2464/2475/2542/2543 sectors.
All four dirty-RAM cold loads pass. This proves capacity, not playback.

The complete four-slot difficult-window run preserves 1769472 screen bytes,
1280 AY ticks and 726 sector contents. Disk size 793 ->780 sectors. Misses
37 ->31, beyond-one-field misses 36 ->29, maximum 43 ->28 fields. All late
runs recover but 12 intervals remain invalid. The window still fails both
timing gates. Every renderer delta matches the formula; complete draw-call
costs also reflect different outer drive service when the shorter stream
reaches EOF. The verifier records that separately. Some book-heavy frames
become slower; the measured mean draw and total window delivery improve.

Reproduce host probes with `probe_partial_row_cells.py` and the single
selected full partition with `measure_partial_row_four.py`. Cached native
rebuild accepts `--cell-probe WINDOW.json`, validating the matching global
histories, initial row table, all host screens and every in-place block.
Retain shared audio/four-slot flags as appropriate; two-bank AY still
precludes a fourth slot. [Evidence](partial_row_report.json),
[native/size verifier](verify_partial_row_cells.py). Generic CLI integration
and complete four-disk timing/EOF continuation are still required.

## Fixed AY overflow with four slots (2026-10-01)

The fixed-tail option supersedes the one-bank restriction above. Keep the
first 16384 coded AY bytes in bank 6 and place overflow after the last fixed
Huffman node. The allocator checks an exclusive BA00h limit; packet length
at BA58h and later workspace remain allocated. B700h..BA00h was first guarded
against every native read/write/fetch over the complete existing 256-frame
window. The selected fourth volume needs 1170 overflow bytes at B398h..B82Ah,
with 5200 total fixed decoder/tree/payload bytes. Video slots remain 0/1/3/4.
There is no new audio format, output change, or compressed video change.

After a payload read, `LD A,IXH; OR A; JR NZ` detects IX wrapping from FFFFh.
The boundary loads `IX=fixed_tail`; `SCF; RL B` restores the sentinel. No
bank switch or mutable payload-bank variable is needed. Ordinary reads
remain 65 T. First wrap is 251 ->74 T (-177), including the old 92-T page
body; the final byte is 92 ->65 T (-27). A fixed-bank bridge is 442 ->436 T
(-6 per refill); initialization saves 20 T. AY consumer instructions do not
change. All counts exclude outer service, IRQs, contention and ROM/disk.
The complete fourth-volume component replay verifies all 6610 records:
fill 20308726 ->20307238 T (-1488), init 1076 ->1056 T, consumer 4088727 T
unchanged. Twenty tests pass, including independent full-flags Z80 runs
and interrupts across the payload boundary.

The cached capacity tool accepts `--four-video-slots --parts 4 --write-images`
to build only this diagnostic volume, retaining the original series and
frame cuts. It still uses 2543/2544 sectors and passes dirty-RAM cold loading.
Full Fuse playback compares 9137664 screen bytes, 6610 AY ticks and 2434
runtime sectors exactly, with zero missing/duplicate AY fields or underruns.
Timing fails: 60 missed nominal frames, 57 beyond one field, maximum 42
fields, 34 invalid actual intervals. Local late runs 39, 568, 577..632, 683
and 921 recover at 40, 569, 633, 684 and 922 respectively. No full-set or
predecessor-EOF continuation claim follows from this single-volume check.

Reproduction uses `measure_shared_audio_capacity.py`,
`benchmark_fixed_resident_audio.py --fixed-tail`, `verify_cached_cell_player.py`,
`measure_fap3_fuse.py --trace-pipeline`, `capture_cell_codebook_full.py` and
`verify_fixed_audio_tail.py`. The diagnostic TRD and complete evidence are
archived in [the fixed-tail report](fixed_audio_tail_report.json). Root
release images remain unchanged while timing is unresolved.
