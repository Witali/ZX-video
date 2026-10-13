# One-disk sea-foam cartoon excerpt

## Current90-second full-disk rebuild (2026-10-13)

The latest independently qualified disk extends the source prefix to90 seconds
with the local solid/pattern transition correction and source-hue guard.
It uses2529 data sectors(99.4104%),15 free, retaining10 fps and50-Hz AY.
All900 actual screens and4500 AY records pass complete cold Fuse, with zero
nominal deadline misses and maximum in-field deviation22 T. The root TRD
matches the new archive. Preserve the older50.7-second versions below.

See [the current TRD, full video, measurements and reproduction](../attribute_pattern/README.md).

## Earlier source-matched colour rebuild (2026-10-13)

The latest qualified version uses `stable_colour.py`, current-source temporal
feedback, actual-pixel colour guards and spatial coherence across attribute
cells. A connected smooth gray region uses a shared source-valid palette;
quiet cells are protected from later spatial regrouping. Meaningfully changed
cells have zero direct history influence. Real source contours and the fixed
dither phase remain intact. `--monochrome` is now available for either public
converter format; `--colour-policy legacy` reproduces the old CB41 selection.

- [Current TRD](evidence-colour/ZX-video-sea-foam_part01.trd)
- [Current native-reference MP4](evidence-colour/native-preview.mp4)
- [Source / previous / current comparison video](evidence-colour/colour-comparison.mp4)
- [Comparison sheet](evidence-colour/colour-comparison.png)
- [Complete qualification](evidence-colour/qualification.json)
- [Frame measurements](evidence-colour/colour-comparison.json)

The source interval, all507 prepared RGB frames and2535 AY controls/WAV bytes
are identical to the original archive below. This remains one50.7-second
independently bootable10-fps TRD with50-Hz AY. The disk now uses1436 sectors
(+115),1108 free; it still meets every nominal deadline. Spectrum's two colours
per8x8 cell remain a hardware constraint. The selector suppresses mismatching
colours, so muted source areas often use gray; it cannot reproduce the source
gamut or guarantee absence of every visible cell/dither artifact.

| Measurement against the scaled source | Previous | Current |
| --- | ---: | ---: |
| Area-averaged RGB MSE | 494.64372 | 465.80088 |
| Actual2x2 pixel RGB MSE model | 8891.00644 | 8621.12748 |
| Actual2x2 opponent-colour MSE model | 2098.39740 | 386.63225 |
| Source-weighted boundary residual MSE | 231.36326 | 151.03494 |
| Temporal chroma residual MSE | 58.44063 | 43.06844 |
| Near-static pooled RGB temporal residual MSE | 19.02686 | 13.89894 |
| Near-static pooled Rec.709 luma temporal residual MSE | 18.12883 | 13.68272 |

Boundary error falls34.72%, temporal colour error26.30%, and quiet-area luma
error24.53%. These are defined error proxies, not perceptual quality grades.
Quiet attribute-change counts rise6 ->831 because choosing current-source
palettes differs from the old strongly held attributes; a count alone is not
a measurement of visible flicker. Near-static temporal errors are pooled over
2194912 logical samples. The synthetic smooth gray ramp's boundary residual
falls54.05114 ->1.23110; actual contour and no-lag source tests also pass.

The complete cold Fuse1.9.0 run compares all507 screens/3504384 bytes and every
2535 AY record. Zero missed nominal deadlines, missing/duplicate AY fields,
or late runs; maximum in-field publication deviation19 T. Runtime1367 sector
reads,38520429 T aggregate read-call service (22303..134473 T per call),937507 T
seek service. These measured intervals combine ROM/disk/IRQ/contention.
The host-only changes add0 T to player instructions; unchanged absolute
baseline costs remain in native metadata. No physical hardware result.

Twenty-seven focused tests and both public monochrome CPU/content smoke builds
pass. The smoke fixtures have6 CB41 frames or5 FAP3 frames,30 silent AY fields;
they do not establish Fuse cadence for an arbitrary monochrome movie. Inspect
source/old/current frames98..100,154,259,506. Earlier unsuccessful selectors,
the gray-regrouping brightness regression and their complete/partial coverage
are retained under `evidence-colour/superseded/` and in the root changelog.
Intermediate producer sources were not saved; the final producer hashes are
authenticated in the qualification. The147-file archive contains61672605
measured bytes, excluding its manifest; binary/media files use Git LFS.

### Reproduce using retained source preparation

