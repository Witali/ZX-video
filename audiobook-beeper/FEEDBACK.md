# Live block-feedback PDM preview

The separate [feedback TRD](../ZX-audiobook-IMA-ADPCM-feedback-test.trd)
boots on Spectrum 128 / Beta Disk, decodes IMA in registers, converts it to
PDM while playing, and loops. Measured average output is **63919.47 Hz**,
approximately 64 kHz but **80.53 Hz below a strict 64000-Hz target**. The
original non-RC accumulator-PDM disk remains available unchanged.

On the common prepared source prefix and the established listening filter,
total reconstruction SNR improves **11.5532 ->14.0291 dB** (+2.4759 dB).
Modulation-only SNR improves **11.8282 ->14.5659 dB**. This is a working
finite-state approximation of the earlier feedback model, not its ideal
16.6-dB total-SNR result. Noise and distortion remain audible limitations.

- [Actual Fuse audio, first loop](experiments/ima-feedback64/result-preview.wav).
- [New output through the comparison filter](experiments/ima-feedback64/feedback-bandlimited-preview.wav).
- [Previous PDM through the same filter](experiments/ima-feedback64/old-pdm-bandlimited-preview.wav).
- [Prepared 8-kHz PCM input](experiments/ima-feedback64/source-preview.wav).
- [Full verification and audio report](experiments/ima-feedback64/report.json).

## Algorithm and memory

The Z80 preserves the exact 16-bit IMA predictor. Its high byte selects one
of 64 midpoint PCM bins. A table evaluates eight decisions from
`u = x + 1.5*previous_error - 0.5*older_error`, with threshold 0.5 and
`new_error = u - output_bit`. At each eight-bit block boundary the recent
error is quantized into 16 midpoint bins, and the older error into four,
both clipped over [-0.5, 0.5]. The resulting 64 states are explicitly finite.
There is no simulated RC circuit. This damped feedback has one DC noise
transfer zero; it is not a full second-order modulator.

The **8192-byte table** maps 64 PCM bins x64 feedback states to an output
byte and next state. The live IMA decoder supplies each new PCM value, and
the table advances the modulator state. No complete PCM/PDM stream is
unpacked, cached or precomputed for playback. Only an eight-bit output word
and state are held in CPU registers.

| Allocation | Bytes |
|---|---:|
| IMA payload, six full banks plus upper half of bank 5 | 106496 |
| Code, IMA tables, pointer pages, feedback table and alignment | 16384 |
| Screen | 6912 |
| Startup stack / ROM workspace | 1280 |
| Total | 131072 |

Code is 1740 bytes, within the 1792-byte reserve. The code/table bank is
uncontended bank 2; no sound payload remains there. Code is assembled from
[the commented ASM](ima-feedback-player.asm) by external pyz80. Python writes
constants, tables and source data, then packages the resulting binary.

The source capacity is **212992 samples /26.624 s** at 8 kHz, versus 28.864 s
previously. It is the same prepared source beginning at audiobook second 60,
shortened to fill the new allocation, with a new final 20-ms fade. IMA bytes
before that fade are checked against the unchanged baseline prefix.
The source WAV remains unsigned PCM8, 8 kHz; six-bit binning is internal to
this approximate modulator, not a change to the source WAV format.

## Timing and playback

The output kernel costs **30 T**: `RLC E` 8, `SBC A,A` 4, `AND 16` 7,
`OUT (FE),A` 11. It rotates the stored output byte and writes only EAR bit 4;
MIC and border stay zero. AY is muted at startup. IRQs are disabled during
playback; all **416 audio sectors** are loaded beforehand.

Four input bytes are unrolled. Each low-nibble path takes **428 T**.
The first three high paths take **436 T**, the fourth **446 T**: mean
**433.25 T/sample**, compared with 437 T in the first feedback attempt
(-3.75 T) and 438 T for the previous six-pulse PDM (-4.75 T).
The first three high paths use `INC IYL` without a jump; four-byte alignment
proves that these particular increments cannot cross a page boundary.

