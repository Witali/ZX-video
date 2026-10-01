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

Full movie resampling, window tests and complete release verification are
the next part of this deliverable. The verified three-disk 25/3-fps root set
is retained until a replacement passes.
