# Beeper PDM audiobook preview

The user rejected the YM2149 speech test as unintelligible and requested a
different path: **one-bit PDM on the beeper, at least 40 kHz**. This subproject
supports both a precomputed noise-shaped bitstream and direct conversion of
unsigned PCM8 to PDM in Z80 registers. Both write ULA port FE bit 4 directly.
They do not fit the voice to tone generators.

## Current test: convert PCM to PDM while playing

[Live conversion TRD](../ZX-audiobook-PDM-live-test.trd) stores the actual
8 kHz /8-bit mono PCM bytes. Z80 converts them while playing, with no PDM
buffer or lookup table. All eight RAM banks provide **121344 PCM bytes
(118.5 KiB)**, with a **15.402-second** repeating excerpt after the initial
disk load. The early-silence paging bug is corrected using the full 7FFD port.
See [memory, timing and reproduction](FULL_MEMORY.md),
[actual Fuse sound](pcm-live-full/sound-128/fuse-preview.wav) and
[complete verification](pcm-live-full/verification.json).
The [original method and comparisons](PCM_LIVE.md) remain archived.

The previous disks already contained packed PDM, eight output bits per
byte; they did not expand it into a separate RAM buffer after loading.
The new disk changes the stored representation to PCM and moves modulation
from the host computer into the Spectrum playback loop.

## Previous test: 8 kHz / 8-bit source, precomputed PDM, continuous repeat

The preceding user request converted the demonstration to **8000 Hz, 8-bit mono
PCM**, raises the PDM rate, saves a TRD and repeats playback continuously.

- [Looping test TRD](../ZX-audiobook-PDM-8k8-test.trd).
- [Exact archived disk](preview-8k8-loop/audiobook-preview.trd).
- [Actual 8000 Hz / unsigned 8-bit mono WAV](preview-8k8-loop/pcm8k-preview.wav).
- [Reconstructed beeper listening WAV](preview-8k8-loop/beeper-preview.wav).
- [Complete build report](preview-8k8-loop/report.json) and
  [two-cycle native/cold-Fuse verification](preview-8k8-loop/verification.json).

Boot in **Spectrum 128 + Beta Disk/TR-DOS**, drive A, with `RUN "boot"` if
needed. Enable beeper audio and normal emulation speed. After preloading
96 KiB, the excerpt beginning at source time 60 seconds repeats from RAM.
Reset to stop. The prior 52-T disk below remains unchanged.

The complete cold-Fuse check measures **75923.916 bit/s average**, versus
66915.539 before (+13.46%). All measured intervals remain at least
**62226.316 bit/s**. The two cycles last 10.3581434 and 10.3581747 seconds;
their output schedules differ slightly with ULA phase. Both repeat holds
are 48 T (13.53 microseconds). Every one of **1572865 writes** matches the
two full bitstreams plus the first bit of the third cycle. There are 384
startup sector reads and zero runtime reads. The 640 KiB TRD occupies
428 sectors. [Delivery integrity check](delivery-8k8.json).

The original recording is **AAC, 44100 Hz, stereo, 127999 bit/s**, verified
with FFprobe; see [source-format evidence](source-format.json). AAC has no
fixed PCM word length: `fltp` is the decoder output format. In this new build,
antialiasing precedes conversion to 8000 Hz and nearest-level quantization
to unsigned 8-bit PCM. The saved 8-bit bytes are reconstructed at 192 kHz
for the modulator. PDM receives only that reconstructed signal. The TRD
stores packed **one-bit PDM**, while the listening WAV is 44100 Hz /16-bit
mono. These are different stages, not contradictory sampling rates.

The 46-T kernel has the same 30-T output operation plus 16-T housekeeping:
**368 T/byte**, versus the baseline's **416 T/byte** (-48 T/byte, -6 T/bit).
The nominal ordinary-bit rate is **77106.522 bit/s**. The final bit of each
repeat has a **48-T** deterministic hold: LD D,E 4 + NOP 4 + JP 10 + the
next 30-T output kernel. Thus a complete cycle costs `bits*46+2` T before
ULA contention; the final byte costs 370 T (-46 T versus the old 416).
No reload, interrupt, mute, or additional pause is inserted at the wrap.
The existing 20-ms audio fades remain at the two excerpt edges.

