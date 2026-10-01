# YM2149 audiobook check at 50 Hz

**Later listener decision (2026-10-01): rejected as unintelligible.** The user
requested [beeper PDM at >=40 kHz](../audiobook-beeper/README.md) instead.
The measurements and pending-listener wording below preserve the state when
this YM experiment was first delivered; they are not a current acceptance.

The user accepted the **software-decoded LPC2 reference**, then requested
better fidelity and an actual AY-compatible generator check. The final
constraints are **one register state per 50 Hz interrupt** and typical
Spectrum mixing. The new diagnostic uses the same **[60,84) second** passage.

## Listen

- [YM2149 candidate, mono](ym2149-preview/ym2149-preview.wav).
- [Previous formant mapping through the same YM2149 model](ym2149-preview/baseline-preview.wav).
- [Original, matched level](ym2149-preview/original-preview.wav).
- [Full LPC2 software reference, matched level](ym2149-preview/lpc-reference-preview.wav).
- [Bootable Spectrum 128 + Beta Disk diagnostic TRD](ym2149-preview/audiobook-preview.trd).
- [Root-level test disk](../ZX-audiobook-YM2149-test.trd), an identical copy
  provided for convenient emulator loading. Mount it in drive A of a
  Spectrum 128 with Beta Disk/TR-DOS. If it does not autostart, enter TR-DOS
  and run `RUN "boot"`. Playback begins after loading and stops after the
  24-second excerpt; reset and boot again to replay.

All four WAVs are 24 seconds, mono, 44100 Hz, with common RMS 0.0560742 and
no sample clipping. The TRD plays the first file's register sequence. It does
**not** execute an LPC filter or play the full software reference. This is a
bounded comparison; the original two-minute disk remains historical.

## Chip and mixing

[Ayumi](https://github.com/true-grue/ayumi), using its unmodified
[JavaScript port](vendor/ayumi-js/README.md), models the YM2149 DAC levels,
three independent square-wave tone generators, and **one shared** 17-bit
noise generator. The shared noise enters the A/B/C Boolean mixers; it is
not an independent fourth analogue output. The wrapper uses R0..R10 only,
fixed 4-bit volumes, 1,773,450 Hz effective chip clock and 50 state changes/s.
Envelope mode and high-rate sample/DAC volume output are disabled.

The three outputs are summed equally to mono, with fixed headroom and
Ayumi's DC removal. There is no stereo widening, reverb or added original
audio. Mono is the stock Spectrum arrangement; see the
[Fuse sound documentation](https://fuse-emulator.sourceforge.net/man/html/fuse.html).
The waveform is a chip simulation, not a physical recording or a component-
level model of a particular board's resistors, loading, amplifier and speaker.
Wave rendering applies each state atomically at nominal 20 ms boundaries;
the real player writes eleven registers sequentially within the same field.
CPU timing is checked separately below. Generator phase persists between
updates, without artificial phase resets.

## Encoder change and result

The selected 50 Hz preparation retains the existing 8 kHz LPC2 analysis,
20 ms hop, 32 ms window, order 10, pitch tracking and synthesis. It disables
**approximate** coefficient repeats (`repeat=.05 -> 0`); identical quantized
coefficients can still repeat losslessly. The LPC stream grows **4114 ->6461
bytes** (1371.33 ->2153.67 bit/s). Approximate/exact repeats fall from 516 to
11 frames. Mode, pitch and silence counts remain unchanged.

The offline formant mapper selects three continuous-frequency resonances,
uses the actual YM2149 fixed-volume table, and routes nonvoiced noise through
B with A/C muted. This remains a restricted approximation of the LPC envelope:
three square waves and unfiltered shared noise cannot implement its full
ten-order speech filter. The chip register stream is 13200 resident bytes;
the LPC file itself is not the data format replayed by the Spectrum.

| Signal, same YM model and source window | Spectral cosine | Loudness correlation | Onset F1 |
|---|---:|---:|---:|
| Previous formant mapping | 0.596526 | 0.858975 | 0.711864 |
| New 50 Hz mapping | 0.666873 | 0.874808 | 0.757576 |
| Full new LPC2 software reference | 0.889800 | 0.823184 | 0.888889 |

These are signal proxies, not intelligibility scores or percentages of
preserved speech. The new mapping improves these three measures, but remains
well behind full LPC on spectral shape. Keep it as a listening candidate;
listener acceptance of this YM version is still pending. Previous acceptance
of the software reference must not be transferred to the chip version.

Before the user specified 50 Hz, one 10 ms/exact-repeat host profile was also
completed. It improved spectral cosine 0.874207 ->0.896003, loudness
correlation 0.809145 ->0.920091 and onset F1 0.840580 ->0.869565, at **4114
->12601 bytes** for 24 seconds. [Its report](lpc-detail/report.json) and WAVs
remain as evidence. It is **not selected for AY playback**: the final
50 Hz candidate above is encoded directly at 20 ms, not dropped or paired
100 Hz register frames.

## Verification and cost

- Independent Python parsing agrees with the JavaScript LPC2 decoder on every
  quantized frame of the original, 10 ms and final 20 ms streams. Pack/unpack/
  repack is exact; complete finite outputs contain 192000 samples each.
- Seven Python tests pass. Chip checks cover the known tone period, independent
  noise tap recurrence, shared A/B noise, all sixteen tone/noise mixer cases,
  distinct AY/YM DAC tables, silence and sample counts.
- All **1200 ticks /13200 register writes** match in the independent Z80 core
  and a complete cold Fuse run. There are **zero missing/duplicate fields**,
  52 startup sector reads and zero runtime reads. The final state is held for
  one full field before muting. The TRD occupies 96 sectors.
- Player code is unchanged: **974 T per tick, delta 0 T** for this one-bank
  interval. This counts deterministic foreground work, separately from IRQ,
  ULA and disk timing. Actual first OUT phase is 150..153 T; consecutive
  first OUTs are 70905..70909 T apart in the 70908-T Spectrum 128 field.
  A 50 Hz label is nominal; the simulated WAV uses exact 20 ms intervals.
- No Z80 LPC decoder, physical-chip recording or real-drive measurement is
  claimed. LPC analysis runs on the host; the Z80 replays precomputed states.

[Complete report](ym2149-preview/report.json) ·
[Native and cold Fuse evidence](ym2149-preview/verification.json).

## Reproduction

First reproduce the cached source PCM with `probe_lpc2.py` as documented in
[LPC2_COMPARISON.md](LPC2_COMPARISON.md), using the identical source and codec.
The PCM SHA-256 is checked before reuse. Then:

```powershell
python audiobook-ay/probe_ym2149.py --lpc-source "C:/Work/LPC-sound-codec/index.html" --node "C:/Tools/node.exe" --ffmpeg "C:/Tools/ffmpeg.exe" --source-pcm "build/lpc-probe/source.f32" --output "build/ym2149-preview"
python audiobook-ay/verify_preview.py "build/ym2149-preview" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
node audiobook-ay/test_ym2149.js
python -m unittest discover -s audiobook-ay -p "test_*.py"
```

`compare_lpc2_detail.py` reproduces the earlier 10 ms host comparison. Its
original producer source files are archived in `lpc-detail/producer-sources/`
to preserve the exact pre-50-Hz experiment. Current code also retains that
profile under `detail`; the selected profile is `detail50`.