Ordinary holds are 49/53/56/58/53/56/59 T, then 44 T for a low path,
52 T for a short high path or 62 T for the fourth high path. A non-bank
page edge adds 18 T. A bank edge adds **434 T**, including one duplicate
eight-bit block of the last sample while switching banks. The feedback
state is not advanced for that brief duplicate. IMA state resets at the
full loop boundary; feedback state continues. Native total:

`433.25*212992 +18*(416-7) +434*7 =92289184 T/loop`.

The first feedback kernel took 93087904 T; unrolling saves **798720 T**
per loop. CPU counts exclude ULA, TR-DOS execution and disk latency.
Measured ULA overhead is **4531131 T across two complete loops**.
Actual loop durations are **26.658452 /26.658388 s**; PCM is
**7989.671 samples/s**, 0.1291% below the 8-kHz source rate. No pitch
correction was applied to the delivered audio.

The frequency is an average, not a uniform-clock or every-period claim.
Maximum measured hold is **85 T**, corresponding to **41728.24 Hz** for
that interval. Both normal cadence variation and real paging edges are
included in the audio comparison.

## Quality, verification and limitations

The previous ideal host model used full-precision state. To fit the Z80
budget, this player rounds PCM and feedback state at block boundaries.
On the complete original fragment with ideal 64-kHz timing, a 3/3-bit
state allocation gave 16.1552 dB modulation SNR; the chosen 4/2 allocation
gave **16.3805 dB**, both below the original 17.5784-dB host model.
The final measured-schedule score on the shorter excerpt is **14.5659 dB**.

An ordinary first-order PDM host model on the final player's exact schedule
scores **13.6354 dB** modulation SNR. Thus the feedback table itself adds
about **0.93 dB** over that comparison; the complete gain over the old
player also includes the higher output frequency. This model is not a
second released player. A tested table using average slot-area weights
did not materially improve the first kernel: 14.1048 versus 14.1061 dB;
the simpler unweighted table was retained.

SNR here includes reconstruction distortion and is relative to prepared
PCM, not a noise-free recording. Both signal and reference use the same
70-Hz high-pass and two second-order 4.5-kHz low-pass filters. There is no
fitted phase or gain; each reference follows its own sample timing, so the
metric excludes tempo error against a fixed 8-kHz clock. The first and last
0.1 s are excluded. Comparison WAVs use the same gain 0.7939606; the actual
Fuse recording has no added filter or gain. No physical machine or analog
speaker noise was measured.

Verification covers:

- All **16384** PCM8/state combinations against an independent Q16 integer
  recurrence and actual assembled lookup instructions.
- **44496** safe IMA transitions across all eight unrolled paths, including
  predictor extremes, every step index and nibble, exact output bits,
  instruction times and memory guards. Unsafe streams are rejected.
- Two complete native and cold Fuse128 cycles: **3407985 output bits**,
  **425984 predictors/indices**, every bank latch, startup stack, no runtime
  disk reads and native guards over fixed RAM and every paged payload bank.
- Normal-speed Fuse sound capture of both wraps, with signal in every
  complete half-second window. First-loop audio is delivered separately.

The initial full Fuse instrumentation attempt timed out: an 8-bit port-FE
breakpoint already matches both 00FE and 10FE, so a second breakpoint double
counted high bits. A short boot trace identified the duplicate timestamps.
Using one breakpoint fixed the verifier; complete runs pass. This was a
debugger-counter defect, not a playback freeze.

## Reproduction and retained evidence

Use the existing Python environment with NumPy, Pillow, pyz80 and z80:

```powershell
python audiobook-beeper/test_feedback.py
python audiobook-beeper/build_feedback.py --output build/ima-feedback --fuse <fuse.exe> --ffmpeg <ffmpeg.exe> --record
python audiobook-beeper/pack_ima.py build/ima-feedback --output build/feedback-repacked.trd
```

The last command only reads `assembly/player.bin` and packages it; it does
not assemble instructions. The guarded-input check also applies to this
feedback variant. [Initial 63.306-kHz kernel evidence](experiments/ima-feedback-initial/verification.json)
is retained as a superseded experiment, with its source and binary snapshots.
Complete final traces, timings, compiled source, source hashes and audio are
in [the final experiment directory](experiments/ima-feedback64/report.json).
