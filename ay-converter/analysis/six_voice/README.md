# Six-voice programmable-waveform experiment

Completed 2026-10-13 from `e38f3c2e`, at the user's request for a hypothetical
generator with six AY-like voices and selectable square/triangle/sine shapes.
The bounded input is the same O. Henry source [60,90) used by the preceding
30-second audition. Its prepared 22050-Hz PCM16 is reused byte-for-byte,
without a second dynamic-range compressor or a fresh source edit.

- [Six selectable-waveform voices](evidence/six-voice-preview.wav)
- [Six square-only voices](evidence/six-square-preview.wav)
- [Previous actual AY-model audition](evidence/previous-ay.wav)
- [Exact prepared reference](evidence/reference.wav)
- [Measurements](evidence/report.json) and [control replay proof](evidence/verification.json)

## Explicit hypothetical model

`../../experimental_six_voice.py` implements six continuously running
oscillators. Each voice receives a 12-bit clock period, 4-bit fixed volume,
waveform and tone/noise/mixed routing at 50 Hz. The clock is 1773400 Hz;
frequency is clock/(16*period), with period1..4095. Volume uses the existing
16-code AY DAC table. A shared17-bit maximal-length LFSR has period1..31.
Mixed mode gates the unipolar oscillator by its common noise bit. Noise-only
holds the tonal gate high. Oscillator and noise phases survive field updates
and muted fields. The output is a mono sum of the six voices.

Waveforms are unit unipolar square, linear triangle or sine followed by the
selected DAC amplitude. The renderer uses fourfold oversampling, an output
FIR and a1024-output-sample moving DC mean. Finite oversampling/filtering is
an approximation, particularly for square harmonics. This does not model a
specified analogue board. Fixed-volume mode is used: no hardware envelope,
sample-rate volume interpolation, encoded phase resets or source PCM mixing.
The experiment is not an actual AY register stream, Z80 player or TRD.

## Fit and bounded verification

At each20-ms field, interpolated spectral peaks propose integer periods and
their subharmonics. Sparse Hann dictionaries cover square1/h, triangle1/h^2
and sinusoidal harmonics. Six nonnegative components are selected with
source-only relative masking, an RMS constraint and channel/shape continuity.
Noise needs source broadband evidence and uses a median-floor colour estimate.
This magnitude model ignores phase cancellation; complete rendering supplies
the final decision.

Each variant receives one fixed whole-stream calibration. Volume half/full,
shared-noise period offsets and (for the selectable variant) an all-sine
proposal are accepted only if full rendered objective improves within peak
headroom. Calibration is never changed between proposals. The square control
cannot accept a different oscillator shape. This is one bounded experiment,
not a global search or a listening-quality guarantee.

The same multiwindow masked spectral/RMS objective evaluates all three outputs
against exactly the same prepared PCM; no time or pitch alignment is added.

| Variant | Combined objective, dB | 20-ms level MAE, dB | Masked spectral MAE512/2048/8192, dB |
| --- | ---: | ---: | --- |
| Previous AY with its running envelopes | 9.24885 | 1.36731 | 10.05137 /8.59097 /7.66853 |
| Six fixed-volume squares | 9.41877 | 1.45010 | 9.92155 /8.84181 /7.97034 |
| Six selectable fixed-volume waves | 8.18696 | 2.03192 | 8.52776 /7.15469 /6.74494 |

The selectable result reduces the spectral proxy at all three windows, while
its field-level volume agreement is worse. Six square voices alone do not
beat the previous AY arrangement on the combined objective. The old AY uses
a different fitter and hardware envelopes, so its comparison does not isolate
voice count. The two new variants share the experimental fitter and differ
in permitted waveforms. These measurements are not percentages of perceived
quality or intelligibility.

Selected periodic channel-fields:2830 square,3198 triangle and2230 sine,
with70 noise-only and226 mixed fields. The30-second WAV has1323000 mono
PCM16 samples at44100 Hz, peak0.949982 and zero clipping. Its float RMS is
0.131256 versus prepared-source0.132312. Four independent tests pass:
analytic Fourier harmonic ratios, phase continuity against a direct reference,
shared noise/control validity, and off-note sinusoid plus source silence.

Both saved control streams reproduce their WAV files byte-for-byte without
reading the original PCM during synthesis. Input, baseline and producer
hashes match. The archive manifest preserves all data; WAV media use LFS.
Real AY conversion, its player instructions and existing releases are unchanged.

## Reproduction

The standalone folder's NumPy dependency is sufficient; no SciPy or Node
runtime is needed by this experimental renderer.

```text
python ay-converter/experimental_six_voice.py ay-converter/analysis/o_henry/evidence/compact30/original-preview.wav --output OUTPUT --ay-baseline ay-converter/analysis/o_henry/evidence/compact30/ay-preview.wav --square-control
python -m unittest discover -s ay-converter -p test_experimental_six_voice.py -v
python ay-converter/analysis/six_voice/archive.py OUTPUT --log RUN_LOG --tests TEST_LOG
```

The input must already be a prepared mono22050-Hz PCM16 WAV containing complete
20-ms fields. The CLI produces WAV, per-field control NPZ, feedback and report.
The archival command preserves exact input bytes and authenticates both
controls-only replays. This requested experiment is complete; no further model
or full-movie sweep is opened automatically.
