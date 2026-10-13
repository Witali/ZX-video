# AY spectral transfer experiments

Started2026-10-13 from `6168ba14`, branch `codex/ay-spectral-transfer`.
Follow [the saved implementation plan](../../../docs/ay-spectral-transfer-plan.md).
[Fuse source and software chip identification](FUSE_SOUND.md) and all four
bounded encoder milestones are complete. No new fitter passes the saved
admission guard; the current default is retained. This is opt-in research,
not a qualified new release. [Completion proof](evidence/completion.json).

## Stage1: direct integer-period candidates — complete, not admitted

Same prepared O. Henry[60,90),1500 states and baseline gain1.619215014884398.
The current14-register AY stream, including hardware envelope, replays its
saved WAV byte for byte. `spectral_fit.py` fits three square/noise/mixed
channels with real AY DAC codes. It searches interpolated peaks/subharmonics
and neighboring integer periods, assigning all3! channel permutations by
physical pitch continuity. The output is normal11-register/AY9 data at50 Hz.
Only one noise or mixed carrier is selected per frame, with one shared R6.
Templates approximate magnitude addition; full chip replay decides admission.

| Complete30-second trial | Log/level objective,dB | Level MAE,dB | Magnitude cosines512/2048/8192 | Decision |
|---|---:|---:|---|---|
| Current AY + hardware envelope |9.248850|1.367314|0.718194/0.709185/0.760072|Baseline|
| Direct512 |10.112593|1.360436|0.836898/0.789642/0.805211|Reject: combined error worsens|
| Direct2048 |10.711803|1.404012|0.779358/0.778900/0.805034|Reject: combined error worsens|

Dominant spectral components improve, but missing/extra weak-bin details
increase log error. Retain both failures; do not claim better speech. The
next authorized milestone tests inverse weighting/regional peaks against this
same baseline. No guard is weakened. Direct512/2048 peaks0.814667/0.786563,
zero clipping. Measured two-trial fitting/render/diagnostic time27.837460 s
excludes archive and baseline replay work.

[Stage1 report](evidence/stage1/report.json),
[common-scale full figure](evidence/stage1/spectrogram-full.png),
[detail](evidence/stage1/spectrogram-detail.png),
[direct512 audition](evidence/stage1/direct512/ay-preview.wav),
[direct2048 audition](evidence/stage1/direct2048/ay-preview.wav),
[current baseline](evidence/stage1/baseline.wav).

All2*1500 raw/packed states and complete WAV replays pass independently.
Three tests check independent bandlimited Fourier squares, off-note physical
periods/pauses/legal controls, and input failures before rendering. Initial
tests exposed aliasing in a discontinuous test square and NumPy2 uint8
multiplication overflow in the decoder helper; fix the test signal/casts
instead of relaxing the model assertion. Default encoder/player unchanged;
native hot-path instruction delta0 T. No new Fuse/physical-chip audio claim.

## Stage2: inverse weighting and regional peaks — complete, not admitted

At window512, exponent1 reduces the direct fit objective10.112593 ->9.926241;
adding four peaks per50..800/800..1800/1800..3500/3500..8000-Hz region gives
9.913041. Both remain worse than current AY9.248850. Level MAE1.417882/
1.419244 passes its bounded tolerance, but8192 dominant cosine0.728756/
0.730898 is below baseline0.760072 by more than0.005. Both are rejected.
The four complete streams, including exactly reproduced stage1 controls,
pass all1500 legal packed states and complete byte-exact WAV replays.
[Stage2 report](evidence/stage2/report.json),
[weighted audition](evidence/stage2/weighted512/ay-preview.wav),
[weighted + band audition](evidence/stage2/bands512/ay-preview.wav).
Next evaluate transition-aware candidates; retain the baseline selection.

## Stage3: transitions and existing feedback — complete, not admitted

Continuity strengths0.02/0.05/0.1 give objectives9.900928/9.901714/9.874857.
The strongest setting is the lowest scalar among these, but still fails
baseline9.248850 and its long dominant cosine0.735210 fails the guard.
One bounded existing-chip feedback round (fixed calibration, no pitch search)
plus existing hardware-envelope proposals reduces the strongest seed to
9.667439, with peak0.901259. It remains rejected. This comparison retains
the baseline's hardware-envelope capability; it is not an unfair comparison
of unrefined squares against a refined envelope output. The proposed full
level correction was below9.83 but failed headroom and was not accepted.
All optimizer histories are retained with their deterministic source/seed
registers; four final streams/WAVs pass complete exact replay and independent
AY9/AY12 decoding. [Stage3 report](evidence/stage3/report.json),
[feedback audition](evidence/stage3/with-existing-feedback/ay-preview.wav).
Next run the separately labeled subframe register-ramp probe on the retained
baseline, including exact channel/envelope restrictions and bus timing.

## Stage4: timed DAC-ramp probe — complete, not admitted to native playback

`timed_ay.py` emits AYE1 timestamp/register/value commands, with no PCM.
`render_timed_ay.js` applies each actual register separately to the vendored
chip core. One44.1-kHz sample separates writes (22.675737us), approximating
the21.991us spacing of the existing78-T loop. This is a nominal50-Hz model;
it is not an instruction-exact Spectrum/Fuse timing model. R13 sentinel255
skips a write and preserves the running envelope. Only fixed-to-fixed DAC
levels with unchanged tone/noise gates are faded; shared-envelope and routing
changes cannot independently fade three channels and are excluded.

