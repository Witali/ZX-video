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

## Current three-disk experiment

The root `ZX-video-fast-preview_part01..03.trd` images use the
[adapted Fast ZX0 player](toolkit/FAST_ZX0_PLAYER.md). Each boots independently.
All 4221 frames complete in Fuse with exact 50-Hz AY and unchanged compressed
video data. Video still misses deadlines: this is an experimental preview,
separate from the verified release and the generic converter defaults.
Disk images are stored in Git LFS.

Historical documentation:

- [Converter options, reports and verification](toolkit/GENERIC_CONVERTER_ru.md)
- [H.263 and lightweight block codecs](toolkit/LIGHT_VIDEO_CODECS_ru.md)
- [Deferred disk-read measurements](toolkit/FAP3_DEFERRED_DISK_ru.md)
- [Earlier movie builds and research](toolkit/README_ru.md)
