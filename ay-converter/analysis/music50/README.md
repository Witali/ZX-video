# Entertainer: implemented 20-ms music profile

Completed 2026-10-04, starting from `8bcc3c3`. The user authorized the
remaining music improvements, excluded 100-Hz playback, fixed the sound
quantum at **20 ms**, and requested spectrogram comparisons. This bounded
experiment implements and tests the changes, then delivers one complete
new listening disk. It does not replace the earlier disk or claim a
universally better arrangement.

## Deliverables

- [New bootable TRD](../../../ZX-music-Entertainer-AY-music50-test.trd)
- [Normal-speed Fuse sound, two complete repeats](evidence/release/fuse-preview.wav)
- [Original / previous AY / new AY comparison](evidence/comparison/comparison-original-old-new.wav)
- [Full spectrogram](evidence/comparison/spectrogram-full.png)
- Detail: [0–4 s](evidence/comparison/spectrogram-00-4s.png),
  [12–16 s](evidence/comparison/spectrogram-12-16s.png),
  [27–31.12 s](evidence/comparison/spectrogram-27-31.12s.png),
  [attack detail](evidence/comparison/spectrogram-attacks-12-16s.png)
- [Full build report](evidence/release/report.json),
  [native/Fuse verification](evidence/release/verification.json),
  [archive audit](evidence/archive-check.json)

The comparison WAV contains three 31.12-s sections, separated by one second:
original at 0 s, previous AY at 32.12 s, new AY at 64.24 s. All sections have
equal global RMS. Its Fuse sections use the fixed clock mapping described
below. The separate normal-speed Fuse WAV retains actual emulator timing.

## Input and implementation

The input is unchanged: the existing public-domain The Entertainer recording
by IE on a Casio WK-3300, [rights/provenance](../../../audiobook-beeper/experiments/ima-3bit-entertainer/source.json).
SHA-256: `08dc5241de419edf9693ad20797389cb735d9b6fc06bfb6936568bb707f13077`.
Request 31.128 s, retain 1556 complete 20-ms states /31.12 s. The analyser
also receives one second of following context, as before. No MIDI score,
recording-specific note sequence or original waveform is mixed into the AY.

The new optional `--profile music` uses:

1. Long-window harmonic analysis for pitches, a second 2048-sample analysis
   for faster note envelopes, and 512-sample windows for attacks. The output
   grid remains 50 Hz throughout. Shorter internal analysis is not a faster
   Spectrum register stream.
2. A bounded joint three-voice beam search (32 states), prioritizing melody
   and bass, excluding duplicated adjacent pitches, with lower transition
   penalties near attacks. The sequential tracks provide a weak prior.
3. A 0.5 blend of short-window note strengths for higher notes; bass retains
   longer-window resolution. Release smoothing stays inside the note
   lifetime and cannot leak through a rest or into a new note.
4. Fixed-volume YM2149 levels from the exact vendored Ayumi DAC table, used
   for quantization and square-wave fitting. Noise's legacy level estimate
   is explicitly converted through physical amplitude before fitting. The
   fitter's candidate cache includes the curve; no global table is mutated.
5. One median integer period per estimated note event. Repeated attacks
   can start another event. All 433 exported events have integer tick bounds
   and one constant period; they are estimates, not labelled source notes.
6. Noise restricted to an attack and its next tick for tonal passages,
   while retaining sustained broadband effects under the documented
   explained-energy/flatness gate. This reduces noise from 243 to 109 ticks
   in the excerpt (4.86 to 2.18 s), instead of disabling it globally.

All project sources remain inside `ay-converter`. `legacy` is still the CLI
default and reproduces the old register stream exactly. The new mode is
intended for fixed-pitch keyboard-like sources: it may erase deliberate
vibrato or pitch bends. It is a heuristic, not a neural transcription or an
instrument-specific physical decay model. No hardware envelope, new mixer
format, high-rate volume modulation or 100-Hz scheduler is introduced.

## Seven fixed host comparisons