This avoids a new download, source normalization or expensive audio fit.
Start from the original archive's exact RGB prefix, full decoded mono PCM,
continuous fit and WAV. Supply the executable `$tools` array and `$ffmpeg`
as described below, and choose new empty scratch/build directories:

```powershell
$preparedColor = '.tmp/sea-foam-colour-prepared'
New-Item -ItemType Directory -Path "$preparedColor/work" -Force
Copy-Item -LiteralPath toolkit/analysis/sea_foam/evidence/work/continuous-audio-fit `
  -Destination "$preparedColor/work/ay-core" -Recurse
Copy-Item -LiteralPath toolkit/analysis/sea_foam/evidence/work/frames.rgb `
  -Destination "$preparedColor/work/frames.rgb"
Copy-Item -LiteralPath toolkit/analysis/sea_foam/evidence/work/continuous-audio-fit/input.f32 `
  -Destination "$preparedColor/work/audio-source.f32"
Copy-Item -LiteralPath toolkit/analysis/sea_foam/evidence/work/continuous-audio-fit/audio-preview.wav `
  -Destination "$preparedColor/work/audio-preview.wav"
python toolkit/analysis/sea_foam/build_prefix.py $preparedColor `
  --plan toolkit/analysis/sea_foam/evidence/prefix-plan.json `
  --output .tmp/sea-foam-colour-rebuild --frames 507 @tools
python toolkit/analysis/sea_foam/preview.py .tmp/sea-foam-colour-rebuild --ffmpeg $ffmpeg
python toolkit/analysis/sea_foam/compare_colour.py .tmp/sea-foam-colour-rebuild --ffmpeg $ffmpeg
python toolkit/analysis/sea_foam/temporal_luminance.py .tmp/sea-foam-colour-rebuild
```

`archive_colour.py` requires complete qualification and the five superseded
candidate report directories before preserving a new archive. The original
report/reproduction section below describes the historical `fe3bb2cf` result;
use that revision for its exact former default. Current scripts use the new
selector, and planning estimates alone remain insufficient for release.

## Original qualified excerpt and preserved baseline

