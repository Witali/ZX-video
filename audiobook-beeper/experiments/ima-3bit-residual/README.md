# Residual voice-distortion investigation, 2026-10-04

**Status: unresolved listening defect; no replacement TRD.** The user reports
unwanted vibration throughout `ZX-audiobook-IMA3-overlap-test.trd`, after
the previous measured boundary-error correction. Do not describe that
correction, or a small average-SNR gain, as a complete flutter fix.

The inspected disk's SHA-256 is
`ac4b740ebdcf2f9fb538d286b8ac679df6babc53462cf79b18f08cc8b5a2d66d`.
Reuse the [complete native/Fuse coverage](../ima-3bit-overlap/README.md):
5980094 live outputs through both parts and EOF, no missing samples,
-0.271723% mean speed error, and 20.436046 dB per full part. Those checks
establish execution correctness, not subjective absence of voice vibration.
No new physical-hardware or emulator execution is claimed here.

## Full-part decomposition

[diagnose.py](diagnose.py) reconstructs the original fixed 8-kHz PCM8 signal,
IMA predictor, 128-level control and actual PDM using the archived final
disk's pulse timestamps. It excludes the final silent guard and uses the
unchanged 70-Hz high-pass / two 4500-Hz two-pole low-passes / 44100-Hz
measurement chain and 100-ms end exclusions. There is no fitted gain,
delay, filter, time stretch, or source substitution.

The PDM result measures 20.434944 dB in that slightly shorter window.
Band SNR is 30.860774 dB at 70–300 Hz, 26.498069 at 300–1000 Hz,
16.608981 at 1–2 kHz, 9.382802 at 2–3 kHz and -2.488953 at 3–4 kHz.
Weak source power in high bands makes their ratios particularly sensitive
to residual noise. This does not by itself identify the perceived symptom.
See [the complete report](diagnostics/report.json).

The intermediate IMA control scores 17.680879 dB and the quantized control
17.655657 dB. They deliberately precompensate for PDM and must not be
interpreted as isolated ordinary codec quality, or subtracted from final
SNR to attribute the cause. The final PDM is better than these controls.
Error/source power folded into 100 bins of a 70908-T Spectrum field varies
by a max/min factor of about 1.74. This is neither a measured pitch excursion
nor evidence that field-frequency modulation is the cause.

## Bounded controls

Use the first 32768 active samples (4.096 seconds), plus 128 silent guard
samples, from the same prepared source. Every control uses the same saved
PDM timeline and filter. Search width is 256, horizon 128, commit 64,
regularization 0.03 unless specified. Values below are **host-model scores**.

| Control | SNR, dB | 1–2 kHz, dB | 2–3 kHz, dB | Original run, s |
| --- | ---: | ---: | ---: | ---: |
| Current three-bit alphabet | 21.600309 | 12.290177 | 9.663710 | 46.390 |
| Regularization 0.003 | 21.651526 | 12.320127 | 9.650980 | 46.766 |
| Derivative weight 0.12 | 20.853030 | 9.907724 | 8.900089 | 45.687 |
| Derivative weight 0.4 | 19.715455 | 8.986572 | 8.904287 | 45.750 |
| Full four-bit IMA alphabet | 23.899006 | 15.313662 | 12.825614 | 151.015 |
| WAV-IMA3 recurrence | 21.207448 | 11.818788 | 9.591872 | 41.953 |
| Quarter-step base, project step adaptation | 21.581862 | 12.327033 | 9.675690 | 43.703 |

Reject the derivative-weighted variants: their small 3–4-kHz improvements
come at a larger loss in the main speech band. The lower-prior change gives
only 0.051 dB and does not justify another purported fix. Both alternate
three-bit recurrences fail to improve the overall score. Four bits improve
the control by 2.298697 dB (about 41% less error power), showing that the
restricted alphabet contributes appreciably to distortion. This does not
prove that four bits eliminate the reported vibration.

The four-bit control uses all 16 IMA nibbles on a hypothetical unchanged
IMA3 output clock. The present three-bit disk cannot play that carrier.
A real four-bit player would need its own memory/timing calibration and
complete qualification. No conversion, memory capacity or timing benefit
is inferred for such an unimplemented player.

The production three-bit format is an even-nibble IMA subset, with
base `step >> 3` and index changes `[-1,-1,+2,+6]`. WAV-IMA3 uses
`step >> 2` and `[-1,-1,+1,+2]`; this was checked against
[FFmpeg's decoder](https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/adpcm.c).
The quarter-step/step6 control combines the WAV base with the project's
adaptation and is explicitly a custom experiment. Private module copies
keep all experimental recurrence changes out of production modules.

The first WAV-IMA3 run failed at the final 0/0 guard assertion. Its minimum
step has no zero-delta code, unlike the project subset. The successful retry
constrains the last six silent samples to end at predictor/index 0/0 using
an exhaustive four-code search. All stored carriers pass unclipped-addition,
control-level and terminal-state assertions. This is not an independently
implemented standard-codec certification.

## Listening controls and decision

The comparable short files have the same reference, output clock, gain and
measurement filter:

- [Source](source.wav)
- [Current three-bit control](ima3.wav)
- [Four-bit control](ima4.wav)

Separately, [normal Fuse audio, first eight seconds](diagnostics/normal-first8.wav)
and [the same recording with two extra 3500-Hz low-passes](diagnostics/normal-lowpass-first8.wav)
were presented to the user. The latter is a WAV diagnostic only; it does not
change a disk, its generator or the quality-acceptance filter. No listening
answer has arrived at this checkpoint. Human comparison is needed to tell
whether the reported vibration corresponds to the modeled codec error,
high-frequency output, or a difference in the user's playback environment.

No production encoder/player/table or release image changes. Native mean
cost stays **427.375 T/sample, delta 0 T**, with +14/+140 T page/bank extras;
RAM and payload capacity stay unchanged. Do not advance any probe as a
release based only on its score. Preserve the user-rejected disk as evidence.

## Reproduction and coverage

Put `audiobook-beeper` and `toolkit` on PYTHONPATH and use project dependencies:

```powershell
python audiobook-beeper/experiments/ima-3bit-residual/diagnose.py --output build/residual-diagnostic --ffmpeg path/to/ffmpeg.exe
python audiobook-beeper/experiments/ima-3bit-residual/probe.py --variant baseline --output build/residual-baseline --ffmpeg path/to/ffmpeg.exe
python audiobook-beeper/experiments/ima-3bit-residual/probe.py --variant ima4 --output build/residual-ima4 --ffmpeg path/to/ffmpeg.exe
python audiobook-beeper/experiments/ima-3bit-residual/audit.py
```

`--variant` also accepts the other table controls. `--replay` accepts a
stored `controls/<variant>/soundtrack.ima.gz` carrier to reconstruct without
encoding. All seven stored carriers were decoded/rendered by the consolidated
script with SNR and every band score matching the original runs to 1e-10 dB;
`controls/*/replay.json` records this reproducibility check, not independent
native-player verification. A fresh baseline encode also reproduces the
stored carrier byte for byte; `controls/baseline/fresh.json` records its
46.562-second run and 21.600309-dB result. Original scripts/logs are retained in
`original-runs/` with their original temporary paths as provenance.

The initial full-part diagnostic needed source-silence padding past EOF to
account for the slightly slower output clock; the unpadded shape mismatch
produced no valid measurement. Preserve this failed attempt's explanation
rather than interpreting a truncated or stretched reference as a result.
