# Standalone audio-to-AY converter

This folder contains all project source needed to convert an audio file into
a bootable Spectrum 128 + Beta Disk music disk and AY listening previews.
Copy the whole folder to another location to use it independently. It does
not import `toolkit`, `audiobook-ay` or `audiobook-beeper`, and does not need
the movie, old speech disks or archived experiment data.

The existing square-wave-aware analyser is preserved: three tonal voices,
shared noise, fixed channel volumes, and R0..R10 updates at nominal 50 Hz.
This is a chip arrangement, not waveform-transparent PCM compression.
The export is packed nine-byte AY states (`soundtrack.ay9.gz`), eleven-byte
register records (`registers.gz`), a TRD player and WAV previews. It does not
produce the unrelated ZXAYEMUL `.ay` music-file container.

## Install and run

Use Python 3.12+, FFmpeg and Node.js. For complete emulator verification,
also install Fuse with Spectrum 128 and TR-DOS support. Python dependencies
are listed locally; Ayumi JavaScript source and its MIT license are vendored.
No npm packages are required.

From this folder:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe convert_audio.py "C:/Audio/song.flac" --output "build/song" --title "SONG TITLE" --ffmpeg "C:/Tools/ffmpeg.exe" --node "C:/Program Files/nodejs/node.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

On Linux/macOS use `.venv/bin/python` and the corresponding executable paths.
FFmpeg and Node.js are found on PATH when their explicit options are omitted.
`--fuse` is optional: without it the disk and model previews are built, and
the report explicitly records that disk timing has not been verified.

- `--duration SECONDS`: limit the excerpt, rounded down to complete 20-ms
  records. The resident limit is 8934 ticks /178.68 seconds.
- `--start SECONDS`: nonnegative source offset on the 20-ms grid.
- `--title TEXT`: screen title, defaulting to the input filename.
- `--once`: mute at EOF; the default repeats from RAM.
- `--output DIRECTORY`: a new or empty destination.

Mount `audio-preview.trd` in drive A of Spectrum 128 + Beta Disk/TR-DOS.
Run `RUN "boot"` if the emulator does not autostart. The disk boots without
RAM from a previous disk; all reads finish before sound begins.

## Outputs and source map

The output includes the TRD, original/model WAVs, compressed AY/register
streams, separately assembled player, constants, screen and build report.
With `--fuse`, it also contains complete native/Fuse verification and a
normal-speed `fuse-preview.wav`. That WAV is emulator output, not a physical
Spectrum recording. Similarity metrics do not establish listening acceptance.

| File | Purpose |
| --- | --- |
| `convert_audio.py` | FFmpeg input, analysis, assembly, preview and verification CLI |
| `ay_fidelity.py`, `ay_square_fit.py` | Harmonic analysis, pitch tracking and square-wave fit |
| `ay_format.py` | Packed AY state format and R0..R10 conversion |
| `quality.py` | Independent comparison metrics and WAV output |
| `music_player.py`, `ay-player.asm` | TRD packaging and separately assembled Z80 player |
| `trd.py` | Disk directory, BASIC boot and Spectrum screen addressing |
| `render_ym2149.js`, `vendor/ayumi-js/` | YM2149 model, source and license |
| `verify_preview.py`, `fmf_audio.py` | Complete native/Fuse execution checks and recording parser |
| `support.py` | Report helpers and hidden Windows process startup |
| `test_music_player.py` | Bank boundaries, capacity, looping, EOF and CPU timing tests |
| `SOURCE_MANIFEST.json` | Original source paths, definitions and source hashes |

The original experiment sources remain in the parent repository for historical
reproduction. This folder is the independent source distribution. Third-party
Python libraries, FFmpeg, Node.js, Fuse and ROMs are external dependencies,
not copied project source.

## Verify

```powershell
.venv/Scripts/python.exe -m unittest discover -s . -p "test_*.py"
```

The native tests execute the real assembled Z80, including 1, 1488, 1489,
1490 and 8934 ticks, both repeats across all six banks, and one-shot EOF.
The ordinary field path remains 974 T; near-boundary 992 T, bank change
1091 T, exact-boundary EOF 1007 T, and first field after loop restart 1079 T.
Moving the sources changes the hot path by **0 T**. These counts exclude
ULA waits, HALT waiting, ROM and physical disk latency. Fuse verifies actual
register-write timestamps against every original 70908-T field deadline.

See [the extraction and full-example verification](verification.json) for
the preserved musical example and the separate-folder execution check.
