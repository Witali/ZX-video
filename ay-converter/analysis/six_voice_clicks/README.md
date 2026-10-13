# Six-voice click and ringing follow-up

The subsequent [spectral follow-up](../six_voice_spectral/README.md) changes
the current CLI defaults. This folder preserves the earlier completed run;
the reproduction command below explicitly requests its original settings.

Completed 2026-10-13 in `.worktree/six-voice-clicks`, branch
`codex/six-voice-clicks`, from `bd2a5be2`. The user reported clicks and periodic
ringing in the [previous six-voice audition](../six_voice/README.md) and asked
to continue this converter in its own worktree. This milestone keeps the same
prepared O. Henry source seconds 60..90 and produces a complete corrected
30-second listening candidate. Listening acceptance remains pending.

- [New 30-second audition](evidence/six-voice-preview.wav)
- [Before/after: original at 0..30 s, silence at 30..31 s, new at 31..61 s](evidence/six-voice-before-after.wav)
- [Exact prepared reference](evidence/reference.wav)
- [Same-control ablations and final comparison](evidence/comparison.json)
- [Complete replay and file verification](evidence/verification.json)
- [Converter run and bounded feedback](evidence/run.log)
- [Eight independent regression tests](evidence/tests.log)

## Diagnosis

[probe.py](probe.py) evaluates the old and new control states at the SAME
oscillator/noise phase at each 20-ms boundary. This excludes ordinary waveform
edges and natural noise-bit changes. The old control-induced jump RMS is
0.144476, maximum 0.719618. Its ensemble DC-step RMS is 0.117457, maximum
0.551612. Active voices have 2213 shape changes, 325 route changes and 3575
pitch jumps exceeding a semitone. Persistent oscillator phase alone does not
prevent a discontinuity when DAC level, shape or route changes abruptly.

The old output FIR cutoff was 19.845 kHz, while fitting and full-render quality
feedback see only 50..8000 Hz. Square-wave harmonics and control transients
above that objective's band remained audible in the WAV. These mechanisms
explain possible clicks and high ringing; they do not identify every sound the
user heard. No specific listening timestamp was supplied during this run.

## Explicit model change

The CLI now defaults to a **4-ms raised-cosine transition** and **8-kHz output
FIR cutoff**. Each voice morphs its level, waveform and tone/noise route from
the previous target to the current target using one continuously running
phase. Period changes still take effect at the field boundary; there is no
frequency glide, old/new frequency crossfade or extra oscillator. The triangle
now starts at its midpoint rising, aligning its fundamental phase with the
square and sine instead of switching by a quarter cycle.

Six phases, one shared LFSR, 12-bit periods, 16 target DAC codes and 50-Hz
control messages remain. Intermediate transition amplitudes and waveform
mixtures are an **explicit extension of the hypothetical synthesizer**. They
are not available through real AY fixed-volume writes. This WAV is not a
native AY, Yamaha, Z80 or TRD qualification. No existing player instructions
or release disks changed.

The direct Python `render()` defaults retain the old model for replay.
`--legacy-render` selects it through the CLI. New controls must be replayed
with the report's `render_options` and single `voice_gain`, as the archiver
does; the model settings are part of the reproducible sound.

## Bounded comparison and decision

Nine full same-control/same-gain ablations cover the original model, bandwidth
only, triangle alignment only, 2/4/8-ms transitions alone, and the three
combined settings. Filtering alone leaves the boundary/interior derivative
power ratio at 1.975, versus 1.864 originally. Transitions alone reduce it to
1.031..1.044. Combined settings reduce it to 1.106..1.121 and suppress output
above 9 kHz. Their objective errors are 8.389/8.362/8.314 dB for 2/4/8 ms.
Keep 4 ms as a short transition with no need for the longer half-field morph;
8 ms has a slightly better spectrum proxy but slightly worse level agreement.
All trials and unsuccessful feedback proposals remain in the saved reports.

The normal converter then fits the full reference again and recalibrates one
constant whole-stream gain. Its volume-0.5 proposal is accepted; volume-1.0,
sine-only and both shared-noise-period offsets are rejected. Final comparison:

| Diagnostic | Previous six voices | New candidate |
| --- | ---: | ---: |
| Combined spectral/level objective, dB | 8.186964 | 8.281203 |
| 20-ms level MAE, dB | 2.031917 | 2.002794 |
| Masked spectral MAE, 512/2048/8192, dB | 8.527756/7.154686/6.744938 | 8.488268/7.424385/6.828021 |
| Boundary derivative RMS, 1-ms windows | 0.0274105 | 0.0144173 |
| Interior derivative RMS, equal windows | 0.0200781 | 0.0136180 |
| Boundary/interior derivative power ratio | 1.863759 | 1.120837 |
| Output power fraction above 9 kHz | 0.00391550 | 0.000000000318746 |
| Source-relative excess fields in 1.8..8 kHz | 12 | 12 |

Boundary derivative power falls 72.3%; this is a discontinuity diagnostic,
not a count of heard clicks. Excess narrow components inside the analysis
band are **not eliminated**. The combined objective worsens 0.094238 dB while
short-field level agreement improves. Do not claim an intelligibility gain
or complete removal of all periodic ringing from these signal measurements.

The new file has 1323000 mono PCM16 samples at 44100 Hz, peak 0.912645 before
quantization, zero clipping, and float RMS 0.134261 versus source 0.132312.
Conversion including fitting/feedback takes 23.480 seconds on this host;
archival comparison/verification is additional work. Both old-model and new
controls-only replays match their complete WAV bytes exactly. The 61-second
comparison concatenates the existing PCM bytes without another quantization.
Eight tests cover harmonic ratios, phase persistence, shared noise, off-note
tone/silence, smooth transitions, fundamental phase alignment, out-of-band
harmonic rejection and invalid model settings. Source/producer/artifact
hashes and every 1500-state replay are checked.

## Reproduction

From the task worktree, using Python with NumPy:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/experimental_six_voice.py ay-converter/analysis/six_voice/evidence/reference.wav --output .tmp/six-voice-smooth --ay-baseline ay-converter/analysis/six_voice/evidence/previous-ay.wav --analysis-window 2048 --spectral-weight-exponent 0 --band-peak-count 0 --no-dc-compensation
python -m unittest discover -s ay-converter -p test_experimental_six_voice.py -v
python ay-converter/analysis/six_voice_clicks/compare.py --output .tmp/six-voice-comparison.json --candidate .tmp/six-voice-smooth
python ay-converter/analysis/six_voice_clicks/archive.py .tmp/six-voice-smooth --comparison .tmp/six-voice-comparison.json --log RUN_LOG --tests TEST_LOG
```

Capture the first two commands' output in `RUN_LOG` and `TEST_LOG` for archival.
The converter output and archive destinations must be new; use an isolated
checkout or a new output name when repeating the run. The previous audition
is retained unchanged. Further model searches and real-chip work require a
new milestone; this bounded follow-up delivers the candidate for listening.
