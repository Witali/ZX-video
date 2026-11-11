# Spectrum Z80 WASM prototype

This report covers the initial CPU-only prototype. Its playback path is
available as `?cpu=wasm&ay=js`. The current `?cpu=wasm` path also runs AY
and the beeper in WASM.

Append `&cpu=wasm` to the normal Expedition 33 player URL and select **Play
disk**. Omitting the parameter selects the default ZX-Dream JavaScript CPU.
The prototype uses the C core pinned in
[z80-tester provenance](../../../emulator/vendor/z80_tester/provenance.json)
and the same flag hooks as the native test platform.

The module keeps eight RAM banks and four ROM slots in its linear memory.
The 7FFD latch maps RAM and selects the ROM. Opcode fetches can switch the
TR-DOS overlay and notify the disk controller at the same transition. The
generated instruction slices use this bus and finish at I/O strobes so a
new device deadline can take effect before the next T-state. Interrupts and
partial slices use the original per-T decoder. The existing ZX-Dream
clock, Beta Disk, keyboard, AY and WebGL/Canvas use the same interfaces for
both backends. The display reads a changed video bank at the field boundary
and runs the same dirty-byte logic as before.

## Expedition 33 measurement

The input was the committed 655,360-byte `Expedition-33-Demo.trd`
(`fd8868220ad6e9f429fc367a9887a446adfccc9c230caa94f37b8805a5046db4`).
The benchmark starts the machine cold, runs the opening slideshow for 60 s
and then uses the guest keyboard to play 3.1 s each of Lumiere and Alicia.
Both variants execute 67.2 s of machine time. Timed work includes CPU,
ROM/disk, stereo AY and display snapshots using a headless renderer. Five
alternating pairs on Node 22.22.3 give median **3,900.2 ms (JS)** and
**3,552.2 ms (WASM)**, an **8.92% reduction**. The speed result is specific
to this workload and host. [Raw paired runs](machine.json).

Both CPU backends booted to autoplay at approximately 20.53 s of machine time.
They matched the AY data sequence, menu glyphs, three slideshow checkpoints,
frame count and PCM packet count. The PCM hashes differ between JS and WASM.
JS observes I/O at instruction-step boundaries and WASM observes individual
port strobes. Fused WASM and per-T WASM matched PCM bit for bit, as well as
the AY writes, boot time and snapshots. WASM captured 3,360 fields with
70,908 T between every pair. JS captured the same number of fields with up
to 16 T of phase error. These are emulator fields. Monitor presentation
still follows browser vsync.

The built-in Chromium browser ran the same TRD with WebGL and the production
44.1-kHz AudioWorklet. A live 45 s pair spent **2,800.7 ms (JS)** and
**2,787.7 ms (WASM)** in the emulation wake callbacks, including rendering
submissions at field capture. The ~0.5% difference from this pair establishes
no material live-browser speed gain. Both generated 2,251 native fields.
During the last 21 s, both delivered stereo PCM to the AudioWorklet with
zero missing or discarded samples. A second WASM run switched to Alicia
through the guest menu and recorded the same zero gaps or drops over
926,976 output samples per channel. Browser-vsync presentation gaps reached
approximately 34 ms. Audio counters cover the Worklet before OS output.
[Live browser results](browser.json).

## Reproduction

With the initialized Emscripten SDK from z80-tester and Python 3:

```powershell
node web/tools/build-spectrum-wasm.mjs C:/path/to/emsdk C:/path/to/python.exe
node web/tools/build.mjs .tmp/web-site C:/path/to/checkout-with-lfs-images
node web/tools/check-spectrum-wasm.mjs .tmp/web-site .tmp/spectrum-wasm.json
Copy-Item web/tools/spectrum-wasm-live.html .tmp/web-site/
node web/tools/serve.mjs .tmp/web-site 4207
```

Open the served `spectrum-wasm-live.html`, choose a CPU and click **Run live
check**. The additional `?song=alicia` case starts Alicia via the demo menu
during the measurement window. The timing page is excluded from the site
build and copied explicitly for this check.

The 118,457-byte WASM artifact was built with Clang 24.0.0git
(`55ea1f4ebea23d0355d5cdb075f1e12f28ab82d0`) from the installed z80-tester
SDK. Its SHA-256 is
`7164dbd018cf143a0f708051e1ac6fea93ac9fc0843d22c2e06fd8c608ae7251`.
The module carries no guest ROM or disk bytes. The prototype keeps the
existing uncontended model and completed-frame display. This verification
covers Expedition 33 and the tested host, not ULA contention, full TRD
compatibility or physical audio output.
