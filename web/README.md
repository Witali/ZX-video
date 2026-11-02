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

Select a root disk or switch to all project disks. Search matches filenames,
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
Playback pauses when the tab becomes hidden; use Resume on return. The
browser requires a user click before audio starts. Use Copy link to share
the selection; shared links do not autoplay. A local TRD is read in the
browser and never uploaded.

The display compensates for Windows DPI and browser zoom using
`devicePixelRatio`: the 256×192 active screen occupies 512×384 **device
pixels**, with a 32-device-pixel border (576×448 overall). Each source pixel
is a square of 2×2 device pixels. The origin is snapped to the device grid.
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

For this repository the expected project URL is
`https://witali.github.io/ZX-video/` once Pages is enabled and the workflow
succeeds. Relative asset and disk paths also support a custom domain.
The workflow materializes LFS before building: Pages must serve actual TRDs,
not Git LFS pointer text.

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
nonzero synthesized audio, and verifies that disk insertion preserves the
mapped memory and CPU program counter. It does not measure browser output
devices or qualify a complete movie's deadlines.

### Display settings

**Settings → Display renderer** switches between Canvas (the default) and
WebGL. The browser saves the choice, and the URL retains it even when local
storage is unavailable; an explicit URL choice takes priority. Switching during playback rebuilds only
the display surfaces, preserving CPU, RAM, disk state and sound. Both render
at native 256×192 and share the exact physical-pixel scaling. Unavailable or
lost WebGL contexts fall back to Canvas with a status message.

The browser comparison fixture renders sixteen bitmap/attribute/FLASH
patterns through both backends and compares native RGBA bytes. The observed
result is 3,145,728 bytes compared with zero differences. This proves those
rendered patterns, not a speed advantage or full-machine timing.
Serve [renderer-check.html](tools/renderer-check.html) at the built site's
root for a local check; this developer fixture is not part of the Pages
artifact. The first fixture readback incorrectly requested WebGL1 after the
upstream renderer selected WebGL2; the final fixture handles both contexts.
