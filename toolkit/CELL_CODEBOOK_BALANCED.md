# Full five-level movie: three TRDs with exact six-field playback

2026-09-30, baseline `2a1686d`. The entire authorized **4221-frame / 506.52 s**
edit now fits three independently bootable CB41/LZSA2 disks and passes full
Fuse playback at **25/3 fps**, with **zero missed nominal frame deadlines**.
All 25326 existing AY ticks remain exact at 50 Hz. Source resolution, five
brightness levels, fixed dither and the post-credit scene through EOF are
unchanged from the [full preparation](CELL_CODEBOOK_MOVIE.md).

## Verified set

| TRD | Frames | Occupied sectors | Free sectors | Late frames | Exact AY ticks |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Part 1](../ZX-video-five-level_part01.trd) | 1504 | 2475 | 69 | 0 | 9024 |
| [Part 2](../ZX-video-five-level_part02.trd) | 1328 | 2505 | 39 | 0 | 7968 |
| [Part 3](../ZX-video-five-level_part03.trd) | 1389 | 2511 | 33 | 0 | 8334 |

The root images use Git LFS. Every disk can boot alone. When playing in
sequence, the player displays its English next-disk prompt and checks the
series and volume number before accepting the next disk. The bottom progress
bar reaches 100% for the current disk.

Full video is **1839554 bytes / 7187 sectors**, 968 bytes smaller than the
previous split. Complete disk files occupy **7491 sectors**, leaving **141
sectors** across the set. No packet format or native decoder change was needed.
Rows including both initial screen histories are **251/256/244** per volume;
resident AY images use **13080/13627/13751 bytes** and fit bank 4.

## Selection used local windows

The previous cuts 1472/2752 overflowed the third disk by 95 sectors.
[plan_cell_codebook_volumes.py](plan_cell_codebook_volumes.py) apportions
already measured compressed-block costs over frame spans and includes the
previous measured startup overhead. Exact row-set prefix counts reject
impossible cuts. This examines 1089 nearby cut pairs without encoding their
movies; 502 satisfy row limits. The selected cuts are **1504/2832**.

Seven local windows, **368 frames total**, then compare old/new volume books
and require identical full host screens. Their independent-reset LZSA2 sizes
are **179881 -> 179421 bytes**. Old full raw streams are reproduced exactly
before reusing their costs. Only the selected complete partition is encoded
and built. Estimated occupied sectors 2474/2505/2518 become measured
2475/2505/2511: estimates select work but never pass the capacity gate.

## Complete playback evidence

- Independently cold-boot each actual image and run it to EOF in Fuse with
  the verified TR-DOS ROM. All **4218 intra-disk publication intervals** are
  exactly six fields. No missed nominal deadline, fallback late run, dropped
  frame or accumulated drift occurs. At the normalized 50-Hz timebase each
  disk averages 8.3333333 fps. Actual OUT phase stays within **-3..21 T**;
  this is instruction-boundary variation inside the scheduled field.
- Verify all **7187 video sectors**, with no retries or wrong bytes, and
  every AY register write/tick. No AY field gaps, duplicates or underruns.
  Most sectors arrive during playback; startup buffering cannot account
  for the full successful run.
- [capture_cell_codebook_full.py](capture_cell_codebook_full.py) compares
  **29175552 complete screen bytes** across all 4221 frames, including
  attributes, black fields and progress. Five independent read-only passes
  export consecutive screen slices at the common native draw return to
  stay below Windows' command-line limit. No debugger pokes, paging changes
  or CPU jumps are used. Separate uninterrupted traces verify actual screen
  publication and AY on the identical TRDs. This replaces thousands of
  per-frame emulator restarts without weakening byte coverage.
- Real prompt/bootstrap opcodes with modeled ROM reads verify both 1->2
  and 2->3: exact prompt pixels, wrong disk/series rejection, correct disk
  acceptance and RAM identical to an independent cold boot.
- A second full Fuse sequence exports **actual predecessor EOF RAM**,
  resumes at the disk prompt using SZX, and plays each subsequent disk to
  EOF. Both next disks are accepted; all deadlines and AY records still
  pass. Other banks are poisoned before resumption, demonstrating reload.
  The emulator/controller restart between volumes; this is not a physical
  drive-swap test. Independently booting each disk was verified separately.

The native kernel and packet instruction listings exactly match the prior
192-frame player: instruction delta **0 T**. No deterministic CPU saving is
claimed from moving cuts. Actual cold bootstrap+runtime totals are
**666188838 / 594940974 / 620929017 T**, including ROM, emulated disk, IRQ and
ULA. These exclude BASIC loading PLAYER and human swap time. Full traces
retain publication and sector timings; they are not pure CPU measurements.
Visual review uses the unchanged [full-movie reference preview](cell_codebook_movie_preview.png);
all of its underlying five-level rasters now also match real Fuse memory.
The existing palette/colour-cell limitations discussed in that report remain.

## Reproduce and archive

Keep the previous `.tmp/cell-codebook-full` preparation and use the same
trusted Python/FFmpeg/LZSA/ZX0/Fuse setup documented in
[the full preparation](CELL_CODEBOOK_MOVIE.md#reproduction).

1. Run `plan_cell_codebook_volumes.py` with `--prepared`, prior
   `--measurements`, prior `--capacity`, `--author`, and
   `--output .tmp/cell-codebook-balanced/windows`.
2. Run `measure_cell_codebook_movie.py` with
   `--partition-plan .tmp/cell-codebook-balanced/windows/plan.json` and
   `--output .tmp/cell-codebook-balanced/measured`. Other inputs are unchanged.
3. Run `build_cell_codebook_movie.py` against those measurements, writing
   `.tmp/cell-codebook-balanced/build`. It now saves the exact per-volume
   row-index view as `volume-N/states.npz` for emulator checks.
4. Run `measure_fap3_fuse.py` on each `volume-N/candidate.trd`, its metadata
   and states, using the original full FAP3 as the AY reference. Save each
   `volume-N/timing.json`. No injected player or pipeline-tracing option.
5. Run `capture_cell_codebook_full.py` on each volume with those same inputs,
   `--timing`, `--work volume-N/full-captures`, and
   `--output volume-N/full-screens.json`. Run Fuse processes sequentially.
6. Run `verify_cell_codebook_continuation.py --mode mock`, then `--mode fuse`,
   with `--build .tmp/cell-codebook-balanced/build`, the existing `--fuse`,
   `--raw` reference, and `--output .tmp/cell-codebook-balanced/continuation`.
7. Run `summarize_cell_codebook_balanced.py --work .tmp/cell-codebook-balanced
   --evidence toolkit/cell_codebook_balanced_evidence
   --output toolkit/cell_codebook_balanced_profile.json --install-root`.
   It checks evidence identity and timing/content gates before installing.

[Summary](cell_codebook_balanced_profile.json) and
[hashed evidence](cell_codebook_balanced_evidence/) retain both cold and
continued playback traces, every screen slice, exact measured streams,
per-volume states/tables, snapshots and the bounded-window decision.

## Remaining project work

The full-movie playback milestone is verified. This path is still driven by
the explicit preparation/measurement/build scripts, with a saved edited AY
input. Integrate it into the generic video converter, preserving arbitrary
source handling and automatic bounded-window selection, before treating the
overall converter goal as complete. Keep the passing movie fixture fixed;
do not reopen codec searches or alter its pixels to finish that integration.
