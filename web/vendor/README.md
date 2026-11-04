# Emulator credits and ROM notices

ZX-Dream by Evgenii Zeiler is vendored from
[ef68e190753d599752d1367050a94b85a06121c8](https://github.com/XMypuK/zx-dream/tree/ef68e190753d599752d1367050a94b85a06121c8).
The hardware modules and common utilities are concatenated into `zx-dream.js`.
Documented local corrections are reproducible through
[`patch-emulator.mjs`](../tools/patch-emulator.mjs): indexed instruction
timings/fetches, block I/O port addresses, RETI aliases, state restoration,
the original 128's 36-T interrupt pulse, standard TR-DOS track construction,
monotonic host pacing that retains pending shared-machine time, a guarded
audio-worklet wake of that same queue for background playback, and a native
Canvas framebuffer with a completed-frame nearest-neighbor presentation blit.
Canvas bank buffers are hidden and copied together with the border to one
visible surface, preserving one pixel grid across the screen boundaries.
The [WebGL presentation override](../tools/webgl-presentation.js) likewise
exposes one full-frame GPU surface and keeps both native bank canvases hidden.
Its final texture uses nearest-neighbor GPU scaling and high-precision sample
coordinates; context loss on any of the three GPU contexts triggers Canvas
recovery. It does not read GPU pixels into JavaScript during playback.
The [streaming patch](../tools/patch-webgl-streaming.mjs) retains identical
vertices and pixels, fills the shared vertex array directly, allocates GPU
bank storage once and uploads only dirty vertices. It submits draws without
waiting synchronously for GPU completion on each bank update.
[Browser measurements and correctness checks](../reports/webgl-streaming/README.md).
The upstream UI, debugger, PHP services, example
disks, jQuery and Knockout are not included. Upstream comments are retained.
See [MIT license](LICENSE.zx-dream) and the per-module hashes in
[provenance.json](provenance.json).

`ayumi.js` is the upstream bundled Ayumi by Peter Sovietov, JavaScript
version by Alexander Kovalenko, with one allocation-only local patch.
Each chip caches the 23 pairs of aliasing FIR ring-window views rather than
creating two new TypedArray views for every stereo sample. All oscillator,
interpolation, 192-tap FIR, DC-filter arithmetic and sample clocks retain
their original order. [Patch generator](../tools/patch-ayumi.mjs) and
[exact differential/benchmark evidence](../reports/performance/README.md).
Its MIT license is included in the file.

The three Spectrum ROM slots use the stock Spectrum 128 ROM pair from the
local Fuse installation, rather than the modified ZX-Dream ROMs. The two
48K lookup slots both contain `128-1.rom`; the 128K slot contains `128-0.rom`.
These ROMs are copyright Amstrad. The Fuse `roms/README.copyright` states
that Amstrad allows their distribution while retaining copyright, and
records restrictions on selling ROMs or embedding them in hardware.
[Fuse ROM notices](https://sourceforge.net/p/fuse-emulator/fuse/ci/master/tree/roms/README.copyright).

The TR-DOS slot contains Fuse's `trdos.rom` (TR-DOS 5.03), copyright
Technology Research Ltd. Its upstream lookup filename `tr5_04t.rom` is
retained solely for compatibility with ZX-Dream; it is **not** a 5.04T ROM.
ROM hashes are recorded in `provenance.json`. ROMs are separate binary
assets, not covered by ZX-Dream's MIT license.

Regenerate from the pinned upstream checkout and the same Fuse ROM files:

```powershell
node web/tools/vendor-emulator.mjs C:/path/to/zx-dream 'C:/Program Files (x86)/Fuse/roms'
```

The project adapter uses eight addressable RAM banks, 70,908 CPU T-states
per field, a 20 ms field period and a 1,773,400 Hz AY clock. This does not
add ULA contention to the upstream Pentagon-style bus or qualify its disk
latency, browser scheduling or audio accuracy against physical hardware.
The TRD model uses the standard interleave (physical IDs 1,9,2,10,...,8,16),
6250-byte MFM tracks, 300 rpm, normal rotational search, CRCs and timed DRQ.
Rotational waits are not skipped. This is still not a complete physical-board
qualification. No Z80 player/decoder code or target hot path is changed.

The [CPU event-loop patch](../tools/patch-cpu-slices.mjs) keeps instruction
execution inside the CPU until the paced host budget ends, dispatching the
same device queue at instruction/prefix boundaries. New I/O deadlines can
shorten the next dispatch immediately. It retains instruction stepping for
debugging and preserves the original bus timestamp contract.
[CPU measurements, rejected variants and exact differential checks](../reports/cpu-slices/README.md).

[Field-locked display scheduling](../tools/patch-frame-clock.mjs) replaces
the old 6.6-ms delay with a native capture at each emulated ULA interrupt.
One coalesced animation callback presents the completed bank and border;
explicit paused redraws remain synchronous. Both rendering backends share
this schedule. [Verification and monitor-refresh limits](../reports/frame-clock/README.md).
