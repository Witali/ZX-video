# Positional no-op runs in the current three-disk format

Date: 2026-09-27. Baseline: `a84451d`, the retained in-place ZX0 player with
resident AY and periodic drive maintenance. This is an optional experiment;
the generic converter, retained baseline and root release TRDs are unchanged.

## Format and implementation

The authorized 4221 frames, resolution, every pixel, all 25326 AY records,
volume ranges and independent cold checkpoints are preserved. AY stays in
its existing resident stream. Only the video-only packet vectors change.

The encoder replaces the first zero of an interior unchanged run with
`128 + length`, retaining the other vector positions and every mask byte.
The run never crosses a 16-tile stripe. First/last stripes remain untouched
because their existing static-edge marker already skips them. The measured
minimum is four tiles; lengths 1..16 remain valid decoder commands.
An independent inverse recovers the original video-only stream exactly.
The disk set has a new identity so an unpatched player cannot continue into it.

The [44-byte Z80 helper](tagged_noop_runs.py) occupies `7C31..7C5C`, below the
producer at `7D50`. The existing fast-fragment CALL is redirected to it.
Ordinary motion/intra tiles and untagged zero runs execute the old path.
The helper sends vectors 85..88 back to their existing fragment routine;
tags advance vectors, bitmap masks, target and tile count in one operation.
It consumes the CALL return itself before jumping to the next tile/stripe.
No additional state or reserved stack is needed; each tagged run temporarily
uses one two-byte return in the existing stack reserve. Both alternate
register sets remain untouched. IRQ tests interrupt every executed run-path
instruction using the actual fast and slow AY/video handlers.

The earlier September 19 FAP5 experiment checked a tag before every nonzero
tile and used a different stream, scanner, block size and capacity budget.
Its rejection is retained in [the earlier report](VECTOR_RUNS_ru.md).
This attempt tests the changed dispatch and current budget explicitly.

## Absolute instruction costs

Counts are Z80 instruction-table T-states, from tile entry through the
branch to the next tile or stripe, excluding the destination instruction,
interrupts, ULA, ROM and physical disk time. The baseline includes the
accepted fast scanner and compact cursor. `k` is the run length.

| Path | Baseline | Tagged | Difference |
|---|---:|---:|---:|
| Run ending a stripe | `74*k + 192` | 308 | `116 - 74*k` |
| Run followed by a vector or correction | `74*k + 258` | 318 | `60 - 74*k` |
| Four tiles, stripe end | 488 | 308 | -180 |
| Sixteen tiles, stripe end | 1376 | 308 | -1068 |
| Existing fast fragment, extra dispatch | 0 | 17 | +17 |
| Existing fast-fragment CALL | 17 | 17 | 0 |

The 17-T dispatch is `CP 128; JP C,fast_fragment`. A first draft used
`OR A; JP P`, but the existing CPU verifier does not implement JP P. The
experiment switched to the supported carry test; no 14-T dispatch saving
is claimed. Boundary tests execute all 256 vector-page offsets, all run
lengths and following-vector/correction/end cases. Mixed frames exercise
the unchanged fragment modes and compare the exact predicted delta.

## Capacity, CPU and complete playback

The raw video packet length stays **2,965,011 bytes**. Marking 34,710 runs
skips 238,785 individual tile checks, but disrupts some outer ZX0 matches.
All **188 blocks** round-trip and satisfy the actual sector-aligned in-place
overlap constraints. Only the measured minimum of four was compressed;
other thresholds in the probe are CPU predictions, not capacity results.

| Volume | Frames | Baseline ZX0 bytes | Tagged bytes | Occupied sectors | Free sectors |
|---|---:|---:|---:|---:|---:|
| 1 | 1624 | 606434 | 624134 | 2537 | 7 |
| 2 | 1297 | 606524 | 619293 | 2512 | 32 |
| 3 | 1300 | 605951 | 619116 | 2512 | 32 |

Total stream: **1,818,909 -> 1,862,543 bytes (+43,634)**; runtime reads:
**7106 -> 7278 (+172)**. Bootstrap/layout effects also count: total occupied
sectors rise by 174. Dirty-RAM cold boots, the first complete native screen,
second compact frame and both disk-change transitions pass with mocked ROM.

The complete producer/ZX0 measurement uses the actual new disk starts and
the same frozen idle clock as the baseline. Every input/output byte and
protected bank is checked. Producer **11,831,304 -> 12,073,757 T (+242,453)**;
ZX0 **189,573,555 -> 195,686,709 T (+6,113,154)**. Combined transport cost:
**201,404,859 -> 207,760,466 T (+6,355,607)**. Both copy 96,256 carry bytes.
Instruction histograms are checked separately against the timing table.

