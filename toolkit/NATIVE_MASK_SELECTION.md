# Select sparse or full native bands using existing output costs

Date: 2026-09-27. Baseline: retained player `a84451d`, original packets,
resident AY and 15872-byte in-place ZX0 blocks. This is a separate experiment
from the [cost-selected fragments](RESIDENT_FRAGMENTS.md) at `fb9c5ac`.

This revisits the earlier [Gray-optimal mask probe](GRAY_CELL_OUTPUT_ru.md),
whose 8192-byte muxed ZX0 stream grew 28,259 bytes to 1,960,688 and was
rejected on capacity. That attempt projected output CPU but did not build
or time a complete disk set. The current resident-audio/larger-slot layout
has different capacity and delivery costs, so a full new measurement is
needed. The per-frame formula projections are checked against that report,
with the four later-volume cold maps excluded from the optimization.

Scope: all 4221 authorized frames, unchanged resolution, pixel values, AY
records and 25/3-fps deadlines. Every disk must boot independently. No new
Z80 opcode, runtime dispatch test, buffer or table is introduced.

## Selection and exact costs

The old encoder marks all 32 cells of a native eight-pixel band dirty once
18 cells change relative to frame n-2. The current Gray-order sparse
renderer is cheaper than the earlier implementation. This experiment
selects either the exact changed-cell map or the existing full-band path
on the host, using current instruction costs:

```text
full-band variable cost    = 5853 + 4 * band_parity T
partial-band variable cost = 261 * marked_cells - 136 * zero_groups T
```

Shared per-band dispatch, frame setup, attributes and paging cancel in the
difference. Probe rows use [`cell_screen_z80.expected_tstates`](cell_screen_z80.py)
with the same fixed attribute-copy cost on each side solely to calculate the
mask delta. The player uses grouped attributes; the full native benchmark
measures its actual absolute costs. Grouped attribute work is unchanged.
These formulas exclude IRQ/ULA, ZX0, queue/packet work,
ROM and physical disk acquisition. Negative variable cost for an empty
partial band is a saving relative to the shared term, not negative execution.

For 18..22 marked cells, the exact partial map is faster. A full band wins
at 23 or more, including the possible zero-group cases and both parities.
Selection nevertheless compares the actual formula rather than assuming
that an old threshold remains correct after future renderer changes.

[The rewriter](native_mask_selection.py) first reproduces every baseline
map from the original states. It modifies only the 80-byte native-map field
inside each packet. Restoring those bytes reproduces the complete original
FAP3 hash; vector data, Huffman codes, literals, masks for reconstruction,
AY, lengths and headers are unchanged. Later volumes keep their first two
stored maps, which the existing independent bootstrap replaces with FF.
All n-2 changed bytes are checked by host replay before compression.

## Verification and measurements

The three focused tests cover every population of the four eight-cell
groups at both parities, execute native output around the 18..24-cell
break-even and n-2 clearing, and verify packet inversion/cold-start maps.
They pass. The complete frame CPU run compares every compact byte and both
complete native screens for all 4221 frames. Actual instruction-table
counts are **1,018,049,241 -> 1,011,675,434 T (-6,373,807)**. Every frame's
delta matches its independent mask prediction and no frame-stage case gets
slower. Formula savings alone do not establish playback or a release.

All raw packet lengths stay unchanged. There are **9126 changed bands in
2230 frames**. The output formula predicts **6,373,807 T** saved; the old
whole-movie projection was 6,383,320 T, before the four later-volume cold maps.
All **188 blocks (62/62/64)** round-trip and meet actual sector-aligned
in-place overlap constraints.

| Volume | ZX0 bytes, old -> new | Occupied sectors | Free sectors |
|---|---:|---:|---:|
| 1 | 606434 -> 615389 | 2495 | 49 |
| 2 | 606524 -> 616574 | 2506 | 38 |
| 3 | 605951 -> 614990 | 2496 | 48 |

Final video is **1,818,909 -> 1,846,953 bytes (+28,044)**. Video reads are
**7106 -> 7216 (+110)**. Total occupied sectors are **7387 -> 7497 (+110)**;
actual bootstrap/placement differences redistribute the free space across
volumes relative to the probe estimate. All independent dirty-RAM boots,
initial frames, immutable AY and both disk handoffs pass with mocked ROM.

The complete producer/ZX0 execution checks all bytes, read order, carry
copies, protected banks and instruction histograms. Producer cost is
**11,831,304 -> 11,982,764 T (+151,460)**; ZX0 cost is
**189,573,555 -> 191,196,564 T (+1,623,009)**. Together:
**201,404,859 -> 203,179,328 T (+1,774,469)**. Carry copies fall by one sector,
**96,256 -> 96,000 bytes**. This uses mocked ROM and a frozen service clock;
queue/AY/IRQ/ULA/ROM and physical disk elapsed time are separate.

Frame stages plus producer/ZX0 cost **1,219,454,100 -> 1,214,854,762 T**:
**4,599,338 T saved, about 0.377%** of these measured components. This is
not the complete player CPU total or the wall-clock playback improvement.

The 481 frames whose baseline elapsed foreground work exceeds six fields
save **1,247,998 frame-stage T**; the other 3740 save **5,125,809 T**. The
new counts of individually over-budget work intervals are **41/165/268 =
474**, versus 481. This grouping includes disk/IRQ/ULA in the baseline work
and does not claim that all of those frames are CPU-bound.

