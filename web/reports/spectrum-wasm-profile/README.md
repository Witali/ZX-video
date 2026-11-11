# Expedition 33 browser CPU and device profile

Measured on 2026-11-11 in the built-in Chromium browser using commit
`17f84fdf` and the committed Expedition 33 TRD. The preceding 45-second
WebGL and AudioWorklet comparison measured 2,800.7 ms of JS wake work and
2,787.7 ms of WASM wake work in one pair.
[Previous live run](../spectrum-wasm/browser.json) ·
[New timing samples and traces](measurements.json).

## CPU and AY

The diagnostic page runs the actual CPU, ROM, TRD controller, AY and field
clock with 4-ms virtual host wakes and a null renderer. Every run executes
the first 48 seconds of the demo. The 0–24 s window includes boot, while the
24–48 s window plays Lumiere. The median of five rotated rounds for each
variant is shown below. After warmup, every variant checks 2,400 fields and
the same sequence of guest AY data writes. The full and no-DSP cases also
emit the same count of 4,134 stereo packets.

The first fixture attempt restored the browser clock before the simulated
run. Its field-count assertion failed at one field. The harness was fixed
to keep virtual time through the entire run, and no timing from the failed
attempt entered the comparison.

| Audio work enabled | JS boot, ms | WASM boot, ms | JS playing, ms | WASM playing, ms |
| --- | ---: | ---: | ---: | ---: |
| Full stereo | 1,571.2 | 1,331.3 | 1,313.0 | 1,108.1 |
| Sample queue, mixer and packets | 988.2 | 749.8 | 814.5 | 581.2 |
| Sample queue with empty callbacks | 937.8 | 692.1 | 737.4 | 503.2 |
| No sample callbacks | 770.4 | 324.9 | 656.6 | 222.3 |

In the playing window, differences between the WASM medians attribute
about **527 ms (48%)** to Ayumi synthesis and filtering, **78 ms (7%)** to
mixing and packet production, and **281 ms (25%)** to servicing the sample
queue and running the CPU up to those deadlines. The remaining **222 ms**
include CPU execution, keyboard, field events and wake overhead. These
differences are estimates from separate runs and include effects on
execution paths and JIT optimization.

With sample callbacks omitted, the WASM machine spends 434 ms less than JS
in the playing window. With empty sample callbacks restored, WASM spends
281 ms servicing them versus 81 ms for JS. A separate instrumented WASM
pass observes **1,065,647** dispatches in the playing window with the
sample queue and **8,447** without it. Each WASM dispatch crosses into JS.
At 44.1 kHz, deadlines are about 80 T apart, and fused execution requires at
least 32 T before the next deadline. This makes shorter slices and extra
single-T work part of the measured cost alongside the calls themselves.
Full headless WASM takes about 16% less time in both windows. Differences in
the earlier single live pair cannot be attributed to one component from
these measurements.

## Disk and renderer

The instrumented WASM boot window invokes **395,056** disk timer callbacks
and **1,068,308** disk port handlers. Direct timing totals about **157 ms**
in that run. With sample callbacks omitted, the counts match and their
timings total about **143 ms**. The probe measures the controller handler
bodies and includes instrumentation overhead. Time inside the CPU polling
loop, JS/WASM port transitions and shared scheduler is outside that total.
The same handlers are invoked **zero times** in the 24–48 s music window.
Moving the disk model could reduce host work during sector reads, while
guest-visible rotation and transfer timing still govern startup.

A new sequential live WebGL/AudioWorklet pair spent **1,517.5 ms JS**
and **1,697.4 ms WASM** in boot-window wakes, followed by **1,493.3 ms JS**
and **1,342.9 ms WASM** in playing-window wakes. The phases nearly
cancel in the aggregate, leaving WASM about 1% higher overall in this
pair. The WASM boot result differs in direction from the controlled
null-renderer comparison. This one pair does not establish a stable
live boot penalty or isolate its cause. The playing-window CPU-side
WebGL submission methods took about **18 ms JS** and **22 ms WASM**
over 1,200 fields. `drawData` is already included in wake time.
GPU execution, OS audio and AudioWorklet thread time fall outside these
main-thread totals.

## Ayumi C/WASM experiment

Compiled the [upstream C Ayumi](https://github.com/true-grue/ayumi/tree/07c08b4874c359169e4a028edf73f046d8b763e2)
as a standalone WASM module, using scalar double arithmetic with FP
contraction disabled. Both variants render the same tone, envelope, noise
and stereo pan setup and write stereo doubles. All 65,536 checked stereo
frames matched bit for bit. Five alternating rounds of 1,572,864 frames
each produced these medians:

| Synthesizer and call size | Host time, ms |
| --- | ---: |
| Current JS Ayumi | 675.9 |
| C/WASM, 1 frame per call | 396.7 |
| C/WASM, 512 frames per call | 382.9 |

C/WASM in blocks took 43% less time in the isolated DSP probe. The
priority for a player implementation is AY with block generation and
T-state-stamped AY/beeper writes. Process writes in chronological order
within each block and preserve sample phase, port read behavior and PCM
delivery. This can remove the per-sample JS dispatch in addition to
accelerating the synthesis. The figures above describe the separate
components; an integrated candidate needs its own PCM and browser timing
checks. Keep disk work as a separate boot-time investigation.

## Reproduce

Build the normal site and copy the diagnostic page to the build directory.
Run both buttons in the built-in browser. Run the timing experiments
serially and keep the page active during the live probe. Append `?cpu=js`
to the fixture URL to time the live JavaScript backend.

```powershell
node web/tools/build.mjs .tmp/web-site C:/path/to/checkout-with-lfs-images
Copy-Item web/tools/spectrum-wasm-profile.html .tmp/web-site/
node web/tools/serve.mjs .tmp/web-site 4208
```

For the Ayumi probe, put `ayumi.c`, `ayumi.h` and `LICENSE` from the pinned
upstream revision in `.tmp/ayumi-upstream/`. Their source SHA-256 values
are `8824bc343726aa9dc7e4172b14f0e9a0a06ed3f21766277ffb9686b07f19401d`
and `506e3b75d8269d670d74f75115d3b385ad0f1c232bc797391bd97cc074f17099`
for C and header respectively. Use the same initialized SDK as the
[CPU prototype](../spectrum-wasm/README.md).

```powershell
$sdk = 'C:/path/to/emsdk/upstream'
& "$sdk/bin/clang.exe" --target=wasm32-unknown-unknown `
  "--sysroot=$sdk/emscripten/cache/sysroot" -O3 -flto -ffp-contract=off `
  -fno-math-errno -ffreestanding -nostdlib -I.tmp/ayumi-upstream `
  '-Wl,--no-entry,--strip-all,--export-memory' `
  .tmp/ayumi-upstream/ayumi.c web/tools/ayumi-wasm-probe.c `
  -o .tmp/web-site/ayumi-probe.wasm
Copy-Item web/tools/ayumi-wasm-probe.html .tmp/web-site/
```

Open `ayumi-wasm-probe.html` on the same local server and select
**Compare synthesis**. The tested probe binary SHA-256 is
`56a3f43db453489388e42dab79bbae2b9d36890daec0150aa722a33fd83df36e`.