Full frame-stage CPU execution checks every compact byte and both complete
native screens across all **4221 frames**. Every per-frame delta matches the
independent run-path calculation: **1,018,049,241 -> 1,004,328,597 T
(-13,720,644)**. Including the measured producer/ZX0 components gives
**1,219,454,100 -> 1,212,089,063 T (-7,365,037, about 0.604%)**. This sum
excludes queue control, AY/IRQ, ULA, ROM and disk elapsed time; it is not
a complete integrated-player CPU total or a claimed playback-rate gain.

The workload split explains why the aggregate saving is misleading. In the
baseline traces, **481 frames** have foreground work above six fields;
their frame-stage CPU total actually **increases by 173,339 T**, and 330
of them get slower. The other **3740 frames save 13,893,983 T**. Overall,
573 frames get slower. This grouping uses the baseline's elapsed work,
including disk/IRQ/ULA; it does not classify every long frame as CPU-bound.

All three Fuse runs reach EOF with exact AY records, zero underruns and zero
read retries. Each frame has 80 pixel samples; this is not an all-pixel Fuse
comparison or physical-drive test. Actual publication OUT timings are checked.

| Volume | Late frames, old -> new | Bad intervals, old -> new | Maximum lateness, fields | Recovered late runs |
|---|---:|---:|---:|---:|
| 1 | 90 -> 90 | 43 -> 44 | 64 -> 67 | 2 |
| 2 | 465 -> 465 | 249 -> 252 | 260 -> 259 | 10 |
| 3 | 766 -> 760 | 491 -> 490 | 265 -> 259 | 4 |

Maximum actual deviations are **4,750,839 / 18,365,172 / 18,365,173 T**.
Publication spans are **690,502,104 / 569,745,780 / 552,656,952 T**. The total
decreases by only **70,914 T**, approximately one 50-Hz field over the movie.
Nominal deadlines and the fallback allowance both fail. Initial disk/IRQ
phases are not matched, so the six fewer late frames are not an isolated
effect of the run helper. Full late-run recovery records remain in the trace.
Volumes 1/3 recover all late runs. Volume 2 still has an unrecovered tail
at local frames **1240..1296**. There are no missing or duplicate IRQ fields.

**Decision: do not adopt.** A very small nominal-deadline improvement costs
172 video sectors, reduces headroom substantially and adds three bad
intervals. Retain the roomier baseline. The next candidate should target
expensive frame work and measure final ZX0 bytes and full delivery together.

## Reproduction and evidence

Run from the existing `streaming-zx0-player` worktree. Source hashes pin the
authorized states and the three original volume streams. The saved reports
and [archive audit](summarize_tagged_noop_runs.py) preserve full evidence;
experimental images stay in `.tmp/tagged-noop-player`, outside the release set.

```powershell
$env:PYTHONPATH='toolkit;C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/python_packages'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest toolkit/test_tagged_noop_runs.py -v
python toolkit/probe_tagged_noop_runs.py --raw-directory ../volume-huffman/.tmp/probe --baseline-build toolkit/inplace_keepalive_build.json --output toolkit/tagged_noop_size.json --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --cache .tmp/tagged-noop-zx0 --read-cache .tmp/inplace-keepalive-player/zx0 --minimum 4
python toolkit/benchmark_tagged_noop_runs.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output toolkit/tagged_noop_cpu.json --minimum 4
python toolkit/build_tagged_noop_player.py --baseline-build toolkit/inplace_keepalive_build.json --size-report toolkit/tagged_noop_size.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/tagged-noop-player --report toolkit/tagged_noop_build.json --read-cache .tmp/tagged-noop-zx0 --read-cache .tmp/inplace-keepalive-player/zx0 --read-cache .tmp/inplace-slot-reload-player/zx0 --read-cache .tmp/inplace-zx0-cache
python toolkit/benchmark_tagged_noop_delivery.py --directory .tmp/tagged-noop-player --build toolkit/tagged_noop_build.json --output toolkit/tagged_noop_delivery_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/tagged-noop-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/tagged-noop-fuse --trace-pipeline --trace-fields
python toolkit/summarize_tagged_noop_runs.py --archive-directory .tmp/tagged-noop-player --trace-directory .tmp/tagged-noop-fuse --write
python toolkit/summarize_tagged_noop_runs.py
```

The first host probe correctly rejected a mismatch because it omitted the
two forced cold-screen maps on volumes 2/3; that fixture omission was fixed
before measuring compression. The first synthetic tests also needed their
explicit cache map contract and an unused legacy decoder region cleared
for the isolated IRQ test. Production installers still require that RAM to
be free, and the native/full-TRD tests use the actual layout.
The first archive audit also rejected a type mismatch in its FPS check:
metadata stores the exact rational string `25/3`. The audit now parses that
value as a rational number; neither the player nor the traces changed.
