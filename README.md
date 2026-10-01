# ZX-video

Convert video files into TRD disk images for **ZX Spectrum 128 + Beta Disk**.
FFmpeg detects the input format: MP4, MKV, AVI, MOV and other supported
formats. The converter processes the complete input; it does not depend on
a particular movie or remove credits automatically.

## Usage

Install Python 3.11+, FFmpeg/ffprobe and the ZX0 v2 compressor in `PATH`.

```powershell
python -m pip install -r requirements.txt
python toolkit/convert_video.py "C:/Video/example.mp4" --output "build/example"
```

The output directory must be new or empty. The converter creates
`ZX-video_part01.trd`, `ZX-video_part02.trd` and as many parts as needed.
Override tool paths with `--ffmpeg`, `--ffprobe` and `--zx0`.

The converter preserves the aspect ratio and uses a 256×192 player screen
with a 256×144 active area, a target rate of 25/3 fps and AY synthesis at
50 Hz. It supports the noise channel, progress for the current disk and
automatic continuation after inserting the next disk. Inputs without an
audio track produce silence.

By default, all frames and Z80 timings are checked with ideal data delivery.
**Playback timing with disk reads is checked separately in Fuse**:

```powershell
python toolkit/convert_video.py "C:/Video/example.mp4" --output "build/example-tested" --disk-profile trdos503 --trdos-rom "C:/Program Files (x86)/Fuse/roms/trdos.rom" --verify fuse --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

Complex video may not sustain 8⅓ fps. The `timing.json` report records each
late frame and disk delays; a successful build does not by itself prove
smooth playback. AY synthesis approximates the original audio; 95% audio
accuracy is not claimed.

[Current decode-speed plan](toolkit/DECODE_SPEED_PLAN.md) ·
[Full-frame CPU profile](toolkit/FRAME_HOTSPOTS.md) ·
[Experiment history](CHANGELOG.md)

## Five brightness levels with CB41/LZSA2

Select `--video-codec cb41` to use five levels, fixed 2×2 dithering and the
player used by the verified three-disk movie. Install the LZSA executable
in addition to ZX0; `--lzsa PATH` overrides its location. This mode selects
the player optimizations automatically and requires the verified TR-DOS 5.03
ROM. The existing FAP3 command remains available as the default.

```powershell
python toolkit/convert_video.py "C:/Video/example.mp4" --output "build/five-level" --video-codec cb41 --lzsa "C:/Tools/lzsa.exe" --trdos-rom "C:/Program Files (x86)/Fuse/roms/trdos.rom" --verify fuse --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

CB41 selects volume boundaries using 32-frame compression windows and exact
row/AY memory checks, then builds one final set. It retains the complete
input, aspect ratio and all five brightness levels. Native table/capacity
limits produce an explicit error. Arbitrary videos are not guaranteed to
fit three disks or meet the timing target; `--verify fuse` measures every
frame's deadline, full screen, AY tick and disk read. See
[generic CB41 details and checks](toolkit/GENERIC_CB41.md).

## Verified three-disk movie

The root LFS `ZX-video-five-level_part01..03.trd` images contain the authorized
4221-frame edit with five brightness levels. Every disk boots independently
and completes at 25/3 fps with zero late frames, exact full screens and 50-Hz
AY. The next-disk prompt and continuation are checked. See the
[complete measurement and limitations](toolkit/CELL_CODEBOOK_BALANCED.md).
The older Fast ZX0 preview images are historical experiments.

Historical documentation:

- [Converter options, reports and verification](toolkit/GENERIC_CONVERTER_ru.md)
- [H.263 and lightweight block codecs](toolkit/LIGHT_VIDEO_CODECS_ru.md)
- [Deferred disk-read measurements](toolkit/FAP3_DEFERRED_DISK_ru.md)
- [Earlier movie builds and research](toolkit/README_ru.md)
