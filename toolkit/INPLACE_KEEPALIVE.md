# Periodic drive maintenance for the larger ZX0 reservoir

Date: 2026-09-27. Baseline: the pre-read recovery variant at `1d3ac46`.
Scope: the full 4221-frame authorized edit on three independently bootable
TRDs, unchanged resolution, video packets, 15872-byte ZX0 blocks and AY data.

**All 25326 AY records now meet 50-Hz delivery with zero underruns or record
gaps. Video timing improves, but neither the nominal nor fallback video gate
passes. This remains an experimental player, not a replacement release.**

## Change and memory contract

The previous player waited until the next read to restore the drive after a
long idle interval. Direct-read retries disappeared, but successful reads
could still wait about 0.64 seconds and empty the sound queue.

[The new helper](inplace_keepalive_player.py) checks elapsed fields during
queue service and before packet reconstruction, preparation, drawing and
final audio draining. Checking only a full queue would miss long runs of
foreground frame work. At 64 fields since the previous read or maintenance,
it invokes the established TR-DOS 5.03 SEEK/HLD procedure for the **last
cached cylinder**, not the next sector's track. It does not change sides,
read a sector, consume stream bytes, advance cursors or replace slot data.
The existing pre-read recovery remains available.

Main AF/BC/DE/HL are saved around the check. The ROM call additionally saves
IX/IY, AF' and BC'/DE'/HL' on the existing disk stack. The slow IRQ vector is
selected atomically for ROM execution, then the fast vector is restored.
AY interrupts remain enabled. The saved service counter is shared with the
producer; no new state bytes or data buffers are allocated. A drive whose
cached track is FE/FF, or a finished stream, receives no maintenance command.

The helper occupies **115 bytes at 7E70..7EE2** in free producer-tail RAM.
A **six-byte wrapper at DB46..DB4B** serves five existing CALL sites. All
five substitutions retain three-byte instructions and **17 -> 17 T** each.
The wrapper calls the original audio service before the drive check. Screens,
AY storage, dictionaries, input slots and private ZX0 stack remain assigned
as in the preceding experiment.

## Actual disk and complete playback results

The video stream stays **1818909 bytes / 7106 sectors**. Occupied sectors are
**2462/2463/2462**, leaving **82/81/82**. Relative to `1d3ac46`, only disk 1
uses one additional occupied sector because of bootstrap/placement changes.
Every decompressed video byte and AY record is unchanged.

| Disk | Late frames, before -> after | Bad 5..7-field intervals | AY underruns | Effective fps |
|---|---:|---:|---:|---:|
| 1 | 137 -> 90 | 87 -> 43 | 12 -> 0 | 8.333333 |
| 2 | 553 -> 465 | 293 -> 249 | 0 -> 0 | 8.063713 |
| 3 | 806 -> 766 | 534 -> 491 | 12 -> 0 | 8.333333 |

Total late frames improve **1496 -> 1321 (-175)** and invalid intervals
**914 -> 783 (-131)**. Compared with the smaller resident-AY baseline at
`da369e6`, late frames improve **1745 -> 1321 (-424)** while both now have
zero AY underruns. Neither comparison establishes smooth video playback.

All three runs reach EOF. There are zero direct-read retries, missing or
duplicate IRQ fields, missing or duplicate AY record fields, or content
errors. Actual AY delivery at 50 Hz passes. Maximum sector-read service is
**155717/155736/155756 T** (about **43.9 ms**), down from the prior maximum
2259050 T. The exact sector count/order is unchanged.

Periodic maintenance occurs **69/60/56 times**. The 185 ROM-service intervals
total **76670 elapsed T** (about 21.6 ms), excluding surrounding player
instructions. Most last around 0.12 ms; the maximum is 1242 T with IRQ/waits.
The removed long waits are therefore not replaced by comparable SEEK pauses.

The summed first-to-last-publication span changes **1815953880 -> 1812975750
T (-2978130)**. Disk 1's span is unchanged; disk 2 improves by 2978133 T;
disk 3 differs by +3 T. Initial disk/IRQ phases were not matched, so this is
an end-to-end playback comparison, not an isolated CPU saving.

Maximum lateness remains **64/260/265 fields**. Actual maximum OUT deviations
are **4538116/18436083/18790630 T**. Recovered late runs number **3/15/3**;
disk 2 ends with an unrecovered run at local frames 1238..1296. The saved
[summary](inplace_keepalive_summary.json) includes every missed frame,
late run/recovery, actual timing gate and full delivery profile.

