# Decoded reserve through the long late runs

Date: 2026-09-27. Baseline: `a84451d`, complete independent playback of all
4221 frames and 25326 AY records. **Analysis of retained evidence; no new
player, compression or timing result.** Player instruction delta: 0 T.

## Method

[profile_late_reservoir.py](profile_late_reservoir.py) joins complete Fuse
packet/publication traces with exact video-only packet lengths and ZX0 block
boundaries. At every packet start, completed blocks come from `blocks_left`;
the active decoder contributes its produced prefix only in phase 2. The
consumer's absolute byte position independently comes from packet lengths.
All 4221 observations must agree with `count`, `position`, slot ownership
and the **47616-byte** capacity. Fully decoded packets include the requested
packet if it already fits; this is not a count of prepared/native frames.

The archived optional-consumer images supply byte-identical compressed video;
their image hashes and the retained baseline's video hashes are checked.
Timing and queue observations come exclusively from the retained baseline.
No result from the rejected optional scheduler is substituted into this run.
The parser uses the resident video's recorded **288-byte minimum**, not the
older muxed packet's 294-byte minimum; the first analysis attempt stopped
on that distinction before producing a report.

The script reuses the disjoint-stage analyzer only for this original,
non-suspending packet reader. Transfer, metadata, preparation and drawing
durations include IRQ/ULA. Disk-service intervals are intersections within
those durations and must not be added again. Deterministic frame CPU comes
from the saved complete two-byte-Huffman execution and remains separate.
Frame intervals and per-block pressure are saved in
[late_reservoir_profile.json](late_reservoir_profile.json).

## Measured reserve

| Volume | Median decoded bytes at packet start | Median complete queued packets | Starts without a complete slot | Starts with at most 6 decoded bytes |
|---|---:|---:|---:|---:|
| 1, 1624 frames | 30092 | 50 | 154 | 104 |
| 2, 1297 frames | 9263 | 11 | 577 | 509 |
| 3, 1300 frames | 4 | 0 | 801 | 757 |

All volumes begin with **47616 bytes** decoded. Capacity is real, but it is
not sustained during difficult scenes. The final volume spends more than
half its packet starts with almost no decoded reserve.

## Worst 32-frame work windows

Indices are global, zero-based, with an exclusive end. Each 32-frame window
has a nominal budget of **13,614,336 T**. These sums describe work assigned
to frames, not exact publication lateness: the pipeline starts some work
before the window and can finish it afterward.

| Frames | Total foreground elapsed T | Transfer T | Disk service inside transfer T | Metadata + prepare + draw T | Excess over nominal work budget T |
|---|---:|---:|---:|---:|---:|
| 642..674 | 17884587 | 7190928 | 2667757 | 10693659 | 4270251 |
| 2870..2902 | 23937005 | 12706585 | 4877724 | 11230420 | 10322669 |
| 3887..3919 | 22918192 | 11643401 | 4886539 | 11274791 | 9303856 |

The last two windows request **63452 / 52483 bytes**. All their packet
starts have zero completed slots and at most **6 decoded bytes** available.
Preparation and output fit the aggregate nominal budget in those windows;
acquisition/decompression/copying pushes total delivery over it. The residual
transfer time is not pure ZX0 CPU: it includes queue/copy code, IRQ/ULA and
other work, so it cannot all be claimed as a decoder saving.

The baseline's long final-volume late run starts at frame 3519; its first
maximum of **265 fields** occurs at frame 4001. Through that point it requests
**453998 bytes**, with **481 of 483** packet starts lacking a completed slot.
Transfer totals **85,111,485 elapsed T**, including **34,281,229 T** of disk
service. This is sustained depletion, not just one unlucky sector read.

## Sensitivity and next decision

A deliberately optimistic two-stage projection removes all transfer and
control work and freezes measured metadata/prepare/draw durations. It has
zero late frames on all three volumes. **This is not a proven timing bound:**
IRQ/ULA phases would change, data availability is impossible as modeled,
and the proposed schedule has not been executed. It only motivates examining
the delivery subsystem before making another small register substitution.

Next measure faster **ZX0 tokenizations** under the roomier resident layout.
Replacing selected short matches with literal runs keeps the existing decoder
and all pixels/AY unchanged but increases storage. Earlier adaptive tests had
only **275/58/746 spare stream bytes**; the current disks have **82/81/82 free
sectors** before accounting for new bootstrap placement. That materially
changes the experiment. Check each candidate's native coroutine cost and
in-place overlap at every sector alignment, then include added sector service
in selection and measure the actual selected producer and full playback.
Do not equate minimum decoder CPU with minimum delivery time.

## Reproduce

With the recorded Python dependencies available, no emulator or source movie
is needed for this saved-evidence analysis:

```powershell
python toolkit/profile_late_reservoir.py
```

Use `--write` to regenerate the report. Reference/source hashes and all
queue-position assertions are checked on each run. Both video timing gates
remain failed; release images and converter defaults are unchanged.
