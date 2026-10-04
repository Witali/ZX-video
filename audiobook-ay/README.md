# AY audiobook preview

The maintained standalone audio conversion entry point is
[ay-converter](../ay-converter/README.md), with all required project sources
in one portable folder. The older speech experiments below remain archived.

**Disk retirement (2026-10-04):** obsolete speech TRDs described below
were removed at the user's request. Links marked "retired" lead to the
[removal inventory](../audiobook-beeper/retired-disks.json), with exact paths, hashes and the recovery
commit. Measurements, WAVs and build instructions remain historical evidence.

**Music and arbitrary audio (2026-10-04):** use
[convert_audio.py](convert_audio.py) and [the converter guide](CONVERTER.md).
The existing movie synthesizer now has an audio-oriented command that builds
a looping TRD, renders a YM2149 preview, and optionally verifies and records
the disk in Fuse. The public-domain The Entertainer example uses the same
initial passage as the beeper comparison, rounded down to a 20-ms AY tick.
The earlier audiobook previews and their listening feedback below remain
historical evidence.

**New experiment (2026-10-02):** after the user's observation about the rabbit's
recognizable vocal effect, a [pitch-preserving AY50 candidate](PITCH_AWARE_PREVIEW.md)
retains the vocal fundamental and fits two harmonic square waves. It includes
a new 24-second listening comparison and fully verified test TRD. Acceptance
of its speech intelligibility remains pending.

**Listening feedback (2026-10-01):** the user found this first preview
completely unintelligible. The original files remain for comparison, not as
an accepted speech result. See the [LPC2 reuse comparison](LPC2_COMPARISON.md)
for a 24-second diagnostic based on the existing LPC codec.

The user subsequently accepted the **full host LPC2 reference** as intelligible.
The latest [YM2149 listening check](YM2149_PREVIEW.md) provides a new 24-second
chip-constrained preview: 50 Hz, three tone channels, one shared noise source,
Spectrum-style mono sum, and a fully verified diagnostic TRD. Do not confuse
the full LPC decoder's voice with what those chip registers can reproduce.

**Subsequent feedback (2026-10-01):** the user also rejected the YM2149 TRD
as unintelligible and requested beeper PDM at >=40 kHz. The new
[beeper subproject](../audiobook-beeper/README.md) provides that separate test.

A separate audio-only subproject. The first **120 seconds** of the supplied
O. Henry recording (1977) are converted with the same refined three-voice,
square-aware AY synthesizer used by the movie. The user selected compact
AY synthesis, then scoped the delivery to a two-minute preview on 2026-10-01.
The complete 667.596916-second audiobook has not been converted.

## Listen and play

- [AY preview](preview/ay-preview.wav): 120-second mono WAV, 22050 Hz.
- [Original excerpt](preview/original-preview.wav): the same source interval,
  downmixed to mono and matched to the AY preview's RMS for comparison.
- [Spectrum disk (retired)](../audiobook-beeper/retired-disks.json): one independently bootable
  TRD. Open in **Spectrum 128 + Beta Disk** mode and run `boot` in TR-DOS
  if the emulator does not autostart it. The sound starts after preloading,
  plays once, then all three channels are muted. Reset to replay.

This is tonal/noise synthesis at 50 updates per second, not a recording of
the original voice. The WAV models AY tones and noise; it is not captured
from the physical analogue output. Voice identity and intelligibility need
listening assessment. There is no claim of a percentage of speech accuracy.

## Result and evidence

The disk contains 6000 AY ticks / 66000 register bytes, occupying **302 of
2544 usable sectors**. The portable nine-byte states use 54000 bytes,
compressed to 25039 bytes in `soundtrack.ay9.gz`; gzip is an archive format,
not the Spectrum decoder. Every playback register is preloaded into RAM.

