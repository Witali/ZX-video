# Cost-selected fast fragments with resident audio and larger ZX0 blocks

Date: 2026-09-27. Comparison baseline: the retained `a84451d` player.
Scope: all 4221 frames of the authorized edit, unchanged resolution, pixels,
AY records, 25/3-fps deadlines and independent boot on every disk.

**Three disks fit and complete Fuse playback with exact 50-Hz AY. Video
still fails both timing gates. These are experimental images.**

## Why repeat the older selection experiment?

The [September 25 experiment](FRAGMENT_COST_SELECTION_ru.md) rejected its
64-bit allowance variant because volume 3 exceeded the old disk layout by
45 sectors. Since then, separating resident AY and using 15872-byte in-place
ZX0 blocks has left 82/81/82 sectors free. This experiment tests the same
selection rule on all three volumes with the current player and layout.

[The probe](probe_resident_fragments.py) first re-encodes each baseline
stream byte-for-byte. It then considers replacing motion/intra tiles with
existing fast-fragment modes 85..88. The historical rule permits up to 64
additional local bits and requires an estimated saving of at least 400 T.
Its 150-T-per-Huffman-symbol term is a historical ranking heuristic, **not
a lower bound for the current 134-T short decoder**. Actual CPU execution
and final optimal ZX0 compression determine the result.

Each volume keeps its original Huffman tables. Packets outside that volume
are unchanged, and all source frames and AY records are independently
decoded after selection. Volume 3 reproduces the old 64-bit candidate
exactly: SHA-256 `14c1c86ea6f0e8798dc722761dd4d885b070ab82eaaf072a84aeac5fd0ebfb9d`.
This is not a repeat of positional no-op tags. No new opcode template,
decoder mode, display approximation or RAM allocation is introduced.

The resident-AY bank, both screens, code/stacks/TR-DOS workspace and three
15872-byte decoded slots retain the [existing memory contract](INPLACE_KEEPALIVE.md).
Every disk contains its own cold-start state and uses a distinct set identity.
Nothing requires RAM from the preceding disk.

## Capacity and delivery CPU

| Volume | Frames | Selected tiles / affected frames | ZX0 bytes, old -> new | Occupied / free sectors |
|---|---:|---:|---:|---:|
| 1 | 1624 | 6075 / 1336 | 606434 -> 622280 | 2525 / 19 |
| 2 | 1297 | 5133 / 1008 | 606524 -> 618427 | 2510 / 34 |
| 3 | 1300 | 4843 / 917 | 605951 -> 616884 | 2507 / 37 |

There are 16051 selected tiles in 3261 frames. Raw video packet bytes grow
**2,965,011 -> 3,032,136 (+67,125)**. Compressed video grows
**1,818,909 -> 1,857,591 bytes (+38,682)**. Runtime reads grow
**7106 -> 7257 (+151 sectors)**; actual occupied sectors grow
**7387 -> 7542 (+155)**, including bootstrap/layout effects. Estimated free
space before the real build was 20/35/39; the table gives actual TRD sizes.
All **193 blocks (64/63/66)** round-trip and meet sector-aligned in-place
overlap constraints. The largest source packet is 3645 bytes.

The [delivery benchmark](benchmark_resident_delivery.py) uses the actual
new starting sectors, the retained producer/ZX0 and the same frozen idle
clock as the baseline. ROM reads are mocked; all bytes, sector order,
carry copies and protected banks are checked. Instruction histograms are
validated against the timing table.

| Measured component | Baseline T | Candidate T | Difference T |
|---|---:|---:|---:|
| Producer | 11,831,304 | 12,093,407 | +262,103 |
| ZX0 decoder | 189,573,555 | 201,093,101 | +11,519,546 |
| Producer + ZX0 | 201,404,859 | 213,186,508 | +11,781,649 |

Carry copies grow **96,256 -> 98,816 bytes**. These counts exclude frame
stages, queue control, AY/IRQ, ULA, ROM and physical disk elapsed time.
No per-opcode saving is claimed: execution frequencies change with the data.

The [full frame benchmark](benchmark_resident_fragments.py) checks every
compact byte and both complete native screens across all **4221 frames**.
It checks executed instruction timings against the generated listing.

| Volume | Baseline frame T | Candidate frame T | Difference T |
|---|---:|---:|---:|
| 1 | 385,003,910 | 373,614,644 | -11,389,266 |
| 2 | 326,528,010 | 317,017,903 | -9,510,107 |
| 3 | 306,517,321 | 297,971,791 | -8,545,530 |
| Total | 1,018,049,241 | 988,604,338 | -29,444,903 |

**No frame becomes slower in this deterministic frame-stage comparison.**
That statement excludes the extra transport work. Volume 3's saving differs
from the old 8,898,970-T result because the retained decoder has since been
optimized; identical candidate data does not imply an identical CPU delta.

The sum of measured frame and producer/ZX0 components is
**1,219,454,100 -> 1,201,790,846 T (-17,663,254, about 1.45%)**. It is not
a complete integrated-player CPU total or a playback-rate improvement.

The **481 frames** whose baseline foreground work exceeds six fields save
**3,444,876 frame-stage T**; the other **3740 frames save 26,000,027 T**.
Both groups have zero slower frame-stage cases. This classification uses
the old elapsed work, including disk/IRQ/ULA, not an assumption that every
long frame is CPU-bound. The new number of individually over-budget work
intervals is **27/165/263 = 455**, versus **41/171/269 = 481**.

## Complete Fuse playback

All three volumes reach EOF. All **25326 AY records** match and update at
50 Hz with zero underruns, missing/duplicate IRQ fields or AY-record gaps.
There are zero read retries and the exact expected sector sequence is read.
Actual screen-publication OUT timings are checked separately from counters.