| Interval after output | 46-T path: work before next 30-T kernel |
|---|---|
| Bit 1 | INC HL 6 + padding 10 |
| Bit 2 | LD A,H 4 + OR L 4 + NOP 4 + EX AF,AF' 4 |
| Bit 3 | EX AF,AF' 4 + JR Z taken 12; or JR not taken 7 + untaken RET C 5 |
| Normal bits 4, 5, 7 | Padding 16 |
| Normal bit 6 | LD E,(HL) 7 + padding 9 |
| Normal bit 8 | LD D,E 4 + JR 12 |
| Boundary bit 4 | LD E,next-bank 7 + padding 9 |
| Boundary bit 5 | OUT (C),E 12 + NOP 4 |
| Boundary bit 6 | LD HL,next-address-1 10 + INC HL 6 |
| Boundary bit 7 | LD E,(HL) 7 + padding 9 |
| Boundary bit 8 | LD D,E 4 + JR 12; final repeat uses the 48-T path above |

The complete single-pass 46-T /8-bit conversion finished before the user
requested repetition. Its [report and artifacts](preview-8k8/report.json),
including exact compressed producer sources, are retained as evidence.
It measured 75924.035 bit/s average and 62226.316 minimum. The looping disk
is the current delivery; its two full cycles also check both repeat edges.
This is a resident demonstration, not a continuous two-minute/full-book stream.

## Original 52-T test disk and listening files

- [Root test TRD](../ZX-audiobook-PDM-test.trd).
- [Identical archived TRD](preview/audiobook-preview.trd).
- [PDM with a 4.5 kHz reconstruction filter](preview/beeper-preview.wav).
- [PDM wideband output](preview/wideband-preview.wav).
- [Prepared original with the same reconstruction filter](preview/original-preview.wav).

Mount the disk in drive A of **Spectrum 128 + Beta Disk/TR-DOS**. If it does
not autostart, enter TR-DOS and use `RUN "boot"`. Enable beeper audio in the
emulator and run at normal speed. It preloads all data, then plays once for
**11.7526065 seconds**, starting at source time 60 seconds. Reset and boot
again to replay. The file is a complete bootable 640 KiB TRD, using 428 sectors.

This is a bounded first test of the new approach, not a two-minute stream.
The final payload uses all six available data banks: **96 KiB /786432 bits**.
Longer continuous playback requires another delivery strategy; disk reads
are not attempted during this resident test.

## Original 52-T measured playback

| Property | Final speech run |
|---|---:|
| Nominal CPU loop rate | 68209.615 bit/s |
| Actual average with ULA contention | **66915.539 bit/s** |
| Lowest instantaneous rate, including bank changes | **59115 bit/s** |
| Highest instantaneous rate | 68209.615 bit/s |
| Actual output intervals | 52, 53, 55, 56 or 60 T |
| Verified speech bits | **786432 /786432** |
| Startup sector reads / runtime reads | 384 / **0** |

Every actual hold interval, including the final one, passes the >=40 kHz
gate. The independent Z80 run verifies exact bits and 52-T intervals without
ULA; the complete cold Fuse run adds real emulated memory/I/O delays. These
are full-excerpt checks, not an extrapolation from a short timing loop.

[Complete report](preview/report.json) ·
[Native and cold Fuse verification](preview/verification.json) ·
[Compressed actual output times](preview/output-times.u32.gz).

