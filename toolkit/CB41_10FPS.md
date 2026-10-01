# CB41 at 10 fps

2026-10-01, baseline `a878583`. The converter now accepts
`--video-codec cb41 --fps 10`. The compatibility default remains 25/3 fps.
Video uses five 50-Hz fields per frame; resident AY continues on every IRQ.

## Implementation and cycle accounting

The publication IRQ changes only the immediate operand of `LD DE,nn`:
`LD DE,6` becomes `LD DE,5`. Both take **10 T-states**, delta **0 T**,
and occupy three bytes. No memory allocation, LZSA2/CB41 wire syntax,
renderer, packet copy, paging or disk instruction is changed. Every later
deadline still advances from the original schedule, including after lateness.
The existing instruction timing table is retained in build metadata.

The original FAP3 builder still expects six AY records per frame. A build-only
envelope repeats the fifth AY state as its sixth record (an empty change).
This preserves every frame-boundary AY checkpoint. CB41 replaces that
envelope with the real five-tick resident stream before writing the TRD;
the dummy record is never played or stored in runtime video. The timing
verifier authenticates the envelope and compares all five real records.

FFmpeg samples the original source at the requested rate. Audio synthesis,
offsets and tail handling use the resulting duration and remain 50 Hz.
Volume planning checks actual resident AY size at five ticks per frame.
The native volume frame bound remains conservatively 10922.

## Verified scope

[Five complete fixtures](cb41_10fps_fixtures.json): one-frame silence,
portrait, moving colour with sound over three disks, non-square pixels and
an audio tail. All **23 frames / 115 AY ticks / 158976 screen bytes** pass
Fuse, with zero missed nominal deadlines, AY gaps or underruns. All seven
disks cold-boot from dirty RAM, and both colour-case transitions reject
wrong disks/series and accept the correct independent bootstrap. Disk service
uses the existing TR-DOS 5.03 ROM. These short clips alone do not establish
sustained full-movie delivery. Nineteen existing tests and three cadence
tests pass. Full traces, metadata and LFS disks are archived in
`cb41_10fps_fixture_evidence/`; `summarize_cb41_cadence.py` checks identities,
native instruction equality, actual timestamps and complete screen captures.

For long `--verify fuse` runs, full native screens are checked in the real
emulator, together with timing/AY/sector reads. The much slower duplicate
Python instruction replay is retained for short fixtures and `--verify cpu`.
Dirty cold boots are always checked. A partial run never passes.

## Motion sampling

The movie source reports 24/1 fps (FFprobe). Selecting 10 frames per second
alternates two- and three-source-frame steps. Exact 100-ms publication removes
player timing jitter, but does not eliminate that source-sampling judder.
The old 25/3-fps rate also does not divide 24. No motion interpolation or
blending is enabled; either would need separate artifact/size verification.

## Complete preparation and sustained window

`prepare_cell_codebook_movie.py --fps 10` resampled the original through EOF:
**5066 frames / 506.6 seconds**. The reviewed cut is evaluated on the new
sample grid, removing source samples `[4904,5804)`. The post-credit scene
and final source frame 5965 remain. All 25326 original AY states are retained
byte for byte, with four silent ticks (80 ms) appended to finish the last
100-ms frame. No source frame-rate acceleration or AY resynthesis is used.

`inspect_cb41_cadence_movie.py` independently checked all 35016192 host screen
bytes, fixed dither, audio prefix and chunk identities. Mean RGB error
improves from 834.069 (four levels) to 743.070 (five levels) for these sampled
frames; no frame is worse under the same-palette refinement. This is not a
perceptual percentage. The nine-frame contact sheet was inspected, including
the opening, difficult motion, edit join and EOF. The early dark frame's
strong blue/red palette pattern remains an existing quantizer limitation;
this cadence change does not correct that visual defect.

The **256-frame window `[4128,4384)`** covers both previously slow scenes.
It passes complete real Fuse execution: 1280 exact AY ticks, 570 checked
sector reads, zero nominal late frames, zero AY gaps/duplicates/underruns,
and all **1769472 screen bytes** exact. Actual publication phase deviation
is at most 18 T. This is sustained-window evidence, not the whole movie.
[Window report](cb41_10fps_window.json).

## Selected three-volume attempt: capacity rejection

The planner measured 159 local 32-frame windows, evaluated 26529 cut pairs
(424 row-valid), then chose `[0,1808,3408,5066]` by the largest estimated
volume cost. All three AY banks fit: 13117 / 13611 / 13756 bytes. No alternative
complete disk sets were encoded. Each independent volume includes both cold
screen histories.

The actual first volume has 692152 video bytes (2704 sectors), and needs
**2782 sectors with startup/audio against 2544 available**: overflow
238 sectors / 60928 bytes. The builder correctly rejected it without emitting
a truncated image. Later volumes were not encoded, and the full movie was
not played at 10 fps. Window estimates remain estimates.
[Archived preparation and failed attempt](cb41_10fps_movie_attempt.json).

The requested 10-fps mode works on short and sustained fixtures; the complete
three-disk 10-fps objective is **not achieved**. This one partition failure
does not prove a minimum disk count. A preference question is pending:
allow a fourth disk at unchanged quality, keep the existing 25/3-fps set,
or prioritize further compression into three. The verified root release
images are unchanged. Reproduction uses `build_cb41_cadence_movie.py` with
the preparation report, `--target-volumes 3` for the bounded full selection,
or `--start 4128 --count 256` for the window. Twelve affected planner/cadence
tests pass after adding the boundary selection.
