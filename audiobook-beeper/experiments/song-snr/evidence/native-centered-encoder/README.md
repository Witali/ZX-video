# Optional centered PCM lookup in the C encoder

2026-10-14. The native waveform encoder accepts the explicit option
`pcm_quantization_bias=512`. Both candidate search and committed-prefix replay
use `min(63,(predictor+32768+512)//1024)`. The upper clamp is required for the
last512 positive PCM16 values. This maps zero and negative-one to the same
bucket; it does not by itself establish better audio quality.

The default remains bias0. The original `ima_waveform_encoder.py` and
`ima_beam.py` stay unchanged from the research starting commit `13819086`.
The public converter's `--encoder python` still runs the original algorithm.
A separate `centered_waveform_reference.py` contains the independent NumPy
search for the new option and delegates bias0 to the original producer.

The original C ABI symbol and workset version1 remain available. An additional
ABI symbol takes the bias; workset version2 stores one little-endian int64 bias
at offset56 after the existing header. Its arrays are identical to version1,
starting at offset64 instead of56. Bias0 still writes version1, and default
statistics omit the new option. Unsupported or non-integer biases fail
explicitly. Neither baseline PCM trellis nor Spectrum instructions change.

Six tests cover all65536 PCM16 values through the actual C lookup, independent
NumPy search parity, page/bank holds, exact settling, saturation, both table
origins, default compatibility, Unicode standalone paths and malformed
version2 inputs. `tests.log` records the completed run. The full default
compatibility evidence is recorded separately in `default-report.json` and
`default-compatibility.json`. All nine complete DLL/standalone streams and
version1 worksets match the archived bytes. `verify_default.py` reproduces
these checks and authenticates original Python against Git. The latest full
song search takes23.4748 s in the DLL and25.4115 s in the standalone process;
these are search timings, not complete conversion timings.

```powershell
python -m unittest discover -s audiobook-beeper -p test_centered_waveform_encoder.py -v
python audiobook-beeper/experiments/song-snr/evidence/native-centered-encoder/verify_default.py
```

Run in the research worktree with the same Python/NumPy, MSVC and project
dependencies as the original native benchmark. Compilation caches and worksets
remain temporary. Timing observations apply to this host and its concurrent
work; this compatibility check is separate from a new conversion benchmark.

This change enables a matched encoder/player experiment. Short exactness tests
and default parity do not qualify centered audio quality, an emulator clock,
an artifact-free release or physical hardware. The full corpus and selected
actual player executions must supply their own evidence.
