# AY and beeper in the Spectrum WASM module

Select `?cpu=wasm` in the player to run the Z80, single AY-3-8910 and
beeper in one module. Append `&ay=js` to compare with the previous
per-sample JavaScript synthesis on the same CPU. The compiled module
uses the [pinned upstream Ayumi C source](../../../emulator/vendor/ayumi/provenance.json)
with double arithmetic and FP contraction disabled.

The fixed player clocks are 3,545,400 T/s for Z80 and 44,100 stereo frames
per second for audio. The Z80 wake counter is rebased for each run. The
audio timeline accumulates the completed T-states across wakes and
uses an integer sample position relative to the last machine reset.
Sample (n) is due at `ceil(n * 3545400 / 44100)` T from that reset.
An AY or beeper write at time (t) first renders through (t-1), then
applies the new value. A sample due on the strobe observes the new value.
The end of each CPU run renders the remaining due frames and retains an
unfinished packet. This removes the 44.1-kHz sample tasks from the
JavaScript scheduler. The ULA fields and Beta Disk still use the shared
device clock. AY port reads combine with the other devices' bus values.

The player copies each 512-frame stereo block out of the reusable WASM
buffer and transfers both resulting buffers to AudioWorklet. The
message transfer moves their ownership without cloning the PCM again.
Shared WASM memory could let the audio thread read a ring buffer directly.
That transport requires cross-origin isolation for the document. The
published GitHub Pages player served neither COOP nor COEP on 2026-11-11.
[AudioWorklet design patterns](https://developer.chrome.com/blog/audio-worklet-design-pattern).

The module handles the single-chip ABC stereo configuration used by the
web player. A machine reset clears an unfinished packet and restarts its
sample phase. Clock pauses and disk swaps preserve the current phase.

## Verification on Expedition 33

The deterministic test cold boots the real ROM/TRD, plays for 60 s,
opens the guest menu and plays the two 3.1-second excerpts. WASM AY
and JavaScript AY on the same Z80 produced identical stereo float32 PCM
across 5,788 complete packets, with the same menu, AY write sequence and
checked slideshow bytes. WASM audio deadlines matched the integer phase
for every packet. All 3,360 emulated fields were spaced at 70,908 T.
The full check also compares the fused and per-T WASM paths. A small
guest program checks simultaneous beeper strobes and sample deadlines,
partial-packet reset and masked AY port readback on both CPU paths.

Across five alternating deterministic pairs, host time for 67.2 s of
emulation fell from a median of **3,538.5 ms** to **1,864.1 ms** (47.3%).
Both versions include cold boot, CPU, disk, stereo synthesis and a
headless display. [Paired runs and exact outputs](machine.json).

| Visible browser run, about 45 s | JS AY | WASM AY |
| --- | ---: | ---: |
| Time inside emulation wakes | 2,734.8 ms | 1,461.7 ms |
| Time inside wakes after 24 s | 1,146.4 ms | 616.5 ms |
| Emulated fields and presentation calls | 2,251 each | 2,251 each |
| AudioWorklet missing samples in the last 21 s | 256 | 0 |
| AudioWorklet discarded samples in the last 21 s | 0 | 0 |

The single live pair reduces host wake work by 46.6%. The measured
WASM playback window delivers 926,592 samples per channel through the
AudioWorklet while switching from Lumiere to Alicia. Browser display
calls are paced by vsync and their largest interval in that run is
37.7 ms. The emulated field clock stays at exactly 50 Hz. Audio delivery
counts are measured before operating-system output. The first WASM run
also kept audio continuous but browser presentation was throttled.
Only the two visible runs enter the live speed comparison.
[Browser measurements](browser.json).

## Reproduce

```powershell
node web/tools/build-spectrum-wasm.mjs C:/path/to/emsdk C:/path/to/python.exe
node web/tools/check-wasm-audio.mjs
node web/tools/build.mjs .tmp/web-site C:/path/to/checkout-with-lfs-images
node web/tools/check-spectrum-wasm.mjs .tmp/web-site .tmp/wasm-ay.json
Copy-Item web/tools/spectrum-wasm-live.html .tmp/web-site/
node web/tools/serve.mjs .tmp/web-site 4209
```

Open `spectrum-wasm-live.html?song=alicia` in a visible built-in browser
tab and run the live check. Repeat with `&ay=js` in the URL. Both variants
boot the TRD and use the Spectrum keyboard to select Alicia at 24 s.
The check records the emulated field times, browser presentation calls
and AudioWorklet underruns and drops during the last 21 s.

The 125,339-byte module uses the same Clang 24.0.0git toolchain as the
[initial WASM prototype](../spectrum-wasm/README.md). Its SHA-256 is
`0a647b243eca9233b77198360b8620e591fcf5ab240954369967bce6f2f9d8b7`.
