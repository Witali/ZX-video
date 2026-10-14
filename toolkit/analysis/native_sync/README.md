# Native delivery progress snapshot — 2026-10-14

This is the stopped experiment on `codex/native-sync`, from `dbde780c`.
The user requested less native-video lag, cancelled the proposed progress-bar
change, then stopped work and requested a commit/push of the current progress.
No broad goal is resumed and no disk here is a qualified release. Public
converter defaults and the accepted image/50-Hz AY fit remain unchanged.

Inputs are the preceding [native-lineart archive](../native_lineart/README.md):
300 accepted native screens, 256x144 active area within 256x192, and 1500
unchanged AY controls for the same 30-second source prefix. All new picture
representations are lossless with respect to those native screens. The
compatibility experiment explicitly selects 250 of the 300 source frames;
it is a temporal resampling to 25/3 fps, not the original 10-fps sequence.
Its last selected source index is 299. The entire AY sequence stays at 50 Hz.

## Actual results and limits

| Experiment | fps | Sectors | Nominal misses | Maximum late fields | Full Fuse screen bytes |
| --- | ---: | ---: | ---: | ---: | --- |
| Original CB47 | 10 | 1488 | 165 | 523 (10.46 s) | All 300 screens |
| CB48 + LZSA2 | 10 | 1551 | 157 | 406 (8.12 s) | Samples only |
| Stored CB48 | 10 | 1982 | 152 | 185 (3.70 s) | Samples; independent CPU checks all 300 |
| Stored CB49 zero planes | 10 | 1951 | 152 | 188 (3.76 s) | Samples only |
| Stored CB50 repeat rows, initial dispatch | 10 | 1786 | 139 | 135 (2.70 s) | All 300 / 2,073,600 bytes |
| Stored CB50 reordered flags, current source | 10 | 1786 | Pending | Pending | Pending |
| Stored CB50 compatibility, current source | 25/3 | 1515 | 0 | 0 (maximum OUT deviation 15 T) | Samples only; full capture pending |

All completed real-Fuse timing runs contain exactly 1500 AY records with
zero gaps, duplicates or underruns. Complete timing measures publication OUTs
and physical TR-DOS reads; samples do not prove all screen bytes. The stored
CB48 and initial CB50 late runs partly recover, then remain late through EOF;
the archived timing JSONs record each run and its recovery separately. All
10-fps measured variants fail the one-field fallback. Compatibility timing
passes its six-field schedule, but complete screen-byte capture and independent
packet CPU replay were not run before stopping. Its disk SHA256 is
`da887fead942275de6129be2d74f10b0ae6b4181075067dd562ff30d0329dc26`.
The current 10-fps disk SHA256 is
`31b497a98b75f62d818e2b5fecc8a5ac2892ca89bfde925ac5cfd08d6a71bf7c`;
only its independent dirty cold-load proof is complete.

## Implementation and counted timing

CB48 replaces changed-cell masks/popcounts with a fixed 144-byte two-bit mode
plane and 72-byte attribute mask. It retains native book/front/raw cells,
adds two changed rows and four immutable row-pair indices (512 bytes at
9e00h). CB49 additionally zero-encodes both planes; measured delivery is worse
despite smaller data. CB50 additionally encodes repeated consecutive native
row bytes, with a shared 61-byte writer at B200h. The build guards overlap
against the fixed resident AY forest. The packet still occupies 6200h..7760h.

Stored transport loads complete, sector-aligned raw blocks directly into the
existing four video banks (0/1/3/4), preserving descriptor publication, queue
consumer, fixed AY, and physical disk reader. The new helper lives at E400h
in bank 7 and must be included in independent cold bootstrap sections.
The step entry changes CALL 17 T to JP 10 T (-7); the fixed-bank read bridge
costs 51 T excluding the retained ROM/read service. Each emitted instruction
has its timing-table count in build metadata. CB48 native literal body remains
188 T; its new mode return adds 4+10 T (202 T for that scoped path).

Complete banked CPU replay for the matched 300-frame stored-CB48 candidate
counts 41,580,075 listed player T-states versus original CB47's 83,163,060,
a difference of -41,582,985 T. This is the instrumented packet/queue/copy/draw
instruction scope with mocked ROM, excluding actual IRQ/cadence, ULA and disk.
It proves every screen byte and memory guards, not real-time publication.
Real-Fuse playback elapsed time separately falls 153,230,921 -> 125,386,214 T
(-27,844,707); real read service rises 39,943,368 -> 53,408,096 T because
runtime reads rise 1443 -> 1934. The smaller repeat-row stream later reduces
actual reads to 1733; compatibility uses 1463.

