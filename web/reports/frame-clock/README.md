# Field-locked capture and vsync presentation

Baseline: `0ba22c13`, 2026-11-04. Previously a ULA interrupt scheduled a
separate display task 6.6 emulated milliseconds later, and the web adapter
disabled animation-frame presentation. The frame phase was arbitrary and
did not follow the completed-field boundary directly.

The [guarded display patch](../../tools/patch-frame-clock.mjs) captures the
native active bank exactly on each emulated interrupt: one snapshot per
70,908-T / 20-ms field. It consumes the dirty bitmap synchronously into the
renderer before the CPU can write the next field. The selected bank and
border color belong to that completed snapshot. Both Canvas and WebGL now
present the latest completed frame through `requestAnimationFrame`.

There is at most one queued callback. A stalled/hidden browser can replace
the pending presentation with a newer completed frame; it never builds an
old-frame queue or changes machine time. Native snapshots still run on every
field. Rebinding a renderer invalidates/cancels earlier callbacks. Explicit
layout and paused `force_redraw()` operations remain immediate. Canceling a
pending presentation marks its border dirty so switching to synchronous
mode cannot lose the latest color. The old shared deferred-copy arrays are
removed; no target RAM or Z80 instruction changes occur (delta 0 B / 0 T).

## Evidence

- [Scheduling checks](scheduling.json) use the actual clock/display modules,
  a four-T CPU and a recording renderer. All eight cases produce exactly
  **50 snapshots per emulated second**, at the same timestamps as their ULA
  interrupts, with zero additional capture phase error and at most one
  pending animation callback. Simulated 50/60/75/120-Hz monitors present 50
  distinct snapshots; a 40-Hz monitor presents 40. Irregular host wakeups and
  hidden-tab cases coalesce presentation while retaining all native fields.
- The same checks verify that post-capture CPU writes do not leak into the
  completed image, the border belongs to that image, explicit paused redraws
  are immediate, stale renderer callbacks cannot run, and a queued border
  survives an animation-to-synchronous presentation change.
- [Actual browser checks](browser.json) run a real Z80 memory-write loop for
  five seconds with the production `SpectrumPlayer`, native Canvas/WebGL
  and browser vsync. Capture timestamps match every interrupt; the observed
  interval-based native rate is approximately **50.000 Hz** in both modes.
  The test kernel's recurring-field deviation is at most 9 T (about 2.54 us),
  due to instruction-boundary dispatch. One animation callback is queued.
- [Pixel/recovery checks](pixels.json) repeat the existing full comparison
  in WebGL 1 and 2: all 192 rows and both banks, 16 attribute/FLASH patterns,
  seams, cached flips, four viewport sizes and all border colors, with zero
  differences. Renderer switching and visible/hidden context-loss fallback
  preserve CPU/RAM/disk state.
- CPU/shared-clock traces, background behavior, keyboard, RC filters and
  cold TRD autoplay/stereo/disk-swap checks remain valid. The complete
  differential machine replay retains the previous PCM/RAM/CPU/PSG/disk
  identity. Vendor regeneration is byte-exact; no TRD is modified.

The interval-rate estimate excludes the initial cold-start field; that
existing IRQ phase is preserved. Browser presentation is quantized to the
monitor's refresh rate. A 60-Hz monitor can alternate roughly 16.7/33.3-ms
display intervals for 50-Hz content; the emulator's frame/audio clock is not
changed to 60 Hz. These checks do not certify physical scanout, every host
refresh configuration, or cycle-by-cycle ULA/raster effects. Capturing at
the interrupt shows the completed preceding field; writes by its new ISR
belong to the next completed snapshot.

## Reproduce

```powershell
node web/tools/check-frame-clock.mjs .tmp/frame-clock.json
node web/tools/check-cpu-slices.mjs
node web/tools/check-clock.mjs
node web/tools/build.mjs .tmp/web-site
```

Copy [frame-clock-check.html](../../tools/frame-clock-check.html) and
[renderer-check.html](../../tools/renderer-check.html) to the built site's
root, serve it locally and run both renderers in the built-in browser.
Development fixtures remain excluded from the Pages build allowlist.
