# Six-voice spectral reconstruction follow-up

Completed 2026-10-13 in `.worktree/six-voice-clicks`, branch
`codex/six-voice-clicks`, from `15d01878`. The user requests a source/output
spectrogram comparison and the closest practical reconstruction. Keep the
same exact prepared O. Henry source[60,90), six oscillators, 50-Hz targets,
16 DAC target levels, three shapes, shared noise, 4-ms transitions and 8-kHz
output filter. This bounded milestone evaluates sixteen complete candidates.

- [Source/refined output and signed difference, complete excerpt](evidence/source-result-full.png)
- [Source/refined output and signed difference, 2.56..5.56 seconds](evidence/source-result-detail.png)
- [Full source/previous/refined spectrograms and signed differences](evidence/spectrogram-full.png)
- [Detailed source/previous/refined comparison, 2.56..5.56 seconds](evidence/spectrogram-detail.png)
- [New 30-second audio](evidence/six-voice-preview.wav)
- [Exact prepared source](evidence/reference.wav)
- [Previous/new audio: old at 0..30 s, new at 31..61 s](evidence/before-after.wav)
- [Independent actual-WAV spectral diagnostics](evidence/spectral-report.json)
- [All sixteen trials, acceptance guards and retained controls](evidence/trials.json)
- [Complete verification](evidence/verification.json)
- [Twelve tests](evidence/tests.log)

## What the spectrogram shows

The previous smooth output loses much of the source's upper partials and
wideband speech detail. At the 2048-sample STFT scale its 2..4-kHz power is
0.315397 of the source, with 0.787981 source-relative missing bin power.
Its overall output RMS still matches the source: a full-track FFT reveals
**29.008758% of output spectral power below 50 Hz**, versus approximately
0.000727% in the prepared source. Moving unipolar DAC means at control changes
produce this artificial low-frequency component. The moving-mean AC coupling
used previously does not suppress it adequately, even with 4-ms transitions.
It consumes RMS calibration and headroom that should represent speech.

The previous 2048-sample analysis spans 92.88 ms, almost five control fields.
It smears rapid speech changes before selecting a 20-ms target. Plain
magnitude least squares also prioritizes loud partials; a global eighteen-peak
proposal budget can miss quieter formant regions.

The figures use a shared source peak, identical sample/time/frequency grids,
1024-sample Hann windows and a 20-ms hop. No image gets its own contrast/gain,
and no audio is time/pitch warped. Difference maps use the same source-only
-60-dB floor and +/-20-dB scale: blue is missing magnitude, red is extra.
The detailed interval is the previous output's worst three-second average
error, selected before examining the new output. Plots are numerical NumPy
STFT heatmaps rendered with Pillow; Matplotlib is not required.

## Changes and selection

The default experimental CLI now uses a **512-sample /23.22-ms analysis
window**, source-only **inverse-magnitude weights with exponent 1**, and up to
four additional peaks per 50..800, 800..1800, 1800..3500 and 3500..8000-Hz band.
Weights stop growing below 2.5% of each field's source peak. Frequency proposals
remain actual integer periods; final acceptance uses the complete running
oscillators and unpooled 512/2048/8192-sample evaluation.

The mixer also explicitly compensates its control-induced DC component.
Each tone/noise target has expected mean 0.5 times its level, and a gated
tone/noise product has mean 0.25 times its level. Subtract the old/new expected
means with the same raised-cosine transition before ordinary AC coupling.
This uses controls only, preserves low tones and phase, and adds no oscillator
or source samples. It is an **explicit balanced-output extension of the
hypothetical mixer**, not a capability of real AY fixed-volume registers.

Initial inverse weighting/band proposals alone give objectives
8.288128/8.286017/8.306427/8.322892 dB and fail the all-scale guard. DC
compensation with the original window improves the objective to
7.642938/7.543670/7.511460 dB for exponents 0/0.5/1. Shortening the window
improves it further. Every attempted setting remains in
[trials.json](evidence/trials.json), including rejected and superseded results.
Early trial records without an `analysis_window` key use the then-fixed2048
window; later records store it explicitly.

