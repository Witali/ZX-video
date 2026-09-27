# Half-row motion cache in the resident-AY player

Date: 2026-09-27. Baseline: `da369e6`, the complete three-volume resident
AY player with foreground audio service. Scope: the same **4221 frames**,
unchanged resolution, all encoded picture fields and **25326 AY records**.
No scene-specific code or quality adjustment is introduced.

**Complete CPU and disk tests pass content checks, but video cadence still
fails.** Smaller cache copies save deterministic CPU, yet the measured
end-to-end improvement is small. Keep this as an optional measured variant;
the resident-AY baseline and root release images remain unchanged.

## Implementation and memory

[The format transform](half_row_cache.py) replaces the three-byte cache map
with six bytes. Each bit selects a 16-byte half of four compact bitmap rows.
The map is computed from all motion-predictor source reads. Combining the
two bits recreates the exact previous map; every other packet byte remains
unchanged. The [builder](half_row_player.py) checks this reversible transform
for every packet, including independent-volume native-mask initialization.
Each transformed packet must still fit the 4702-byte guarded payload window.

The new selector retains the existing paired full-row copier when both
halves are needed. It copies only the selected 16 bytes for a partial group,
and advances the same pointers without writing for an unused group.

- Selector: **62 bytes at 7823h..7860h**, after the resident-audio initializer
  bridge and inside retired metadata space ending at 78A0h.
- Half-row copier: **80 bytes at 7B00h..7B4Fh**, inside the retired initializer
  space ending at 7B58h, before the ZX0 suspension stack at 7B70h.
- Old cache selector at **876Eh** becomes a three-byte tail jump, followed
  by an eleven-byte five-LDI parser helper. The old 52-byte selector region
  leaves **38 zero bytes** after these entries. The paired full-row helper
  at 87A2h is unchanged.
- Cache map: **BA40h..BA45h** instead of BA40h..BA42h. Screens, compact data,
  cache, AY FIFO, resident soundtrack, three video banks and stacks keep
  their existing allocations.

The new 7823h/7B00h code is in **contended bank 5**. Instruction-table
savings do not include its ULA delays. Both CPU and actual Fuse playback
are measured below; no contention-free speedup is assumed.

The parser keeps all entry addresses. Its minimum payload increases
288→291, and the fixed-length validation term increases 275→278. A CALL
copies five map bytes, followed by the sixth LDI and one NOP. The range
immediates keep their 10-T instruction costs. A distinct disk-series
fingerprint prevents swapping between formats.

## Deterministic Z80 costs

