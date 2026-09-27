# Resident AY in three independently bootable TRDs

Date: 2026-09-27. Baseline: `8a49d3c`, including the complete two-byte
Huffman-cache player measurement at `8bc6a09` and the resident AY CPU
prototype. Input: all **4221 frames** of `movie_no_credits.json`, unchanged
resolution, video fields, nominal 25/3 fps and all **25326 AY records**.

**Actual three-disk capacity and continuous 50-Hz AY now pass in Fuse.
Video timing still fails, including the one-field fallback.** These images
are experiments in the build directory; root release TRDs are unchanged.

## Format, memory and startup

[The builder](build_resident_audio_player.py) accepts the existing encoded
FAP3 inputs, volume boundaries and reference states. No scene-specific
decoder behavior is introduced. It removes the six AY records from each
video packet, retains every video field and trains a resident AYH1 stream
per independent volume. It preserves the established first-two-frame native
mask initialization on later disks. A format-specific disk-series identity
prevents a swap into the previous muxed format.

- Banks **0/1/3**: three 8-KiB ready-video/history slots, 24 KiB in total.
  Admission and both slot cursors use three slots; bank 4 is unreachable
  through the video queue. The three-slot implementation is exercised through
  EOF on every disk, including all ZX0 blocks and sector reads.
- Bank **4**: complete resident audio code, state, trees and compressed
  soundtrack: **14230/13215/13037 B**, leaving **2154/3169/3347 B**.
- Existing screens, reconstruction code/data, stack, TR-DOS workspace and
  A000h AY FIFO remain allocated as in the integrated player. The FIFO has
  31 usable records. It is separate from the video history.
- The fixed service guard and paging bridge reuse the retired enqueue
  routine at **941Eh**: 22+35 bytes inside its former 75-byte region.
  A second 35-byte initializer bridge occupies retired code at **7800h**.
  Bank-7 hooks start at **DB20h**, after the DB00h overlay installer and
  before the DC00h packet parser. Every patch checks its original bytes.
- Two additional bounded startup sections load bank 4 before the final
  visible-screen restore. Shared-sector offsets are included in the
  staging-capacity check. Dirty-RAM boot verifies every installed section;
  mocked-ROM swaps 1→2→3 verify the prompt, disk identities and new cold RAM.

| Disk | Frames | Video bytes | Video sectors | Used / 2544 | Free |
|---|---:|---:|---:|---:|---:|
| 1 | 1624 | 610042 | 2383 | 2476 | 68 |
| 2 | 1297 | 611170 | 2388 | 2479 | 65 |
| 3 | 1300 | 610984 | 2387 | 2479 | 65 |

Video starts at sectors 106/107/108. Both attempts have the same stream and
capacity. The corrected build reads 91/92/93 startup sectors, versus
90/92/93 in the first attempt because of section-boundary sharing. These
read counts are not the count of uniquely occupied disk sectors. Video-only
streams total **1832196 B and 7158 sectors**, versus **1919945 B and 7501
sectors** in the old mux. Audio is now part of the startup payload; do not
interpret the video-only difference as the net disk-capacity saving.

## Audio scheduling: two complete attempts

1. **Queue-only service, batch limit 6:** call the resident service before
   each producer step and during final audio drain. This reaches EOF with
   exact records but causes **3830 AY underruns**. The producer-step service
   does not cover long foreground drawing/reconstruction sequences. Keep
   this failed attempt and its original generator in
   [the queue-only evidence](resident_audio_player_evidence/queue-only/manifest.json).
2. **Foreground service, batch limit 31:** additionally service audio before
   packet acquisition, reconstruction and native drawing. When occupancy
   falls below 24, decode up to 31 records, stopping at FIFO-full or EOF.
   This fills available space without waiting or exposing partial records.
   All **25326 records run at 50 Hz**, with **zero underruns, skipped record
   fields or duplicate record fields**. The IRQ consumer is unchanged.
   [Complete evidence](resident_audio_player_evidence/foreground/manifest.json).

The service-call placements and batch limit changed together. Their
individual contributions were not measured separately. The first failure
motivates the correction but does not prove a single exclusive cause.

## Instruction costs

