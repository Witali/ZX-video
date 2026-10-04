# Convert arbitrary audio to an AY music disk

**Standalone sources (2026-10-04):** [ay-converter](../ay-converter/README.md)
contains the complete converter, analyser, assembly player, renderer and
verification code without imports from other project folders. Use that folder
for independent conversion. The commands and measurements below preserve the
original integrated experiment and its evidence.

`convert_audio.py` uses the existing movie analyser in `toolkit/ay_fidelity.py`
and its square-wave spectral fit in `toolkit/ay_square_fit.py`, unchanged.
It accepts FFmpeg audio input, downmixes to mono, selects three tonal voices
and shared noise, and prepares register R0..R10 updates at nominal 50 Hz.
This is an arrangement for the chip, not a waveform-transparent recording
codec. Piano timbre, chords containing more than three notes and percussion
can change. Spectral/rhythm metrics do not replace listening assessment or
have the same meaning as the PDM waveform SNR.

## One command

Use Python with the repository dependencies, pyz80, Node.js and FFmpeg.
The vendored Ayumi implementation is already included; no npm install is
needed. From the repository worktree:

```powershell
python audiobook-ay/convert_audio.py "C:/Audio/song.flac" --output "build/song-ay" --title "SONG TITLE" --ffmpeg "C:/Tools/ffmpeg.exe" --node "C:/Program Files/nodejs/node.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

The command performs analysis, separately assembles [ay-player.asm](ay-player.asm),
packages its binary, produces previews and runs complete native/Fuse checks.
Python generates constants, pixels and audio data, not Z80 instructions.
With `--fuse`, it also records normal-speed emulator sound. Without this
option the disk is built but explicitly marked as not timing-verified.

- `--duration SECONDS` limits the initial excerpt. It is rounded down to
  complete 20-ms records. Omitting it retains as much as fits, up to 178.68 s.
- `--start SECONDS` selects a nonnegative offset on the 20-ms grid.
- `--title TEXT` sets the screen title; the filename is the default.
- Playback loops by default; `--once` holds the final record for a field,
  then mutes all channels.
- The output directory must be new or empty. Missing/too-short input is
  rejected; the converter never silently repeats a short input to fill RAM.

Outputs are `audio-preview.trd`, `original-preview.wav`, `ay-preview.wav`,
register streams, assembly and `report.json`. The original and Ayumi WAVs
are RMS-matched for comparison. `fuse-preview.wav` is the unnormalised
normal-speed Fuse sound-generator output and contains two repeats by default.
`verification.json` records every register, field, EOF/wrap and disk-read check.
No physical sound-card or Spectrum measurement is implied.

## The Entertainer example

Use [the root TRD](../ZX-music-Entertainer-AY.trd),
[actual Fuse sound](music-preview/fuse-preview.wav),
[YM2149 model](music-preview/ay-preview.wav), and
[original excerpt](music-preview/original-preview.wav).
Run the disk in Spectrum 128 + Beta Disk/TR-DOS; use `RUN "boot"` if needed.
The loading message disappears when the data is ready. Reset stops playback.

The input is the same unrestricted recording used for the PDM example:
Scott Joplin's The Entertainer, performed by IE. See
[source and rights](../audiobook-beeper/experiments/ima-3bit-entertainer/source.json)
and the [recording page](https://commons.wikimedia.org/wiki/File:The_Entertainer_-_Scott_Joplin.ogg).
The 31.128-s requested comparison interval becomes **31.12 s / 1556 ticks**,
discarding only the final 8 ms to fit the 50-Hz grid. No 8-kHz preprocessing
is applied: the AY analyser reads the original 44.1-kHz stereo Ogg and uses
a 22.05-kHz mono analysis signal with one second of following context.

```powershell
python audiobook-ay/convert_audio.py audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --output build/entertainer-ay --duration 31.128 --title "THE ENTERTAINER" --ffmpeg "C:/Tools/ffmpeg.exe" --node "C:/Program Files/nodejs/node.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

The example needs **17116 resident register bytes**, compared with 93432
bytes of IMA3 in the preceding 31.128-s PDM example. The archive AY9 stream
uses 14004 bytes before gzip. Gzip is for host storage; the Spectrum plays
resident raw register records. There are 243 noise-enabled ticks. The actual
YM2149 model has three tone generators and one shared noise generator,
Boolean tone/noise gating, four-bit fixed volumes and equal mono mixing.
No original recording, PCM DAC stream or LPC reconstruction is mixed in.

The unchanged independent analysis gives spectral cosine **0.892788**,
chroma cosine **0.975713**, loudness correlation **0.995346**, and onset
F1 **0.887097**. These are similarity measures, not percentages of fidelity.
The [report](music-preview/report.json) and
[verification](music-preview/verification.json) preserve measured coverage.

Complete native and cold Fuse runs verify all **34232 writes / 3112 fields**
over two repeats, with no missed or duplicate nominal fields, 67 startup
sector reads and zero runtime reads. The loading check reads all 768 bitmap
bytes in the message area before and after loading. First-OUT phases are
150..255 T; intervals are 70805..71010 T, including the extra 105-T wrap path.
The first write stays in its nominal field at every tick. Nominal tempo error
is +0.042308% at the verified Spectrum clock. Normal cold startup is
10.677687 s; the captured WAV is 62.226236 s including its final audio chunk.
It contains two full repeats; it is not a claim that each music loop has
exactly half that container duration.

TRD SHA-256: `c6139c9c5cd4c18df82d3b1f208064790487a48db3883b26f916d00765fc177c`.

## Memory and timing

All eight RAM banks are accounted for. Banks 0/4/6/1/3/7 provide up to 8934
whole 11-byte records, with five unused tail bytes per bank. Bank 5 holds
the display, BASIC and TR-DOS workspace. Bank 2 reserves 8000..8FFF for code,
9000..AAFF for the screen copy, a stack below B800, the BDBD IM2 jump and the
BE00..BF00 vector table. Fixed-bank gaps are unused; audio never aliases code,
stack or TR-DOS workspace. No previous disk state is required. There are no
runtime disk reads or producer/consumer disk-buffer assumptions.

The ordinary field path is **974 native T**, delta **0 T** from the earlier
AY audiobook player. R0..R10 setup/output is 867 T, field check 38 T,
decrement/store 46 T and ordinary bank test 23 T. Near a bank end it is 992 T;
bank change is 1091 T; exact-boundary EOF is 1007 T. These instruction-table
counts are checked by the independent Z80 emulator.

Loop restart adds **105 T**, once per repeat: `LD DE,nn`10 +
`LD (nn),DE`20 + `LD HL,nn`10 + `LD (nn),HL`16 + `LD A,n`7 +
`LD BC,nn`10 + `OUT (C),A`12 + `LD HL,nn`10 + `JP nn`10.
The first repeated field therefore costs **1079 T**. It publishes tick zero
in the original next field, with no extra silent field or schedule drift.
The loading-message clear runs only before playback, with zero hot-path cost.
IRQ body remains 18 T, IM2 acknowledgement 19 T and vector jump 10 T.
These counts exclude ULA contention, HALT waiting, ROM and physical disk time.

At the Spectrum 128 clock of 3546900 Hz, each field is 70908 T, slightly
different from exactly 20 ms. Complete Fuse checks validate actual write
timestamps and all nominal fields, including the wrap; native checks alone
do not certify that timing. The native boundary suite also covers one tick,
1488/1489/1490 ticks, and two repeats of the full six-bank capacity. The
capacity fixture is synthetic, not a complete 178.68-s music release.
