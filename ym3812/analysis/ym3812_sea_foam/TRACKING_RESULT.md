# Coherent source-supported YM3812 song

Completed 2026-10-14 under [the authorized plan](TRACKING_PLAN.md), in the
existing `codex/ym3812-sea-foam` worktree. The selected `soft52` rendition
passes every original admission guard and an additional low-frequency content
guard. Improvement is modest; the measurements do not establish that every
reported electronic tone has become inaudible.

- **[Selected complete 90-second audition](tracking-evidence/ym3812-preview.wav)**
- **[Old/new comparison: original 0..90 s, silence, selected 91..181 s](tracking-evidence/before-after.wav)**
- [VGM commands](tracking-evidence/ym3812.vgm), [483,310-byte VGZ](tracking-evidence/ym3812.vgz)
- [Full spectrogram](tracking-evidence/spectrogram-full.png), [12.50..15.50 s detail](tracking-evidence/spectrogram-detail.png)
- [All 15 trials, selection and hashes](tracking-evidence/report.json), [independent verification](tracking-evidence/verification.json)

## Implementation and selection

The source remains the original unprocessed main song [133.6,223.6), with
all 1,984,500 prepared mono 22050-Hz PCM16 samples. The fitting gain
3.535606377250534, playback gain 3.031479042166069, pinned ymfm-py 0.2.0,
20-Hz AC coupling and 8-kHz fractional resampling filter remain fixed.
Prepared-source SHA256 is
`378c0bdfa5119b38d954f1871c88b5cb4b15c93054fe09d3e828e42e5c34345c`.
All earlier auditions and producers are preserved.

[The temporal model](../../coherent_ym3812.py) combines short 512-sample and
confirming 2048-sample source features, five-field confirmation, and a
second-order Viterbi path with pitch, level and acceleration costs. It offers
legal inactive states, confidence-dependent penalties, joint nonnegative
level fitting and three-field envelopes for weak components. Strong source
attacks retain their immediate response. The first six global trials and two
stronger gate trials fail the saved full-track spectral guard: stronger
continuity can hold an incorrect partial. Inactive voices alone have little
effect on this input.

[Measured harmonic groups](../../grouped_ym3812.py) allow a sine-carrier 1:1 FM
alternative only at source-supported fundamentals at or below 1500 Hz.
Carrier and modulator TL both use real smooth register writes. Of the two
initial group trials, `group01` improves the objective to 9.254882, but its
1044 A/B/A returns fail the required 20% reduction from 1050.

[Localized tracking](tracking_local.py) confines neighboring-pitch substitutions
and inactive choices to baseline exposed-line events or weak, poorly supported
A/B/A events. Current source-supported pitches and long-window refinements
remain available elsewhere. `local04` and `local08` pass the original guards;
`local02` has lower scalar error but fails the A/B/A guard. These stronger FM
variants add low-frequency energy that the objective's 50-Hz floor does not
measure, so selection adds a stricter guard: below-50-Hz power fraction must
not exceed the source fraction plus 0.0002. Source power is 0.044466%; the
limit is 0.064466%. This rejects all stronger local variants.

[Two softer modulation trials](tracking_soft.py) use modulator TL 48 and 52
instead of 40. `soft48` still exceeds the extra low-frequency limit; `soft52`
passes it and every original guard. The final choice retains the original
50-Hz target grid and nine available voices, with mean active voices 8.9973.
Patch IDs 7 and 21 in its saved controls require the recorded modulator TL 52
when re-exporting. The VGM/VGZ commands themselves contain the actual settings.

## Complete-track measurements