Selection requires improvements over the prior WAV at ALL three scales in
magnitude cosine, root-magnitude cosine, log error and spectral convergence,
plus level MAE improvement and sub-50-Hz power below 1%. The lowest eligible
objective is exponent1/window512: **6.771538 dB**. Exponent1.5/window512 has a
lower scalar objective6.723018, but its long-window magnitude cosine worsens
0.852582 ->0.846768 and spectral convergence worsens0.483057 ->0.498788.
Reject that tradeoff instead of describing a single lower number as success.

## Actual saved-WAV results

All values below compare the actual PCM16 files with the same source, with
one identical decimation filter and no post-hoc gain adjustment. Small
differences from converter float metrics are PCM16 quantization.

| Metric | Previous smooth output | Refined output |
| --- | ---: | ---: |
| Combined spectral/level objective, dB | 8.281245 | 6.771566 |
| 20-ms level MAE, dB | 2.002844 | 0.789174 |
| Masked spectral MAE, 512/2048/8192, dB | 8.488287/7.424396/6.828067 | 7.137307/6.399630/5.949129 |
| Magnitude cosine, 512/2048/8192 | 0.820376/0.823144/0.852582 | 0.899120/0.848475/0.864305 |
| Root-magnitude cosine, 512/2048/8192 | 0.877264/0.873759/0.899170 | 0.914079/0.901872/0.920446 |
| Spectral convergence, 512/2048/8192 | 0.423273/0.465396/0.483057 | 0.282958/0.408591/0.460184 |
| Power below 50 Hz | 29.008758% | 0.137689% |
| Power relative to source, 2..4 kHz | 0.315397 | 0.846484 |

Band power agreement does not mean agreement in the same bins. Above 4 kHz,
missing and extra bin power remain large even though total band power is now
close to the source. The full/detailed maps show this remaining structure.
Six constrained shapes cannot independently control every partial or recreate
an arbitrary source noise realization. Further fitting may improve individual
regions; neither a global optimum nor speech intelligibility/listening
acceptance is established by these signal metrics.

The complete candidate is 1323000 mono PCM16 samples at44100 Hz, float peak
0.838500, RMS0.132497, zero clipping. Its normal standalone conversion takes
20.370 seconds on this host; comparison, search and archival work are additional.
Twelve tests pass, including independent short/long Hann scaling, retention
of a quiet upper tone, DC-energy suppression with tone preservation, previous
harmonic/phase/noise tests and invalid settings. All1500 states, the current
candidate, the previous WAV and ALL sixteen rejected/retained trial streams
replay byte-exactly from controls/model parameters only. Source/producer/file
hashes are checked. Rejected WAVs are reproducible from their retained NPZ
controls, gain, renderer settings and SHA256; their duplicate media is omitted.
Existing native players and release disks are unchanged.

## Reproduction and compatibility

From the task worktree with NumPy (Pillow additionally for figures):

```powershell
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/experimental_six_voice.py ay-converter/analysis/six_voice_clicks/evidence/reference.wav --output .tmp/spectral-rebuild --baseline ay-converter/analysis/six_voice_clicks/evidence/six-voice-preview.wav
python ay-converter/analysis/six_voice_spectral/analyze.py --output .tmp/spectral-figures --candidate .tmp/spectral-rebuild/six-voice-preview.wav
python -m unittest discover -s ay-converter -p test_experimental_six_voice.py -v
```

`search.py` accepts `--window-size`, `--weight`, `--band-peaks` and
`--dc-compensated` to reproduce the recorded trials. `archive.py` receives the
build, plots, eleven `--trial-root` folders and saved run/test logs, verifies
all sixteen streams and the guard, then creates a new evidence directory.
Use new output directories when reproducing; archived evidence is immutable.

Direct Python `fit()`/`dictionary()` and `render()` defaults retain the original
fitter/render for historical replay. `--legacy-render` selects that original
CLI model and fitter. To reproduce the immediately preceding smooth audition,
use `--analysis-window 2048 --spectral-weight-exponent 0 --band-peak-count 0
--no-dc-compensation`. The new `--baseline` supports hypothetical-model
comparisons while `--ay-baseline` retains its actual AY label. The prepared
reference is now copied byte-for-byte by the CLI.

This bounded deliverable is complete, with listening acceptance pending.
Do not start further shape/channel/hardware experiments automatically.
