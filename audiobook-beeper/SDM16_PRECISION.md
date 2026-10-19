# Reconstructed16-bit input to SDM

2026-10-19. The user's proposed precision mechanism has been implemented as
an automatic standalone C research program, with an independent exact Python
reference. This is a complete nine-source **host counterfactual**, not a new
Spectrum player or replacement TRD. The source-independent quality goal is
still active.

## Where precision is currently lost

The IMA decoder already reconstructs a16-bit predictor. The continuous
player keeps its unsigned-biased value in IX and adds16-bit IMA deltas.
However, `pcm_high_lookup` uses IXH to select a64-level modulation input:

```
unsigned = signed_predictor + 32768
existing_input = floor(unsigned / 1024) / 64
proposed_input = unsigned / 65536
```

Thus all eight IXL bits and two low IXH bits currently disappear at this
boundary. A16-bit container alone changes nothing. A valid implementation
must demonstrate that those lower bits affect the modulator's carried state
and eventual source pulses. Source preparation stays the same PCM8 reference
in this experiment; this does not claim16-bit original-source fidelity or
alter the source/gain/bandwidth to obtain a better score.

Normalization has no half-LSB bias: signed0 is exactly duty0.5, and maximum
32767 is65535/65536, not1. The new model agrees with the old one at each of
the64 zero-origin anchors `signed=1024*k-32768`.

## Separate input and state precision

The new C program has three modes, all with beta0.5 and the existing449-T
ordinary table weights. Modulation order does not change in this milestone.

| Mode | Input | State between packets |
|---|---|---|
|A, authenticated control|64 input levels|Original16 accumulated-error codes and two recent-error codes|
|B, input-only control|Full reconstructed PCM16|The same rounding/clipping asA|
|C, state-precision control|Full reconstructed PCM16|Continuous f64 accumulated/recent state; no packet or bank resets/clipping|

All variants use the same complete decoded IMA samples and physical449-T
timeline, including real page/bank additions. Ordinary modulation weights
are not silently changed to absorb those sparse holds. The original IMA
nibbles remain frozen; they were optimized jointly forA and have **not** been
reoptimized forB/C. A total-quality regression is not a proof that a new
matched encoder cannot improve, nor is this an SNR upper bound.

Six tests compare all2048 anchor words/successors with the original table
and an exact Fraction implementation, check175 full16-bit cells, compare
whole A/B carried trajectories, and independently check continuousC state.
A one-LSB example is signed37 versus38: A is unchanged; B changes its first
successor and its third output word. This demonstrates real lower-bit
influence while also exposing the discontinuities of the coarseB state.

## Measured result and limits

All nine complete original sources finish. Every A packet word and successor
matches the existing implementation, and all nine archived original-clock
scores reproduce exactly. The same continuous f64 filter,768-kHz area
integration, fixed100-ms edges and unfitted original8-kHz reference are used.

| Complete song metric,dB |A|B|C|
|---|---:|---:|---:|
|SDM reconstruction versus decodedIMA16, diagnostic|25.831087|26.270322|26.579564|
|Total versus original8-kHz source|20.250316|19.096820|19.118673|

The song's SDM diagnostic improves0.439235 dB from full input precision and
0.748477 dB with continuous state as well. The total falls on the frozen old
IMA path. Across the corpus B has eight total-SNR/nine RMS regressions; C has
six/seven. Short original silence RMS is0.0154867382 inA and approximately
0.0155139391 inB/C. Noise, AM/delay and coherent-line diagnostics remain saved;
the experiment does not establish absence of flutter, AM or added background.
Decoded near-silence can have a tiny nonzero reference, producing an extreme
PDM diagnostic SNR. Use absolute original-silence RMS for background decisions.

The standalone C program uses no Python child, Python DLL or BLAS dependency.
Python performs input authentication, rendering and diagnostics. It retains
all1,195,520 decoded source samples across27 variant runs; the179-file archive
contains packed pulse words, carried-state bytes, source/IMA identities,
producer snapshots, listening WAVs, diagnostics and exact parity checks.
Raw f64 arrays remain a reproducible ignored cache. No full emulator run is
claimed for these new modulators, and no physical sample timing was changed.

[Whole-corpus results](experiments/song-snr/evidence/sdm16-precision/report.json),
[parity evidence](experiments/song-snr/evidence/sdm16-precision/parity.json),
[independent archive audit](experiments/song-snr/evidence/sdm16-precision/audit.json).

```powershell
python -m unittest discover -s audiobook-beeper/experiments/song-snr `
  -p test_sdm16_precision.py -v
python audiobook-beeper/experiments/song-snr/sdm16_precision.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --output .tmp/reproduce-sdm16 --scratch .tmp/reproduce-sdm16-cache
```

## Implementation still required

The present fixed lookup layout and CPU schedule do not implementB orC.
More source RAM does not automatically enlarge fixed packet/decoder code
space. Expanding the complete song to raw packed128-kHz pulses would require
approximately1.44 MB and lose seamless residency on Pentagon1024.

The next step is a CPU/RAM-feasible representation that retains lower-bit
influence, followed by reoptimization of the IMA encoder for that actual
modulator and complete own-clock playback/artifact checks. Input precision,
state precision and true second-order shaping remain separate mechanisms.
The old25-level/reduced-gain SD2 port must not be repeated as an apparent
precision upgrade. Existing encoders, player defaults and delivered b96763ca
remain unchanged.
