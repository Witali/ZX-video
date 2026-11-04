# Online TRD player for GitHub Pages

A static disk library with a locally vendored ZX-Dream emulator, AY/beeper
sound, Beta Disk and a 128K configuration. It does not need a backend or a
third-party emulator iframe. Disk bytes are fetched only when played, and
checked against their SHA-256 identity before insertion.

## Build and preview

Use Node.js 22 or newer and Git LFS. From a complete checkout:

```powershell
git lfs pull
node web/tools/build.mjs
node web/tools/serve.mjs
```

Open the printed local address. Build output is `.tmp/web-site`, not `web/`.
The builder replaces that task-owned output directory on each invocation.
It copies an explicit allowlist of static assets and every **tracked** TRD;
it never publishes the repository directory, logs, media sources or Git data.
It rejects LFS pointers, invalid geometry, images differing from committed
bytes, and mismatches against the curated catalogue. Existing catalogue
coverage gaps are shown as uncatalogued experiments, not silently omitted.

For a sparse worktree, an optional third argument supplies materialized
images from another local checkout. Every image must still match this
worktree's committed identity:

```powershell
node web/tools/build.mjs .tmp/web-site C:/Work/ZX-video
```

## Use

The public library excludes historical one-bit beeper PDM experiments,
including their root aliases. Classification follows converter provenance,
not IMA/mu-law names, so AY/YM music and speech remain available. Authenticated
direct TRD downloads are retained for historical links; repository archives
are preserved. [Library policy](tools/catalog-policy.mjs).

Select a root disk or switch to all library disks. Search matches filenames,
paths and descriptions; media filters narrow the list. **Play disk** inserts
into drive A and resets to TR-DOS. If TR-DOS displays its prompt, press Enter
to start the disk's `boot` file. Some archived fixtures are not bootable.

For a running multi-disk program, select the next image and use **Insert
without reset**, then confirm the program's prompt. This preserves RAM and
the original timeline; **Restart** always restarts the currently mounted
disk, even if a different library entry is selected. Swap is manual.

Click the screen for the emulated keyboard; Shift and Alt map to Caps Shift
and Symbol Shift. Arrows map to Caps Shift + 5/6/7/8 (left/down/up/right),
including shared modifier holds. Keyboard focus and window blur release held
keys. Enter, Space, 1/2 and arrows are also available as touch controls.
The arrow keys retain normal browser behavior outside the emulator display.
**Play in background** is enabled by default in Settings and remembered in
this browser. The Spectrum and sound continue when switching tabs or
minimizing the browser; the audio worklet wakes the shared paced clock even
when ordinary timers are throttled. Disable the checkbox to pause automatically
while hidden and resume on return. A manual Pause remains paused. The
browser requires a user click before audio starts. Use Copy link to share
the selection; shared links do not autoplay. A local TRD is read in the
browser and never uploaded.

The display compensates for Windows DPI and browser zoom using
`devicePixelRatio`: the 256×192 active screen occupies 512×384 **device
pixels**, with a 32-device-pixel border (576×448 overall). Each source pixel
is a square of 2×2 device pixels. The origin is snapped to the device grid.
Both renderers expose **one visible 576×448 canvas**, including the border.
Canvas keeps native 256×192 frame data and copies its selected 512×384 bank
surface at (32, 32). WebGL keeps hidden 256×192 GPU bank buffers, transfers
the selected bank to a native-size texture and draws it in the same full-frame
surface with a 512×384 integer viewport and `NEAREST` sampling. GPU scaling
does not add pixel readback into JavaScript. Screen and border are composed
before CSS/DPI presentation; the browser does not overlap separate canvases.
The scale updates after zoom, resizing, full screen and moving between
monitors. Narrow windows scroll instead of shrinking or stretching the image.

TR-DOS uses the emulated floppy controller rather than a ROM fast-load
trap. A disk that preloads its full audio cache can take about a minute to
start; the loading screen remains visible during that time.
A spinner beside the machine status follows the floppy controller's busy
state, including subsequent reads during playback. It also appears while
the browser fetches and authenticates a selected image.

## GitHub Pages