[probe.py](probe.py) performs one shared source decomposition and seven
predetermined full renders. [Results](evidence/results.json) retain all
settings, hashes, pitch diagnostics, STFT metrics and onset counts. Each
variant's complete register stream and arrangement metadata are saved in
`evidence/ablations/`; host WAVs are reproducible from those streams.

| Variant | STFT cosine, 512 | 2048 | 8192 | Onset proxy F1, ±20 ms | Noise ticks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Legacy control | .83076 | .82366 | .81797 | .65891 | 243 |
| Held pitch + calibrated levels | .82949 | .82166 | .81439 | .71967 | 264 |
| Add faster envelopes | .83222 | .82212 | .81281 | .75105 | 261 |
| Add transient-only tonal noise | .83172 | .82310 | .81437 | .78539 | 124 |
| Add joint voices | .82909 | .82319 | .81374 | .70732 | 245 |
| Envelopes + transient noise, sequential voices | .83235 | .82406 | .81504 | .78414 | 120 |
| **Joint voices + envelopes + transient noise** | **.83381** | **.82558** | **.81513** | **.74783** | **109** |

Every non-control row includes held pitch and calibrated levels. The three
single-addition rows are relative to that pair, not cumulative. The final
row is the selected listening preview: it has the strongest short/medium
window magnitude cosine among the seven and lowers spectral convergence
error at all three resolutions versus the control:
`.56230/.58059/.59838 -> .55799/.57038/.59679`.
It improves onset F1, but the sequential combined variant scores better on
that particular proxy. Long-window magnitude cosine decreases. This is an
explicit tradeoff, not selection by one best-looking score.

The old semitone-pooled metric is nearly unchanged: `.89279 -> .89209`;
chroma `.975713 -> .975791`; legacy coarse onset F1 `.88710 -> .90323`.
Neither cosine is a percentage of correct notes. The finer flux detector
finds 92 source events; baseline matches 85 with 166 generated detections,
new host render matches 86 with 138 detections. Fewer extra attacks explain
most of this improvement.

Pitch changes within unchanged note labels decrease from 279/134/197 to
20/10/18 for bass/harmony/melody. Remaining changes are between separately
detected attacks, not inside exported events. The largest bass step remains
49.78 cents, so this is not proof of accurate tuning. Short harmony runs
increase from 34 to 51; joint allocation does not solve every tracking error.
Retain these regressions rather than presenting note stability as perfect
transcription. No additional parameter search follows this bounded comparison.

The probe's original module, before addition of the thin CLI preset wrapper,
is preserved in `evidence/probe-sources/music_profile.py`; its hash exactly
matches the probe report. The release report hashes the current production
sources. The selected CLI register stream is byte-identical to `joint_full`.

## Independent spectrogram check on actual Fuse sound

[compare_fuse.py](compare_fuse.py) compares both complete captured loops,
not just the host renderer. [All measurements](evidence/comparison/fuse-spectrogram.json)
include raw-time comparisons and both loops. Each STFT uses Hann windows,
twofold FFT padding, linear frequency bins 50–8000 Hz, and a 20-ms hop.
Window lengths are 23.22, 92.88 and 371.52 ms. One global RMS normalization
is applied to each whole interval; there is no local gain matching, fitted
delay, dynamic time warping or octave/chroma folding. Log-magnitude MAE
uses the union of bins above a common source-relative −60 dB floor.

Spectrum 128's nominal 50-Hz interrupt is 70908 T at 3546900 Hz in Fuse.
The fixed source-time mapping is `50*70908/3546900 = .99957709549`; a physical
loop lasts 31.106839 s. Both captures receive this same known clock mapping,
including its tiny resampling pitch effect; no signal-dependent alignment
is fitted. Unmapped first-31.12-s metrics are also saved and show the same
general short/medium-window trend. They include about 13 ms of the next loop.

First complete Fuse loop:

