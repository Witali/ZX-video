# Compact G.711 bytes decoded inside the modulator — PC simulation

2026-10-05. After the IMA study did not reach 30 dB, the user authorized
eight-bit PCM /mu-law /A-law instead, then specified that amplitude conversion
must happen during modulation while the audio stays compact. The earlier
instruction to simulate on the PC before a new Z80 implementation still
applies. **Select mu-law for this test input: 30.92 dB in the ideal PC model.**
No new Spectrum player, TRD, default converter mode or hardware result is
claimed. The prior IMA/duration constraint was superseded for this experiment;
the existing IMA player and its disks remain available.

## Storage and playback model

```
one stored mu-law/A-law byte
    -> exact amplitude lookup inside the modulator
    -> second-order error feedback
    -> 16 one-bit decisions per 8-kHz sample (128 kHz)
```

[stream_model.py](stream_model.py) consumes the compact bytes directly.
There is **no expanded PCM audio buffer**. A read-only table of 256 signed
16-bit levels costs **512 bytes**; only the current recovered level is held
while generating that sample's pulses. The byte stream is not expanded to
PCM16 in advance, and the recovered level is not truncated back to PCM8.
PC arrays used for reference/error checks and recording the output bits
are measurement instruments, not proposed Spectrum buffers.

[g711_codec.py](../../g711_codec.py) provides both standard code mappings
and PC encoding through FFmpeg. The formats are defined by
[ITU-T G.711](https://www.itu.int/rec/T-REC-G.711-198811-I/en).
The separate decoder implementation is checked against all 256 codes of
each [FFmpeg G.711 decoder](https://ffmpeg.org/doxygen/7.1/pcm__tablegen_8h_source.html).

Both [raw mu-law payload](soundtrack.mulaw) and
[raw A-law payload](soundtrack.alaw) contain exactly **186880 bytes**, one
byte per sample, without a WAV header or predictor state. They represent
23.36 seconds at 8000 Hz. Gzip copies in the evidence directory are archival
wrappers, not a requirement of the playback format. Linear PCM8 also uses
one byte per sample; companding changes the allocation of amplitude levels,
not the byte rate. Compared with PCM16 it uses half the audio storage.

This costs 8000 bytes/s (64 kbit/s), twice the IMA4 rate and 8/3 times the
IMA3 rate. The whole 23.36-s model input exceeds the Spectrum's entire RAM;
it is **not** a resident-playback duration claim. At the previous IMA3 audio
payload budget of 94458 bytes, one-byte audio would hold 11.80725 seconds
before any new layout tradeoffs. A future player must load successive parts.
Its final capacity, code, stack, workspace and modulator tables remain to be
designed and verified; 512 bytes is only the inverse-companding table size.

## Comparable whole-fragment results

All formats use the same 186880 prepared PCM8/8-kHz reference samples,
including the existing 128-sample silent guard, and the same 128-kHz clock.
There is no fitted gain, delay, time stretch or changed bandwidth. Use a
70-Hz high-pass and two two-pole 4500-Hz low-pass filters on both signals;
exclude the fixed first/last 100 ms. SNR includes reconstruction distortion.

| Stored eight-bit format | Total SNR, 768-kHz integration /float64 filtering |
| --- | ---: |
| Linear PCM8 control | 32.248227 dB |
| **mu-law** | **30.920091 dB** |
| A-law | 30.221673 dB |

The selected mu-law result at an even finer **1536-kHz integration grid** is
**30.917095 dB**, a change of only -0.002996 dB. Thus the PC model passes
30 dB with about 0.92 dB margin. This is not a guarantee after Z80 timing,
table quantization, analog output or real hardware effects are included.

The comparison starts from the identical existing PCM8 reference for
continuity. It does not show that mu-law recovers precision already lost
when that reference was quantized. The encoder accepts PCM16 directly,
and `simulate.py --input` accepts either mono PCM8 or PCM16 WAV at 8000 Hz;
future media preparation should encode from its higher-precision signal
directly. This particular reference favours mu-law; it is not a universal
ranking for every recording. Linear PCM8 is still the best of these three
models for the already-PCM8 reference.

At 64-kHz PDM, the initial controls score about 15.88..15.98 dB under the
legacy arithmetic. They give no reason to use that lower rate for this
full-gain SD2 model. This is not a universal statement about all 64-kHz
modulators or filters.

## Precision and independent checks

The modulator uses integer DAC scale 65536 and preserves two feedback
coordinates exactly. A byte is inverse-companded only when consumed:

```
x = decoded_PCM16[code] + 32768
u = x + q + recent
bit = (u >= 32768)
recent = u - 65536*bit
q += x - 65536*bit
```

For mu-law the observed peak state is 315292 (4.810974 DAC units), fitting
the model's two signed 32-bit coordinates. There is no state clipping or
rounding. This finite-clip observation does not prove stability for every
possible input, or that a Z80 can execute the arithmetic in the available
cycles. No new hot path is introduced in this study (Z80 delta 0 T).

Every pulse of all six direct-byte models (three formats x two rates)
matches the earlier expanded-reference simulation exactly. For each128-kHz
model all2990080 decisions also match an independent two-history integer
recurrence. Every decoded sample of both G.711 streams matches FFmpeg.
Three unit tests cover signed extrema, silence codes, the512-byte tables,
read-only data and rejected invalid inputs.

The initial legacy float32 renders gave31.691681/30.385297/29.776037 dB.
A finer-grid check exposed **numerical instability in automatic float32 IIR
filtering**, including an invalid -7.606974-dB result at1536 kHz. The
failed convergence report and logs are preserved. Fix the measurement by
specifying float64 for both reference and output with the **same frequencies
and filter orders**; do not change pulse data or the quality threshold.
The stable768/1536-kHz results above supersede the preliminary values.
The old192-kHz score is retained as a diagnostic, not used as a convergence
reference after the precision failure. The new high-precision scores must
not be mixed directly with old historical float32 scores without rescoring.
Shared historical measurement modules and the paused IMA study are unchanged.

A separate legacy-arithmetic diagnostic truncates each law's decoded value
to its high byte before PDM: mu-law falls30.385297 ->29.885037 dB and A-law
29.776037 ->29.507387 dB. The selected direct-byte producer preserves the
full recovered level. Its full-stream bit checks confirm that removing the
PCM audio buffer costs no quality.

## Artifacts and reproduction

Verified listening WAVs use the same fixed0.5 export gain (-6.02 dB) to
avoid clipping brief reconstruction peaks. This does not enter the SNR
calculation. All WAVs have44100-Hz mono PCM16 output and no clipped samples.

- [mu-law result](mulaw-preview.wav)
- [A-law result](alaw-preview.wav)
- [Linear PCM8 control](pcm8-preview.wav)
- [Reference at the same listening gain](reference-preview.wav)
- [Streaming report](evidence/stream/report.json), [final verification](evidence/stream/verification.json)
- [Manifest](manifest.json), [producer snapshots](producers)

With the repository Python environment and installed FFmpeg:

```powershell
python audiobook-beeper/experiments/xlaw-pc/simulate.py --output build/xlaw-new --ffmpeg <ffmpeg.exe>
python audiobook-beeper/experiments/xlaw-pc/verify.py --output build/xlaw-new --ffmpeg <ffmpeg.exe>
```

Supply `--input <8000-Hz-mono-PCM-WAV>` to both commands to test another
prepared source. No Fuse or Z80 assembler is invoked. The full-memory layout,
real OUT timing, repeat boundary and disk loading remain future port work;
the current deliverable is the requested compact-byte PC simulation.
