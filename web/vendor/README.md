# Emulator credits and ROM notices

ZX-Dream by Evgenii Zeiler is vendored from
[ef68e190753d599752d1367050a94b85a06121c8](https://github.com/XMypuK/zx-dream/tree/ef68e190753d599752d1367050a94b85a06121c8).
The hardware modules and common utilities are concatenated into `zx-dream.js`.
Documented local corrections are reproducible through
[`patch-emulator.mjs`](../tools/patch-emulator.mjs): indexed instruction
timings/fetches, block I/O port addresses, RETI aliases, state restoration,
the original 128's 36-T interrupt pulse, standard TR-DOS track construction,
monotonic host pacing that retains pending shared-machine time, and a native
Canvas framebuffer with a completed-frame nearest-neighbor presentation blit.
Canvas bank buffers are hidden and copied together with the border to one
visible surface, preserving one pixel grid across the screen boundaries.
The [WebGL presentation override](../tools/webgl-presentation.js) likewise
exposes one full-frame GPU surface and keeps both native bank canvases hidden.
Its final texture uses nearest-neighbor GPU scaling and high-precision sample
coordinates; context loss on any of the three GPU contexts triggers Canvas
recovery. It does not read GPU pixels into JavaScript during playback.
The upstream UI, debugger, PHP services, example
disks, jQuery and Knockout are not included. Upstream comments are retained.
See [MIT license](LICENSE.zx-dream) and the per-module hashes in
[provenance.json](provenance.json).

`ayumi.js` is the upstream bundled Ayumi by Peter Sovietov, JavaScript
version by Alexander Kovalenko. Its MIT license is included in the file.

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