| Measure | Original mild-FM baseline | Selected `soft52` |
| --- | ---: | ---: |
| Combined log/level objective, dB (lower better) | 9.444631 | 9.358669 |
| 20-ms level MAE, dB | 1.379574 | 1.431317 |
| Dominant magnitude cosine, 512 | 0.950017 | 0.950792 |
| Dominant magnitude cosine, 2048 | 0.854519 | 0.857057 |
| Dominant magnitude cosine, 8192 | 0.798115 | 0.801599 |
| Rapid 40-ms A/B/A returns | 1050 | 798 |
| Audible transitions of at least 3 semitones | 14,185 | 13,446 |
| Exposed synthetic line events | 1155 | 1141 |
| Below-50-Hz power fraction | 0.024779% | 0.059148% |
| Register writes | 242,868 | 323,569 |
| VGM bytes | 992,252 | 1,309,602 |
| VGZ bytes | 369,327 | 483,310 |

A/B/A returns decrease exactly 24%; exposed-line events decrease only 1.21%.
All three dominant magnitude cosines improve, while level MAE worsens by
0.051744 dB within the saved 0.20-dB allowance. Some root-magnitude cosine
scales also worsen; this is not uniform superiority across every metric.
Peak output is 0.907273 with zero native or output clipping.

The exposed-line heuristic counts field/voice events with source local
prominence below 8 dB, output prominence above 14 dB, TL at most 40 and
frequency 300..8000 Hz. It is a diagnostic proxy, not an audible beep count.
The selected spectrogram still lacks diffuse upper-frequency source detail
and retains some isolated lines. Direct auditory perception is unavailable
in this agent session; the saved auditions support the user's listening test.

All four matched 3-second excerpt objectives improve. Each 11-second file
contains source 0..3 s, silence, old rendition 4..7 s, silence, selected 8..11 s:

- [12.50..15.50 s](tracking-evidence/span-1-source-old-new.wav)
- [22.82..25.82 s](tracking-evidence/span-2-source-old-new.wav)
- [63.98..66.98 s](tracking-evidence/span-3-source-old-new.wav)
- [78.06..81.06 s](tracking-evidence/span-4-source-old-new.wav)

## Verification and reproduction

All 14 existing and focused chip/trajectory/group tests pass. The independent
[verifier](verify_tracking.py) re-exports and audits all 15 full streams,
67,500 fields in total: every nine-channel target and real write interval.
Each replay produces all 4,474,431 native and 3,969,000 output samples;
commands, decompressed VGZ and saved PCM match exactly, with no clipping.
It also confirms the original exporter remains byte-exact for all 4500
baseline fields, authenticates source/native-core/producer/artifact hashes,
and verifies every segment of the full comparison and four excerpt files.

With NumPy/Pillow and a local pinned `ymfm-py==0.2.0` dependency, from the
worktree root, use fresh trial directories:

```powershell
$env:PYTHONPATH='.tmp/dependencies/ymfm;ym3812'
$env:OPENBLAS_NUM_THREADS='1'
python ym3812/analysis/ym3812_sea_foam/tracking_trials.py --output .tmp/new-phase1
python ym3812/analysis/ym3812_sea_foam/tracking_more.py --output .tmp/new-gates
python ym3812/analysis/ym3812_sea_foam/tracking_more.py --groups --output .tmp/new-groups
python ym3812/analysis/ym3812_sea_foam/tracking_local.py --output .tmp/new-local
python ym3812/analysis/ym3812_sea_foam/tracking_soft.py --mod-tl 48 --output .tmp/new-soft48
python ym3812/analysis/ym3812_sea_foam/tracking_soft.py --mod-tl 52 --output .tmp/new-soft52
python -m unittest test_experimental_ym3812 test_coherent_ym3812 test_grouped_ym3812 -v 2> .tmp/new-tests.log
python ym3812/analysis/ym3812_sea_foam/verify_tracking.py --tests .tmp/new-tests.log
```

The verifier checks the immutable archived evidence, independently of a new
fit. [The archive/selection producer](finish_tracking.py) records all attempts
and constructs the listening files; it refuses to overwrite completed evidence.
Hydrate evidence WAV/PNG files through Git LFS before replay.

The bounded implementation is complete. Higher 100/200-Hz target rates remain
an optional later listening experiment. Native Spectrum players and release
disks are unchanged; there is no new Z80 hot-path timing delta or physical
YM3812 delivery qualification.
