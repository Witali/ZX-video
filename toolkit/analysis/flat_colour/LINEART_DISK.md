# Source-line drawing and a practical full disk

2026-10-14. The user rejected flat fills because too much detail disappeared,
then requested comprehensive contours, with black and reasonably matched
native colours filled where possible. This supersedes the flat disk build,
not the project's existing default encoder or earlier qualified disks.

## Result

One independently bootable Spectrum128/TR-DOS5.03 disk contains source
seconds[0,97.7):977 frames at10 fps and4885 unchanged50-Hz AY updates.
Actual disk allocation is2541 of2544 data sectors,99.8821%, with three
sectors/768 bytes free. TRD SHA256:
`c573cdd954f2d8cf29350c4e5092df876d7c1596fad8bdbd44fa5042c6758808`.
This is a practical full disk, not a mathematically maximum-duration claim.

- [Root TRD](../../../ZX-video-sea-foam-lineart_part01.trd)
- [Archived TRD](disk-evidence/ZX-video-sea-foam-lineart_part01.trd)
- [Full97.7-second MP4](disk-evidence/native-preview.mp4)
- [Source / previous / line drawing comparison, common90 seconds](disk-evidence/lineart-comparison.mp4)
- [Character/general-scene comparison](lineart-review/lineart-comparison.png)
- [Qualification](disk-evidence/qualification.json)
- [Every-frame source checks](disk-evidence/lineart-comparison.json)
- [Actual complete native timing](disk-evidence/timing.json)
- [Preserved attempts](disk-attempts/)

The viewing MP4 renders the exact native references with the unchanged AY
chip-model WAV; complete Fuse screen/AY/timing evidence independently
qualifies the actual TRD. It is not a recording of Fuse audio/video. FFprobe
confirms512x384,977 frames at10 fps and97.7 seconds of picture and sound.

## Image policy

Public converter option: `--video-codec cb41 --fps 10 --colour-policy lineart`.
It retains128x96 logical samples,256x192 native screen and256x144 active area.
A line is one logical sample(two native pixels); no new arbitrary-bitmap
player or neural/semantic person recognition is introduced.

Trace the **original current RGB** at two scales:3x3 sigma0.4 Canny24/48 for
fine detail,5x5 sigma0.9 Canny40/80 for larger silhouettes. Combine and retain
connected lines of at least two samples. Never derive lines from attributes,
dither or the old picture. Eyes, mouth, beard, clothing and scene lines are
more visible in the inspected boy/king/general shots than in the rejected
flat preview, but this is stylistic tracing, not a semantic recognition score.

Classify original RGB against normal and BRIGHT native colours. Accept a
colour only within60 encoded-RGB RMS,100 maximum component delta and a
30-degree(R-G,B-G) hue cone, with at least four connected samples. Black
additionally requires every source component<=64 and a two-sample region.
These are defined model-colour thresholds, not perceptual Delta-E guarantees.
The earlier45-RMS/75-component review accepted **no** colours on the six
chosen frames; retain that rejected strict review in`lineart-review-strict`.
The selected thresholds find1466/323/76 source colour samples on frames
259/300/506 before contour and hardware restrictions.

Use uniform NORMAL-white paper RGB205. Required black lines, matched black
areas and paper samples remain exact. Other matched colours may use their
exact native endpoint or fall back to paper. When black line/white paper/
colour fill need three colours in one8x8 cell, sacrifice optional fill before
losing a line or spilling colour onto unmatched source. BRIGHT fills remain
possible inside regions whose cell does not also require NORMAL paper.
This reduces false colour rectangles; it does not remove the hardware's
two-colour limit or reproduce all source shades. No dither is used anywhere.
Every mask follows the current frame; no history blending or delayed palette.

## Complete verification

All50 integration tests pass. The actual disk cold-boots with independently
dirty RAM and passes complete Fuse1.9.0 playback. Every977 screen matches
all6912 bytes:6,753,024 compared bytes. Every4885 AY field/register record
matches, without underruns, missing/duplicate fields, dropped screens,
missed nominal five-field deadlines or late runs. Maximum in-field
publication deviation17 T. The fallback allowance is not needed.

All977 frames additionally check every detected source line is black,
every classified black region is black, every required paper sample is205,
and every actual coloured pixel equals its accepted original-source label.
Actual compression-selected reference RGB equals the prepared image exactly.
The previous disk's900 available frames have byte-identical original RGB,
AY controls and model-WAV prefix. Full-source native RGB MSE6885.6597 is a
style diagnostic, not evidence of photographic or recognition superiority.

Runtime2450 verified sector reads, zero retries. Read-call service totals
68,229,686 T, range22,344..134,473 T; seek service1,655,691 T. These combine
ROM, physical disk emulation, IRQ and ULA effects. Deterministic instruction
costs and data-dependent block measurements remain in the build metadata.
No native player instruction changes:0 T delta relative to the previous
qualified sea-foam player. Historical AYH2/profile deltas in inherited
metadata describe earlier changes, not a new delta in this host-only task.
Physical hardware is untested.141 measured files/93,558,021 bytes plus the
manifest preserve full inputs, native proofs, media and17 producer snapshots.

## Attempts and reproduction

The original flat1005-frame build was stopped following user steering,
after219 complete host-state rows; no TRD/native qualification was reached.
Keep its log/partial states and original source hash in`interrupted-flat`.
Its uncommitted original wrapper was not snapshotted; the final wrapper's
explicit flat option is an equivalent reproducer, not a historical hash claim.

Actual line-art assembly rejects1005 frames at2589 sectors, then980 at2545
sectors (one sector too large). The977-frame result uses2541 and completely
qualifies. No image threshold, source detail, audio fit or cadence was changed
to fit it. Reuse byte-checked host image preparation from the1005 attempt;
regenerate all packets, disk allocation and native qualification for each cut.
The resident AY forest also caps this cached continuous input at1005 frames,
so no further audio/RAM/codec experiment is needed for this practical fill.

Use `build_disk.py --image-policy lineart --compact-cache CACHE --one-disk
PREPARED --plan PLAN --output NEW --frames 977` with the existing FFmpeg,
FFprobe, Node, ZX0, LZSA, Fuse and trusted TR-DOS ROM arguments documented
in[the source preparation guide](../sea_foam/README.md). `--image-cache`
is optional and checks the policy/parameters, each RGB byte and preceding
state. `--verification none` can only probe capacity; the default Fuse
verification is required before `archive_disk.py` publishes a new result.

The failed1005 cache's`cache-inputs.npz` stores full original RGB, coarse
states and line-art states. To reconstruct a host cache, write`source` to
`work/frames.rgb`, save`compact` as`work/states.npy` and`states` as
`work/five-states.npy`; copy its`conversion.json` and`video-quality.json`.
Continuous audio is retained in`disk-evidence/work/continuous-audio-fit`.
Use its`input.f32`, full preview WAV and fit as the prepared source, following
the source guide. Source/artifact hashes and exact producer snapshots are
authoritative. Existing root movie disks and ordinary encoder defaults remain.
