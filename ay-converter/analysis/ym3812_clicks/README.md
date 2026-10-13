# YM3812 frame-transition click reduction (2026-10-13)

The user likes the nine-channel audition but hears clicks, suspected at audio
frame boundaries. This bounded follow-up uses the exact1500 targets and constant
gain from `60e8bb3e`, prepared O. Henry[60,90). There is no spectral refit.
Worktree `.worktree/ym3812-speech`, branch `codex/ym3812-speech`.

Listen to [the revised30-second output](evidence/ym3812-preview.wav), or
[the61-second comparison](evidence/before-after.wav): old0..30 s, silence30..31 s,
revised31..61 s. [A slightly slower transition](evidence/slower-transition.wav)
is retained too. Listening acceptance is pending; measured reductions do not
prove that every click is inaudible.

## Cause and actual chip commands

The old VGM performs an abrupt carrier TL update and retunes each channel at
the start of each20-ms frame. Its entire timed write burst ends within1.859411
ms. Equal1-ms derivative windows at boundaries versus10-ms offsets give a
power ratio1.169034: ordinary tone slope is included, so this alone is not a
click detector. A more specific diagnostic clones the complete chip state
before each timed write, predicts the first native output sample with the old
registers, and compares it with the sample after that write. Both predictions
use the same oscillator/envelope state. Sum squared perturbations over the
whole30 seconds rather than averaging over the changing number of writes.

The old immediate write effects have squared sum6.984949; carrier TL changes
account for6.664998, or95.42%. Largest output-gain-scaled sample perturbation
is0.286625. This diagnostic still includes legitimate pitch/envelope changes,
phase dependence and quantization; it is not a perceptual click score.

`experimental_ym3812.smooth_vgm()` replaces each carrier amplitude step with
eight raised-cosine targets, quantized to real0.75-dB TL levels. A newly keyed
channel is tuned at TL63 before fading in; key-off follows the quiet end of
its fade. Carrier MULT, FNUM low byte and BLOCK/FNUM high byte cannot be
written atomically. Their order minimizes the worst temporary excursion
outside the old/new pitch interval, then unnecessary frequency travel.
The small residual modulator at TL63 stays the same real operator as before.

This adds real YM3812 register commands. It does not add interpolated samples
to the chip output, reset phases in software, modify the source, or change
the fixed20-Hz coupling/8-kHz fractional resampling filter. Nine sine carriers,
exact frame targets and gain2.3357702813587116 are unchanged. The new exporter
is restricted to sine patches0/14; transitions between general FM/waveform
patches remain outside this experiment.

Writes remain45.35us apart. Nominal2-ms deadlines can overrun because writes
to nine channels consume bus time: the selected stream's last bus slot ends
at up to4.217687 ms (95th percentile3.492063 ms). It is not an atomic2-ms
crossfade. Every target is attained before the next exact20-ms boundary;
all1500 boundaries, key states and target register values pass independently.

## Eight complete same-target trials

| Export | Log/level objective,dB | Level MAE,dB | Squared write-effect sum | VGZ bytes |
|---|---:|---:|---:|---:|
| Abrupt baseline |7.242039|0.304720|6.984949|61,653|
| Historical4-step linear4-ms TL ramp |7.338953|0.521878|1.990289|109,031|
| **8-step cosine, nominal2 ms, ordered pitch** |**7.376224**|**0.424978**|**1.398379**|**134,200**|
|8-step cosine4 ms, ordered pitch |7.377505|0.487336|1.411234|142,306|
|8-step cosine8 ms, ordered pitch |7.412581|0.749348|1.376354|145,147|
|8-step cosine4 ms, old pitch order |7.364102|0.495150|1.456972|138,338|
|4-step cosine2 ms, ordered pitch |7.356537|0.395960|2.203186|108,444|
|4-step cosine4 ms, ordered pitch |7.344730|0.515903|2.207496|111,214|

The selected eight-step2-ms trial balances the observed results: **79.9801%**
less squared immediate write effect and75.78% lower largest perturbation
(0.286625 ->0.069429), with the smallest level/log penalty among the eight-step
trials. Four steps leave materially more step energy. Eight ms has slightly
less perturbation energy but substantially worse per-frame levels. Ordering
helps transient pitch and dominant spectral agreement, with a small log-score
tradeoff. These are measured tradeoffs, not an independent perceptual ranking
or a global-optimum claim. All trials, including rejected alternatives, retain
their VGZ streams and complete measured results in [report.json](evidence/report.json).

| Selected saved-WAV measure | Before | After |
|---|---:|---:|
| Magnitude cosine512 |0.944152|0.944361|
| Magnitude cosine2048 |0.899093|0.899641|
| Magnitude cosine8192 |0.903570|0.904923|
| Root cosine512/2048/8192 |0.899614/0.920404/0.929875|0.898599/0.915341/0.927015|
| Level MAE,dB |0.304720|0.424978|
| Boundary/interior derivative-power ratio |1.169034|0.986364|
| Peak |0.892415|0.792078|

The combined log/level objective worsens0.134185 dB, while all three dominant
magnitude cosines improve slightly. Root cosines worsen. Fixed global gain
is preserved, not adjusted to hide the tradeoff. See common-source-scale
[full spectrogram](evidence/spectrogram-full.png),
[detail](evidence/spectrogram-detail.png), and
[energy by phase in the frame](evidence/frame-phase.png). The phase plot includes
ordinary oscillation energy and uses the same absolute scale for both traces.

## Verification and reproduction

Eight unit tests cover native chip constraints, actual TL steps and shapes,
nine distinct voices, full register timing, malformed inputs, exact smooth
targets, reduced native3.5..8-kHz edge power in a one-carrier amplitude test,
and an equivalent-pitch MULT/BLOCK retune avoiding a double-frequency burst.
All eight full1500-frame streams pass independent register audits and two
continuous native replays. The counterfactual diagnostic does not disturb
the real replay. Each has1491477 native samples /1323000 output samples,
zero native-chip/output clipping, only YM3812 writes/waits, and exact duration.
The old VGM/WAV replay byte for byte. The revised CLI separately reproduces
the selected WAV/VGM/VGZ byte for byte; the comparison retains exact segments.

The selected stream has82,166 writes,337,171 VGM bytes /134,200 VGZ bytes.
Smoothing roughly doubles writes and makes the standard compressed VGM2.18
times larger. This is not a compact native Z80 command format. No player hot
path, release TRD, or six-voice model changes; no native T-state delta applies.
Pinned ymfm-py0.2.0 and the same core hash/limitations as
[the original experiment](../ym3812/README.md) apply. Physical chip/Z80/disk
delivery remains unqualified.

With the existing local dependency setup:

```powershell
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies/ymfm).Path
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/experimental_ym3812.py ay-converter/analysis/ym3812/evidence/reference.wav --controls ay-converter/analysis/ym3812/evidence/selected-controls.npz --gain 2.3357702813587116 --output .tmp/ym3812-click-replay
python -m unittest discover -s ay-converter -p test_experimental_ym3812.py -v
python ay-converter/analysis/ym3812_clicks/compare.py --output .tmp/ym3812-click-comparison
python ay-converter/analysis/ym3812_clicks/verify.py --cli .tmp/ym3812-click-replay
```

Use new output directories. Saved controls default to the selected nominal2-ms,
eight-step ordered exporter. New sine fits use it too; the explicit
`--legacy-sine-transitions` flag and historical `vgm()` preserve old streams.
The complete bounded deliverable is archived; further fitting or hardware
experiments require a new user request.
