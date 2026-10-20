# Format-preserving native encoder profiling

Measured on 2026-10-20. These bounded experiments preserve the original
headerless low-nibble-first IMA format, search parameters, exact floating-point
operation order and decoder-state tie breaks. They do not change the player
or establish new waveform quality or release acceptance.

The prefix contains the first 16384 original song samples plus 512 silent
samples. Its 16896-sample workset has 74 distinct floating-point hold shapes,
29097336 bytes and SHA256 `aa41e4e57a773f7561cd247dc85834255c939d704ae226502508632662b50cc5`.
Every retained variant produces identical 8448 IMA bytes, SHA256
`5962d32bcc5cc9effdb2cbb3fba06b2b9161aaef6ea8afa8c46eba42e7851630`,
33472 search iterations and final predictor/index 0/0.

The original complete song record separates 8.254 s of model preparation
from 26.522 s of C execution plus workset/hash/decoder verification work;
its 35.661 s total must not be labelled as C search alone. The original
all-nine total is 65.514 s. This investigation regenerated the full song
workset using frozen original Python producers: all 138493944 bytes match
the original SHA256 `2c62776a8c3d94ec61c941c4bf44839e3191d9025bef20d437a5bec83b24853a`.
That preparation took 8.190 s plus 0.107 s to write the file. This profile
did not launch a full-song C encode; the parent experiment owns that test.

## Measured hot sections

QueryPerformanceCounter brackets each stage in a separate C copy. The second
profile pass records 0.294432 s in state merge/beam selection, 0.230586 s
in candidate scoring, 0.020052 s in both BLAS products, 0.008067 s in state
copy/ancestry and 0.001282 s in accepted-prefix replay. Thus selection and
scoring account for about 53% and 42% of bracketed search time. Replacing
BLAS is not the primary opportunity. These stage totals omit process/DLL
startup, input reads and the final PCM guard, and instrumentation itself has
overhead. They are wall measurements during concurrent development work.

## Bounded alternatives and decisions

The per-parent 64-level memo caches only `nwf_sum16(terms)`. The original
`costs[parent] + sum` and per-predictor regularization stay in their original
order. It reduces scored rows from 16930126 to 12802986, but the measured
scoring section changes only from 0.230586 to 0.227806 s. Warm child times
overlap the baseline. Do not integrate this uncertain gain.

A cheaper last-level/last-sum memo and explicit SSE2 elementwise arithmetic
also reproduce exact bytes and states. Their mixed child wall times show no
stable benefit under concurrent activity. Keep them as rejected/uncertain
controls, rather than a speed improvement claim.

The parent's online top-beam selector has a separate frozen candidate here.
Three alternated bounded runs take baseline 1.3280/1.3024/1.2827 s versus
candidate 1.2035/1.1032/1.0944 s. The medians differ by 15.3%, including
startup. This is supporting evidence only: concurrent parent unit checks
were not excluded, and full-source performance and independent selector
parity belong to the parent experiment. No data format or search preset
changes in these comparisons.

## Reproduction and artifact identity

Use the project's Python/NumPy runtime and import paths, then run
`reproduce.py --scratch <new-empty-directory> --rounds 3`. It regenerates
the exact bounded workset and builds frozen baseline/selector C sources.
Use `--variant memoized --variant baseline` for a negative memo control,
or `--variant profile` for phase timers. `--song --workset-only` reproduces
the authenticated full workset without repeating the complete encoder.

`variants/*.c.gz` contain complete standalone translation units, including
the original shared selector source. Original Python/C producers are copied
from authenticated prior evidence, not read from mutable live files during
workset reproduction. Build logs, raw JSON reports and exact IMA outputs are
retained. `context.json` pins the installed ILP64 OpenBLAS DLL and compiler
command. `manifest.json` authenticates all evidence files other than itself.
