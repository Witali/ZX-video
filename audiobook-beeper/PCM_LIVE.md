# Convert PCM8 to beeper PDM on the Z80

The independently bootable [test disk](../ZX-audiobook-PDM-live-test.trd)
stores unsigned **8000 Hz /8-bit mono PCM** and converts it directly to
beeper pulses during playback. No prepared PDM payload, expanded PDM RAM
buffer or PDM lookup table is used. The accumulator and output pipeline
occupy registers A and E; D holds the current PCM byte.

The earlier [8k8 disk](../ZX-audiobook-PDM-8k8-test.trd) stored already
packed PDM, eight pulses per byte. It loaded those bytes and shifted them
directly to the beeper; there was no separate decompression buffer.

## Listen and boot

- [Measured beeper preview](pcm-live-preview/beeper-preview.wav).
- [Matched PCM reference](pcm-live-preview/original-preview.wav).
- [Wideband beeper preview](pcm-live-preview/wideband-preview.wav).
- [Exact source PCM8 WAV](pcm-live-preview/pcm8k-preview.wav).
- [Build report](pcm-live-preview/report.json),
  [native and cold-Fuse verification](pcm-live-preview/verification.json).

Mount the TRD in drive A on **original Spectrum 128/+2 with Beta Disk and
TR-DOS**. Use `RUN "boot"` in TR-DOS if needed, enable beeper sound and normal
emulation speed. Playback repeats continuously; reset to stop. The input is
the same audiobook passage beginning at 60 seconds, 82865 original samples
plus 79 midpoint samples to complete the last disk sector. This is a resident
excerpt, not a full-book or streaming player.