Counts use the [Zilog Z80 table](https://www.zilog.com/docs/z80/um0080.pdf),
exclude IRQ/ULA, ROM and disk latency, and are recorded in generated metadata.
Outer CALL instructions are included only where stated.

| Operation | Previous | Resident variant | Difference |
|---|---:|---:|---:|
| Video-slot admission, `CP 4` → `CP 3` | 7 T | 7 T | 0 |
| Slot cursor, `INC A; AND 3` → helper call | 11 T | 39 / 47 T | +28 / +36 |
| Packet minimum/range immediate load | 10 T | 10 T | 0 |
| Audio-prefix dispatch, CALL → JP video body | 17 T | 10 T | −7, excluding old enqueue body |
| Queue/drain source load → service hook, FIFO already sufficient | 13 T | 160 T | +147 |
| Foreground frame CALL → service-tail hook, FIFO already sufficient | 17 T | 147 T before original entry | +130 |

The service guard costs **103 T** when no refill is needed. On refill its
prefix costs **108 T**, then the fixed bridge adds **436 T** plus actual
bank-local decode work. The queue/drain hook adds **44 T + service** over
the old source load. Each foreground hook adds **27 T + service** over the
old direct call. Cursor helpers cost 22/30 T excluding their 17-T CALL.
Initialization adds a 10-T tail JP and the 436-T bridge to the measured
1056-T resident initializer; this is outside playback.

The existing [resident decoder formulas](RESIDENT_AUDIO_Z80.md) still apply
to the actual number of records/bits produced by a call. In particular,
the 31-empty-record test measures **108+436+109+789×31 = 25112 T**.
The historical six-record producer total **52600652 T** is a separate CPU
fixture, **not the current integrated scheduling total**. A complete new
instruction replay is still required before claiming a net CPU saving.

## Complete playback results

| Disk | Old late frames | Queue-only late / AY underruns | Corrected late / AY underruns | Corrected average fps | Maximum lateness, fields |
|---|---:|---:|---:|---:|---:|
| 1 | 984 | 203 / 537 | 213 / 0 | 8.314549 | 103 |
| 2 | 834 | 546 / 1409 | 654 / 0 | 8.032726 | 291 |
| 3 | 1248 | 847 / 1884 | 878 / 0 | 8.333333 | 291 |

Both actual OUT timestamps and field counters identify all missed nominal
deadlines. Corrected playback has **1745 late frames**, **1047 intervals
outside the 5..7-field fallback**, and maximum actual deviations of
**7303527/20634228/20634227 T**. Fourteen late runs recover (5/3/6 by disk),
but final runs **1607..1623** and **1233..1296** remain late on disks 1 and 2.
All late runs recover on disk 3; its exact average fps does not imply smooth
frame delivery. The schedule origin remains fixed, with no dropped frames.

Summed first-to-last publication spans improve from **1851904234** to
**1816733868 T**, a difference of **−35170366 T**. This is end-to-end elapsed
time, including changed boot phase, IRQ/ULA, disk rotation and scheduling;
it is not an isolated CPU benchmark. Corrected playback is 1701793 T slower
than the failed queue-only attempt while eliminating its sound gaps.

The pipeline traces identify **90/247/328** frames whose measured foreground
stages alone exceed six fields. No late frame was native-ready at least
1000 T before its deadline. Empty-input waits total **31160087/95577634/
123315323 T**, including producer work and disk service. Frame stages do not
include audio hooks outside their traced boundaries. Do not call the entire
wait removable overhead or solve this only by changing publication timing.

All 7158 video sectors are checked without retries. Measured read-call
intervals total **222555893 T**, and seek-call intervals **4922392 T**.
These intervals combine ROM, emulated drive, IRQ and contention. There are
no missing or duplicate physical IRQ fields between first and last video
publications. No physical drive has been measured.

## Verification, limitations and reproduction

- **24 unit tests pass**, including all FIFO occupancies and index wrapping,
  exact service/slot costs, both batch sizes, real AY IRQ after individual
  instructions, register preservation, bank switching and the prior AYH1
  full-alphabet/bounds tests.
- [The verifier](verify_resident_audio_player.py) compares every separated
  video packet against the original, including the existing independent
  native-mask initialization. It executes real boot/prime opcodes with
  mocked ROM, checks all installed sections, 31 prepared AY records, initial
  AY state, the complete first native screen and complete second compact
  frame on every disk. Priming takes **1813732/2933949/3088629 T**, excluding
  boot; it is not a scheduled-IRQ playback test.
- Full read-only Fuse runs check all 4221 publications, 25326 AY records,
  all runtime sectors, progress to 100%, physical IRQ fields and EOF.
  Pixel coverage is **80 samples per frame**, not every screen byte. The
  unchanged renderer has its earlier full-frame CPU comparison; a complete
  new integrated CPU replay remains pending.
- The first packet verifier mistakenly compared later-volume forced native
  masks with unmodified raw input. Correcting that verification assumption
  made all packets pass; no video data or decoder changed for that repair.

Run from the worktree with the project's Python dependencies and
`PYTHONPATH=toolkit` (use the existing dependency directory when necessary):

```powershell
python -m unittest test_resident_audio_player test_resident_audio_z80 test_ay_interrupt test_ay_huffman_stream test_audio_lookahead_profile -v
python toolkit/build_resident_audio_player.py --directory .tmp/lookahead-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/resident-audio-player-foreground --report .tmp/resident-audio-build-foreground.json --stored-video toolkit/resident_audio_storage.json --read-cache .tmp/resident-audio-player/zx0 --audio-batch 31 --foreground-audio
python toolkit/verify_resident_audio_player.py --directory .tmp/resident-audio-player-foreground --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --report .tmp/resident-audio-build-foreground.json --output .tmp/resident-audio-prime-foreground.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/resident-audio-player-foreground --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/resident-audio-player-foreground-fuse --trace-pipeline --trace-fields
python toolkit/snapshot_resident_audio_player.py --build .tmp/resident-audio-build-foreground.json --directory .tmp/resident-audio-player-foreground --fuse .tmp/resident-audio-player-foreground-fuse --output toolkit/resident_audio_player_evidence/foreground
python toolkit/summarize_resident_audio_player.py
```

For the failed queue-only attempt omit the two audio flags and use separate
output paths. Its exact historical generator is in the source snapshot.
Do not use the old `--trace-queue-calls` fixture here: its audio enqueue/return
assumption does not describe the new resident service. The saved
[summary/auditor](summarize_resident_audio_player.py) checks archive hashes,
historical source pins, current corrected sources, trace/metadata identities,
priming evidence, complete frame/tick counts and both timing gates. It does
not replay Fuse. The [summary](resident_audio_player_summary.json) and
[priming report](resident_audio_player_prime.json) preserve the results.

## Decision and next work

Keep the corrected resident format as the experimental baseline. It provides
independent sound availability and 65 or more spare sectors per disk, but
has not met the release goal. Revisit finer motion-cache maps and other
lossless speed/size choices using this actual per-volume capacity. Their old
offline savings are candidates, not expected combined savings: rebuild the
new streams and include extra sectors, reduced video history and all CPU
work in the next full comparison. Also obtain a complete deterministic
replay of the current parser, producer and resident service. Generic
converter defaults and root release images remain unchanged.