All three Fuse volumes reach EOF with **25326 exact AY records at 50 Hz**,
zero underruns, missing/duplicate IRQ fields or read retries. Actual screen
publication times are measured separately from field counters.

| Volume | Late frames, old -> new | Invalid intervals, old -> new | Maximum lateness, fields |
|---|---:|---:|---:|
| 1 | 90 -> 87 | 43 -> 41 | 64 -> 63 |
| 2 | 465 -> 420 | 249 -> 238 | 260 -> 262 |
| 3 | 766 -> 761 | 491 -> 482 | 265 -> 261 |

Total late frames: **1321 -> 1268 (-53)**. Invalid 5..7-field intervals:
**783 -> 761 (-22)**. Both video timing gates still fail. Initial disk/IRQ
phases are not matched, and Fuse checks 80 pixel samples/frame rather than
every native pixel. A physical drive is not tested.

Maximum actual deviations are **4,467,209 / 18,577,896 / 18,506,994 T**.
Recovered runs are **2/12/4**. Volumes 1/3 recover all runs; volume 2 retains
an unrecovered tail at local frames **1239..1296**. Publication spans are
**690,502,104 / 569,958,504 / 552,656,952 T**, totaling **1,813,117,560 T**:
**141,810 T more** than the baseline. Average fps on volumes 1/3 returns to
25/3 after recovery; it must not be mistaken for smooth frame delivery.

## Decision and remaining delivery work

**Do not adopt the global CPU-optimal masks as the default.** They spend
110 extra video sectors for a 0.377% saving in measured CPU components.
Although late-frame counts improve, total publication span and volume 2's
maximum deviation worsen, with neither video timing gate met. Keep the
roomier `a84451d` comparison and the separate fast-fragment candidate.
The old capacity rejection is superseded by actual fitting disks; the new
full delivery result is the reason to keep this policy experimental.

The archive auditor also locates optional packet reads that cross a screen
publication while the following compact frame is already prepared. It
requires that the following native draw starts only after the transfer
ends. In the baseline there are **64 such calls**, 16 followed by a late
frame; the largest transfer tail after publication is **1,542,815 elapsed T**.
These are observed blocking intervals, not estimated removable CPU time.
The native-mask run contains 63 such calls, 12 followed by a late frame,
with a maximum tail of 1,519,170 T. All event rows are retained in the summary.

A next experiment can make optional packet acquisition resumable at safe
sector/ZX0-quantum/copy boundaries, yielding when publication frees the next
screen. Preserve partial header/body state, queue ownership and the original
six-field deadlines. Mandatory reads must finish the same packet exactly.
This differs from the old guards that rejected read-ahead before it started,
and from adding a guard to every ZX0 input operation. Measure its complete
overhead and all EOF/IRQ/slot-crossing paths before full Fuse evaluation;
the trace observations alone do not establish a speedup.

## Reproduction

Run from the existing `streaming-zx0-player` worktree, with the project Python
dependencies available. The retained generic frame and delivery benchmarks
are reused with explicit native-mask input/output reports; no fragment
selection is performed by those benchmarks.

```powershell
$env:PYTHONPATH='toolkit;C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/python_packages'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest toolkit/test_native_mask_selection.py -v
python toolkit/probe_native_mask_selection.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --baseline-build toolkit/inplace_keepalive_build.json --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/native-mask-probe --report toolkit/native_mask_selection_probe.json --read-cache .tmp/inplace-keepalive-player/zx0
python toolkit/benchmark_resident_fragments.py --raw-directory .tmp/native-mask-probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --probe toolkit/native_mask_selection_probe.json --output toolkit/native_mask_selection_cpu.json
python toolkit/build_native_mask_selection.py --baseline-build toolkit/inplace_keepalive_build.json --probe toolkit/native_mask_selection_probe.json --raw-directory .tmp/native-mask-probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/native-mask-player --report toolkit/native_mask_selection_build.json --read-cache .tmp/native-mask-probe/zx0 --read-cache .tmp/inplace-keepalive-player/zx0
python toolkit/benchmark_resident_delivery.py --directory .tmp/native-mask-player --build toolkit/native_mask_selection_build.json --output toolkit/native_mask_selection_delivery_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/native-mask-player --raw-directory .tmp/native-mask-probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/native-mask-fuse --trace-pipeline --trace-fields
python toolkit/summarize_native_mask_selection.py --archive-directory .tmp/native-mask-player --trace-directory .tmp/native-mask-fuse --source-directory .tmp/native-mask-probe --baseline-raw-directory ../volume-huffman/.tmp/probe --write
python toolkit/summarize_native_mask_selection.py
```

Experimental TRDs stay in `.tmp/native-mask-player`. Release images and
generic-converter defaults are not changed by this experiment. Saved evidence
will distinguish actual capacity, deterministic CPU, full emulated delivery,
and any remaining physical-hardware or pixel-comparison limitations.

The completed [archive audit](summarize_native_mask_selection.py) passes.
It checks **81 gzip files / 16,294,279 compressed bytes**, independently
replays every source pixel and AY record, reverses every map replacement to
the original raw hashes, recomputes selection/formulas and verifies their
agreement with every measured native frame. It also reconstructs runtime
streams including cold maps and verifies complete publication/AY/read traces.
The [saved summary](native_mask_selection_summary.json) pins source and
report hashes. Successful evidence auditing does not mean the video gates pass.