| Timed30-second stream | Log/level objective,dB | Level MAE,dB | Instant DAC-step squared sum | Writes | Commands gzip bytes |
|---|---:|---:|---:|---:|---:|
| Serial current baseline |9.338099|1.582626|10.401989|19,574|67,644|
| Nominal2-ms eight-step ramp |9.326758|1.576297|8.125744|25,707|88,122|
| Nominal4-ms eight-step ramp |9.302608|1.578038|8.124667|25,707|88,872|
| Nominal8-ms eight-step ramp |9.264055|1.628808|8.098357|25,707|89,953|

Squared instantaneous DAC changes fall21.88..22.15%, below the probe's
pre-run25% threshold for justifying a native scheduler. This diagnostic uses
the exact same tone/noise/envelope phase before/after each command and counts
no ordinary square edges; it does not predict future pitch transients or
perceptual click audibility. All three probes slightly improve the timed
baseline's scalar error, but the absolute serial baseline already differs
from ideal atomic rendering. Do not attribute that difference to ramps.
All are rejected for native integration under this bounded decision rule;
no native scheduler consumes AYE1, and existing player code remains unchanged.

In the same serial model, regional fitting has squared DAC steps5.013071;
continuity0.1 has4.684238 (-6.56%). This reduces amplitude/mixer steps while
its spectral loss prevents admission. Six complete timed streams pass all
1500 final states, bus spacing,1323000 samples, two identical continuous
replays and zero clipping. Current stricter exporter reproduces all six byte
for byte. The original pre-validation producer snapshot is retained with its
matching source hash in `ramps/producer-timed_ay.py.gz`.
The original renderer is saved too. Current export/render explicitly force
the AY target regardless of ambient settings and reproduce all six streams
and full WAVs exactly; the stricter validation does not alter these controls.

Listen to [current serial model versus4-ms ramp](evidence/ramps/before-after.wav):
old0..30 s, silence30..31 s, ramp31..61 s. This audition remains an unqualified
model alternative. [Six-trial report](evidence/ramps/report.json),
[common-scale ramp comparison](evidence/ramps/spectrogram-detail.png).

## Final target comparison and verification

The general experimental CLI supports both real DAC targets. With identical
source, gain,512/weight1/band4/continuity0.1, AY gives9.874857 /level1.425594,
YM2149 gives9.814675 /level1.338828. Each is rendered with its actual selected
DAC/envelope model, not AY-encoded registers relabeled as YM. This is a target
comparison, not proof that Fuse has a Yamaha chip or that its output improves;
Fuse1.9.0 retains the AY behavior established above. [YM audition](evidence/ym2149/ay-preview.wav).
The general AY CLI separately reproduces the complete stage3 stream/WAV
byte for byte. No second source conditioning is applied.

All seven focused tests pass, including30 optional native probe fixtures.
Nine unique AY50-Hz streams, including current baseline, execute two complete
loops each in the independent Z80:27,000 fields, exact values, bank/loop/stack
checks. Existing11-register work is974 T ordinary /992 near boundary /
1091 bank /1079 restart. Existing14-register work is1166 T without shape
restart /1206 with restart; observed boundaries/loop reach1184/1224/1271/1283.
The same instruction paths and bytes are retained; hot-path delta0 T.
[Native report](evidence/native-streams.json) excludes ULA/IRQ/disk/Fuse sound.
No new physical-chip, cold-Fuse audio or movie-release qualification is made.

Common-source-scale [full comparison](evidence/comparison-full.png) and
[1.76..4.76-s detail](evidence/comparison-detail.png) include rejected fits too.
Visual inspection confirms stronger dominant tracks in direct512 but extra
upper-band energy and missing weaker texture; scalar loss is not hidden by
panel normalization. Best new completed50-Hz pipeline9.667439 remains worse
than current9.248850. The current encoder remains selected. Every trial,
rejection, source/core/producer hash and exact audition is retained. The plan
is complete; another search or native-ramp implementation needs a new request.

## Reproduce

With NumPy/Pillow and Node.js; native probe tests also need pyz801.3.0/z801.2.0:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies).Path
python -m unittest discover -s ay-converter -p test_spectral_fit.py -v
python ay-converter/analysis/ay_spectral_transfer/run.py --stage 1 --output .tmp/ay-transfer-stage1-replay
python ay-converter/spectral_fit.py ay-converter/analysis/o_henry/evidence/compact30/original-preview.wav --output .tmp/general-spectral-audition --weight 1 --band-peaks 4 --continuity .1 --output-gain 1.619215014884398
python ay-converter/analysis/ay_spectral_transfer/ramps.py --output .tmp/timed-probe-replay
python -m unittest discover -s ay-converter -p test_timed_ay.py -v
python -m unittest discover -s ay-converter -p test_psg_probe.py -v
```

Use a new output directory. `archive.py` checks producer hashes, independent
AY9 decoding and exact complete media replay before creating an immutable
stage archive. Registered data, fit controls, reports and auditions are
retained; transient chip buffers/noise-dictionary builds stay untracked.
Use stage commits6425a8b4/f7281fae/b1bdf12e for exact original producer-hash
assertions. Current helpers reproduce the corresponding control/audio data,
but later CLI/validation additions intentionally change their source hashes.
