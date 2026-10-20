# DHA precision and model provenance audit

This is a read-only audit of `C:/Work/z80-tester/audio/lib/dha-codec`.
The inspected repository was not modified. Source hashes and exact line
references are retained in [report.json](report.json). The audit reads C and
documentation and exhaustively evaluates all 511 declared predictor values;
it does not execute the C decoder or Z80 player, train, encode, resample, or
measure audio quality.

Run the standalone reproducer without importing tester research modules:

```powershell
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B audit.py --source-root C:/Work/z80-tester
```

The predictive decoder stores `q` in an `int16_t`, but permits only
`-256..254`: 511 distinct internal values. Its public PCM16 output is
`(((q+257)/2)-128)*256`, giving exactly 256 levels with eight zero low bits.
The separate raw PCM16 fallback preserves the input; this does not make
predictively compressed frames full precision. The decoded `state.q` and
`dha_encode_trajectory()` expose the internal value. A new adapter could use
`q*128` to retain all 511 levels, but that is nine-bit amplitude precision,
and differs from the existing output by 0 or 128 PCM16 units.

The encoder's loss function explicitly compares the rounded PCM8 output
with the original PCM16 target. Therefore using raw q in a new modulator
changes the signal being scored; a higher precision buffer alone does not
prove an improvement. The optional `dha_pdm_next()` helper is a first-order
eight-bit accumulator accepting an unsigned eight-bit target. Its caller
owns scheduling and reconstruction filtering.

The fixed default model is trained on this same song: all 375,000 samples
of the retained 56..71-second excerpt at 25 kHz. `probe.py::fit_model()` fits
four coefficients by ordinary least squares to a frozen reconstructed
history and the prepared reference. Its independently rounded 1024 bytes
hash to `70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f`;
this audit hashes the actual C array and confirms that identity. The model
is not trained on a source-independent corpus. The library copies this
frozen model and ANS book into caller-owned stream tables; its search does
not refit them. Using the same frozen model across sources is a legitimate
labelled baseline, but generic quality remains to be measured. Per-source
residual/gain selection is part of encoding, not coefficient retraining.

Default search settings are beam 64, eight gain candidates, lookahead two,
rate penalty 82 and PCM fallback enabled. These search settings do not
request a fixed bit rate or guarantee an error bound. The file carries the
actual predictor and ANS tables. The PC DHAF framing is a separate transport
from the compiled-first Z80 ROM wire, so the library file cannot simply be
substituted into the existing Spectrum player.

The retained firmware documentation reports 401 T synthesis plus 399 T
parsing per 800-T sample at 20 MHz / 25 kHz. These are the other project's
published counts, not a native execution or an optimization bound from
this audit. Its 25-kHz unsigned R2R measurement does not establish quality
or timing of our 8-kHz EAR disk. A 448-T Spectrum port, RAM layout, and
full playback still need separate proof.

All facts are scoped to the retained source hashes. No default player,
encoder, model, disk image or older experiment was changed.