[Verification](preview/verification.json) covers the complete preview:
independent native Z80 execution and a cold Fuse 1.9.0 run, all 66000 actual
register writes, all 6000 successive fields, all four bank changes and EOF.
No field is missing or duplicated. There are 258 startup sector reads and
zero runtime reads. Actual first-OUT phases are 150..153 T after the field
boundary; intervals are 70905..70911 T (the 3 T variation comes from HALT
alignment). Each tick belongs to its original nominal field, with no drift.
The last tick is held for a full field before muting. No physical hardware
was tested. The preview's 120 seconds use the conventional 50 Hz timing;
real Spectrum 128 fields are 70908 T, slightly different from exactly 20 ms.

[Quality report](preview/report.json): spectral cosine 0.850804, chroma
cosine 0.960339, loudness correlation 0.989443 and onset F1 0.807198 at a
10 Hz metric rate. These are signal proxies, not an intelligibility score.
The source SHA-256, exact interval, fit settings and artifact hashes are
recorded. [Raw emulator trace](preview/verification-work/fuse-trace.txt.gz)
preserves actual write timestamps and values.

## Build and verify

Use Python 3.12+ with the parent project's `requirements.txt`, FFmpeg and
the `z80` Python package for independent CPU verification. The build imports
the existing movie synthesizer; no copy or change to that synthesizer is made.
The two-minute host analysis additionally reads one second of source context.
Existing output directories must be empty. Supply the original audio path:

```powershell
python audiobook-ay/build_preview.py "C:/Audio/book.m4a" --output "build/book-preview" --start 0 --duration 120 --ffmpeg "C:/Tools/ffmpeg.exe"
python audiobook-ay/verify_preview.py "build/book-preview" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python -m unittest discover -s audiobook-ay -p test_player.py
```

`--start` and `--duration` use 20 ms increments. This resident preview player
accepts up to 7445 ticks (148.9 seconds). Longer continuous playback needs a
separate streaming milestone; this program rejects an oversized request.
It also rejects an excerpt extending past source EOF.

## Memory and timing

All eight 16 KiB banks are accounted for. Bank 5 holds the screen, BASIC and
TR-DOS workspace. Bank 2 holds code at 8000h, the title screen at 9000h..AAFFh,
the stack below B800h, the BDBDh interrupt jump and the BE00h..BF00h IM2 table.
Banks 0/4/6/1/3 hold sound, with 1489 whole eleven-byte ticks per full bank;
five tail bytes per bank are unused. Bank 7 remains spare. No preceding
program's RAM is required. Disk reads occur before audio starts, so no
smaller runtime disk buffer or unmeasured producer schedule is assumed.

Instruction counts follow [Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf)
and are checked by the independent Z80 core. The R0..R10 output loop costs
78 T per continuing register, 73 T for the final one:
`LD E,(HL)` 7 + `INC HL` 6 + `LD B,FFh` 7 + `OUT (C),D` 12 +
`LD B,BFh` 7 + `OUT (C),E` 12 + `INC D` 4 + `LD A,D` 4 +
`CP 11` 7 + `JR NZ` 12/7. Setup is 14 T, totaling **867 T**.
The field check costs 38 T; decrement/store 46 T; ordinary bank test 23 T.
Thus ordinary complete foreground work is **974 T**, or 992 T near the end
of a bank and 1091 T when changing banks. The exact-EOF bank-boundary path
costs 1007 T, covered by native boundary tests. IRQ body `EI; RETI` is 18 T;
IM2 acknowledgement is 19 T and the vector `JP` adds 10 T. ULA contention,
HALT waiting, boot ROM execution and physical disk latency are separate.

Baseline: movie sources and hot paths are unchanged (**0 T delta**). For a
contextual comparison, its older queued `ay_interrupt.audio_tick` costs
`367 + 83*11 = 1280 T` for eleven changed registers, excluding call/IRQ.
The new dedicated foreground path is 974 T (306 T less), but has a different
contract: full resident records, no queue, and no concurrent video or disk
work. This is not a speedup claim for the existing movie player. Both paths
produce the same selected AY register states. Chip register semantics follow
the [General Instrument manual](https://map.grauw.nl/resources/sound/generalinstrument_ay-3-8910.pdf).

The authorized deliverable is complete. A further synthesis change or a
full-book streaming player should follow the user's assessment of this sound.
