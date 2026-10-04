# Persistent channels and mixed noise, 20-ms AY states

Completed 2026-10-04 after `c886631`. The user clarified that continuing
components must stay on the channels where they started despite small pitch
or amplitude changes, with three dominant components and separately detected
noise. This is now the standalone converter's optional `--profile music`.
The output quantum remains **20 ms /50 Hz**. `legacy` remains the default.

## Listen and inspect

- [Latest independently bootable disk](../../../ZX-music-Entertainer-AY-tracked50-test.trd)
- [Normal Fuse recording, two complete repeats](evidence/release/fuse-preview.wav)
- [Original / original AY disk / new version, equal global RMS](evidence/comparison/comparison-original-old-new.wav)
- [Channel tracks and noise](evidence/comparison/channel-tracks.png)
- [Complete spectrogram](evidence/comparison/spectrogram-full.png),
  [12–16-s detail](evidence/comparison/spectrogram-12-16s.png),
  [attack detail](evidence/comparison/spectrogram-attacks-12-16s.png)
- [Every 20-ms state and component ID](evidence/release/channel-states.json.gz)
- [Channel/mixer audit](evidence/comparison/channel-audit.json),
  [native/Fuse proof](evidence/release/verification.json),
  [completion audit](evidence/completion.json)

The comparison WAV starts its original, old and new sections at 0, 32.12 and
64.24 seconds. Each contains the full 31.12-s excerpt, separated by one second.
The normal Fuse recording retains physical timing. The comparison maps both
captures by the same known Spectrum clock ratio, without fitting alignment
to the signal; see the [comparison method](../music50/README.md).

## Component identity

The input remains the same public-domain keyboard recording of The Entertainer,
first 31.128 s requested, 1556 states /31.12 s retained. Source SHA-256:
`08dc5241de419edf9693ad20797389cb735d9b6fc06bfb6936568bb707f13077`.
Use the [existing provenance](../../../audiobook-beeper/experiments/ima-3bit-entertainer/source.json).

`channel_tracking.py` selects three dominant fitted harmonic fundamentals,
rather than the three largest raw FFT harmonics. Selection excludes adjacent
duplicate pitches, rejects components below 6% of the strongest estimate and
uses a 15% retention bonus to reduce rank chatter. The previous role ranges
(bass/harmony/melody) no longer fix channels to those musical roles.

For every 20-ms update, all six assignments are compared by pitch continuity.
The match gate is two semitones with bounded pitch-motion prediction; amplitude
rank is absent from the matching cost. A continuing component retains its ID
and hardware channel. When it leaves the selected components, that lifetime
ends and a new component can use the released slot. The three-channel limit
still prevents retaining all overlapping notes of a dense source. Coincident
sources and estimation mistakes remain ambiguous; IDs are not ground truth.

Existing held-note pitch, short-window envelopes and YM2149 calibration are
retained. The exported interval contains **289 estimated component lifetimes**,
with **zero ID migrations**. Tests independently permute input candidates and
swap their amplitudes while moving pitches slightly; outputs keep the expected
physical channels. Separate tests cover releasing one channel and filling it
without moving the other two. These tests, plus every-state audits, establish
the algorithm's invariant without claiming perfect source separation.

## Noise controls and physical mixing

Noise detection now uses the broadband residual independently of a particular
tone's loudness. A 17-bin frequency median rejects narrow peaks; energy-share
hysteresis is .18 on / .12 off. The source RMS/estimated broadband energy sets
the requested level. Correlation with 31 sample-and-hold noise templates fits
R6's period, which changes the noise's frequency colour. This is a heuristic;
keyboard attacks and dense harmonics can still be misclassified as noise.

