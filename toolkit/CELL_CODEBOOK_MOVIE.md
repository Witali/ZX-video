# Complete five-level movie preparation for CB41

2026-09-30, baseline `2a9fa05`. Extend the verified 192-frame experiment to
the entire authorized edit before selecting independently bootable volumes.
This is host preparation and exact capacity evidence, with dirty-RAM cold
bootstrap checks for the two fitting volumes. It does not prove playback
deadlines, disk latency or a complete independently bootable release set.

## Full-data result

All **4221 frames**, **25326 AY ticks** and **29175552 host screen bytes**
pass. The full movie uses **289 distinct rows**. Equal thirds need
245/259/244 rows, so the middle third cannot use the current 256-row table.
A bounded prefix-count search checks 64 boundary pairs, finds 19 that fit,
and selects cuts at **1472 and 2752**. Only this selected layout is encoded.

| Volume | Frames | Row entries, including checkpoints | LZSA2 video bytes | Video sectors | Resident AY bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1472 | 249 | 596174 | 2329 | 12681 |
| 2 | 1280 | 256 | 596202 | 2329 | 13297 |
| 3 | 1469 | 246 | 648146 | 2532 | 14467 |

Total video: **1840522 bytes / 7190 sectors**, from 2906209 raw CB41 bytes,
with **185 independent LZSA2 blocks**. Complete packet/book bytes are counted.
All author/host block round trips and overlap proofs pass. Native all-block
cycles, IRQ delivery and actual full-movie publication remain unmeasured.

All resident sound banks fit and replay the original register states.
The row-only minimum is three volumes; that minimum ignores all other
capacity and timing requirements. It must not be reported as a release fit.

The mean RGB squared error changes **834.5453 -> 743.7552 (-10.879%)** versus
the matching four-level quantizer, with no frame worsening. This score does
not establish source-identical or perceptually transparent output. Inspected
the rabbit, forest textures, tree/grass boundaries and the retained final
scene in the [preview](cell_codebook_movie_preview.png). Spectrum colour-cell
limits remain visible; the worst numeric frame (7, a dark opening fade)
also shows the existing palette-history/colour-quantization limitation.
The fixed dither raster agrees exactly; this is not a new phase-inversion
artifact. The cut and EOF are black in the source; frame 4150/source 4900
shows that the intervening post-credit action is retained.

## Exact disk capacity and decision

The [builder](build_cell_codebook_movie.py) reuses the already compressed
streams and measured AYH1 records. It retains the previous FAP3 container
only for AY and bootstrap scaffolding, replacing every runtime video packet
and both histories with CB41. The per-volume row-index view covers only
that volume plus its two checkpoint frames; indices outside that range are
unused. Each volume has its own tables and stored histories.

| Volume | Video sectors | Startup/player/AY sectors | Total occupied sectors | Free sectors |
| --- | ---: | ---: | ---: | ---: |
| 1 | 2329 | 96 | 2425 | 119 |
| 2 | 2329 | 104 | 2433 | 111 |
| 3 | 2532 | 107 | 2639 | **-95** |

Volumes 1 and 2 produce local candidate images and pass the existing dirty
RAM bootstrap verifier. Volume 3 exceeds the 2544-file-sector limit by
**95 sectors / 24320 bytes**; no invalid third image is written. Total
occupied data is 7497 sectors versus 7632 across three disks, leaving 135
sectors in aggregate, but aggregate capacity does not prove that a valid
partition exists. Reject this particular split as a complete disk set.
Root release/test TRDs are unchanged.

**Next:** use saved frame costs, exact row-set constraints and bounded
windows near the two cuts to rebalance at least 95 sectors from the third
volume. Measure candidate windows, then build one selected complete set;
do not sweep whole movie images. Preserve every frame, AY record and exact
five-level raster. After capacity passes, run each volume through actual
Fuse EOF/publication timing, full screens, AY, disk switching and independent
boot, then integrate the path into the generic converter. Zero late nominal
deadlines remain the target; this preparation supplies no new fps claim.

[Summary](cell_codebook_movie_profile.json) and
[hashed evidence](cell_codebook_movie_evidence/) preserve the successful
preparation and the rejected capacity split. A temporary duplicate `ticks`
field in the first audio-report invocation was fixed before any retained
measurement. The failed unpadded-EOF attempt above is retained as a reason
for the explicit final-interval check.

## Input and preservation

- Original movie SHA-256:
  `dc2146a2b1172def56730143ad80cd1825b7fad15f1fc9c23a4e7d01a741ac11`.
- [Reviewed edit](movie_no_credits.json): retain source frames `0..4085`
  and `4836..4970`, **4221 frames / 506.52 seconds**. The post-credit scene
  and the original final interval remain present.
- Existing edited 50-Hz AY is recovered from the saved full FAP3 input.
  Serialize all nine-byte states and require the original
  [edited soundtrack hash](no_credits_timeline.json); do not resynthesize it.
- Keep the same 256x192 native screen, 256x144 active area, 128x96 logical
  grid, 1.25 center zoom and five-level refinement used in the 192-frame
  fixture. Keep the existing attribute-change penalty of 100000. Palette
  history is continuous across retained frames, including the edit join.