The user requested a TRD from [this YouTube video](https://www.youtube.com/watch?v=WGc7ptKfA9c).
The completed deliverable is source interval **[0,50.7) seconds**, 507 frames
at 10 fps and 2535 AY updates at 50 Hz, on one independently bootable disk.
Target: Spectrum 128, Beta Disk and the verified TR-DOS 5.03 ROM. This is a
verified excerpt, not the complete cartoon or a maximum-duration claim.

- [TRD](evidence/ZX-video-sea-foam_part01.trd)
- [MP4 preview](evidence/native-preview.mp4)
- [Qualification and producer hashes](evidence/qualification.json)
- [Complete timing and screen evidence](evidence/timing.json)
- [Artifact manifest](evidence/manifest.json)

The MP4 renders exact native reference screens with the shared AY simulation.
It is a convenient listening/viewing preview; actual disk timing, complete
screen bytes and AY register records were independently checked in Fuse.
The soundtrack targets the real three-channel AY-3-8910, with the current
shared automatic fitter, compact dynamics, sparse noise and hardware envelopes.
The separate hypothetical six-voice experiment is not used by this disk.

## Input and bounded selection

The downloaded 648x480, 25-fps H.264/AAC source has SHA256
`995ddb8988fd57f5d718df9f4811faf7d7dc68999164116effe04ce1178bd931`.
Public identifiers are retained in [source.json](evidence/source.json); temporary
signed media URLs and the large downloader metadata are not archived.

The first 120 seconds were prepared and tested in 32-frame windows using
existing guarded CB46 representations. This estimated a 101.5-second candidate.
Its mux/decode endpoint produced 1016 frames, or 101.6 seconds, and resident
AY forest allocation split it at frames [0,507,1015,1016]. The original build
then failed before qualification because an old bootstrap checkpoint used
only 11 registers for a 14-register AYH2 stream. The unsuccessful attempt's
[partition, manifest and log](evidence/superseded-longer/) are retained.

Commit `7f9206ed` fixes complete checkpoint restoration. The final build uses
the first resident-valid 507-frame part, with lossless RGB-prefix equivalence
checked before encoding. It reuses the exact first 2535 controls and the same
processed reference/calibration from continuous 5080-field audio analysis.
The complete source mono PCM and continuous fit are retained under
`evidence/work/continuous-audio-fit/`; there is no new partial-audio fit claim.
Explicit video frame count avoids the earlier extra EOF frame.

[prefix-plan.json](evidence/prefix-plan.json) records the final extent but also
retains the original 120-second probes and longer-candidate size estimate.
Those estimates are planning evidence, not measured sizes of the final disk.
The selected disk uses 1321 of 2544 usable sectors, leaving 1223 free. Its
duration was bounded by the existing resident audio allocation and conservative
partition, rather than exhaustively maximizing disk occupancy.

## Complete verification

Fuse 1.9.0 cold-boots the selected TRD, with dirty RAM, and completes the whole
excerpt. All 507 screens match, including all 6912 bytes per screen:
3,504,384 compared bytes over five complete capture passes. All 2535 AY records
match with zero missing or duplicate fields. All nominal five-field frame
deadlines are met, with zero late frames or late runs. Maximum publication
deviation within the nominal field is 17 T-states; no fallback field is needed.

Actual runtime includes 1250 sector reads. Fuse reports 35,305,209 T-states
of aggregate read-call service, range 22,308..134,473 per call, and 852,681
T-states of seek service. These measurements combine ROM, disk emulation,
interrupts and contention; deterministic instruction costs are kept separate.
No physical-machine or physical-drive result is claimed.

The checkpoint repair has **0 T runtime delta**. Its startup restore loop
changes from 930 T for 11 registers to 1185 T for 14, **+255 T**, plus the
same 17-T setup. Existing CB46 and AYH2 runtime costs remain those documented
in generated metadata and [CHIP_MODEL.md](../../../ay-converter/CHIP_MODEL.md).
Generic converter reports retain their conservative `release:false` labels;
the input-specific complete qualification above applies only to this excerpt.

Eight checkpoint/bootstrap/disk tests and 19 generic converter tests pass.
Five-level refinement reduces cell-averaged source RGB MSE from 620.26689
to 494.64372, maximum frame MSE 759.81737; compression adds no pixel changes.
Frames 98..100,154 and506 were visually inspected. These are palette/error
measurements and visual checks, not a perceptual percentage score.
The 20-ms PCM16 RMS audit finds zero fields more than 15 dB below the prepared
source among 2530 source fields above -45 dBFS. See [level-check.json](evidence/level-check.json).

## Reproduction

Use the recorded producer versions, NumPy, FFmpeg/ffprobe, Node, ZX0, LZSA2,
Fuse 1.9.0 and the TR-DOS ROM recorded in the conversion metadata. From the
repository root, set the executable variables below to the local installations
and keep each new output directory empty. The source is downloaded explicitly
from the user's URL; no account or cookies are needed.

```powershell
yt-dlp --js-runtimes "node:$node" --no-cache-dir --ffmpeg-location $ffmpeg `
  -f "135+140-1" --merge-output-format mkv `
  -o .tmp/youtube-WGc7ptKfA9c.mkv "https://www.youtube.com/watch?v=WGc7ptKfA9c"
python toolkit/analysis/sea_foam/plan.py .tmp/youtube-WGc7ptKfA9c.mkv `
  --output .tmp/sea-foam-plan --ffmpeg $ffmpeg --ffprobe $ffprobe --lzsa $lzsa
$tools = @('--ffmpeg',$ffmpeg,'--ffprobe',$ffprobe,'--node',$node,`
  '--zx0',$zx0,'--lzsa',$lzsa,'--fuse',$fuse,'--trdos-rom',$trdosRom)
python toolkit/convert_video.py .tmp/sea-foam-plan/selected-prefix.mkv `
  --output .tmp/sea-foam-candidate --prefix ZX-video-sea-foam --video-codec cb41 `
  --fps 10 --guarded-cb46 --ay-chip AY-3-8910 --ay-dynamics compact --verify none @tools
python toolkit/analysis/sea_foam/build_prefix.py .tmp/sea-foam-candidate `
  --plan .tmp/sea-foam-plan/plan.json --output .tmp/sea-foam-final --frames 507 @tools
python toolkit/analysis/sea_foam/preview.py .tmp/sea-foam-final --ffmpeg $ffmpeg
```

The fixed implementation no longer reproduces the historical checkpoint crash;
the first conversion only prepares the continuous data for the selected build.
`build_prefix.py` requires full Fuse qualification. [archive.py](archive.py)
requires successful complete gates before copying evidence and creating the
SHA256 manifest. Its arguments specify public metadata, planning/conversion/
download logs, test logs and the superseded longer attempt. The archive contains
122 measured files totaling 60,290,864 bytes, excluding the manifest itself.
TRD, media and large binary arrays are stored in Git LFS; every measured file
is retained without newline conversion.
