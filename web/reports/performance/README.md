# Allocation-only AY synthesis optimization

Measured on 2026-11-02 against `b120b13533c07e29766527e55180010a5a6a1d35`.
The pinned ZX-Dream CPU, bus, clock, floppy and display core remains
`75fe5555411d60e68ccc927d734b06dab5b25b129b379358d6a8d62f0af7b874`.

## Change and tradeoff

Ayumi's stereo 192-tap FIR ring has 23 positions. Previously `process()`
called `Float64Array.subarray()` twice per output sample. Cache the same
23 aliasing windows per channel at construction and reuse them. The two
sample buffers, every arithmetic operation and its order, oscillator clocks,
interpolator, FIR, DC filter and output precision stay unchanged. This
retains 46 view objects and two small arrays per chip, without additional
sample storage. At 44.1 kHz it removes 5,292,000 `subarray()` calls per minute
per chip. The dynamic probe observes 2000 calls becoming zero per 1000
stereo frames; it does not measure the engine's actual heap allocations or
garbage-collector pauses.

The [patch generator](../../tools/patch-ayumi.mjs) rejects changed upstream
anchors. [Provenance](../../vendor/provenance.json) records both the original
Ayumi hash `bd189a81…483326d` and patched hash `8a42f526…aca710c`.

## Measurements

Five before/after pairs alternate order. Node trials use fresh processes;
each synthesis trial warms up 100,000 frames before timing 3,000,000 stereo
frames. Every pair improves in these runs. Values are median elapsed host
milliseconds, not emulated time.

| Workload | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Built-in Chromium, AY synthesis | 1532.4 | 1369.8 | 10.61% |
| Node 22.22.3, AY synthesis | 2096.4 | 1859.7 | 11.29% |
| Node, complete machine workload | 4450.2 | 4182.6 | 6.01% |

[Browser trials](browser-psg.json) and [Node trials](emulation-benchmark.json)
retain all samples. The machine workload cold-boots real ROMs and the
qualified music TRD `3ae7d156…3209e71`, then plays both 3.1-second excerpts,
covering 66.2 emulated seconds, Z80, disk, AY and NullRenderer display events.
Setup/parsing and output hashing are outside the timed region. It is not
an end-to-end browser rendering or GPU benchmark. Timing spread is visible
in the raw trials; these percentages are observations on this host.

The [initial Node CPU profile](profile.json) of the integration smoke
identified its per-sample statistics callback as 41.10% of self samples,
Ayumi process/decimate as another 17.02%, clock processing as 11.93%, and
PSG packet production as 7.85%. This diagnosed a diagnostics cost as well
as the synthesis cost: the benchmark captures packets and hashes them
after timing. Raw profiler paths remain local. No RAM/bus, task queue,
floppy or renderer optimization is claimed from this experiment.

## Correctness and limits

- [Differential synthesis](ayumi-correctness.json): 1,048,576 stereo frames
  (2,097,152 Float64 values) match bit for bit, with exact oscillator,
  interpolation, FIR and DC state. Four AY/YM and 44.1/48-kHz cases exercise
  all 16 hardware envelope shapes, zero/one/extreme periods, tone/noise,
  mixer/volume changes, pan, and live sample-rate/DAC reconfiguration.
- Every timed machine run asserts identical PCM hash, all 64 KiB of
  mapped memory, CPU state, PSG registers, disk state and emulated clock.
  An additional differential pair retains the full identical state in
  the Node report; its timing is excluded from the five-pair summary.
- [1356 pinned Fuse vectors](opcodes.json) pass registers, RAM, ports and
  instruction T-states, including the existing four independently
  hardware-adjusted repeat-flag expectations.
- [Shared-clock checks](clock.json) produce identical ULA/disk/audio event
  timelines under regular/irregular callbacks, host stalls, wall-clock
  jumps and pause/resume. [Integration smoke](integration.json) matches
  the baseline report exactly, with real-ROM/TRD cold autoplay, stereo
  song excerpts and preserved RAM/PC across a disk swap. Existing keyboard
  and all eight RC filter checks also pass; [verification scope](verification.json).

The browser fixture checks final synthesis state, while the offline
differential checks every PCM value. No target Z80 instruction changes:
before/after player paths have identical T-state counts (delta 0 T).
Physical rotational search, DRQ deadlines, ULA fields, audio sample count
and real-time pacing are unchanged. Known disk lost-data/timing limitations
of this core remain; this is not a full-movie release, physical WD1793,
contention, chip, sound-card or perceptual qualification.

The first benchmark attempt stopped after synthesis because the upstream
common module replaced the Node ROM loader with its XHR implementation.
Restoring the local ROM loader after evaluation fixed the harness; partial
timings were discarded and the five complete pairs were rerun. A preview
port was already occupied, so the task server used another port. No
production emulator workaround was added for either setup issue.

## Reproduce

Use the pinned ZX-Dream checkout in `web/vendor/README.md`; preserve its
original `source/js/ayumi.js` byte for byte as `.tmp/baseline-ayumi.js`.
Run from the repository root after building the static site with all LFS
TRDs materialized. In a sparse worktree, the optional build disk source
must contain the exact images committed at that worktree's HEAD.

```powershell
node web/tools/build.mjs .tmp/web-site
node web/tools/check-ayumi-views.mjs .tmp/baseline-ayumi.js web/vendor/ayumi.js .tmp/ayumi-correctness.json
node web/tools/bench-emulation.mjs .tmp/baseline-ayumi.js .tmp/web-site 5 .tmp/emulation-benchmark.json
node web/tools/check-opcodes.mjs .tmp/fuse-test-source/z80/tests .tmp/opcodes.json
node web/tools/check-clock.mjs .tmp/clock.json
node web/tools/check-emulator.mjs .tmp/web-site .tmp/integration.json
node web/tools/check-keyboard.mjs
node web/tools/check-audio-filter.mjs
```

For the browser benchmark, copy `web/tools/ayumi-benchmark.html` into the
built site root, the original source beside it as `ayumi-baseline.js`,
and `web/vendor/ayumi.js` as `ayumi-candidate.js`. Serve the built site
using `web/tools/serve.mjs`, open the fixture in the built-in browser,
and press **Run benchmark**. Avoid concurrent CPU-heavy jobs when timing.
The fixture and baseline source are excluded from the Pages allowlist.