The initial CB50 dispatch is physically valid but the small logical-flag CPU
model rejects JP M after JP Z. Current source puts JP M immediately after
OR A: repeat dispatch saves 10 T, front dispatch adds 10 T per selected cell,
relative to that initial variant. Its complete 10-fps replay/timing is pending;
do not reuse the initial 2.70-second measurement for the reordered disk.

## Preserved failed and partial attempts

Exact span representations (front-copy on/off, merge gaps 3/6) need 545,617..
619,545 compressed bytes and 44,677,773..48,068,247 flat decoder T-states.
Separately compressed full native screens need 522,102 stream bytes and
72,778,214 flat decoder T-states. These offline estimates are rejected,
not playback qualifications. Adaptive pair tables increase update overhead;
no adaptive player or approximate pixel replacement was implemented.

The rejected direct raster prototype overlaps fixed AY at 8000h and was
restored before the actual mode-plane implementation; its source snapshots
remain archived. The first stored prototype omitted its E400h helper from
cold loading and timed out in Fuse after 120 seconds. That failed image and
timeout console were overwritten during correction and cannot be recovered;
its recorded image identity was
`3e3b6a0fe717c209ba8a0e49b1b4d073c1ea50137ab4d2a7dec4a8dbdd8513f8`.
No successful measurement is attributed to it.

`session/modeplane/timing.json` authenticates the earlier LZSA disk
`eaee320c06052c7ec41687edc13aeaca840fa3181ac79dcfdaf2fda9443d2d0e`.
The saved `modeplane/candidate.trd` and metadata were subsequently overwritten
by an invalid stored-reader/LZSA-stream combination, SHA256
`daacc928db332716edd2c51863cdc7dae76e5c728da82a1115e28c76dafd0dd0`.
Preserve the mismatch explicitly; the saved candidate is not playable and its
cold-load proof does not fix the transport mismatch. No rebuild was launched
to replace historical objects when committing this stopped progress.

## Evidence and reproduction

[Summary](evidence/summary.json) distinguishes each disk identity and coverage.
[Manifest](evidence/manifest.json) authenticates every archived object.
`evidence/session` preserves the complete stopped `.tmp` experiment except
disposable ZX0 caches/Python bytecode, including TRDs, traces, screen captures,
host streams, metadata, rejected sources and original scripts. Current seven
production source files are also frozen under `evidence/current-source`.
[save_snapshot.py](save_snapshot.py) is the non-overwriting archival operation;
it does not run a converter or emulator.

[verify_snapshot.py](verify_snapshot.py) checks archive hashes, current source
syntax/snapshots, disk/metadata identities and host lossless wire decoding.
Tracked source comparisons allow Git's LF/CRLF normalization; archived source
objects and all measured binary/report objects remain SHA256-exact.
Its [save-time checks](checks.json) explicitly retain the known historical
timing mismatch and do not qualify any pending native playback check.

```powershell
python toolkit/analysis/native_sync/verify_snapshot.py --input-root C:/Work/ZX-video
```

The original session scripts retain their Windows environment paths as
provenance. They ran in `C:/Work/ZX-video/.worktree/native-sync` with `.tmp`
as the work directory, `toolkit` plus the existing local ZX0/LZSA/Python
dependencies on PYTHONPATH, and frozen inputs from the main checkout's native
archive. `build_mode.py`, `build_stored.py`, `build_repeat.py`, `build_zeros.py`
and `build_compat.py` reproduce their respective construction choices.
Use the archived initial renderer source to reproduce the initial CB50 disk;
current source reproduces the reordered variant. Old measured TRDs/traces
remain the authoritative evidence until any new complete run is performed.

The existing `measure_fap3_fuse.py` measures a candidate with its metadata,
states and original FAP3 scaffold; compatibility uses its own `stream.raw`.
`capture_cell_codebook_full.py` performs full-byte captures, and
`build_cell_codebook_trd.verify` performs the independent banked CPU replay.
These pending runs, generic CLI integration and multi-disk native prompt/RAM
qualification are future work. This save/push does not start them.
