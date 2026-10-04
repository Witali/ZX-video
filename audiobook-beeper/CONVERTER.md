# Audio-to-TRD converter

`convert_audio.py` defaults to **packed IMA3 decoded directly to beeper PDM**.
The user accepted the overlap speech disk in an interactive Program Files
Fuse 1.9.0 session on 2026-10-04 and requested this playback algorithm as the
main option. The existing `convert_ima3_audio.py` entry point remains usable.
Select `--codec ima4` explicitly for the [historical four-bit converter](IMA4_CONVERTER.md).

## Run

Use the project's Python dependencies and put `audiobook-beeper` and `toolkit`
on PYTHONPATH. Supply paths to FFmpeg and Fuse when needed:

```powershell
python audiobook-beeper/convert_audio.py "input.m4a" --codec ima3 --output "build/audio" --ffmpeg "path/to/ffmpeg.exe" --fuse "path/to/fuse.exe"
python audiobook-beeper/convert_audio.py "input.m4a" --codec ima4 --output "build/ima4" --ffmpeg "path/to/ffmpeg.exe" --fuse "path/to/fuse.exe"
```

Omitting `--codec` is equivalent to `--codec ima3`. Use `--help` for the
default profile or `--codec ima4 --help` for the four-bit profile's options.
Existing shared preparation functions and the four-bit Python `convert()`
API remain compatible; CLI dispatch selects the profile.

| Option | IMA3 (default) | IMA4 (explicit) |
| --- | --- | --- |
| RAM representation | Packed three-bit codes | Packed four-bit codes |
| Playback | Decode directly to PDM; no IMA3-to-IMA4 conversion | Decode directly to PDM |
| Default disk output | `audio.trd`, sequential RAM-sized parts | `audiobook-preview.trd`, looping RAM excerpt |
| Whole selected track | `--disk-mode all` | Not supported by this historical converter |
| Looping RAM excerpt | `--disk-mode preview` | Default |
| Search controls | `--target-snr`, `--attempts`, `--resume` | `--iterations` |

Both accept `--duration N` and `--no-recording`. The latter omits normal-speed
Fuse sound capture while retaining complete native/Fuse verification. New
outputs must use an empty directory; IMA3 can resume only a matching saved
run. Changed producer sources invalidate old resume caches by design.

For a shared externally normalized comparison reference, both codecs accept
`--prepared-pcm` without changing its gain. Use `--disk-mode preview` for
IMA3. IMA4 requires mono PCM8/8 kHz, 8192..186880 samples in multiples of
512, and 128 final silent samples (value 128); do not combine it with
`--duration`. IMA3 retains its documented groups-of-eight/RAM validation.

## Main profile

The PC prepares mono 8-kHz /8-bit source audio and optimizes its packed
IMA3 stream against the measured PDM schedule. Waveform search uses
128/256-sample horizons with 64-sample commits. Spectrum loads the packed
codes into RAM and decodes them as it emits PDM; there is no full PCM/PDM
expansion buffer. Disk reads happen between consecutive RAM-sized parts.

One TRD is the default. `--disk-mode all` produces numbered independently
bootable disks. See [sequential playback](IMA3_SERIES.md) for output names,
capacity and audible loading pauses, and [the direct decoder](IMA3_DIRECT.md)
for timing, search and verification details.

The accepted reference is [ZX-audiobook-IMA3-overlap-test.trd](../ZX-audiobook-IMA3-overlap-test.trd),
SHA-256 `ac4b740ebdcf2f9fb538d286b8ac679df6babc53462cf79b18f08cc8b5a2d66d`.
Its two verified parts measure 20.436046 dB with -0.271723% mean speed error.
These are input-specific measurements. Other audio retains the 20-dB default
quality gate and +/-2% speed requirement; an unmet IMA3 quality target exits
with code 2 and an explicitly marked preview. No physical-hardware result
or universal absence of audible artifacts is claimed.

The accepted emulator setup was Spectrum 128 + Beta 128, 100% speed,
44.1-kHz /16-bit host output. [Launch the reference](experiments/fuse-host-output/manual-launch.cmd)
with those settings. The earlier vibration's original cause remains unknown;
the user accepted this direct interactive playback. Host output rate is
separate from the source sample rate and the Spectrum PDM pulse rate.

Promoting the CLI default changes no Z80 instruction, table, stream or TRD.
Mean native IMA3 cost remains 427.375 T/sample, delta 0 T; page/bank extras
remain +14/+140 T. Reuse the complete prior disk verification.