The player deliberately uses the original 128/+2 paging-port alias
`10FD..17FD` during playback. That decode is **not compatible with +2A/+3**.
Cold Fuse verification uses machine `128` and Beta 128. Physical hardware
has not been tested. See the [128K port and contention reference](https://worldofspectrum.org/faq/reference/128kreference.htm).

## Four-instruction conversion kernel

```asm
; A = 8-bit fractional accumulator, initially 128
; D = current unsigned PCM byte
; E = pipeline, initially 0; BC = 10FEh
ADD A,D       ;  4 T: carry is the new PDM pulse
RR E          ;  8 T: carry enters bit 7
RES 3,E       ;  8 T: prevent previous pulse reaching MIC/border
OUT (C),E     ; 12 T: bit 4 drives the beeper
              ; 32 T total
```

Every pulse adds PCM to the fractional accumulator; overflow produces a one.
Bits 7..5 delay that carry by three output slots before it reaches bit 4.
Bits 7..5 of the ULA output byte are unused, while bits 3..0 remain zero.
This avoids branches on amplitude and does not overwrite the accumulator
to prepare the output byte. No PCM values are prequantized to a small set
of patterns. The input bytes remain exact.

Instruction costs follow the [Zilog Z80 manual](https://www.zilog.com/docs/z80/um0080.pdf).
The previous precomputed-PDM kernel cost 30 T: `RLC D` 8, `SBC A,A` 4,
`AND 16` 7, `OUT (FE),A` 11. Live conversion costs **32 T, delta +2 T**.
Housekeeping is amortized by unrolling four PCM samples. Page and bank work
is distributed across separate output slots while the current sample stays
in D; it never creates a long bank-switch pause.

The selected version produces **10 pulses per sample**. Padding with
`JR next` (12 T, no changed registers/flags) makes most output intervals
44 T. The complete ordinary block costs **1764 T /4 PCM samples /40 pulses**,
or **44.1 T/pulse**, versus the old 46 T/pulse: **-1.9 T on average**.
That comparison concerns output CPU cost, not equal encoded audio quality.

| Hold after an output | Instructions before the next 32-T kernel | Total |
|---|---|---:|
| Most pulses | JR next 12 | 44 T |
| Sample 1/2/3 last pulse | INC L 4 + LD D,(HL) 7 | 43 T |
| Sample 4 first pulse | INC L 4 + JP Z 10 | 46 T |
| Sample 4 last pulse | JP loop 10 + LD D,(HL) 7 | 49 T |
| Last sample of page, pulse 2 | INC H 4 + JP Z 10 | 46 T |
| Last sample of bank, pulse 3 | EX AF,AF' 4 + LD A,n 7 + OUT (FD),A 11 + EX AF,AF' 4 | 58 T |
| Last sample of bank, pulse 4 | LD HL,next-address 10 | 42 T |

Thus, for a sector-aligned N-byte PCM payload in B banks, deterministic
playback costs `441*N + 2*(N/256) + 12*B` T per loop. For this excerpt that
is **36579024 T**. This excludes ULA delays, ROM execution and disk latency.
The actual port timestamps in the complete Fuse check include ULA memory
and I/O contention. Disk/ROM activity ends before playback; it is not hidden
in the CPU timing formula. Interrupts are disabled during PDM, after one
startup synchronization interrupt. AY volumes are zero.

The complete cold run verifies **1658881 exact outputs**: two loops plus the
first pulse of the third. Measured average PDM rate is **78783.411 Hz**;
minimum instantaneous rate is **59115 Hz** and maximum is 84450 Hz. Actual
holds span 42..60 T, including ULA contention, with both loop holds at 49 T.
The two cycles last **10.5281629 and 10.5280465 seconds**. Actual average PCM
clock is **7878.341 Hz, -1.5207%** relative to the 8000 Hz source: playback is
slightly slower/lower-pitched. This fixed-clock test does not claim exact
8000 Hz playback or interrupt-based clock correction.

Reconstruction SNR rises **6.5376 ->9.8698 dB** (+3.3321 dB) and correlation
**0.904615 ->0.952116** compared with the fast experiment. Each metric uses
its own schedule-aligned PCM reference; the two playback clocks differ.
These results justify selecting the steadier version for listening, not a
claim of transparent reproduction or improvement over the older host-side
second-order PDM. The fast 104.4 kHz disk remains available in the archive.

## RAM and storage

Physical bank 2 holds code at 8000..8FFF, screen staging at 9000..AAFF and
stack below B800. Bank 5 holds the displayed screen, BASIC and TR-DOS
workspace. PCM occupies banks **0,4,6,1,3,7**, with the 1024-byte final bank
right-aligned at FC00. No RAM state from a previous disk is required.

Stored PCM takes **82944 bytes**, versus the prior **98304 PDM bytes**:
**15360 bytes /15.625% saved** for the same original PCM excerpt, before
its short alignment padding. The 655360-byte TRD uses **368 sectors**,
down from 428. There are 324 startup sector reads and zero playback reads.
Gzip files in the evidence archive are host-side storage only; the Spectrum
loads uncompressed PCM files `PCM0..PCM5` from the TRD.

## Speed experiment and reconstruction limits

An initial 13-pulse variant used the same 32-T kernel with minimal padding.
It reached **104428.484 pulses/s** in a complete two-loop Fuse run, with
instantaneous rate at least 56300/s and exact PCM/PDM throughout. Its uneven
holds nevertheless degraded the output: reconstruction SNR **6.5376 dB**,
correlation **0.904615**. Retain the
[complete fast experiment](experiments/pcm-live-fast/report.json), its
listening WAVs and exact compressed producer sources; it is not the root
test disk selected for listening.

A bounded offline diagnosis using the same 13-pulse bit sequence gives
SNR 12.7522 dB with ideal uniform holds, 6.7833 dB with its deterministic
CPU holds, and 6.5376 dB with the measured Fuse holds. This identifies
unequal pulse area as the main avoidable error in that candidate; it is
not a hardware measurement of the idealized schedule. The selected player
spends padding cycles to reduce this error while retaining live conversion.

The modulator is first-order and holds each PCM byte between updates.
The older host-produced PDM used a second-order area-aware modulator,
dither and band-limited interpolation. Moving conversion into a small Z80
loop changes those quality tradeoffs; higher pulse frequency alone is not
a claim of better speech quality. Fixed instruction timing also means the
actual PCM clock differs slightly from the source WAV's exact 8000 Hz.

Listening WAVs integrate the **measured output hold times** at 192 kHz and
resample to 44100 Hz /16-bit mono. The standard preview uses a 70 Hz highpass
and two two-pole 4500 Hz lowpasses; wideband omits those lowpasses. The
reference uses the same actual sample timing and three-slot pipeline delay,
with the same filters and common scalar gain. No original speech is mixed
into the beeper reconstruction. The documented reconstruction SNR excludes
100 ms at each edge and measures conversion error, not intelligibility or
a measured Spectrum speaker response.

## Reproduce

Use the existing Python environment with NumPy, Pillow and the independent
`z80` core, plus FFmpeg and Fuse. Use a new output directory.

```powershell
python audiobook-beeper/build_pcm.py audiobook-beeper/preview-8k8-loop/pcm8k-preview.wav --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output build/pcm-live
python -m unittest discover -s audiobook-beeper -p "test_*.py"
```

`--fast --quarter-nops 4` selects the archived speed experiment's player
and payload. The current verification harness differs only in the safe
debugger stop location. Source snapshots preserve exact historical evidence.
Each complete build checks two entire loops plus the first pulse of loop 3,
every PCM input, every PDM bit, page/bank transitions, both loop boundaries,
startup read count and absence of runtime reads. Unit tests also cover all
256 PCM values, all six full banks, a partial final bank, timing trim in the
fast mode, and stack/code preservation. No partial run is treated as a pass.

Recompute the bounded pulse-area diagnosis and comparison with
`python audiobook-beeper/compare_pcm.py --ffmpeg C:/Tools/ffmpeg.exe`.
See [saved comparison](pcm-comparison.json).
