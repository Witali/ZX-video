# Independent codec acceleration evidence audit

Completed 2026-10-20 without repeating any encoder, audio decoder, renderer,
filter, native CPU fixture or emulator. The final audit authenticates
13 manifests and 366 unique retained files across ten speed evidence sets.
Every indexed size/hash and gzip stream passes. Complete final indexes cover
all files, including READMEs and nested manifests. The two native preparation
`initial-manifest.json` files intentionally predate their READMEs; their final
indexes authenticate both the initial index and added README. The integration
root index covers the nested optimized index as well as its artifacts.

The compact report also crosschecks retained results independently:

- Six full-song search outputs match all 360192 original IMA bytes and saved
  final statistics; timing medians are recomputed from the six raw runs.
- Both preparation experiments retain 22 exact workset pairs each, covering
  nine full sources, two nonuniform fixtures and both workset versions.
- Both host decoder experiments cover 18 complete streams. Compressed input,
  word/state arrays and PCM16 hashes agree with prior independent frozen
  evidence. All 14192 saved integer boundary records are checked arithmetically.
- The integrated encoder retains every compressed byte, prior WAV, workset
  hash, recorded decoded PCM hash and completion marker over all nine complete
  sources, 1195520 samples. Original source WAV and PCM8 hashes are rechecked.
- Both public conversions retain the original449 model. Their payload hash
  `2b30481f…` is distinct from the uniform16 experiment's `44a07e30…`.
  All 28 actual scratch output files are rehashed; payloads, priors, previews
  and entire TRDs agree. Conversion metadata reports may differ.
- Final test evidence records 28 passing tests, no skips and exit0. Tested
  source snapshots equal the live producers; the FFmpeg binary is authenticated.
- The Z80 review retains 32 native component cases and a corrected parser
  failure. Its ledger totals 49T, or57T with register exchange; live player
  instruction and timing deltas remain0T. No native fixture is rerun here.

Twelve original reference/model/player files remain byte-identical to
authenticated prior sources. The delivered 655360-byte TRDs retain SHA256
`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`
and `226388fb795ac70cfd940545a9eb73e3e81b6c7e96533dc6deb0c215257338ea`.
Current local links in `audiobook-beeper/CODEC_SPEED.md` resolve. That document
may subsequently gain a link to this audit; the audited revision hash is
recorded rather than treating documentation as an immutable audio producer.

An initial audit harness assumed three int32 fields in each saved boundary
record. The producer actually stores six: index, code, seed, raw predictor,
acceptance and resulting index. Its assertion failed before writing a pass
report. The traceback and original harness are preserved as
`initial-audit-failure.json` and `initial-audit.py.gz`. The corrected audit
uses all six fields and verifies their arithmetic. This was an audit harness
mistake, not a product or codec failure. `initial-report.json` retains the
successful earlier eight-set audit, whose configuration is separately retained.

Run `audit.py --output <new-report.json>` with ordinary Python to repeat the
read-only checks. It requires this checkout's retained evidence, original
source/disk files, converter scratch outputs and installed FFmpeg; it launches
no native program or test. The audit's own source/configuration identities
are included in `report.json`. `manifest.json` covers every file here except
itself. This audit does not promote a new disk, close the separate artifact
gate or establish new whole-player/physical-hardware verification.
