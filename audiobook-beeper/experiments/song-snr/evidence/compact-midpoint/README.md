# Optional compact continuous-stream loader

2026-10-14. This completed feasibility change enables the quieter universal
duration-midpoint table without changing the live player or RAM capacity.
Set `model.compact_stream_loader=True` explicitly; defaultFalse preserves
the main226388fb... disk and executed clock-joint disk/metadata exactly.

Move the persistent311-byte cache probe to808A..81C1 and the mutable256-byte
bounce to81C1..82C1, within startup padding belowFIRST8340. The hot startup
ends at808A unchanged. Place the worker at the64-byte-aligned actual resident
endBC40. Song worker endsBF8F; maximum2392-sector worker endsBFBC, leaving
112/67 bytes beforeBFFF. No overlay or mutable hot dictionary is introduced.
Both probe and loading/refill code remain in fixed bank2 for the entire run.
Generated assembly documents the layout and asserts each boundary.

Six tests and four complete native old-song runs pass. Each full run verifies
11,526,111 bits,720,382 predictor/index states, every continuous CPU hold and
memory guard. Refills remain3/1/0/0 on128/Scorpion/Pentagon512/1024. Maximum
disk cold loading also passes on all four profiles with exact physical bytes,
capacity, untouched probe and final-sector bounce. The input is the unchanged
historical packed song; this is no new clock-compensated quality measurement.

Before/after CPU counts are423/449-T ordinary,14-T page and243/267-T bank
extras, delta0. Native ROM stubs prove layout/refill mechanics; no new Fuse
or physical floppy execution is claimed here. Do not infer quieter actual
audio, artifact safety or a release from this feasibility proof. A new frozen
midpoint encoder candidate still needs complete own-clock/audio checks.

`report.json` authenticates producers/inputs, records all complete runs and
contains the reproduction command. `producer.testlog` records all six tests.
Saved player metadata is sufficient to rebuild the two layouts from the
authenticated old stream/cover; duplicate media and temp binaries are omitted.

```powershell
python audiobook-beeper/experiments/song-snr/test_compact_stream_worker.py `
  --native-evidence audiobook-beeper/experiments/song-snr/evidence/compact-midpoint
```

Earlier research manifests authenticate their saved artifacts and the
producers at their respective Git commits. This opt-in adds current producer
code while preserving the old default disk and PLAYER metadata.