Instruction timing uses the [Zilog Z80 table](https://www.zilog.com/docs/z80/um0080.pdf).
The copy formula includes the twelve routine calls' bodies and RETs, but
excludes their outer CALLs, which are unchanged. For 24 four-row groups:

```text
old paired whole-row map: 3795 + 2227*N
new half-row map:         4998 + 1436*R + 1373*L + 2234*F
N = R + L + F
R/L/F = groups requiring right, left, or both halves
```

Frames with cache disabled execute no cache copy. The new base includes
twelve 10-T entry jumps. The full-row helper remains **2240 T**. All group
positions, pair patterns and empty/full maps execute against the formula.
Every written and untouched byte, wrap, final pointer, register and stack
is checked after each prefetch.

| Measured region | Before, T | After, T | Difference, T |
|---|---:|---:|---:|
| Cache-copy bodies, all 4221 frames | 112146097 | 96166094 | −15980003 |
| Complete metadata/reconstruction/native stages | 1018049241 | 1002069238 | −15980003 |
| Packet map copy, one frame | 68 | 147 | +79 |
| Packet map copies, all frames | 287028 | 620487 | +333459 |
| Sum of measured frame stages and map-copy instructions | 1018336269 | 1002689725 | −15646544 |

The [full CPU benchmark](benchmark_half_row_cache.py) checks every compact
frame and both complete 6912-byte native screens against the existing
states. Per-frame measured deltas equal the independent cache formulas.
**124 frames are slower** because extra map dispatch does not always avoid
enough copying. This benchmark excludes changed ZX0/queue work, actual AY
service frequency, IRQ/ULA, ROM and disk latency; its total is not the whole
player CPU cost. [Saved frame-level results](half_row_cache_cpu.json).

## Actual disks and complete Fuse playback

| Disk | Used / 2544 | Free | Video bytes | Video sectors | Late frames, before→after | Max late fields, before→after | Average fps |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2491 | 53 | 613413 | 2397 | 213→206 | 103→97 | 8.315401 |
| 2 | 2492 | 52 | 613632 | 2397 | 654→660 | 291→287 | 8.036711 |
| 3 | 2491 | 53 | 612734 | 2394 | 878→874 | 291→282 | 8.333333 |

Raw maps add **12663 B**; optimal ZX0 stream size rises **1832196→1839779 B
(+7583)**. Runtime reads rise **7158→7188 sectors (+30)**. Total allocated
disk sectors rise **7434→7474 (+40)**, including startup and interleave
padding. These are actual built disks, not the old offline +7201-B estimate.
The audio bank and all record values remain unchanged.

All three independent runs reach EOF, all **25326 AY records** are exact
at **50 Hz**, and there are **zero underruns, record gaps or duplicates**.
All runtime sectors are checked without retries; no physical IRQ fields
are missed or duplicated between the first and last video publications.

Nominal lateness changes **1745→1740 frames**; fallback interval violations
change **1047→1043**. Maximum actual deviations are **6878086/20350596/
19996070 T**. Late runs recover 5/3/6 times. Disks 1 and 2 still end late,
with unrecovered local runs **1609..1623** and **994..1296**. All disk-3 runs
recover. Neither the nominal schedule nor the one-field fallback passes.

Summed first-to-last publication spans change **1816733868→1816379328 T**:
only **−354540 T**, or five 50-Hz fields (0.1 seconds summed over the disks).
This includes all contention, IRQ and disk effects and different startup
phases. It is not an isolated measure of the cache copier's speed.
Measured reconstruction-stage elapsed time falls by 6883894 T, less than
the deterministic 15980003-T reduction. Contended instruction placement is
a concrete candidate to investigate, but these traces do not isolate its
cost from IRQ phase effects.

Foreground stage totals exceed six fields on **84/244/323** frames, and
none of the late frames was native-ready at least 1000 T before its nominal
deadline. Empty-input waits remain **29410452/96004777/122859133 T**;
they include actual producer and disk work and are not idle-only overhead.

## Verification and reproducibility

- Three new tests cover every group position/pattern, exact cycle formulas,
  dirty/untouched cache bytes, map reversibility, bounds and the real AY
  interrupt after each instruction of a mixed copy sequence. All pass.
- All 4221 frame stages execute with full compact/native comparisons and
  per-frame old/new instruction counts. Installed helper bytes match the
  benchmarked code in every volume.
- [Cold build/prime checks](build_half_row_player.py) execute real Z80
  opcodes with mocked ROM reads, verify every installed section, first full
  native/second compact frame, 31 queued audio records and immutable audio
  bank contents. Mocked swaps 1→2→3 verify prompts and reject wrong disks
  and series. This is distinct from actual independent Fuse boots.
- Fuse checks all publication timestamps/field counters, 80 sampled screen
  bytes per frame, every AY record, every runtime sector and final progress.
  It does not compare every screen byte. Physical-drive testing and a full
  new integrated deterministic CPU replay remain pending.

Run with the project's Python dependencies and `PYTHONPATH=toolkit`:

```powershell
python -m unittest test_half_row_cache -v
python toolkit/benchmark_half_row_cache.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output toolkit/half_row_cache_cpu.json
python toolkit/build_half_row_player.py --baseline-build .tmp/resident-audio-build-foreground.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/half-row-player --report toolkit/half_row_player_build.json --read-cache .tmp/resident-audio-player-foreground/zx0
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/half-row-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/half-row-player-fuse --trace-pipeline --trace-fields
python toolkit/snapshot_resident_audio_player.py --build toolkit/half_row_player_build.json --directory .tmp/half-row-player --fuse .tmp/half-row-player-fuse --output toolkit/half_row_player_evidence
python toolkit/summarize_half_row_player.py
```

The saved runs used the equivalent per-volume `measure_fap3_fuse.py`
commands as each disk became available. [Evidence manifest](half_row_player_evidence/manifest.json),
[build report](half_row_player_build.json), [auditor](summarize_half_row_player.py)
and [summary](half_row_player_summary.json) preserve sources, generated code,
full raw traces, timing gates and the unsuccessful cadence outcome.

## Decision and next tests

Retain as an optional implementation, not a new release/default or the only
baseline. Its CPU saving is real, but +40 occupied sectors buy only five
fewer late frames in this delivery measurement. Continue to compare against
the smaller resident-AY format.

First test moving the hottest 16-LDI body to the **38 unused bytes in the
old uncontended selector**: sixteen LDIs plus RET require 33 bytes. A CALL
and return/skip add control cost, so count it and measure the full player.
Do not assume that moving all helper code is necessary or profitable.

Then investigate a larger prepared-video reservoir. Each current video
bank reserves 8 KiB for compressed input and 8 KiB for decoded history;
completed blocks no longer need their compressed prefix. A possible separate
format is overlap-safe, bank-local ZX0 with output toward the bank bottom
and compressed bytes toward the top. First trace **every unread input byte**
and compute the necessary gap for every block; size alone cannot prove safe
in-place decoding. Account for EOF markers, shared disk sectors, live LZ
history, wraparound and all copies before changing the player. Larger
history alone is not a solution: the earlier 16-KiB study used a different
stream and a separate input area. Reuse it only as background evidence.
