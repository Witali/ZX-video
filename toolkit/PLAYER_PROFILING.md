# Player profiling: CPU costs and actual delivery

Date: 2026-09-27. Repository input: `f701c54`. The retained disk baseline
is `a84451d`; the direct-HL motion optimization is still a separate CPU
prototype. Input is all **4221 frames**, the authorized no-credits edit,
three independent volume checkpoints, unchanged pixels and 25326 AY records.

**The main costs are frame reconstruction/output and sustained input
delivery. The largest stalls occur when decoded input runs out.** Optimizing
a small register setup cannot by itself restore the six-field schedule.
None of the seven measured disk configurations passes the video timing gates.

## What was measured

- [Current frame profiler](profile_current_frame.py): fresh execution of
  every instruction of all 4221 direct-HL frames; exact compact data and
  both complete native screens; instruction, stage and per-frame counts.
  Every total must equal the previous direct-HL benchmark. Retained-player
  stage totals are reconstructed by restoring the proven 21-T motion-entry
  difference, explicitly distinguished from fresh execution.
- [Packet CPU profiler](profile_packet_cpu.py): fresh execution of the
  actual cold-loaded retained TRD parser/queue, all packets and 7106 sectors.
  Every payload byte matches and is written once. Required reads begin
  before prefill, with a frozen field clock and mocked ROM. This workload
  measures on-demand CPU costs; it does not reproduce integrated read-ahead,
  real sector latency, ULA contention or the running audio consumer.
- [Playback comparison and auditor](profile_player_comparison.py): re-audit
  all seven archived complete Fuse configurations, all three volumes each.
  Verify archive sizes/hashes, metadata/TRD/trace identities, full stage
  boundaries and publication results. This is **existing complete playback
  evidence**, not seven new emulator runs.

The player and compressed streams are unchanged by this profiling work:
**0 instruction T-state delta, 0 stream-byte delta**. No new TRDs were built.
Saved reports: [frame CPU](current_frame_profile.json),
[packet CPU](packet_cpu_profile.json), [combined results](player_comparison_profile.json).

## Current frame CPU profile

The fresh direct-HL execution totals **1,017,445,008 T**. Restoring the
proven motion-entry delta gives the retained disk player's frame-component
baseline, **1,018,049,241 T**. These totals exclude packet acquisition, ZX0,
audio/IRQ, disk/ROM, ULA and waiting.

| Phase | CPU T-states | Share of frame fixture |
|---|---:|---:|
| Compact reconstruction | 610,026,283 | 59.96% |
| Native screen output | 337,654,716 | 33.19% |
| Compiled metadata | 63,590,055 | 6.25% |
| Attribute-group preparation | 4,569,974 | 0.45% |
| Frame handoff | 1,603,980 | 0.16% |

Mean **241,043.59 T/frame**, p99 **363,553 T**, maximum **378,448 T**.
Under the project's nominal clock conversion these are 67.99 / 102.54 /
106.74 ms. No frame's isolated CPU fixture exceeds 425448 T, but that does
not prove playback: the maximum leaves only about 13.26 ms for all excluded
work, and sector/input bursts can be much larger.

Largest detailed regions (each is a subset of the phases above):

| Region | CPU T-states | Share of frame fixture | Code to inspect |
|---|---:|---:|---|
| Dense-band pixel conversion/writes | 136,520,064 | 13.42% | `cell_screen_z80.py`, `pixel()` / `dense_row` |
| Huffman symbol decode | 125,825,146 | 12.37% | `prefix_huffman_z80.py`, lookahead patches |
| Motion-cache filling | 112,146,097 | 11.02% | `causal_tile_z80.py`, `cache_copy` / `cache_pair` |
| Sparse-cell pixel conversion/writes | 80,589,740 | 7.92% | `cell_screen_z80.py`, `draw_cell` |
| Patch dispatch/control | 80,521,194 | 7.91% | `causal_tile_z80.py`, patch loop |
| No-op handling | 72,729,621 | 7.15% | reconstruction no-op loop |
| Motion reconstruction | 66,279,424 | 6.51% | motion phase handlers |

The largest single aggregated instruction group is motion-cache `LDI`:
**5,689,088 byte copies, 91,025,408 T**. This is useful required cache work
under the current design, not proof those bytes can safely be omitted.
The existing [half-width/pair-copy experiment](CACHE_COLUMNS_ru.md) already
examines this tradeoff; pair copying is active, while narrower cache masks
alter stream cost and need a separate current-budget comparison.

Remaining indexed memory loads in the frame fixture total only
**9,586,716 T (0.94%)**, all in Huffman: 407820 `LD E,(IX+1)`, 59071
`LD B,(IX+0)` and 37673 `LD L,(IX+0)`. This subtotal excludes other index
register bookkeeping. Replacing these loads can help, but their entire
current cost is already under 1% of frame CPU; pointer setup and preservation
must still be paid. Dense/sparse pixel handling together costs
**217,109,804 T**, over twenty times that indexed-load subtotal.

