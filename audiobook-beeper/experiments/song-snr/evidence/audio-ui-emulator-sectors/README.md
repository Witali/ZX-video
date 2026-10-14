# Complete audio progress UI verification

Date: 2026-10-14. The final sector-cadence UI disk is
`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`.
[The aggregate report](report.json) records complete audio and complete UI
acceptance. The earlier FRAMES-based failure remains unchanged in
[its separate evidence](../audio-ui-emulator/README.md).

## Verified behavior

All four complete native runs verify 11,526,111 source bits and 720,382
predictor/index observations per profile, with memory guards and independently
loaded audio. Spectrum 128 retains three explicit insufficient-RAM refills;
Scorpion retains one. Their loading redraws occur only while paused.
Pentagon 512 and 1024 have no refills and retain the 277-T maximum continuous
hold. Native ROM stubs alone do not establish physical loading animation.

Both complete, independently cold-booted installed-Fuse captures verify every
source bit, sample state, source-relative pulse timestamp, sector/page handoff,
and cover/progress/end path. Each observes 92 loading phases in strict
1→2→3 cycles, 22 live updates, a correct gray loading bar, correct green
prefixes, and a final full-green bar. Dots advance after 16 completed physical
reads; this is a read-count cadence whose wall-clock period depends on drive
latency. It deliberately makes no ROM FRAMES or fixed 0.5-second claim.

`finish.py` separately verifies all 22 live boundaries on each model. It derives
compressed bytes consumed from the observed source pulse number:
`bytes = (pulse + 33) // 32`, checks the integral sector boundary, and requires
the actual filled-column count to equal `floor(32 * bytes / packed_bytes)`.
The first three fills are 1, 2, and 4 columns; the final live fill is 31.
The final redraw fills all 32. This checks the complete prefix geometry,
rather than only monotonic progress. The builder separately rejects sources
that would require more than two new cells in one fixed-time handoff.

## Exact audio clock and quality scope

Each model's 11,526,111 relative source timestamps exactly matches the prior
best disk `ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074`:
maximum introduced change 0 T, SHA256
`2280bd22a0517b7ba907509a02e14f111f44014b7a0870fa663fb5e452c3ad88`.
The compressed source/model is also identical. The established
20.25031588676249-dB quality result is therefore reused without another filter
fit or source encoding. This evidence does not claim a new general quality
improvement, and no physical machine was tested.

The explicit terminal mute is measured separately: 219 T after the last source
OUT, versus 201 T before the UI change. The +18 T is 5.022321 microseconds at
3,584,000 Hz. Every source-bearing pulse remains exact; the raw waveform
through terminal mute is not byte/time identical. The established final
100-ms listening crop excludes that teardown interval.

## Actual screen evidence

The complete captures preserve `.scr` and 768×576 PNG snapshots of all three
loading labels, playback start/middle, and final completion. The snapshots
combine actual observed UI glyph/attribute bytes with exact COVER pixels
outside the unchanged UI region; they are not full 6912-byte debugger dumps.
Loading-three-dot, PLAYING/middle, and END images were visually inspected.

| Model | Reports and actual snapshots |
|---|---|
| Pentagon 512 | [Full capture](installed-full-512/report.json), [loading](installed-full-512/pentagon512/loading-3.png), [middle](installed-full-512/pentagon512/playing-middle.png), [end](installed-full-512/pentagon512/playing-end.png) |
| Pentagon 1024 | [Full capture](installed-full-1024/report.json), [loading](installed-full-1024/pentagon1024/loading-3.png), [middle](installed-full-1024/pentagon1024/playing-middle.png), [end](installed-full-1024/pentagon1024/playing-end.png) |

## Producer and emulator provenance

Both actual captures explicitly use `C:/Program Files (x86)/Fuse/fuse.exe`,
SHA256 `e7aba457ea405f8e2fcab9d4bc703e9f1013453726e178d8c7333ce9685a1266`.
The shared capture verifier remains
`f6c97433bdf3a044ba6b19de9f930187f09d289e77a8e1be477cc98499c6cdd9`;
no phase assertion was relaxed. The new `verify.py` is
`8f4a6724be330a325e5b7e6bf7976bb6d505efa70691cd5f5e563db255a7eb08`.
Every full run requires unchanged producer hashes before and after execution.
Exact capture/aggregate producer bytes and metadata are archived in
`producer-source/`; the conversion has its own separate producer archive.

The non-UI baseline debugger script remains exactly 19,689 bytes, SHA256
`fe93b4f14b1fa4396b7b946861898bf4333240939206b61f50063cbba61e6096`.
Its per-run default-script proof intercepts launch and checks exact prior
script equality; it does not execute another baseline capture. Full actual
source comparison uses the already complete prior traces.

## Reproduction

From the research worktree with NumPy and the project `z80` dependency:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator-sectors/verify.py --disk audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery-sectors/generated/audio.trd --metadata audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery-sectors/generated/player.json --packed audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery-sectors/generated/soundtrack.ima.gz --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --profiles pentagon512 --output NEW_OUTPUT
python audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator-sectors/finish.py --metadata audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery-sectors/generated/player.json
```

Substitute `pentagon1024` for the other actual capture, or
`--native-profile PROFILE` for one complete native run. Existing complete
captures are protected against accidental overwrite; `--captured` rechecks
saved raw traces. `finish.py` aggregates this directory's four native and two
actual captures, including exact prefix geometry. `make_manifest.py` hashes
all artifacts except the manifest itself and Python bytecode caches.
