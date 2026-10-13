# AY spectral transfer experiments

Started2026-10-13 from `6168ba14`, branch `codex/ay-spectral-transfer`.
Follow [the saved implementation plan](../../../docs/ay-spectral-transfer-plan.md).
[Fuse source and software chip identification](FUSE_SOUND.md) are verified;
encoder milestones remain in progress. This is opt-in research, not a changed
default or a qualified release.

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

## Reproduce

With NumPy/Pillow and Node.js; native probe tests also need pyz801.3.0/z801.2.0:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies).Path
python -m unittest discover -s ay-converter -p test_spectral_fit.py -v
python ay-converter/analysis/ay_spectral_transfer/run.py --stage 1 --output .tmp/ay-transfer-stage1-replay
```

Use a new output directory. `archive.py` checks producer hashes, independent
AY9 decoding and exact complete media replay before creating an immutable
stage archive. Registered data, fit controls, reports and auditions are
retained; transient chip buffers/noise-dictionary builds stay untracked.
