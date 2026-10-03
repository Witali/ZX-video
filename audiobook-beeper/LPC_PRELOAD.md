# LPC preload experiment (rejected)

Measured on 2026-10-03 in branch `codex/lpc-ima-preload`, in the separate
`.worktree/lpc-ima-preload` checkout. This is preserved experimental work,
not a new recommended disk or a replacement for the established player.

## Implemented path

The PC runs the existing LPC2 analysis from `C:/Work/LPC-sound-codec` and
converts its LSF/LPC coefficients to ten Q15 reflection coefficients.
The new Spectrum-specific **LPS1** format is not compatible with `.lp2`.
Its 32-byte header and 1168 28-byte records occupy 32736 bytes. A Z80
preloader performs excitation, ten-stage lattice synthesis, de-emphasis,
DC filtering and standard four-bit IMA encoding. It produces all 93440
IMA bytes for the original 186880-sample, 23.36-second control excerpt.
The disk itself contains LPC records, not precomputed IMA audio.

There are two real 32-cell progress bars: completed disk sectors and
completed IMA bytes. Both are verified at every increment. The preloader
uses input banks3/7, temporary product tables in bank5 and the existing
seven-section output layout. Before output reuses bank7, the remaining
LPC tail is copied to fixed RAM at A000..B7FF. Code/stack, screen, TR-DOS
workspace and the final bank2 IMA tail at B800 are kept separate.

After conversion a small bank5 handoff loads the unchanged playback core
and its tables. Only conditional startup paths were added to the direct
player; ordinary playback remains 423 T/sample, delta **0 T**. This does
not imply that the experimental LPC disk passed the complete PDM release
checks: a phase probe reached playback, but a full bit trace and quality
qualification were not pursued after startup was rejected.

## Verification and rejection

The native Z80 core verifies all 186880 PCM samples, every one of 93440 IMA
bytes and the final resident IMA memory, all input reads, bank transitions
and both complete progress bars. Ten coefficient edge cases and 730
multiply cases match the independent scalar implementation. Initial
conservative excitation was too quiet (PCM111..150); the recorded fixed
normalization yields PCM32..224 with no counted forward lattice clipping
or IMA saturation. This is not an original-waveform fidelity claim.

The first native run reached its two-billion-T test limit after 170400
correct samples. Raising the test budget, without changing the codec,
completed all samples: **2192183887 T /618.056 s**, excluding ROM, disk
latency and ULA waits. Cold Fuse 128 measured **657.181 s** for conversion
and **5.326 s** for the 128 sectors of LPC data.

The user's final startup budget is twice the time to read **128 KiB of
raw data**, not twice the compressed LPC read time. The separate benchmark
reads and verifies 512 actual sequential TR-DOS sector requests using a
reused 16-KiB destination buffer: **70767734 T /19.952 s**, giving a
**39.904 s** conversion limit. It does not claim that a program plus
128 KiB of separate audio fits in Spectrum memory. These are emulator
measurements; physical hardware and different disk mechanisms can differ.

The LPC path fails this budget by a large margin and was rejected by the
user for both startup delay and altered sound. The user subsequently
authorized moving synthesis/IMA coding to the PC, then requested a study
of alternative waveform codecs targeting 10:1 relative to 8-kHz PCM16.
No claim of a successful fast LPC disk or 21-dB LPC output is made.

## Reproduction and evidence

Use the project's `numpy`, `pyz80`, `z80` and Pillow packages on PYTHONPATH,
including `audiobook-beeper` and `toolkit`. Assemble sources externally;
Python packages the assembler's binary, not hand-emitted Z80 opcodes.

```powershell
python audiobook-beeper/lpc_preload.py --source <original-source-preview.wav> --output build/lpc-source --node <node.exe>
python audiobook-beeper/build_lpc_disk.py --source build/lpc-source --output build/lpc-disk
python audiobook-beeper/verify_lpc_preload.py build/lpc-disk
python audiobook-beeper/benchmark_raw128.py --output build/raw128 --fuse <fuse.exe>
python audiobook-beeper/probe_lpc_startup.py build/lpc-disk --fuse <fuse.exe> --raw128-report build/raw128/report.json
```

Saved [native proof](experiments/ima-lpc-preload/preload-native.json),
[cold startup](experiments/ima-lpc-preload/startup-timing.json),
[raw-128 benchmark](experiments/ima-lpc-preload/raw128/report.json), source
payloads, assembly and the rejected experimental TRD are kept together.