| Volume | Late frames, old -> new | Invalid intervals, old -> new | Maximum lateness, fields | Recovered runs |
|---|---:|---:|---:|---:|
| 1 | 90 -> 73 | 43 -> 36 | 64 -> 72 | 2 |
| 2 | 465 -> 432 | 249 -> 239 | 260 -> 247 | 8 |
| 3 | 766 -> 732 | 491 -> 472 | 265 -> 238 | 4 |

Total late frames are **1321 -> 1237 (-84)**; invalid 5..7-field intervals
are **783 -> 747 (-36)**. Maximum actual deviations are
**5,105,374 / 17,514,276 / 16,876,119 T**. Volumes 1/3 recover all late runs;
volume 2 ends with an unrecovered run at local frames **1238..1296**.
The first volume has fewer late frames but a worse maximum deviation.

Publication spans are **690,502,104 / 568,894,884 / 552,656,952 T**, totaling
**1,812,053,940 T**, down **921,810 T** from the baseline. Initial disk/IRQ
phases were not matched, so differences in the traces are not an isolated
measurement of fragment CPU savings. Average fps on volumes 1/3 returns to
25/3 because their late runs recover; that does not establish smooth video.

Fuse checks 80 pixel samples per frame; this is not an all-pixel comparison
inside Fuse. Independent scalar replay covers every source pixel and AY
record. Dirty-RAM boot, first native screen, second compact frame, immutable
audio storage and both handoffs pass under mocked ROM, including the prompt,
wrong disk/set rejection and correct continuation. Physical hardware remains
untested. Neither the nominal nor fallback video timing gate passes.

## Decision and next experiment

Keep the selector as a measured optional candidate and preserve `a84451d`
as the roomier comparison. Do not change converter defaults or release TRDs:
the additional 151 video sectors reduce headroom, the worst deviation on
volume 1 increases, and the complete video schedule still fails. The uniform
64-bit rule has now been measured under the new layout; repeating its old
local size estimate cannot resolve the remaining deadlines.

Large block-acquisition bursts remain visible. For example, global frame
3688 takes **2,244,289 elapsed T** of foreground work, including **1,862,993 T**
in packet transfer and **1,390,428 T** of disk service inside that transfer.
Its separate deterministic frame stage is 365,117 T. Those intervals must
not be added again to the CPU count or described as pure decoder overhead.
No late frame in any volume was native-ready at least 1000 T before its
nominal deadline, so changing only the publication wait cannot fix this run.

Next, compare data choices on expensive frame windows using actual CPU and
final compressed blocks, including extra sectors and usable queue reserve.
An independent lossless candidate is native-map density selection: the
encoder currently rounds a band to full at 18 changed cells. Choosing an
exact partial map or full band before compression needs no new Z80 dispatch
test. Measure the existing sparse/dense output paths, including zero-group
and band-parity costs, then compress and execute all volumes. Do not assume
that a CPU-optimal mask is optimal for ZX0 size or physical disk delivery.

## Reproduction and evidence

Run in the existing `streaming-zx0-player` worktree. The Python interpreter
must have the project's NumPy dependencies. Experimental TRDs stay in
`.tmp/resident-fragments-player`; root release images and converter defaults
are unchanged.

```powershell
$env:PYTHONPATH='toolkit;C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/python_packages'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest toolkit/test_fragment_cost_selection.py -v
python toolkit/probe_resident_fragments.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --baseline-build toolkit/inplace_keepalive_build.json --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/resident-fragments-probe --report toolkit/resident_fragments_probe.json --read-cache .tmp/inplace-keepalive-player/zx0
python toolkit/benchmark_resident_fragments.py --raw-directory .tmp/resident-fragments-probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --probe toolkit/resident_fragments_probe.json --output toolkit/resident_fragments_cpu.json
python toolkit/build_resident_fragments.py --baseline-build toolkit/inplace_keepalive_build.json --probe toolkit/resident_fragments_probe.json --raw-directory .tmp/resident-fragments-probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/resident-fragments-player --report toolkit/resident_fragments_build.json --read-cache .tmp/resident-fragments-probe/zx0 --read-cache .tmp/inplace-keepalive-player/zx0
python toolkit/benchmark_resident_delivery.py --directory .tmp/resident-fragments-player --build toolkit/resident_fragments_build.json --output toolkit/resident_fragments_delivery_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/resident-fragments-player --raw-directory .tmp/resident-fragments-probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/resident-fragments-fuse --trace-pipeline --trace-fields
python toolkit/summarize_resident_fragments.py --archive-directory .tmp/resident-fragments-player --trace-directory .tmp/resident-fragments-fuse --source-directory .tmp/resident-fragments-probe --baseline-raw-directory ../volume-huffman/.tmp/probe --write
python toolkit/summarize_resident_fragments.py
```

The first frame/build attempt stopped with missing process handles and no
Python process remaining. Its cause is unknown. The incomplete build report
contains no completed volumes; the CPU report contains 101 frame comparisons.
Both were preserved as `resident_fragments_interrupted_*.json` before rerunning
the unchanged code. They are incomplete evidence, not a playback pass. The
archive audit requires those 101 comparisons to match the completed replay.

The archive retains compressed source packets, runtime streams, source
snapshots and full traces. Its audit independently replays every source
pixel/AY record, reconstructs the runtime stream including cold-start maps,
checks hashes and CPU arithmetic, and recomputes all timing results. An audit
success means the reported evidence is consistent, **not that timing passes**.
The completed archive contains **82 gzip files / 16,107,210 compressed bytes**;
the saved [summary](resident_fragments_summary.json) pins its manifest and
all input reports. The interrupted 101-frame prefix exactly matches the
completed replay.
