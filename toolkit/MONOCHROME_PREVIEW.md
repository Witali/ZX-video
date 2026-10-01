# Monochrome five-level disk preview

2026-10-01, baseline `1a0c7d0`, branch `codex/cb41-10fps`.

The user requested a black-and-white disk for visual comparison. The root
image [ZX-video-monochrome-preview.trd](../ZX-video-monochrome-preview.trd)
contains **256 frames / 25.6 seconds**, prepared movie frames `[4128,4384)`.
It is a single independently bootable preview of the same difficult window
as the previous colour test, not the complete movie or a new release set.

## Picture and sound

- Active cells use PAPER black, INK BRIGHT white, FLASH off (`0x47`).
  Physical pixels are exclusively RGB 0 or 255. All five 2x2 area coverages
  remain available at the original fixed phase and resolution: 128x96
  logical samples, 256x192 physical screen, 256x144 active picture.
- Quantize the cached source directly, using encoded-RGB Rec.709 luma
  `(2126 R + 7152 G + 722 B)/10000`, then nearest 0/25/50/75/100% coverage.
  This intentionally discards colour. There is no palette inertia,
  per-cell colour search, extra contrast stretch or error diffusion.
- Preserve static black bands and the existing white-on-black per-disk
  progress bar. The original 1280 AY ticks are copied exactly at 50 Hz.
- Contact sheet inspected at frames 4128, 4213, 4298, 4383. Coloured cell
  artifacts are removed; five-level banding/dither and loss of chromatic
  detail remain. Mean error against the grayscale source is 337.807 luma
  MSE; this is not a colour-fidelity or perceptual percentage.

[Source / grayscale / Spectrum comparison](monochrome_preview_evidence/monochrome-preview.png)

## Capacity and complete playback verification

| Same 256-frame window | Previous colour | Monochrome |
| --- | ---: | ---: |
| LZSA2 video bytes | 145814 | 159862 |
| Used disk sectors | 618 | 669 |
| Free sectors | 1926 | 1875 |
| Row dictionary entries | 180 | 178 |
| Missed nominal deadlines | 0 | 2 |

Removing colour does not guarantee better compression: the new grayscale
quantization changes bitmap patterns, even though attributes are constant.
No full-movie disk-count estimate follows from this window.

The complete Fuse run verifies all **1769472 screen bytes**, all **1280 AY
ticks**, **625 runtime sector reads**, and progress through 100%. Dirty-RAM
independent bootstrap passes. No missing/duplicated AY fields or underruns.
Thirteen unit/regression tests pass.

The exact five-field target is **not met** on two zero-based local frames:

| Late frame | Prepared movie frame | Original schedule recovered at |
| --- | --- | --- |
| 80 | 4208 | 81 |
| 115 | 4243 | 116 |

Both are one field late, with 6-field then 4-field intervals, no dropped
frames and no accumulated drift. Actual OUT deviation is `-1..70912 T`:
one 70908-T field plus four instruction-phase T-states at the maximum,
within the existing 64-T phase tolerance. The user-authorized one-field
fallback passes; the zero-late objective remains unmet. Average measured
cadence is 9.99999978 fps. This is a tested preview with disclosed jitter,
not an exact-deadline release. No physical drive run was performed.

The player is unchanged from the colour window. Native renderer and packet
instruction listings and cadence metadata compare exactly: **0 T instruction
delta**. The cadence `LD DE,5` remains **10 -> 10 T** and the same codebook
loader remains **54028 -> 54028 T**. Changed data still changes decoding,
memory-write and disk costs; actual whole-player timing above includes
TR-DOS, emulated drive latency, IRQ and contention.

## Reproduce and evidence

The builder now accepts the explicit `--monochrome` option; its default
colour path is unchanged. It uses authenticated cached RGB, keeping the
existing media fit, frame selection and AY timeline.

```powershell
$env:PYTHONPATH='local_tools/python_packages;.tmp/lzma-z80-packages;toolkit'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest toolkit.test_monochrome_five_level toolkit.test_five_level_dither toolkit.test_video_cadence
python toolkit/build_cb41_cadence_movie.py --prepared .tmp/cb41-10fps-movie/prepared/preparation.json --output .tmp/cb41-monochrome-preview --trdos-rom tools/fuse-1.9.0-sdl/roms/trdos.rom --zx0 .worktree/compression/.tmp/ZX0/win/zx0.exe --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --fuse tools/fuse-1.9.0-sdl/fuse.exe --start 4128 --count 256 --verify fuse --prefix ZX-video-monochrome-preview --monochrome
python toolkit/finalize_monochrome_preview.py --build .tmp/cb41-monochrome-preview --prepared .tmp/cb41-10fps-movie/prepared/preparation.json --colour-baseline toolkit/cb41_10fps_window_evidence/cb41-10fps-window-ZX-video-10fps_part01.json.gz --tests .tmp/monochrome-tests.log --evidence toolkit/monochrome_preview_evidence --output toolkit/monochrome_preview_report.json --image ZX-video-monochrome-preview.trd --allow-fallback
```

Use a new/empty build output and capture the passing unittest log for
`--tests`. The explicit `--allow-fallback` archives a completely measured
preview only when one-field recovery passes; it never marks missed nominal
deadlines as exact playback. The finalizer authenticates all images, traces,
screen passes, source audio and native listings before copying the root TRD.

[Report and archive hashes](monochrome_preview_report.json) include the
complete screen/timing traces, quality, RGB/state inputs, codebooks, streams,
AY and reproducing script snapshots. Root and archived TRDs use Git LFS.
Existing colour release images remain available for comparison.

Image SHA-256: `38cecad279376a10b86fa5265930976b923d202465310026525eef2ed40cd16f`.
