# One-disk sea-foam cartoon excerpt

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