| Window | Magnitude cosine old → new | Log-magnitude MAE old → new, dB | Spectral convergence old → new |
| --- | ---: | ---: | ---: |
| 512 | .81846 → .82346 | 9.92776 → 9.71170 | .60151 → .59289 |
| 2048 | .80556 → .80889 | 9.26998 → 9.13648 | .63050 → .61734 |
| 8192 | .79872 → .79644 | 7.78490 → 7.64777 | .64599 → .64353 |

Lower MAE/convergence is better. Second-loop MAE also falls at all three
resolutions, but long-window convergence slightly regresses
`.64670 -> .64732`. Long-window magnitude cosine regresses in both loops.
The actual-sound finer onset F1 rises `.62963 -> .77533` and
`.64093 -> .74894`; matched source events are `85 -> 88` and `83 -> 88`.
The old coarse onset F1 regresses on the first loop and improves on the
second. Oscillator/noise phases continue through repetition, so identical
registers need not produce identical repeated PCM waveforms.

Figures use a common colour scale and global RMS, with 80–6000 Hz shown on
a logarithmic vertical axis. Inspect the full piece and fixed intro/busy/end
regions rather than only a favourable fragment. Visual inspection shows
more stable horizontal partials and less continuous noise in some gaps,
while the keyboard's dense partial structure and decaying chord overlaps
remain different. Three square-wave voices still lose source polyphony and
timbre. The improvements are modest, not a faithful piano reconstruction.

## Playback and regression evidence

The complete cold-boot disk passes native and Fuse checks through two loops:
3112 fields, 34232 exact R0..R10 writes, zero missing/duplicate fields, 67
startup sector reads and no disk reads during playback. The loading message
is shown during loading and hidden before sound. Startup is 10.677687 s;
normal recording is 62.226236 s including the capture's final partial field.

The Z80 player binary is **byte-identical** to the previous disk. Ordinary
work stays **974 -> 974 T, delta 0 T**; near-boundary 992 T, bank switch
1091 T, loop restart 1079 T. These are deterministic instruction counts,
excluding ULA, IRQ, HALT, ROM and disk latency; actual Fuse output phases
are verified independently. Storage stays 17116 register bytes /1556 states,
550 bytes/s, 178.68-s maximum resident capacity. The stream describes all
three channels every 20 ms, including unchanged values.

Eight regression tests pass: existing full-bank/loop/EOF Z80 tests plus
calibration isolation, repeat-event bounds, envelope rests, chord allocation,
silence/pure tone, and spectrogram identity/gain/octave rejection. An actual
CLI excerpt starting at 12.02 s with requested duration 1.019 s yields 50
states /1.00 s, correct clipped events and complete native one-shot mute.
That offset case is not separately Fuse-qualified. The archive audit verifies
all release artifact/source hashes, held periods in all exported events,
selected-host/CLI identity, and unchanged hashes of all 175 prior disk images.

New disk SHA-256:
`e1ef02bc4bee6163698a4b8ed16dfaa12ec5c2852834a24e57b60d6631619663`.
Existing `ZX-music-Entertainer-AY.trd` is retained. New disks and WAVs use Git
LFS. No physical-hardware result or subjective listening acceptance is claimed.

## Reproduce

Use the converter dependencies, FFmpeg, Node.js and Fuse. Matplotlib is
needed only for `compare_fuse.py`, not for conversion. Set
`OPENBLAS_NUM_THREADS=1` for the recorded numerical environment. From the
repository root, replacing executable placeholders:

```powershell
python -m unittest discover -s ay-converter -p "test_*.py" -v
python ay-converter/analysis/music50/probe.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline audiobook-ay/music-preview --output build/music50-probe --ffmpeg FFMPEG --node NODE
python ay-converter/convert_audio.py audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --output build/music50-release --duration 31.128 --title "THE ENTERTAINER" --profile music --ffmpeg FFMPEG --node NODE --fuse FUSE
python ay-converter/analysis/music50/compare_fuse.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline audiobook-ay/music-preview --candidate build/music50-release --output build/music50-comparison --ffmpeg FFMPEG
```

The first two output directories must be new. The converter still defaults
to `legacy` when `--profile` is omitted. The preserved generic music preset
does not import the Entertainer probes or any source outside this folder.
