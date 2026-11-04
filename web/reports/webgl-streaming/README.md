# WebGL vertex streaming

Measured on 2026-11-04 against `1cabface8c3c801fd587f5de0a7807adfbd7157e`.
This is a browser rendering optimization. CPU instructions, RAM/ROM mapping,
the shared clock, rotational disk delivery, AY synthesis, Canvas and the
single visible presentation surface retain their previous behavior.

## Change

The old WebGL renderer allocated a temporary 24-number JavaScript array for
every dirty eight-pixel group, then uploaded its entire 589,824-byte vertex
buffer with `STATIC_DRAW`. Every bank redraw called both `flush()` and
`finish()`, synchronously waiting for GPU completion before presentation.

The [guarded patch](../../tools/patch-webgl-streaming.mjs) writes the same six
vertices directly into the existing Float32 array. Each bank's GPU buffer is
allocated once using `DYNAMIC_DRAW`; subsequent draws use `bufferSubData`
with only the populated prefix. One small TypedArray view per nonempty draw
remains. `flush()` is retained; the per-bank `finish()` is removed. The
browser synchronizes the later canvas-to-texture copy. Both source bank
canvases retain `preserveDrawingBuffer: true`, native resolution and their
original attributes, FLASH handling and nearest-neighbor sampling.
The WebGL drawing-buffer and presentation guarantees are documented in the
[Khronos specification](https://registry.khronos.org/webgl/specs/1.0.3/).

A full update removes 6,144 temporary JavaScript arrays. A 64-byte dirty
update transfers 6,144 bytes instead of 589,824 (96 times less). Empty draws
still issue no vertex upload. Target RAM usage changes by zero bytes; host
GPU storage is the same two maximum-size bank buffers, now allocated at
initialization rather than repeatedly during redraw.

## Measurements

The built-in Chromium 156 runs five alternating before/after pairs for each
workload, with a fresh iframe per trial, two fully initialized banks and 20
warmup frames. Each trial draws 200 updates while alternating banks, including
the final visible canvas-to-texture copy. Both variants have the same small
WebGL-call counting wrappers. One final visible-context GPU completion
barrier is included in each timed batch; hashing/readback occurs afterward.
These are unpaced rendering batches, not real-time FPS or CPU-emulation
throughput measurements. Setup, shader compilation and buffer allocation are
outside timing. All individual samples are retained in [browser.json](browser.json).

| 200-frame workload | Before median | After median | Time reduction |
| --- | ---: | ---: | ---: |
| All 6,144 pixel bytes dirty | 133.4 ms | 67.6 ms | 49.33% |
| 64 pixel bytes dirty | 62.0 ms | 8.0 ms | 87.10% |
| No dirty pixel bytes, bank switching | 6.3 ms | 5.9 ms | 6.35% |

Every full/sparse pair improves. Treat the much smaller unchanged-frame
difference as noise rather than a separate optimization. Final visible RGBA
SHA256 hashes match between variants in all three workloads. These values
describe this host and browser; they do not establish gains for every GPU,
driver, fullscreen size or other browser. Performance was measured in WebGL 2;
pixel correctness and recovery were checked in both WebGL 1 and WebGL 2.

## Correctness

- [Vertex characterization](vertices.json): all 6,144 byte addresses, both
  banks, FLASH/semicolor combinations, sparse and empty updates produce the
  independent expected vertices and exact upload lengths: 295,344 vertices
  compared, no per-redraw GPU reallocation or synchronous finish.
- [Browser checks](browser.json), each WebGL version: 16 color/FLASH patterns
  compare 16,515,072 RGBA bytes against Canvas with zero differences. The
  independent Spectrum-address oracle checks 1,769,472 pixels across all 192
  rows, incremental writes and both banks. Seam and border-only checks each
  compare 1,161,216 pixels; cached bank flips compare 4,644,864 bytes.
- Each version also passes four landscape/portrait/fullscreen dimensions
  and all eight border colors: 13,065,872 border pixels and 3,145,728 raster
  samples. Switching renderer, loss of visible/hidden WebGL contexts and
  unavailable-WebGL fallback preserve CPU, RAM and disk state.
- [Machine identity](verification.json): all source outside the WebGL module
  is byte-identical. A 66.2-second cold real-ROM/TRD workload produces exact
  matching PCM hashes, mapped 64 KiB, CPU, disk, PSG and shared-clock state.
  Its NullRenderer intentionally does not benchmark GPU rendering.
- [Integration smoke](integration.json): 67.2 emulated seconds, cold autoplay,
  native menu after input, stereo Lumiere/Alicia excerpts without clipping,
  and RAM/PC preserved on disk swap. [All 1356 Fuse vectors](opcodes.json)
  and [seven shared-clock schedules](clock.json) pass. Background playback,
  keyboard, RC filters and authenticated site-build guards also pass.

Vendor regeneration reproduces the checked-in bytes. No target instructions
or TRD bytes change: every player path has the same absolute T-state count
as before, delta **0 T**. Native movie deadlines and physical disk/audio
qualification are outside this host-rendering change.

## Rejected preliminary probes

Before selecting the WebGL change, three local CPU/clock probes were screened
in the same built-in browser on a cold music-disk workload with real CPU,
disk, AY and NullRenderer display events (66.2 emulated seconds). Three
alternating-order trials produced the following medians: baseline 3078.6 ms;
live queue-head guard 3188.6 ms; separated ED/CB decoder functions 3075.0 ms;
cached paged-RAM selection 3106.4 ms. Every final memory/PCM/machine identity
matched, but none justified promotion. Their raw timings remain under
`screening` in [browser.json](browser.json); production retains the original
implementations. An initial prefix-split draft failed parsing because of
mixed line-ending anchors; only the corrected draft reached the screen.

Additional one-shot Node probes of normal-opcode switch dispatch and a local
AY interpolation phase reproduced final machine identity but did not
establish a gain. No repeated qualification or adoption is claimed. Initial
profiling pointed at a nonexistent local site directory; the corrected run
used the authenticated task build. Partial setup failures are not timings.
These attempts do not change the previously qualified allocation-only Ayumi
patch or its evidence in the neighboring performance report.

## Reproduce

From a checkout containing materialized, authenticated TRDs:

```powershell
node web/tools/vendor-emulator.mjs C:/path/to/zx-dream 'C:/Program Files (x86)/Fuse/roms'
node web/tools/check-webgl-streaming.mjs
node web/tools/check-clock.mjs
node web/tools/check-opcodes.mjs C:/path/to/fuse/z80/tests
node web/tools/build.mjs .tmp/web-site
node web/tools/check-build.mjs
node web/tools/check-emulator.mjs .tmp/web-site
```

For timing, save `web/vendor/zx-dream.js` from baseline commit `1cabface`
byte-for-byte as `.tmp/web-site/baseline.js`. Copy the candidate vendor file
as `.tmp/web-site/candidate.js`, and copy
[`webgl-benchmark.html`](../../tools/webgl-benchmark.html) to that site's root.
Serve with `node web/tools/serve.mjs .tmp/web-site 4202`, open the fixture in
the built-in browser, and press **Run benchmark** without concurrent heavy
work. Copy [`renderer-check.html`](../../tools/renderer-check.html) to the
same root for the four pixel/recovery checks; repeat with **Force WebGL 1**.
These development fixtures and baseline source are excluded from Pages.