- Reconstruct brightness before the fixed-phase 2x2 dither. A changed
  per-volume row table only renames exact patterns; it cannot approximate
  pixels or omit BRIGHT. FLASH stays disabled and black fields stay fixed.

## EOF correction and resumable preparation

The first attempt with a plain `fps=25/3` filter produced 4970 frames and
was rejected by the timeline check. The original full-movie converter uses
the ceiling of the longer video/audio duration, holding the final image
for the remaining fraction of a six-field interval. The corrected preparation
uses that same policy: probe the duration, require 4971 frames, clone the
source's final image through EOF and stop at the verified rounded duration.
The unextended output is retained for an exact prefix comparison.

The [preparer](prepare_cell_codebook_movie.py) hashes source, FFmpeg,
quantizers and timeline. Its sequential 64-frame caches retain palette
history, source indices, resized RGB and per-frame quality/screen hashes.
Resuming a cached chunk must not reset attributes or borrow future frames.
The refinement is checked against the same frame's four-level result; this
is a quantization-error comparison, not a perceptual score or original-pixel
identity claim.

## What is measured

[measure_cell_codebook_movie.py](measure_cell_codebook_movie.py) begins with
equal-duration thirds. If their rows overflow, it selects the nearest valid
64-frame-aligned boundaries within 256 frames of those cuts using prefix
counts, without compressing candidate movies. Only the selected partition
is compressed. Each row-table union includes
both required screen checkpoints and the black row. The greedy row-only
partition reports a separate capacity constraint; it ignores disk bytes,
audio and timing and cannot select a release by itself.

For each representable volume, include the complete 2048-byte cell book,
packet masks and literal fallbacks, compress independent blocks with the
unchanged LZSA2 format, verify author/host decoding and in-place overlap,
and compare every reconstructed host screen. Video sectors exclude the
bootstrap, program and stored AY, so even a video-only fit is insufficient.
Resident AY sizes include native code/state/alignment, tree nodes and payload;
every original register state is replayed after independent initialization.

The [verifier](verify_cell_codebook_movie.py) checks every complete host
screen with an explicit 2x2 tile raster independent of the lookup tables.
It also verifies the edit mapping, EOF extension, complete AY hash and RGB
alignment with six old fixture samples. The preview includes difficult
scenes, both sides of the edit, EOF and the largest RGB-error frame.
No native hot-path instruction changes occur: **0 T instruction delta**.
No deterministic full-movie CPU or physical disk timing is inferred.

## Reproduction

Run from the repository root with the existing trusted Python runtime and
`PYTHONPATH=local_tools/python_packages;.tmp/lzma-z80-packages;toolkit`.
Use one work directory with an unchanged cache contract.

```powershell
python toolkit/prepare_cell_codebook_movie.py `
  --source C:/Work/HLV-codec/out/sources/big_buck_bunny_1080p_h264/big_buck_bunny_1080p_h264.mov `
  --ffmpeg .worktree/audio-fidelity/.tmp/bin/ffmpeg.exe `
  --audio-raw .worktree/volume-huffman/.tmp/probe/volume-1.raw `
  --work .tmp/cell-codebook-full --report .tmp/cell-codebook-full/prepared.json
python toolkit/measure_cell_codebook_movie.py `
  --prepared .tmp/cell-codebook-full/prepared.json `
  --metadata .tmp/cell-codebook-192/player/metadata.json `
  --author .tmp/lzsa2-oracle/build/lzsa2_oracle_host.dll `
  --output .tmp/cell-codebook-full/measured
python toolkit/verify_cell_codebook_movie.py `
  --prepared .tmp/cell-codebook-full/prepared.json `
  --old-fixture .tmp/five-level-trd/prepared.npz `
  --unextended-rgb .tmp/cell-codebook-movie/analysis.partial.rgb `
  --output .tmp/cell-codebook-full/verification.json `
  --preview toolkit/cell_codebook_movie_preview.png
python toolkit/build_cell_codebook_movie.py `
  --prepared .tmp/cell-codebook-full/prepared.json `
  --measurements .tmp/cell-codebook-full/measured/measurements.json `
  --source-fap3 .worktree/volume-huffman/.tmp/probe/volume-1.raw `
  --options toolkit/fast_zx0_player_build.json `
  --zx0 .worktree/compression/.tmp/ZX0/win/zx0.exe `
  --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe `
  --output .tmp/cell-codebook-full/build
python toolkit/summarize_cell_codebook_movie.py `
  --prepared .tmp/cell-codebook-full/prepared.json `
  --measurements .tmp/cell-codebook-full/measured/measurements.json `
  --verification .tmp/cell-codebook-full/verification.json `
  --capacity .tmp/cell-codebook-full/build/capacity.json `
  --preview toolkit/cell_codebook_movie_preview.png `
  --evidence toolkit/cell_codebook_movie_evidence `
  --output toolkit/cell_codebook_movie_profile.json
```

The first unextended RGB output is diagnostic input, not a player asset.
It can be regenerated with the same source/FFmpeg using
`-an -vf fps=25/3,scale=256:144:flags=area -pix_fmt rgb24 -f rawvideo` to EOF.
The [archiver](summarize_cell_codebook_movie.py) retains hashed full five-level
states, AY, measurements, frame-level quality and representable CB41 streams.
RGB caches remain local; a complete preparation can be reproduced from the
identified original source.
