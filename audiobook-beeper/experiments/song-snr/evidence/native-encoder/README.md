# Complete C waveform encoder

2026-10-14. The unchanged `ima_waveform_encoder.py`, `ima_beam.py` and
`clock_control.py` remain the Python reference. New native sources implement
the complete waveform beam search, prefix replay, two 64-sample settling
blocks and nibble packing in C. No Python sample-loop callbacks occur.
Model preparation, input validation and the surrounding conversion front end
remain in Python. No Spectrum instructions or audio measurement settings
change in this performance stage.

## Exactness and measured performance

`python-reference.json` records a complete fresh Python comparison on all
nine full sources, including 720,384 samples of the main song. All bytes match
the initial complete C core. Song search took 24.7596 seconds in C against
282.7497 seconds in the unchanged Python reference, 11.42 times faster.
Its model preparation took 7.5447 seconds separately. These sequential wall
times were measured on this host with other research jobs; they are not a
machine-independent throughput promise.

`benchmark.py` checks the final C producer and the standalone executable
against those complete reference hashes and the saved `clock-joint` bytes.
It includes startup, model preparation, workset serialization and standalone
process timings separately. `report.json` is the complete final run. The final
DLL/standalone song runs took 36.3012/35.9395 seconds, preserving every byte
and reaching 7.79 times the archived Python search throughput. This final
measurement ran with concurrent work; the initial 11.42-times result remains
a separately recorded historical observation. Tests
cover silence, quiet tones, transients, random input, page/bank holds, exact
zero guard, no saturation, unsupported options, malformed worksets and
Unicode output paths.

The C code calls the same installed NumPy ILP64 OpenBLAS for matrix products
and reproduces NumPy's 16-term pairwise reduction and candidate-ID ties.
Switching BLAS or arithmetic order without repeating byte parity is outside
this evidence. The common proved search uses all 16 nibbles, 64 PCM bins,
32 feedback table states, width 32, horizon 128, commit 64 and regularization 0.1.
`history_bins`, restricted code alphabets, level bounds and narrower beams
fail explicitly rather than quietly change the algorithm.

Byte parity proves that this speed change introduces no new waveform error
relative to the Python reference. It does not qualify the reference's audio
quality, a new TRD, a new clone, physical hardware, or unexecuted player
changes. Reuse of earlier emulator evidence requires identical complete disk
and stream identities, not only similarity of one short waveform.

## Interface and standalone program

```python
from native_waveform_encoder import encode_waveform_native
packed = encode_waveform_native(prior, desired, features, ids, nxt)
```

The wrapper compiles a private build with the installed MSVC compiler and
atomically publishes the complete library in the ignored `.native-cache`.
The original Python producer is neither edited nor replaced.

`write_workset(path, prior, desired, features, ids, nxt)` writes the deterministic
input for `build_executable()`. `execute_workset(input, output)` runs it as a
separate process. The executable itself needs no Python interpreter or
callbacks; it loads the installed NumPy OpenBLAS DLL for matrix arithmetic:

```text
kernel.exe source.nwf encoded.ima path-to-numpy-openblas.dll
```

The current standalone build targets Windows/MSVC and supports Unicode paths.
It is not a self-contained arbitrary-WAV converter: the surrounding front end
must prepare the source clock and analytic workset. The DLL path is an explicit
runtime dependency. No compiler or network access is needed when running an
already built executable with that installed DLL.

Workset version 1 is little-endian: eight magic bytes `NWFB001` plus NUL,
five uint64 values(samples, feature shapes, width, horizon, commit), then
float64 regularization. Arrays follow in order: source uint8[N], desired
float64[N-128,16], A[F,6,6], L[F,16,6], response[F,2048,16],
endpoint[F,2048,6], weights[F,16], IDs int64[N-128], feedback int64[64,32],
IMA deltas int64[89,16] and successors int64[89,16]. The program validates
the complete input before encoding, including the silent guard and exact IMA
table. Worksets and compiled caches remain temporary, not duplicate media
stored in Git.

## Reproduction

Run from the research worktree with the bundled Python/NumPy, original project
dependencies and installed MSVC. Add `audiobook-beeper`, `toolkit` and
`audiobook-beeper/experiments/song-snr` to PYTHONPATH.

```powershell
python -m unittest discover -s audiobook-beeper -p test_native_waveform_encoder.py -v
python audiobook-beeper/experiments/song-snr/evidence/native-encoder/benchmark.py
```

The default benchmark checks every full final C/standalone output against the
archived complete Python bytes. Add `--python-reference` to repeat all full
Python searches. The saved report authenticates current producers and the
installed matrix library. Numeric outcomes and byte identities reproduce;
elapsed times depend on the host and concurrent work.
