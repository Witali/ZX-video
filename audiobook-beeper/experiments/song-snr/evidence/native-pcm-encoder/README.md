# Complete C PCM-error IMA encoder

2026-10-14. The original `ima_beam.py` remains the unchanged reference.
`native_ima_encoder.c` performs the entire PCM trellis, block ancestry,
predictor/index carry and low-nibble-first packing. A separate replay checks
the accepted raw additions and reports actual output extrema. This stage
changes host encoding speed, not the waveform algorithm, source preparation,
Spectrum instructions or audio measurement settings.

All trellis arithmetic is integer. The maximum squared difference is
65535 squared; a supported block of at most 65536 samples has cost below
2 to the power 49. Every cost remains exactly representable when passed to
the existing C hash/heap selector as float64. Decoder-state merging and
candidate-ID tie order therefore preserve the Python decision exactly.

## Scope and interface

```python
from native_ima_encoder import encode_pcm_native
packed = encode_pcm_native(pcm8, width=32, block_samples=64)
```

The API also supports valid initial predictor/index, custom signed predictor
bounds, integer IMA alphabets and their original ordering, other supported
beam widths/even block sizes, and partial final blocks. It never silently
clips, normalizes, inserts a guard or discards source samples. Invalid inputs,
bounds or unreachable decoder paths fail explicitly. Sources must be even,
integer mono PCM8 within 0..255. Scratch budgets are bounded. Unsupported
float sources do not receive an implicit truncating conversion.

The wrapper builds with the installed compiler in a private cache directory
and atomically publishes the finished library. It needs no BLAS matrix
library. The committed waveform C encoder and all Python references remain
unchanged.

`build_executable()` also builds the standalone default width 32/block 64,
zero-seed, all 16-code program. It reads prepared raw uint8 PCM and writes
headerless low-nibble-first IMA:

```text
kernel.exe source.raw encoded.ima
```

The Windows/MSVC executable uses the statically linked C runtime and no
Python or BLAS dependency. Unicode file paths are supported. The surrounding
front end remains responsible for preparing an arbitrary source file, its
sample clock, level and guard. `execute_pcm_file(input, output)` exposes that
standalone process to the front end.

## Complete proof and reproduction

`benchmark.py` freshly repeats the unchanged Python encoder on all nine full
sources: silence, quiet440, loud3000, steps, quiet997, multitone, O. Henry,
Entertainer and the complete main sea-foam song. It compares every byte from
the C library and standalone process against that fresh reference, proves the
final prepared guard reaches predictor/index 0, and independently checks the
saved `general` stream. Historical differences, if found, are recorded rather
than assumed to be a C regression or silently replaced.

`report.json` preserves the complete results, producer identities and separate
startup/Python/C/process timings. The complete song took 63.6411 seconds in
Python, 7.7862 seconds in the C library and 7.0315 seconds in the standalone
program. The C library was 8.17 times faster in this paired run. All nine
current outputs also match the historical general bytes exactly.

These are sequential wall times on this
host; workload and machine differences can change elapsed times. `tests.log`
also covers high-entropy sources, extrema, partial blocks, custom bounds,
seeds, alphabets and exact ties, invalid states, Unicode paths and odd-source
rejection. No narrow prefix stands in for a whole-source check.

Run from the research worktree with `audiobook-beeper`, `toolkit` and the
`song-snr` experiment folder on PYTHONPATH:

```powershell
python -m unittest discover -s audiobook-beeper -p test_native_ima_encoder.py -v
python audiobook-beeper/experiments/song-snr/evidence/native-pcm-encoder/benchmark.py
```

Byte identity permits retaining the original encoder's waveform evidence.
This performance proof alone does not establish a new SNR gain or qualify a
changed TRD/player. Earlier emulator evidence requires the same complete disk
and stream identities when reused. All Z80 hot-path instruction counts are
unchanged, with delta 0.
