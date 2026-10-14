# Generated-overtones reduction and true sine-carrier audition

2026-10-14 follow-up to `4b73f9ea`. The user hears extra high harmonics,
suggests mainly sine signals, and asks about the update rate. Retain the
entire90-second source, nine voices,50-Hz targets, smooth TL transitions,
fixed gain3.031479042166069 and the existing playback filter.

- **[Revised complete YM3812 WAV](overtones-evidence/ym3812-preview.wav)**
- **[Previous0..90 s, silence, revised91..181 s](overtones-evidence/before-after.wav)**
- [VGM](overtones-evidence/ym3812.vgm), [VGZ](overtones-evidence/ym3812.vgz)
- [Source/previous/revised spectrogram](overtones-evidence/spectrogram-full.png)
- [Detail20.34..23.34 s](overtones-evidence/spectrogram-detail.png)
- [All outcomes and selection](overtones-evidence/report.json)
- [Native oscillator measurements](overtones-evidence/purity.json)
- [Complete independent verification](overtones-evidence/verification.json)

## Cause and selected register changes

The original sine carrier still had a modulator at TL63 with AR15. In the
pinned native core this is not an absent modulator: it produces measurable
harmonics. Use additive connection C0=1 and modulator AR=0 from silent reset.
The carrier remains waveform0 and retains its envelope, multiplier, frequency
and key schedule. The modulator stays silent even when its TL is changed to0.
There is no phase modulation. The chip's sine/DAC quantization still remains.

Four integer-cycle native steady-tone checks, with no playback filtering:

| Fundamental,Hz | Previous harmonics,dB | Revised,dB | Reduction,dB |
| --- | ---: | ---: | ---: |
|48.551 |−25.634 |−66.460 |40.826 |
|194.203 |−25.622 |−62.680 |37.058 |
|388.405 |−25.645 |−60.306 |34.661 |
|776.811 |−25.609 |−59.559 |33.950 |

These are summed harmonic-bin power relative to the fundamental for these
four held tones, not whole-song noise, silicon measurements or a listening
grade. The revised modulator-silence/native samples are repeatable exactly.

The selected `cap10` also compares source and previous output around each
high carrier in aligned512/2048 Hann windows. Require excess at both scales,
allow1.5 dB, blend correction from1800 to3000 Hz, and limit it to12 dB.
Only72 of40,500 channel/field TL targets need attenuation. Every FNUM/BLOCK,
carrier multiplier and key state is identical to the previous soundtrack.
No new high-frequency filter or gain normalization is used.

## Full-song results and explicit selection limits

The earlier overall high-band power deficit hides individual added tones.
Measure positive bin-wise power difference from the source separately from
missing power on the same STFT grid. Do not equate band totals with fidelity.

| Measure | Previous | Selected |
| --- | ---: | ---: |
| Extra1.8..8-kHz power/source band power,window2048 |0.158338 |0.157631 |
| Extra4..8-kHz power/source band power,window2048 |0.042710 |0.040636 |
| Missing1.8..8-kHz fraction,window2048 |0.523134 |0.526509 |
| Low-band cosine512/2048/8192 |0.962842/0.860398/0.799585 |0.961751/0.860229/0.799607 |
|20-ms level MAE,dB |1.379574 |1.368393 |
| Combined log/level objective,dB |9.444631 |9.897613 |
| Peak |0.902472 |0.904347 |
| Writes |242,868 |242,850 |
| VGM/VGZ bytes |992,252/369,327 |992,180/369,336 |

Extra4..8-kHz bin power falls24.4575/4.8548/3.7432% for windows512/2048/8192.
Across1.8..8 kHz the reduction is4.1247/0.4467/0.3555%. Some weak matching
harmonics are lost too; the full log score worsens. This is an oscillator-
purity audition with modest whole-song excess reduction, not a claim that
all ringing is removed or the complete spectrogram becomes more accurate.