## Packet acquisition: where ZX0 time goes

The independent demand-only packet fixture totals **340,877,648 T**:

| Component | CPU T-states | Share of this fixture |
|---|---:|---:|
| ZX0 coroutine and decoder | 190,422,888 | 55.86% |
| Compiled frame metadata | 63,590,055 | 18.65% |
| Packet copying, including its dispatch | 50,177,846 | 14.72% |
| Queue control | 11,366,156 | 3.33% |
| Compressed-input producer | 5,521,100 | 1.62% |
| Disk adapter instructions, ROM mocked | 4,937,743 | 1.45% |
| Paging | 4,923,656 | 1.44% |
| Packet parser | 4,190,429 | 1.23% |
| Other hooks, service guards and bridges | 5,747,775 | 1.69% |

**Metadata is also counted in the frame fixture. Do not add the two totals
without removing that overlap.** Even after removing it, their sum is a
component-workload comparison, not an integrated playback CPU measurement.
The frozen clock permits only the initial audio refill; it does not measure
the complete soundtrack's producer or interrupt cost.

The histogram separates the actual `LDIR` instructions inside ZX0:

| Retained code site | Bytes copied | Runs | Mean bytes/run | CPU T |
|---|---:|---:|---:|---:|
| Match copy, 8E95h | 1,768,062 | 412,126 | 4.2901 | 35,068,672 |
| Literal copy, 8EBDh | 1,196,949 | 249,029 | 4.8065 | 23,890,784 |

