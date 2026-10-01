# Beeper PDM audiobook preview

The user rejected the YM2149 speech test as unintelligible and requested a
different path: **one-bit PDM on the beeper, at least 40 kHz**. This subproject
stores the original speech as a noise-shaped bitstream and writes ULA port
FE bit 4 directly. It does not fit the voice to tone generators.

## Test disk and listening files

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

## Measured playback

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

## One bounded improvement

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

## Z80 cost and memory contract

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
```

Use the project's Python environment with NumPy, Pillow and the independent
`z80` core. The source must match the existing audiobook hash. A build performs
one complete timing pilot, encodes speech, then performs one complete speech
run. `--resume-render` reuses already complete, hash-matching verification if
only rendering was interrupted; it never skips incomplete playback checks.
