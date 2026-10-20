# Complete-song standalone C selector benchmark

Measured 2026-10-20. Six separate C child processes encode the exact same
authenticated original full-song workset, sequentially in baseline/selector,
selector/baseline, baseline/selector order. No other heavy agent experiment
was intentionally started during these measurements; the all-nine integration
run was explicitly held until the final child exited. Ordinary operating
system/background activity was not isolated. Raw variation remains in the
report rather than selecting a favourable pair.

| Run | Variant | Wall seconds | Process CPU seconds | Process CPU cycles, billions |
| --- | --- | ---: | ---: | ---: |
| 1 | Baseline | 27.962239 | 27.015625 | 99.551580 |
| 2 | Selector | 20.747952 | 19.734375 | 72.575171 |
| 3 | Selector | 28.115302 | 23.562500 | 87.305901 |
| 4 | Baseline | 33.185248 | 30.046875 | 110.623698 |
| 5 | Baseline | 30.611742 | 28.671875 | 106.072710 |
| 6 | Selector | 20.597056 | 18.921875 | 69.754569 |

The baseline and selector medians are 30.611742 and 20.747952 s wall time:
32.22% shorter, or 1.4754x as fast. Process CPU medians improve from
28.671875 to 19.734375 s, 31.17% shorter. Median process cycles decrease
from 106.072710 to 72.575171 billion, 31.58%. Each adjacent paired control
is faster: wall reductions are 25.80%, 15.28% and 32.72%; CPU reductions
are 26.95%, 21.58% and 34.01%. These distributions distinguish the observed
gain from a guarantee about every future run or host.

Wall timing brackets child creation, loading the workset/BLAS, complete
search/guard/packing, output writing and process exit. Windows GetProcessTimes
supplies user+kernel CPU time; QueryProcessCycleTime supplies process cycles
after child exit. These x86 process cycles are separate from Z80 T-states.
Analytic model preparation, workset writing by Python, subsequent waveform
rendering, TRD assembly and emulator execution are outside these timings.
Do not report these measurements as full converter or disk-build time.

All six children emit exactly 360192 bytes for all 720384 original samples,
SHA256 `44a07e303522dfc4eef31d4654ba35dc6f275d82f6a07d2b3e723155a4d58d06`.
This is byte-for-byte equal to the frozen matched uniform16 IMA stream.
Every child records 1440448 search iterations and final predictor/index 0/0.
No sample rate, codec representation, score arithmetic, candidate tie rule,
beam width32, horizon128, commit64 or regularization0.1 changes. The
existing shared selector source and executable original Python reference
are retained. The parent owns independent selector tests and complete
nine-source integration checks; these timings do not replace those tests.

`context.json` authenticates the full 138493944-byte workset, both original
executables, complete C translation units and the installed NumPy ILP64
OpenBLAS DLL. The input workset exactly reproduces prior SHA256
`2c62776a8c3d94ec61c941c4bf44839e3191d9025bef20d437a5bec83b24853a`.
Both frozen translation units and their exact IMA outputs are retained.
`report.json` is complete; `partial.json` intentionally preserves the
last in-progress status written by the same producer.

`executed-producer.py.gz` is the exact initial measurement script. For a
fresh repeat, generate the full workset with the sibling codec-speed-profile
`reproduce.py --song --workset-only`, then run this directory's
`reproduce.py --workset <workset.bin> --scratch <new-empty-directory>`.
It compiles the frozen translation units with the retained strict floating
point command and repeats three alternating pairs. The repeat script was
syntax checked; no redundant second six-run benchmark was launched.
The frozen source builds and actual six executions above already passed.
`manifest.json` authenticates all files other than itself.