PDM occupies the CPU continuously. Interrupts are disabled during playback;
the old 50 Hz AY update requirement was superseded by the user's beeper PDM
request. A ROM interrupt synchronizes startup, then all sample writes run
without interrupts. AY volumes are zero; MIC and border bits remain zero.
See the [ULA output register](https://worldofspectrum.org/faq/reference/48kreference.htm)
and [128K contention notes](https://worldofspectrum.org/faq/reference/128kreference.htm).

## Signal preparation and what the WAV means

The source is the same supplied O. Henry recording, authenticated by SHA-256.
FFmpeg downmixes it to mono, applies a 70 Hz highpass and two two-pole 3800 Hz
lowpasses, and resamples to 192 kHz. Peak is normalized to 0.65; only the first
and last 20 ms are faded. Audio bandwidth and PDM clock frequency are distinct.

The second-order error-feedback modulator works in pulse-area units using
the measured slot durations. It uses fixed-seed, low-level TPDF dither to
avoid coherent idle patterns. Eight bits pack into one byte, MSB first.
The first full pilot determines the schedule. The speech run then independently
checks every bit and every interval. Cold-start phase differs by two T in the
final pair of runs: at most 0.564 microseconds, without accumulating drift.
The bounded startup allowance is three T; the >=40 kHz gate is unchanged.

The listening WAV integrates the **final measured port hold times**, then
uses two two-pole 4500 Hz lowpasses and a 70 Hz highpass. This is an explicit
reconstruction filter, **not a measured Spectrum speaker response**. The
wideband WAV omits the 4500 Hz filters, retaining audible quantization noise.
All three WAVs use the same scalar gain; no original audio is mixed into
the reconstructed beeper signal. Actual speakers and emulator sound filters
can change the sound. No physical hardware recording is claimed.

## Earlier 64-T to 52-T improvement

The first complete implementation used 64 T/bit and 80 KiB: average 54823.104
bit/s, minimum 44336.25 bit/s, 11.954084 seconds. It met the frequency gate,
but retained more reconstructed speech-band noise. Its exact source snapshots,
disk, waveform and full verification remain in [experiments/pdm64](experiments/pdm64/report.json).

One faster candidate distributes boundary work over more output slots and
uses 52 T/bit. Compare the same **[60.1,70.1)** passage, with identical filters:

| Decoder | Waveform correlation | Reconstruction SNR |
|---|---:|---:|
| 64 T/bit | 0.907986 | 6.6909 dB |
| **52 T/bit** | **0.964705** | **11.2622 dB** |

The SNR improvement is **4.5713 dB**. These measurements support choosing the
faster version; they are not listener acceptance or a percentage of speech
quality. [Comparison script](compare_previews.py) · [result](comparison.json).

## Original 52-T cost and shared memory contract

Instruction costs follow the [Zilog Z80 manual](https://www.zilog.com/docs/z80/um0080.pdf).
The output kernel is `RLC D` (8 T), `SBC A,A` (4 T), `AND 16` (7 T),
`OUT (FE),A` (11 T): **30 T**. Housekeeping/padding occupies another **22 T**,
giving **52 T/bit /416 T/byte**, versus **64 /512 T** initially: **-12 T/bit,
-96 T/byte**. No existing movie or AY player hot path changes.

| Interval after output | Work before next 30-T output kernel |
|---|---|
| Normal bits 1, 2, 5, 7 | 22 T padding |
| Bit 3 | INC HL 6 + LD A,H 4 + OR L 4 + NOP 4 + EX AF,AF' 4 |
| Bit 4 | EX AF,AF' 4 + JP Z 10 + padding 8 |
| Normal bit 6 | LD E,(HL) 7 + padding 15 |
| Normal/boundary bit 8 | LD D,E 4 + padding 8 + JP 10 |
| Boundary bit 5 | LD E,next-bank 7 + padding 15 |
| Boundary bit 6 | OUT (C),E 12 + padding 10 |
| Boundary bit 7 | LD HL,next-address 10 + LD E,(HL) 7 + padding 5 |

The last bit is held for 52 T before zeroing FE: padding 37 + XOR A 4 + OUT
11. Padding uses NOP, JR to the next instruction, LD A,0 and **untaken RET C**;
carry is explicitly clear wherever RET C is used. Saved AF preserves the
pointer-wrap test across the bit-4 kernel. All 256 input byte values, every
bank transition, a partial final bank, stack and code guards are checked in
the independent CPU tests. Deterministic counts exclude ULA, ROM and disk.

Physical bank 2 contains code at 8000..8FFF, the screen staging area at
9000..AAFF and stack below B800. Bank 5 retains the visible screen, BASIC and
TR-DOS workspace. Banks **0,4,6,1,3,7** supply six full 16 KiB payloads. No
RAM from an earlier disk is required. Paging finishes inside scheduled bit
slots while the current byte remains in D; no bit is skipped at a bank edge.

## Reproduction

```powershell
python audiobook-beeper/build_pdm.py "C:/Audio/book.m4a" --ffmpeg "C:/Tools/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output "build/beeper-pdm" --start 60 --kib 96
python -m unittest discover -s audiobook-beeper -p "test_*.py"
python audiobook-beeper/compare_previews.py
python audiobook-beeper/build_pdm.py "C:/Audio/book.m4a" --ffmpeg "C:/Tools/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output "build/beeper-8k8-loop" --bit-tstates 46 --pcm8k --repeat
```

Use the project's Python environment with NumPy, Pillow and the independent
`z80` core. The source must match the existing audiobook hash. A build performs
one complete timing pilot, encodes speech, then performs one complete speech
run. `--resume-render` reuses already complete, hash-matching verification if
only rendering was interrupted; it never skips incomplete playback checks.