`.github/workflows/pages.yml` builds and deploys the allowlisted artifact
with GitHub Actions. In repository **Settings → Pages → Build and deployment**,
choose **GitHub Actions**. The workflow runs on main changes to the website,
catalogue or disks, and can also be run manually on main. A pull request
only builds and validates; it does not deploy. See
[GitHub's custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

The published player is at [witali.github.io/ZX-video](https://witali.github.io/ZX-video/).
Relative asset and disk paths also support a custom domain.
The workflow materializes LFS before building: Pages must serve actual TRDs,
not Git LFS pointer text.
Its partial, sparse checkout includes the web sources, catalogue and all
tracked TRDs, so unrelated archived audio/video LFS objects are not fetched.

## Verification scope

### CPU and disk investigation, 2026-11-02

The patched browser CPU passes **1,356 Fuse instruction vectors**, including
registers, MEMPTR, refresh register, interrupt flip-flops/mode, modified RAM,
port addresses/data and total instruction T-states. Four legacy expectations
for interrupted repeat flags are updated using the independent
[Banks hardware observations](https://github.com/hoglet67/Z80Decoder/wiki/Undocumented-Flags);
the report retains both AF values. This is not exhaustive coverage of every
initial state, interrupt phase or bus contention cycle.

Corrections cover DD/FD-CB non-M1 opcode fetches and internal timing,
`LD (IX/IY+d),n` timing, INI/IND and OUTI/OUTD port addresses, RETI aliases,
and IX-prefix/MEMPTR/Q state restoration. They are kept in the generator.
See [CPU report](reports/opcodes.json). Reproduce using the official Fuse
repository at `67d72235610a9821c780499a0c10d89512656127`:

```powershell
node web/tools/check-opcodes.mjs C:/path/to/fuse/z80/tests
node web/tools/check-video.mjs C:/Work/ZX-video 2 700 .tmp/video-check.json
```

TRD track generation now uses the canonical Fuse/TR-DOS layout: 6250 MFM
bytes per revolution, physical IDs `1,9,2,10,...,8,16`, standard ID/data marks,
CRCs and gaps. Rotation remains **300 rpm**, independently of CPU frequency.
The controller searches the rotating track and delivers timed DRQ; no
rotational wait is skipped. TRD has logical sector bytes, so this layout is
an explicit reconstruction, not recovered physical metadata.

The complete second refined disk produces all **1,360** expected full-screen
identities and **6,800** AY ticks. However, its rotational-controller run
takes **617.56 emulated playback seconds** for 136 seconds of content and
misses 1,330 nominal publication deadlines at the instruction-boundary
observation point. It **fails the 10-fps timing requirement**. This reproduces
the apparent freezes as long disk waits; correctness of the screen bytes
does not qualify playback timing. Synthesized audio was not checked by that
run. [Full report](reports/rotational-video-part02.json).

The bounded read diagnostic reproduces **178 LOST DATA completions out of
775 completed sector reads** in 120 emulated seconds. All 178 errors include
an IM2 dispatcher entry during the largest data-register service gap. The
first four failed reads transfer only 254 bytes, with gaps of 324–384 T
(about 91–108 microseconds, versus a 32-microsecond disk-byte period).
This identifies an IRQ/read-service conflict in the current model; it does
not certify that model against hardware. The partial run compares 328 screen
identities with no errors and cannot pass release timing.
[Diagnostic report](reports/disk-reads-partial.json). Reproduce with:

```powershell
node web/tools/check-video.mjs C:/Work/ZX-video 2 120 .tmp/disk-reads.json --profile-reads
```

### Shared machine time

CPU, ULA interrupts/display, AY sample generation and floppy-controller
events use the same T-state counter and ordered event queue. Each device's
period is converted to that common timeline. The browser's monotonic
`performance.now()` paces machine time. Delayed callbacks process bounded
catch-up slices while retaining the real-time origin and every pending
hardware event. They no longer silently discard time after 50 ms. Explicit
pause/resume rebases the host clock for the whole machine; a hidden tab
pauses through the existing page policy.

The [clock test](tools/check-clock.mjs) compares complete event sequences
with regular/irregular callbacks, a 700-ms stall, wall-clock edits, and a
two-second pause. All five cases produce identical ULA/disk-byte/audio-sample
timelines over 3,545,400 T. This isolates scheduling with a four-T NOP CPU;
it is not a full-machine speed, audio-output or disk-accuracy qualification.
[Clock report](reports/clock.json). Retaining elapsed time cannot by itself
repair the IRQ-associated read errors or guarantee real time on a slow host.

### Backend selection

Choose **Fuse as the full-machine reference and practical basis for a
WebAssembly backend**, while retaining the project's native Z80 adapter as
an independent CPU reference. Do not claim that an unmodified Fuse disk
controller meets the stricter physical-timing requirement. No complete
replacement browser backend has been installed or performance-qualified.

| Candidate | Evidence and decision |
| --- | --- |
| [Fuse](https://github.com/fuse-emulator/fuse/tree/67d72235610a9821c780499a0c10d89512656127) / [fuse-libretro](https://github.com/libretro/fuse-libretro/tree/e997e2bc32c888348f862f69f2c53babfedf7791) | Mature complete Spectrum machine and Beta Disk; libretro has Emscripten and disk-control integration. Best practical starting point here. Its Beta setup omits `WD_FLAG_DRQ`, and data-register reads advance bytes; per-byte physical timing needs an explicit qualification/correction. |
| Project [native core](../emulator/README.md) | Pinned floooh CPU, per-T callbacks, tested banking/IRQ and decoder comparisons. Useful for WebAssembly and independent CPU checks. Fused execution is disabled when a bus is attached. Display, sound and disk are absent; instruction-level ULA contention is not qualified. It cannot replace the full machine by itself. |
| [ZX84](https://github.com/damieng-zx/zx84/tree/a95a85f353c086fe4fdf588bf17539f9a2f9ca4d) | Broad browser hardware and good inspection tools, but `src/cores/wd179x.ts` explicitly models sector transfers instantly and uses polling counts for lost-data timeouts. This does not satisfy the requested disk timing. |
| [JSSpeccy 3](https://github.com/gasman/jsspeccy3) | Worker/WebAssembly architecture, Spectrum/AY support; its documented media support does not include TRD/Beta Disk. Not a direct replacement. |
| Patched ZX-Dream | Usable browser preview and transparent CPU test results, but its Pentagon-style bus lacks qualified original-128 ULA contention and its complete rotational run fails playback timing. Do not promote it to a hardware reference. |

There is **no measured fastest complete backend** in this investigation.
Native decoder microbenchmarks do not rank full emulators. Compare candidate
builds on the same browser/device with unchanged ROM/TRD bytes, video/audio,
disk phase and ULA contention enabled, with acceleration disabled. Require
full EOF, byte-identical frames and AY states, actual IRQ/DRQ schedules,
nominal/fallback timing and real-time host headroom before switching defaults.

The web adapter does not change the Z80 player, nominal frame deadlines or
release disk contents. Browser playback is a preview, not a replacement for
the full Fuse/native timing, sound and EOF checks in the project evidence.
See [credits, pinned source and ROM notices](vendor/README.md).

The deterministic integration smoke is also run in CI:

```powershell
node web/tools/check-emulator.mjs
```

It boots the real music-menu TRD through the real ROM/controller/core,
matches the fourteen title glyphs against the stock ROM font, checks actual
nonzero synthesized audio separately in both channels of short Lumiere and
Alicia excerpts, and verifies that disk insertion preserves the
mapped memory and CPU program counter. It does not measure browser output
devices or qualify a complete movie's deadlines.

### Synthesis performance

Ayumi caches its 23 stereo FIR window pairs instead of creating two typed
views for every sample. Synthesis PCM and internal state remain bit exact.
Five alternating pairs measured 10.61% less synthesis time in the built-in
browser and 6.01% less host time for a complete Node real-ROM/TRD workload;
these are bounded host measurements, not a browser rendering or physical
disk qualification. [Reproduction, raw trials and correctness scope](reports/performance/README.md).

### Stereo output investigation

The reported left-only music output did not reproduce after reloading the
page, and the user then confirmed hearing both channels. The unchanged
ABC mix pans AY A/B/C at 10/50/90% toward the right: it is stereo separation,
not a missing channel. The two 3.1-second excerpts produce left/right RMS
levels of 0.09895/0.09838 (Lumiere) and 0.07898/0.10083 (Alicia), with no
clipped samples. These are bounded output checks, not complete-song or
physical-listening qualification. [Core report](reports/audio.json).

The browser [audio fixture](tools/audio-check.html) exercises the production
AudioWorklet-to-gain graph with separate left/right and stereo signals.
Both outputs are nonzero, with zero observed opposite-channel signal for
the isolated probes. Windows output meters also receive both channels while
other player audio is paused. No microphone or raw system audio is recorded,
and no Windows balance/volume settings are changed.
[Browser report](reports/audio-output-browser.json),
[Windows report](reports/audio-output-windows.json).
The original transient fault remains unexplained; no audio-mixing fix is
claimed or installed.

For local reproduction, copy `web/tools/audio-check.html` to the built
site root and open it over the same HTTP server. It is a development fixture
and is excluded from the Pages artifact. On Windows, start
`web/tools/measure-windows-audio.ps1 -Seconds 25` and run the browser probe
during that interval to read the default multimedia endpoint's peak meters.

### Audio filter settings

**Settings → Audio low-pass filter** selects 5, 10, 15 or 20 kHz; the
default is 20 kHz. The preference is retained locally and in the URL's
`lpf` parameter (Hz). An explicit URL value takes priority. Switching during
playback crossfades over 20 ms and preserves emulator state and stereo.

This is a digital single-pole RC-style output filter after the AudioWorklet,
before mute/volume. For `p = 1 - alpha`, its transfer is
`H(z) = alpha / (1 - p z^-1)`. With `d = 1 - cos(2π fc/fs)`, use
`alpha = sqrt(d(d+2)) - d` to put the digital response at exactly -3 dB at
the selected cutoff, including the near-Nyquist 20-kHz preset at 44.1 kHz.
The positive exponential impulse response has unity DC gain and cannot
overshoot a bounded input. Four parallel preset filters retain warm states;
only their output gains crossfade. AY synthesis and CPU/disk timing are
unchanged. This models a first-order response, not a measured analog board.

[Coefficient checks](tools/check-audio-filter.mjs) run in CI. The local
[native Web Audio fixture](tools/filter-check.html) verifies all four presets
at 44.1/48 kHz, independent stereo impulse responses, rapid switching and
preserved CPU/mapped RAM/disk state. Serve it at the built site's root like
the other development fixtures. [Browser report](reports/audio-filter.json).
The production Worklet-to-output stereo probe also passes with the default
20-kHz filter: [stereo report](reports/audio-filter-stereo.json).

### Display settings

**Settings → Display renderer** switches between WebGL (the default) and
Canvas. Existing saved choices and explicit selection URLs still take
priority over the default. The browser saves the choice, and the URL retains it even when local
storage is unavailable; an explicit URL choice takes priority. Switching during playback rebuilds only
the display surfaces, preserving CPU, RAM, disk state and sound. Both retain
native 256×192 frame data and share the physical-pixel scaling. Canvas uses
512×384 bank surfaces; WebGL keeps its bank surfaces at 256×192. Both expose
one 576×448 full-frame surface. Unavailable WebGL, or loss of either its visible
or hidden bank context, falls back to Canvas with a status message.

The browser fixture checks WebGL 1 and WebGL 2 separately against the actual
visible Canvas output, including the border. Each run compares sixteen
bitmap/attribute/FLASH patterns over 16,515,072 RGBA bytes without differences.
An independent inverse Spectrum-address oracle checks all 192 rows, banks 5/7
and partial writes: 1,769,472 pixels per run. Continuous border/screen fields
and border-only changes each check 1,161,216 pixels. Bank switches without
memory writes compare 4,644,864 cached-frame bytes. All differences are zero.
Live switching, visible/hidden context loss and unavailable-WebGL recovery
preserve CPU, RAM, paging and disk state. Both modes have one visible canvas.
[WebGL composition report](reports/webgl-composition.json).

Inspection of the in-app browser at DPR 1.25 complements those readback tests;
it does not certify every host DPI/zoom configuration or benchmark speed.
The historical [Canvas scaling](reports/canvas-scaling.json) and
[Canvas composition](reports/canvas-composition.json) reports retain the earlier
bank-only test limitation, user observations and reverted transform/zoom
experiments. Z80/player timing qualification is separate from display checks.
The [WebGL streaming optimization](reports/webgl-streaming/README.md) reduces
temporary arrays, redundant vertex uploads and synchronous GPU waits, while
retaining these pixel checks. Its rendering benchmark measures host work;
the emulated CPU, disk and sound keep the same real-time schedule.
Native frames are now captured directly on the emulated 50-Hz interrupt.
Both renderers present the latest completed frame on browser vsync, with at
most one queued callback; hidden tabs do not accumulate old presentations.
Paused layout/renderer redraws remain immediate.
[Frame scheduling and browser checks](reports/frame-clock/README.md).
Serve [renderer-check.html](tools/renderer-check.html) at the built site's
root for a local check; this developer fixture is not part of the Pages
artifact. The first fixture readback incorrectly requested WebGL1 after the
upstream renderer selected WebGL2; the final fixture handles both contexts.
# Expedition 33 Demo preview

Fullscreen centers the active 256x192 raster, fitting it to the available
viewport while retaining at least two character cells (16 native pixels) of
border on every side. Remaining space uses the current Spectrum border color.
Canvas and WebGL draw the complete result on one visible device-sized canvas;
no second border or screen overlay is introduced. Windowed mode restores exact
2x2 physical pixels, including Windows DPI/browser zoom compensation. WebGL
remains the default; saved explicit Canvas preferences remain available.

The default disk is now `Expedition-33-Demo.trd`. It contains the complete
looping Lumiere/Alicia AY playlist and eighteen native illustrations. The
first loading screen remains visible until playback; any Spectrum key opens
the hidden menu, I toggles pictures, and M returns to the slideshow.
`Download TRD` is a prominent button beside Play and downloads the selected
disk. The local-file path remains browser-only and hides that download link.

Existing `?disk=ZX-Music-Menu.trd` links select the renamed demo. The static
build retains `disks/ZX-Music-Menu.trd` as a byte-identical download alias,
without a second library card. The complete demo was reviewed before publication.
Native qualification is documented in
`music-menu/README.md`; `check-emulator.mjs` checks the new cold boot, autoplay,
menu-on-Space title, stereo excerpts and preserved disk-swap state.
