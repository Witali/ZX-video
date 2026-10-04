# Discarded drafts, 2026-10-04

These are historical diagnostics, **not accepted quality evidence**. All
draft template banks incorrectly ran the Ayumi JS core at 22050 Hz with a
1773450-Hz clock. Its interpolation step exceeds one at that rate. The C API
returns failure for this configuration, whereas the vendored JS port omits
the validity return and can produce very large finite samples. Normalizing
such samples does not make the model valid.

The initial source-shape correlation, shape log error, pooled-band joint
period/level fit, level-only/period-only controls, and unpooled fit are retained
in `invalid-template-results.json`. Their final candidate waveforms were
rendered at valid 44100 Hz, but the choices came from invalid templates.
Do not compare these rows as evidence for a successful fitting method.

`unsmoothed/` and `smoothed-invalid-rate/` contain the two discarded CLI
reports and register streams. Both disks passed complete native/Fuse timing
checks, which establishes execution correctness, not sound-model correctness.
The latter's implausible source/model gain, about 4.9e-10, exposed the invalid
configuration. No discarded disk is published as the final listening disk.
Only summaries/streams are retained here; their full temporary build artifact
inventories are not included in this archive.

Before detecting the sample-rate constraint, a held-out-phase test missed
the target period (27 instead of 23). Narrow frequency smoothing alone did
not fix it. Matching the invalid-rate baseline and candidates made that test
pass, but its reference also used the invalid rate, so that result is rejected.
The final fixture, baseline and all templates now run at 44100 Hz and use
identical anti-alias filtering. It recovers median period 23 and volume 11
from an independent-phase reference with period 23 /volume 11.

`prototypes/` contains exact exploratory source snapshots, including the old
fitter and CLI. Their `.tmp/ay-noise-colour` paths are intentionally retained
as historical working paths. The original renderer is available at baseline
commit `4ab6d7f:ay-converter/render_ym2149.js`; current rendering explicitly
rejects the invalid configuration. Reproduction of a bad draft requires that
historical renderer and must not be confused with the current supported CLI.
The source is the unchanged first 31.12 s of The Entertainer; all drafts use
the tracked50 register stream as their control. Intermediate PCM/template
banks are reproducible temporary files and are not archived.

Use the parent milestone's `release/`, `host/`, `comparison/` and `tests.txt`
for the accepted, valid-rate implementation and its independent Fuse checks.
