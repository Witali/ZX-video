# Uncontended half-row copy body

Date: 2026-09-27. Baseline: the complete half-row experiment at `0c674b6`.
This experiment retains all 4221 frames, exact video and AY streams, three
independent disks and the nominal six-field schedule. It tests whether
avoiding contended opcode fetches outweighs an extra CALL/RET.

## Implementation and exact CPU cost

The previous 80-byte half-row controller occupies bank 5 at 7B00..7B4F.
Its hottest body is sixteen consecutive LDIs (32 bytes, **256 T**). The new
[generator](uncontended_half_copy.py) replaces those instructions with a
CALL into the unused tail of the old bank-2 cache selector. The body and
RET occupy **877C..879C**, 33 of the available 38 bytes, before the unchanged
full-row copier at 87A2. The controller shrinks to **51 bytes**, 7B00..7B32;
its remaining allocated bytes are zeroed. Repacking avoids an extra skip
jump. The one crossing DJNZ displacement is regenerated and checked.

Each copied half-row now costs **17 + 256 + 10 = 283 T**, a deterministic
increase of **27 T**. Each partial four-row group adds **108 T**. For a frame
that enables the cache, including all twelve selector-entry jumps but
excluding their outer CALLs:

```text
old = 4998 + 1436*right_only + 1373*left_only + 2234*full
new = 4998 + 1544*right_only + 1481*left_only + 2234*full
```

Cache-disabled frames cost zero in both formulas. Full/empty groups are
unchanged. Parser cost remains 147 T/frame, with **zero delta**. These counts
use the [Zilog instruction table](https://www.zilog.com/docs/z80/um0080.pdf)
and exclude IRQ, ULA waits, TR-DOS ROM execution and physical disk latency.
Extra nested-call stack use is two bytes; active code grows by four bytes.
All allocated regions, video buffers, screens and AY storage remain unchanged.

The subclass [builder](uncontended_half_player.py) recompresses changed boot
sections and gives the experiment its own disk-series identity. It does not
change maps, Huffman symbols, ZX0 video bytes or resident audio bytes.

## Measurements

The [full CPU report](uncontended_half_copy_cpu.json),
[build report](uncontended_half_player_build.json) and
[full playback summary](uncontended_half_player_summary.json) retain the
per-frame and per-volume results.

All **4221 compact frames and both complete native screens** match in the
CPU fixture. Frame-stage CPU grows **1002069238→1004729062 T (+2659824)**;
the cache-copy component grows **96166094→98825918 T** by the same amount.
Exactly 3421 frames incur extra work; the other 800 are unchanged. Each
frame's measured difference matches the independent **108 T per partial
four-row group** formula. Parser delta is zero, so accounted frame/parser
work grows by the same 2659824 T. This does not measure total player CPU.

Video and audio streams are byte-identical to the half-row baseline. Used
sectors remain **2491/2492/2491**, free sectors **53/52/53**; the video needs
**2397/2397/2394 sectors**, **1839779 bytes** in total. There is no bootstrap
sector increase. Mocked cold boot saves 1411 T per disk due to changed
startup compression; this is outside timed playback.

All three cold Fuse runs finish, with **zero AY underruns, gaps or duplicate
record fields**. All 25326 AY records and all 7188 runtime sectors match.

| Disk | Frames | Late frames, old → new | Max late fields | Bad intervals, old → new | New fps |
|---|---:|---:|---:|---:|---:|
| 1 | 1624 | 206 → 206 | 97 | 93 → 93 | 8.315401168 |
| 2 | 1297 | 660 → 661 | 287 | 371 → 371 | 8.036710902 |
| 3 | 1300 | 874 → 874 | 282 | 579 → 584 | 8.333333333 |

Late frames grow **1740→1741**, invalid fallback intervals **1043→1048**.
Each first-to-last publication span is unchanged: **691991172/571731204/
552656952 T**, totaling **1816379328 T**. Maximum actual deviations are
**6878086/20350596/19996059 T**. Recovered late runs change **5/3/6→5/2/6**;
the two middle runs on disk 2 merge. Disks 1 and 2 still finish with
unrecovered local runs **1609..1623** and **994..1296**; all disk-3 runs recover.
Both the nominal and fallback video gates fail.

Reconstruction elapsed time changes **640812368→640903384 T (+91016)**.
The disk read intervals total **74601775/74495381/74398493 T**, seeks
**1663560/1660475/1662423 T**. These are elapsed service intervals, including
interrupt effects, rather than deterministic ROM instruction counts.
Foreground work exceeds six fields on **84/245/323 frames**. No late frame
was native-ready at least 1000 T before its nominal deadline. Empty-input
waits are **29434327/96119605/122657718 T** and include useful producer/disk
work. The saved trace retains individual missed deadlines and recoveries.

## Decision

Reject this placement as a speed improvement. The measured total delivery
does not improve and cadence slightly worsens; keep the implementation and
evidence as an optional reproducible experiment. The smaller resident-AY
baseline and the original half-row variant remain available. A new attempt
must not assume that removing opcode contention alone repays CALL overhead.

Next investigate the larger prepared-video reservoir already proposed in
the [decode-speed plan](DECODE_SPEED_PLAN.md). Prove the unread-input/output
gap for every candidate ZX0 block, including EOF and shared-sector carry,
before implementing in-place decoding or changing queue/history ownership.

## Verification and reproduction

Four tests cover every map position/pattern, copied and untouched bytes,
wraparound, exact instruction costs, patch bounds, and the real AY IRQ after
every instruction of a mixed copy sequence, including the nested return.
The full CPU fixture compares compact data and both complete native screens.
Cold boot/prime checks use real generated Z80 code with mocked ROM reads,
dirty RAM, immutable audio storage, the first full native and second compact
frame, and both disk swaps with wrong-disk/series rejection.

Independent cold Fuse runs cover every frame through EOF, 80 sampled screen
bytes per frame, all 25326 AY records, every runtime sector, actual publication
OUT timestamps, IRQ fields and progress through 100%. This is distinct from
the full pixel comparison in the CPU fixture. Full integrated deterministic
CPU totals and physical-drive behavior remain unmeasured. Startup disk/IRQ
phases are not matched to the baseline, so elapsed deltas cannot isolate ULA
contention alone.

Use the project's Python dependencies and `PYTHONPATH=toolkit`:

```powershell
python -m unittest test_uncontended_half_copy -v
python toolkit/benchmark_uncontended_half_copy.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output toolkit/uncontended_half_copy_cpu.json
python toolkit/build_uncontended_half_player.py --baseline-build toolkit/half_row_player_build.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/uncontended-half-player --report toolkit/uncontended_half_player_build.json --read-cache .tmp/half-row-player/zx0 --read-cache .tmp/resident-audio-player-foreground/zx0
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/uncontended-half-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/uncontended-half-player-fuse --trace-pipeline --trace-fields
python toolkit/snapshot_resident_audio_player.py --build toolkit/uncontended_half_player_build.json --directory .tmp/uncontended-half-player --fuse .tmp/uncontended-half-player-fuse --output toolkit/uncontended_half_player_evidence
python toolkit/summarize_uncontended_half_player.py
```

The [evidence manifest](uncontended_half_player_evidence/manifest.json) pins
the generator sources, generated metadata, full raw traces and debugger
scripts. The [auditor](summarize_uncontended_half_player.py) checks archived
hashes, current source hashes, CPU arithmetic against the old per-frame
report, installed helper bytes, stream identity, capacity, boot and timing.
The images remain experimental; root release TRDs are not replaced.