The first source-cap experiment retains three full trials: pure setup only,
strength0.6 and strength1.0. All preserve the content/level guards (low-band
cosine loss<=0.005; added high-band missing fraction<=0.04; level MAE increase
<=0.20 dB), but none meets an exploratory20% aggregate1.8..8-kHz excess
reduction target. That failed guard remains recorded, not silently weakened.

Three further pure-sine refits use1024/exponent0 and2048/exponents0/0.5,
no regional weak-peak quota and unchanged calibration. Their2048 excess
fractions0.095682/0.085109/0.087828 are lower, but short-scale excess,
missing-detail or low-band guards fail. The exponent0.5 trial peaks1.050863,
clipping11 samples at fixed gain; it is rejected. No gain change conceals it.
The initial runner aborts at that clipping assertion. `recover_refit.py`
reuses all three exact completed NPZ targets, retains the failed attempt,
and completes the full reports/replays without admitting clipping. A first
archive call then encountered the missing interrupted report; its partial
scratch copy was preserved and the final archive uses the recovered report.

For the user's explicit sine suggestion, select a narrower audition goal:
at least30-dB held-tone intrinsic harmonic reduction, lower extra bin power
at every scale, and all original content/level guards still passing. `cap10`
has the lowest2048 upper-band excess among the three preserved-note variants.
The aggregate20% target is still marked unmet. Preserve all six trials.

## Timing, verification and reproduction

Frequency and level targets still arrive50 times/s, every20 ms. Eight
intermediate raised-cosine TL steps require extra real writes inside the
field; serial45.35-microsecond slots finish within the next field. Generators
run continuously; ordinary frequency updates do not reset phase. Key-on
can reset the phase when a previously silent voice starts a note.

Twelve tests cover the old chip/export rules plus four new purity, source-cap,
source-sine fit and invalid-input checks. All six4500-field streams audit all
nine states and bus spacing, replay4,474,431 native samples and recover every
3,969,000 PCM sample exactly. Only the explicitly rejected third refit clips.
The selected stream is clipping-free, its notes/keys match the predecessor,
and every181-second comparison segment is byte-identical to the WAVs. Source,
old evidence, pinned core, producer and media hashes pass. Native oscillator
checks repeat exactly. These are complete emulator runs; no physical chip,
Z80/disk delivery or Spectrum hot-path change is claimed.

With the same dependencies as the original trial, from the worktree root:

```powershell
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies/ymfm).Path
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/analysis/ym3812_sea_foam/overtones.py --output .tmp/new-overtones
# This historical runner rejects its third full fit on fixed-gain clipping.
python ay-converter/analysis/ym3812_sea_foam/refit_overtones.py --output .tmp/new-refits
python ay-converter/analysis/ym3812_sea_foam/recover_refit.py --fitted .tmp/new-refits --output .tmp/new-refit-reports
python -m unittest discover -s ay-converter/analysis/ym3812_sea_foam -p test_overtones.py -v 2> .tmp/new-tests.log
python ay-converter/analysis/ym3812_sea_foam/finish_overtones.py --setup .tmp/new-overtones --refit .tmp/new-refit-reports --tests .tmp/new-tests.log --output .tmp/new-overtones-archive
$env:PYTHONPATH='.tmp/dependencies/ymfm;ay-converter;ay-converter/analysis/ym3812_sea_foam'
python -m unittest test_experimental_ym3812 test_overtones -v 2> .tmp/new-all-tests.log
python ay-converter/analysis/ym3812_sea_foam/verify_overtones.py --evidence .tmp/new-overtones-archive --tests .tmp/new-all-tests.log
```

Add `ay-converter` and `ay-converter/analysis/ym3812_sea_foam` to PYTHONPATH
when running tests. `verify_overtones.py --evidence OUTPUT --tests LOG`
independently rechecks the archive; provide a combined12-test unittest log
from `test_experimental_ym3812` and `test_overtones`. Use new output directories.
The original baseline, historical CLI and native release players are unchanged.