AY has **one shared noise generator**. R6 selects its period, R7 routes tone
and/or noise to each channel, and R8–R10 control channel amplitude. When tone
and noise share a channel, they also share its volume. The chip combines their
binary gates rather than adding an independently adjustable fourth oscillator.
These controls follow the [General Instrument register description](https://cpctech.cpcwiki.de/docs/ay38912/psgspec.htm).

Each detected noise event first uses a free channel if available. Otherwise,
the algorithm selects the occupied channel with the closest achievable
tone/noise balance and keeps that route through the event. The tone gate stays
enabled. A shared-level fit approximates the Boolean mix: coherent tone
amplitude M/2 and additional noise equivalent to M/sqrt(2), with fourfold
weight on preserving the tone. This cannot reproduce independent tone and
noise amplitudes exactly; it is not a freely adjustable additive mixer.

Noise is enabled for 415 of 1556 ticks: 398 alongside a tone and 17 on a free
channel. **No active tone is disabled**, and no noise route changes within an
event. Pitch, volume, noise period and mixer changes are all described on the
20-ms grid. The tone generators' fast oscillation is produced by the chip.

## Four bounded host comparisons

[probe.py](probe.py) reuses one complete analysis and compares four fixed
variants; [all results and settings](evidence/results.json) are retained.
The control is the exact register stream from the preceding music milestone,
not the original legacy disk used by the later Fuse comparison.

| Variant | STFT cosine, 512 | 2048 | 8192 | Finer onset F1 | Noise ticks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Previous music v1 | .83381 | .82558 | .81513 | .74783 | 109 |
| Persistent role-selected tones + noise | .83195 | .82315 | .81462 | .68800 | 415 |
| Persistent dominant tones, noise disabled | .84022 | .83536 | .82929 | .63810 | 0 |
| **Persistent dominant tones + noise** | **.83882** | **.83063** | **.82231** | **.69106** | **415** |

Select the final row because it implements both explicit requirements and
improves full-bin magnitude cosine at all three resolutions versus v1. The
no-noise variant has stronger tonal cosine but fails the requested noise
behavior. Role-based selection is weaker here. Adding noise changes the
spectral balance: log-magnitude MAE and onset F1 regress against v1. The
selected row's semitone-pooled cosine rises .89209 -> .90302, while chroma
falls .97579 -> .97433. No row is declared universally better sounding.

## Complete Fuse spectrogram comparison

Compare both loops against the original keyboard signal using the same
method as before: three Hann window sizes, unpooled 50–8000-Hz bins, 20-ms
hop, global RMS match, common −60-dB floor. The fixed known clock mapping is
50*70908/3546900; raw-time results are saved too. The reference disk in this
table is the user's original `ZX-music-Entertainer-AY.trd`.

| Window | First-loop cosine old → new | First-loop log-magnitude MAE old → new, dB |
| --- | ---: | ---: |
| 512 | .81846 → .82651 | 9.92776 → 9.77503 |
| 2048 | .80556 → .81248 | 9.26998 → 9.45849 |
| 8192 | .79872 → .80224 | 7.78490 → 8.12608 |

Second-loop cosine also improves at all scales: .82500/.80678/.79729 ->
.82846/.81330/.80227. Its medium/long-window log error also worsens. Fine
onset F1 is mixed: .62963 -> .64662, then .64093 -> .63396. Thus dominant
spectral lines agree better, but weaker/noisier structure and rhythm are not
uniformly closer. [Complete measurements](evidence/comparison/fuse-spectrogram.json)
retain all regressions. Visual inspection of the complete piece and fixed
intro/busy/end regions confirms remaining missing polyphony and stronger
broadband texture; do not equate cosine gains with listening acceptance.

## Format, timing and verification

The packed AY9 extension keeps nine bytes and all tone-period bits. Byte 5
bit 7 marks an explicit six-bit mixer. Byte 3 bits 7..5 store R7 bits 2..0;
byte 5 bits 6..4 store R7 bits 5..3. Noise-period packing is unchanged.
Without the marker the reader retains exact legacy tone/noise-only-B behavior.
Old movie AY9 readers do not implement this new marker; use the standalone
converter's updated reader. R0..R10 output stays eleven bytes per tick.

All 32 noise periods ×64 mixers round-trip and match an independent packed
decoder. All 64 mixer values also execute through the native Z80 core. The
14-test suite covers old full capacity/banks/loops/EOF, channel continuity,
noise versus a pure tone, calibration, envelopes and spectral metrics.

The entire new disk cold-boots and plays two full Fuse loops: 34232 exact
register writes /3112 fields, zero missing fields, 67 startup sectors, no
runtime disk reads. Loading-message handling passes. Startup is 10.677687 s;
normal captured audio lasts 62.226236 s including the final capture tail.
The player binary is identical to the original: **974 ->974 T ordinary work,
delta 0 T**, unchanged 992/1091/1079-T special paths, 17116 resident bytes.
Instruction counts exclude ULA/HALT/IRQ/ROM/disk latency; actual write timing
is separately checked in Fuse. No physical-hardware test is claimed.

The complete default CLI reproduces the original disk, AY/register streams
and both original/model WAVs byte for byte. All 176 prior image hashes remain
unchanged. New disk SHA-256:
`2e6a14a9637a9fae6d7546826473148de1e3b263a8b58717abfcbfe61f79e8d4`.
Generated trace/capture evidence, normal WAV, every 20-ms state, spectral
figures and all four host variants' register streams are archived here.

## Reproduce

Use the existing Python dependencies, FFmpeg, Node.js and Fuse; Matplotlib
is only required for diagnostic figures. Set `OPENBLAS_NUM_THREADS=1`.

```powershell
python -m unittest discover -s ay-converter -p "test_*.py" -v
python ay-converter/analysis/tracked50/probe.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline ay-converter/analysis/music50/evidence/release --output build/tracked-probe --ffmpeg FFMPEG --node NODE
python ay-converter/convert_audio.py audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --output build/tracked-release --duration 31.128 --title "THE ENTERTAINER" --profile music --ffmpeg FFMPEG --node NODE --fuse FUSE
python ay-converter/analysis/music50/compare_fuse.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline audiobook-ay/music-preview --candidate build/tracked-release --output build/tracked-figures --ffmpeg FFMPEG
python ay-converter/analysis/tracked50/inspect_channels.py --directory build/tracked-release --baseline audiobook-ay/music-preview --probe build/tracked-probe/results.json --output build/tracked-figures
```

Use new output directories for conversion/probing. The earlier milestone's
historical source hashes refer to its commit `c886631`, not to this revision.