## Instruction counts

All paths execute native opcodes and check each instruction against its
timing-table entry. The fixture deliberately destroys ROM-clobberable
registers. The previous path contains no periodic check, so its additional
cost is 0 T. The existing audio service is identical in both variants.

| Check path | Helper including RET, T | Total additional cost with wrapper, T |
|---|---:|---:|
| Recent service, no action | 252 | +279 |
| Due within low-byte range | 709 | +736 |
| Due across counter wrap | 709 | +736 |
| Nonzero high-byte difference | 688 | +715 |
| Uninitialized/invalidated drive | 158 | +185 |
| No remaining sectors | 128 | +155 |

The extra wrapper cost is 27 T: CALL audio service (17) and JP check (10).
The original outer CALL remains 17 T. Due-path counts include switching to
the disk stack, all saves/restores, IRQ-vector changes and the shared adapter
return path. ROM execution, IRQ, ULA waits and drive latency are excluded;
the Fuse intervals above report those elapsed costs separately.

The actual number of skipped checks is not replayed, so these figures do
not claim a full integrated-player CPU delta. The 15872-byte producer and
ZX0 byte code are unchanged; their earlier all-block CPU evidence remains
valid for its documented fixture scope. The extra checks increase CPU work
while avoiding much longer disk stalls.

## Verification, decision and next bottleneck

Three tests cover all 160 current logical tracks (including a different
next track), threshold 63/64, 16-bit wrap, long idle, uninitialized/invalidated
drive, EOF and a real AY interrupt after every maintenance instruction.
Both register sets, page, screen/slot data, cursor/count, READ command,
I/IM2/vector and stack are checked. No test maintenance call reads a sector.

All three builds pass dirty-RAM independent boot, complete first native and
second compact frames, resident-audio immutability and both disk swaps with
wrong-volume/series rejection. Full Fuse coverage includes all frames and
AY writes, every runtime sector, progress and actual publication/IRQ timing.
Fuse compares 80 screen bytes per frame. The unchanged frame/block-decoder
full-byte tests are reused; this is not a new full-screen Fuse comparison
or a physical-drive measurement.

Retain periodic maintenance for the larger-slot experimental path. The
remaining delays are preparation/transfer stalls: **41/171/269 frames** have
foreground work longer than six fields. Empty-queue waits sum to
**14243820/74341524/107308953 elapsed T**, including producer/decoder and
disk service. Worst packet transfers still approach 1.9 million T, although
individual sector reads now stay below 156000 T. No late frame was already
rendered at least 1000 T before its nominal deadline.

Next profile those block-acquisition bursts and the usable reserve through
the worst runs. Compare earlier sector acquisition or incremental consumption
of a partially acquired compressed block against the current full-input
requirement. Preserve the per-byte overlap proof, live LZ history, all AY
deadlines and exact slot ownership. Reuse the historical streaming-input
failure as a CPU-cost comparison; do not assume that smaller waits imply
faster sustained playback. A later local option is reducing the common
maintenance-check path, but that alone cannot remove multi-field packet waits.

## Reproduction and evidence

Run with the project dependencies and `PYTHONPATH=toolkit`:

```powershell
python -m unittest test_inplace_keepalive -v
python toolkit/test_inplace_keepalive.py --report toolkit/inplace_keepalive_cpu.json
python toolkit/build_inplace_keepalive.py --baseline-build toolkit/inplace_slot_player_build.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --read-cache .tmp/inplace-slot-reload-player/zx0 --read-cache .tmp/inplace-zx0-cache --output .tmp/inplace-keepalive-player --report toolkit/inplace_keepalive_build.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/inplace-keepalive-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/inplace-keepalive-fuse --trace-pipeline --trace-fields
python toolkit/snapshot_resident_audio_player.py --build toolkit/inplace_keepalive_build.json --directory .tmp/inplace-keepalive-player --fuse .tmp/inplace-keepalive-fuse --output toolkit/inplace_keepalive_evidence
python toolkit/summarize_inplace_keepalive.py
```

[Source/build/metadata/full traces](inplace_keepalive_evidence/manifest.json),
[CPU paths](inplace_keepalive_cpu.json), [build report](inplace_keepalive_build.json)
and [auditor](summarize_inplace_keepalive.py) are saved. The snapshot refuses
to overwrite different evidence; use a new folder for another attempt.
The verified root release images remain unchanged.