All **2,965,011 decoded bytes** are accounted for. `LDIR` itself takes
**58,959,456 T (30.96% of ZX0)**; other decoder instructions take
**131,463,432 T (69.04%)**. These include lengths/offsets, bit handling,
copy setup, boundaries and coroutine suspension. Short runs make their
per-run cost important. A blanket long-copy unroller is not justified by
these averages; measure the length distribution and charge short-run setup.
The run counts use the 16-T final / 21-T repeating `LDIR` iterations in
[Zilog UM008011-0816, printed pages 132–133](https://www.zilog.com/docs/z80/um0080.pdf).

The packet-copy path already uses unrolled `LDI`: its actual transfers cost
**47,440,176 T = 16 × 2,965,011 bytes**. The remaining **2,737,670 T** is
dispatch/address work inside the copy region; common bridge/paging costs
are separate. Removing that copy has a measurable gross ceiling, but is
not automatically possible: packet source slots and Huffman tables compete
for the paged C000h window. Charge every replacement paging operation and
preserve slot/history ownership. See the prior
[unrolled-copy experiment](UNROLLED_STREAM_COPY_ru.md).

The all-block producer benchmark's **189,573,555 ZX0 T** is a different
workload. This reader executes different demand boundaries and measures
**849,333 more ZX0 T**. Neither value substitutes for real integrated
producer scheduling.

## Elapsed time in the retained disk player

Window: first to last actual screen publication on each disk, summed
**1,812,975,750 elapsed T**. The following bins are disjoint. Disk service
is removed from every other bin. Suspended packet calls in other variants
are also separated from intervening reconstruction/drawing.

| Elapsed context | T-states | Share |
|---|---:|---:|
| Compact frame reconstruction | 647,013,761 | 35.69% |
| Native screen output | 345,752,714 | 19.07% |
| Disk/seek service | 214,783,127 | 11.85% |
| Packet transfer outside disk/other frame stages | 180,180,689 | 9.94% |
| Metadata | 78,462,297 | 4.33% |
| Outside the instrumented stages | 346,783,162 | 19.13% |

These are **elapsed contexts, not instruction CPU costs**. IRQ and ULA time
remain included. The final row contains background production, audio hooks,
scheduling and waits; it must not be described as entirely idle or wasted
time. The trace has no paired entry/exit coverage to isolate all those costs.
Disk service combines ROM execution, drive emulation, IRQ and contention;
these measurements do not artificially separate its physical component.

All captured video read/seek intervals, including prefill outside that
publication window, total **225,773,126 T**. Do not add this to the table.
Individual reads peak at **155,756 T, about 43.9 ms**. Packet transfer peaks
at **1,884,022 elapsed T, about 531.4 ms**; it can require several reads,
ZX0 and copying. One packet stall can therefore span several 120-ms deadlines.
Milliseconds use the project's nominal 50-Hz, 70908-T-per-field convention.

The [decoded-reserve profile](LATE_RESERVOIR.md) explains sustained late runs:
median ready reserve is **30092 / 9263 / 4 bytes**. Packet starts with at most
six bytes ready number **104 / 509 / 757**. In the worst 32-frame windows:

| Global frames, exclusive end | Foreground elapsed T | Transfer T, including disk | Excess over 32 × 425448 T |
|---|---:|---:|---:|
| 642..674 | 17,884,587 | 7,190,928 | 4,270,251 |
| 2870..2902 | 23,937,005 | 12,706,585 | 10,322,669 |
| 3887..3919 | 22,918,192 | 11,643,401 | 9,303,856 |

The last two windows start every packet with no completed slot and at most
six decoded bytes ready. Average CPU or average fps alone hides this failure.

## Comparison of complete disk configurations

Each row covers all 4221 frames. All retain exact AY at 50 Hz with zero
underruns; **every row fails both the nominal and fallback video gates**.
Video bytes exclude the separately resident soundtrack/bootstrap.

| Configuration | Video bytes | Video reads | Late frames | Bad 5..7-field intervals | Maximum lateness by disk, fields |
|---|---:|---:|---:|---:|---|
| Retained complete-input ZX0 | 1,818,909 | 7106 | 1321 | 783 | 64 / 260 / 265 |
| Sector-streamed ZX0 | 1,818,909 | 7106 | 1457 | 943 | 63 / 306 / 345 |
| Cost-selected fast fragments | 1,857,591 | 7257 | 1237 | 747 | 72 / 247 / 238 |
| CPU-selected native masks | 1,846,953 | 7216 | 1268 | 761 | 63 / 262 / 261 |
| Tagged no-op runs | 1,862,543 | 7278 | 1315 | 786 | 67 / 259 / 259 |
| Globally resumable parser | 1,818,909 | 7106 | 1337 | 797 | 64 / 266 / 271 |
| Separate optional consumer | 1,818,909 | 7106 | 1329 | 790 | 64 / 263 / 269 |

The retained player recovers **21 of 22 late runs** (3/15/3 by volume).
Disk 2's final run, local frames 1238..1296, remains late at EOF. The combined
report preserves every missed global frame, each late run and its recovery,
actual OUT deviation, and the archived audio/fallback verdicts for every variant.

Fast fragments give the lowest late-frame count in this comparison, but add
151 reads and worsen disk 1's peak. Their full publication span improves by
only 921,810 T despite a 17,663,254-T saving in separately measured CPU
components. Sector-streaming adds 20,050,855 producer/ZX0 T and worsens
cadence. Do not select a default solely from an isolated CPU subtotal.

## Priorities supported by this profile

1. **ZX0 short-run and input-delivery cost.** Profile length/offset dispatch
   and demand-boundary checks first, preserving the current stream. For a
   separate encoder experiment, remeasure short-match removal against the
   current 82/81/82-sector headroom; charge extra reads and verify native
   coroutine execution plus full deadlines. The already rejected streamed
   decoder and global/optional parser variants are comparison points.
2. **Native pixel conversion and reconstruction hot paths.** Use the exact
   instruction/stage histogram, with expensive-scene windows as well as
   whole-movie totals. Cache filling, Huffman and patch control merit more
   attention than a one-off motion-entry transfer. Preserve compact n-1
   prediction and native-screen n-2 masks. Existing cache unrolling,
   selective cache coverage and black-border omission are already active.
3. **Avoid copies only with a complete bank/ownership design.** The packet
   copy is substantial but smaller than ZX0. Compare any zero-copy design
   against its added bank switches, table access, guards and history
   lifetime. Do not reuse a previous disk's RAM as a requirement.
4. **Keep small register substitutions proportional to their benefit.**
   Direct HL' is verified at -604,233 T, 0.059352% of frame CPU. Remaining
   indexed loads need per-path measurements including pointer setup; do not
   infer a large overall improvement from the nominal cost of one opcode.
5. **Refine the unclassified elapsed bin in the next changed-player run.**
   Add non-mutating trace points for resident-audio service, background
   producer calls and wait entry/exit. The existing traces cannot provide
   exact separate totals for these. Do not call all 19.13% idle or CPU loss.

No new optimization or release is accepted by this profiling task. Full
Fuse comparisons sample 80 native pixels per frame; the CPU fixture checks
every compact/native byte. Physical drives remain unmeasured.

## Reproduction

Saved-data audit uses the standard library and archived Git/LFS evidence:

```powershell
python toolkit/profile_player_comparison.py --check
```

Fresh CPU replay requires the same NumPy/OpenCV-capable toolkit environment
as previous player benchmarks and the source fixtures. Defaults point to
the locally retained worktree input/build directories. Supply alternatives
with `--raw-directory`, `--states` and `--directory` as appropriate. Hashes
pin the frame sources/states, previous reports and actual baseline TRDs.

```powershell
python toolkit/profile_current_frame.py --output .tmp/current-frame-replay.json
python toolkit/profile_packet_cpu.py --output .tmp/packet-replay.json
```

Both refuse to overwrite evidence. `--limit N` is a smoke run and cannot
pass the complete profile gate. Prefix CPU counts also match the earlier
256-packet-per-volume retained-reader fixture. The comparison auditor
checks all per-frame/stage/instruction sums and identical metadata costs
across the two fresh fixtures. Per-address histograms remain in the full
JSON reports; the combined report ranks instruction groups across addresses.
