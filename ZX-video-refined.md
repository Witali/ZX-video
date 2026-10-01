# Refined movie: four independently bootable disks

Built and verified 2026-10-01. This replaces the 15-disk refined preview.
Download the four root `ZX-video-refined_part01..04.trd` images through Git
LFS (`git lfs pull` after cloning). Play in numerical order, or boot any disk
independently on Spectrum 128 with Beta Disk and the verified TR-DOS 5.03 ROM.
At each boundary the player displays `INSERT NEXT DISK` and resumes after
the correct next disk is inserted. The progress bar covers the current disk.

## Content and capacity

The entire authorized edit is retained:5066 frames, 506.6 seconds at 10 fps,
including the post-credit scene through source EOF. Final credits are removed
using [the authorized edit](toolkit/movie_no_credits.json). Resolution,
five-level fixed dithering, refined colour and the square-aware AY50 soundtrack
are unchanged. Every rendered RGB pixel and all 25330 AY register states match
the prepared refined movie. Only invisible attribute bits may differ.

| Disk | Frames | Duration | Used sectors /2544 | Free sectors |
|---|---:|---:|---:|---:|
| [1](ZX-video-refined_part01.trd) | 1312 | 131.2 s | 2464 | 80 |
| [2](ZX-video-refined_part02.trd) | 1360 | 136.0 s | 2476 | 68 |
| [3](ZX-video-refined_part03.trd) | 1072 | 107.2 s | 2542 | 2 |
| [4](ZX-video-refined_part04.trd) | 1322 | 132.2 s | 2543 | 1 |

Total compressed video:2462188 bytes. Images occupy2621440 bytes in total.
Dynamic row replacement, front-screen reuse and partial row-pair updates use
CB46 packets with LZSA2. The four-slot player uses bank 6 plus a checked fixed
tail for AY, and spare bank 7 RAM for compressed-sector prefetch. Actual memory
sections, protected ranges, stacks and native instruction tables are archived
per disk. Each bootstrap reconstructs its own complete state.

## Verified timing and limits

Full cold runs and actual predecessor-EOF continuations check every frame,
screen byte, AY tick and sector in Fuse. Native runs separately check every
screen with poisoned startup RAM and protected-buffer guards. Continuation
screen captures use the same exported EOF snapshots as the timing runs.
The snapshots preserve actual predecessor RAM while poisoning other banks;
the emulator/controller restart between disks. No physical-drive test is
claimed.

| Mode | Nominal late frames by disk 1/2/3/4 | Maximum deviation |
|---|---|---:|
| Independent cold starts | 0 /0 /1 /0 | 70907 T, less than 20 ms |
| Sequential playback | 0 /0 /1 /1 | 70908 T, exactly20 ms |

On disk 3, local frame 933 (global3605) is late and frame 934 recovers. During
continuation disk 4 additionally delays local 576 (global4320), recovering at 577.
Indices are zero-based. Every interval is 4..6 fields; the original deadlines
are retained, with no drift or dropped frame. AY remains continuous at 50 Hz.
All other frame publications stay within the recorded instruction/IRQ phase
variation. The nominal measurement tolerance is 64 T, not a whole field; the
fallback rejects any actual deviation beyond 70908 T.

This set **passes the user's one-field fallback**, but the zero-late target
remains open. Accordingly the report retains `release: false` and
`preview_only: true`, alongside `user_authorized_delivery: true` and the
explicit fallback gate. The missed nominal deadlines are not hidden by an
average-fps claim. The remaining stalls come from long cylinder reads around
an upcoming publication; heads already traverse cylinders only forward.

## Reproduction

The general converter selects the player profile using:

```text
python toolkit/convert_video.py input.mp4 --video-codec cb41 --guarded-cb46 --fps 10 --output build/output --verify fuse --fuse PATH --lzsa PATH --zx0 PATH --trdos-rom PATH
```

For this accepted cached movie partition, the saved commands are:

```text
python toolkit/build_cached_cell_set.py --base .tmp/front-retired-capacity/ZX-video-front_part01.json --probe .tmp/partial-row-four --audio .tmp/four-dynamic-probe --replacement-metadata .tmp/side-only-seek-part04/part04.json --output .tmp/refined-four-candidate --zx0 PATH --lzsa PATH
python toolkit/check_cached_cell_set.py --build .tmp/refined-four-candidate --fuse PATH --native-jobs 4 --resume
python -m unittest test_cached_set_gate
python toolkit/finish_cached_cell_set.py --build .tmp/refined-four-candidate --prepared .tmp/refined-av-movie/preparation.json --baseline .tmp/side-only-seek-part04/part04.json --root . --evidence toolkit/refined_four_evidence --output toolkit/refined_four_report.json --allow-fallback --install
```

The builder reuses one accepted partition; it does not search complete disk
variants or requantize media. Its common series ID is derived from all input
streams and options. The installer checks the complete evidence and existing
root hashes before replacing files, checks LFS attributes, verifies all new
copies, then removes only obsolete numbered refined parts.

[Full report](toolkit/refined_four_report.json) ·
[Head-selection timing](toolkit/SIDE_ONLY_SEEK.md) ·
[Historical 15-disk evidence](toolkit/refined_av_movie_report.json) ·
[Changelog](CHANGELOG.md)
