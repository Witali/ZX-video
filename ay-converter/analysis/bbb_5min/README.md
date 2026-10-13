# First five minutes of Big Buck Bunny as AY audio

Requested 2026-10-13, initial baseline `e7450386`. The selected interval is
exactly 0..300 seconds (15000 states at 50 Hz), without a movie edit. One second
of following PCM context supports continuous analysis. The original input is
48-kHz AAC 5.1; its SHA256 and exact decoding command are in the saved report.

The selected result uses the actual AY-3-8910 model, 16 effective envelope
levels, source-evidenced noise and smooth compressed PCM dynamics. The common
engine also supports YM2149, with 32 envelope codes; both public entry points
share analysis and preprocessing. See [the chip audit and exact instruction
costs](../../CHIP_MODEL.md).

The continuous [AY listening WAV](evidence/ay-preview.wav) contains all five
minutes. [The processed reference](evidence/original-preview.wav) is the mono,
compressed PCM used by feedback. [The preceding uncompressed AY audition](evidence/baseline/ay-before-compression.wav)
is retained for comparison. Three independently bootable one-shot resident
disks contain 5000 states/100 seconds each. All payload reads finish before
playback. Manual swaps pause sound; the continuous WAV retains chip phase.
Each cold disk starts a separate phase, with a legal initial envelope action.

## Preprocessing and measured level recovery

5.1 reduction uses FL/FR 0.23 each, centre 0.40, surrounds 0.07 each and no
LFE. This prioritizes central content while retaining surrounding effects.
It is a practical narrow mono arrangement, not an objectively optimal matrix
for every recording. Other layouts use FFmpeg's standard mono reduction.

Before analysis, calibrate the selected sample peak to -1 dBFS. Default
`compact` dynamics use a 2.5:1 ratio around -24 dBFS, bounded upward +9 dB and
downward -18 dB, 10-ms attack and 150-ms release. Offline smoothing and sample
interpolation avoid gain steps without moving timestamps. Global makeup
returns the selected sample peak to -1 dBFS. Silence remains silence.
`--dynamics original` preserves dynamics; movie equivalent `--ay-dynamics`.
This is not LUFS or oversampled true-peak normalization.

On this source the new mono raw peak is 0.55664551. Initial gain is
1.60111043; compression makeup is +5.89839 dB. Active 20-ms RMS p90-minus-p10
spread changes 24.95316 ->20.94300 dB, with reference RMS 0.07148980 and zero
clipped samples. The active set uses -55 dBFS independently for each signal;
this is a level-spread proxy, not an EBU loudness range.

Complete AY feedback against that processed PCM reduces its objective
10.01839 ->7.64596 dB and level MAE 8.26147 ->1.37248 dB. These values belong
to this new reference and cannot be compared as a quality percentage with the
older reference's objective. Fixed output calibration stays 1.02428883 for
all candidates; only real registers change after source preprocessing.

The initial compressed fit retained four strong low-level fields, including
a 40-ms hole. The final common algorithm proposes a nearby fixed-level tonal
state only for a fully muted, audible source field within 100 ms of a tonal
neighbour. It preserves hardware actions and source silence. Both the recovery
alone and its combination with period/level proposals receive complete chip
rendering; accepted changes lower the combined objective. The first recovery
attempt was superseded when a better noise-period proposal discarded its
recovery. Combined proposals resolve that selection problem.

[Final level audit](evidence/level-drops.json): on 13234 fields whose processed
reference exceeds -45 dBFS, zero fields are more than 15 dB below reference,
zero are muted, and active level MAE is 0.86743 dB. PCM16 listening peak is
0.927948, with no clipping. These thresholds define this bounded check; they
do not assert perfect PCM reproduction or subjective listening acceptance.

## Search, physical controls and provenance

The canonical analyser tracks persistent tonal components. The analytic
mixer estimates broadband colour using 31 sinc templates, retains completed
noise-colour proposals, solves noise-only M=N or mixed M=(4*T+sqrt(2)*N)/3,
quantizes to the selected chip DAC, then checks period scales 1/2, 1, 2 and
level offsets -1/0/+1. Seed and pure tones make 20 candidates instead of 374.
A Viterbi path limits chatter, followed by complete unpooled verification.
This is a bounded proposal search, not a global optimum.

These historical shortlist cases used the preceding YM renderer before the
physical AY audit; final AY feedback is measured separately.

[Five complete validation excerpts](shortlist-validation/report.json):

| Excerpt | Seed log MAE, dB | Analytic 20 | Full 374 |
| --- | ---: | ---: | ---: |
| Entertainer | 8.75613 | 8.48796 | 8.35282 |
| O. Henry | 8.74940 | 8.09358 | 7.78872 |
| Movie 60 s | 7.42225 | 7.24126 | 7.07508 |
| Movie 170 s | 6.34678 | 5.88827 | 5.75762 |
| Movie 430 s | 6.92900 | 6.70362 | 6.62787 |

All five improve the seed metric and retain every tone period. The full search
wins by 0.07575..0.30486 dB. Shortlist stages take 10.88..17.70 seconds per
8-second excerpt on this host, while the earlier full musical search was
144.74 seconds. Those were not a controlled same-load speed benchmark: the
validation ran alongside the incomplete full-movie search. No perceptual
quality equivalence or full-search optimality is claimed.

Independent renders run in joined processes/threads. The original scheduling
fixture matches all 465 noise/mixer candidate waveforms and all cost values
byte-for-byte. Exact-context cache keys include PCM, controls, producer sources
and selected chip. This is exact stage reuse, not a lossy phrase dictionary;
the separately tested phrase dictionary was rejected for increasing size.

Final feedback compares continuous chip output with three unpooled STFT sizes
(512/2048/8192), source-only Bark masking and absolute 20-ms RMS differences.
The relative masking model approximates simultaneous and short forward
masking; it has no calibrated SPL or PEAQ claim. Ordinary errors remain in
reports. [Primary psychoacoustic tutorial](https://publica-rest.fraunhofer.de/server/api/core/bitstreams/02820baa-82ed-4a16-80c3-c4c974362413/content).

Noise needs both source broadband evidence and a measured benefit. AY
retargeting reduces audible noisy fields from 10203 to 3831; final level
changes leave 3817/15000. Weak noise omission deliberately increases some
ordinary spectral errors. R6 may remain nonzero during muted intervals;
routing and channel volume determine whether noise is audible.

One shared hardware envelope supplies accepted periodic shapes and disjoint
slow ramps. R13 starts a shape only at a block boundary; 255 stores no action.
It never resets each field. The final stream has 145 shape actions. AY12 packs
12 bytes/state; bus records are 14 bytes with optional R13. The player sends
13 ordinary writes plus a legal shape action, never software sentinel 255.

Historical normalized and YM-fitted controls are reused only as register
seeds. Actual AY feedback, sparse-noise policy and envelope selection were
recomputed with the AY model. The final compressed reference then receives
fresh complete waveform feedback from those legal controls. Existing envelope
blocks and component/colour proposals remain seeds, rather than a claimed
fresh exhaustive search against changed PCM. The ordinary public engine runs
all stages against its own processed input. Stage reports preserve this scope.

Interrupted full-copy, column-pool and bounded 374-search attempts are saved,
as are the superseded unnormalized audition, normalized fit and YM envelope
proofs. The first envelope Fuse trace falsely counted skipped R13 values;
its original trace is retained. Conditioning that trace point on E!=255 fixes
the measurement; corrected complete runs follow. No chip workaround is used.

## Playback qualification and reproduction

41 standalone tests, 70 toolkit tests, and six final recovery regressions pass.
They include both chip models, silence, PCM timing, packed actions, shared
movie/audio identity, all banks, EOF/loop boundaries and native AYH2 decoding.
A complete five-frame 10-fps public CB41 fixture selects hardware envelopes
and passes cold boot, every screen, every AY field and nominal deadlines in
Fuse. Rebuilding with final producers yields an identical disk, permitting
reuse of those actual binary proofs. The complete movie release is unchanged.

The selected audio set passes all three complete cold Fuse runs: 15000 fields,
195145 exact bus writes, no missing/duplicate fields and no runtime disk reads.
Each disk loads 274 startup sectors; first OUT phase is 150..153 T, and
consecutive OUT intervals are 70905..70911 T on the original 70908-T grid.
The completed archive is qualified for this sound audition. [Report](evidence/report.json) records exact native
and Fuse counts, every field, startup/runtime reads and normal-speed captures.
No physical Spectrum or seamless drive-swap listening claim is made.

Fresh common-engine conversion:

```text
python ay-converter/analysis/bbb_5min/build.py --source SOURCE.mov --output OUTPUT --node NODE --ffmpeg FFMPEG --chip AY-3-8910 --dynamics compact
```

Reproduce the selected staged seed refinement using authenticated inputs:

```text
python ay-converter/analysis/bbb_5min/rebuild_ay.py NORMALIZED --output AY_FIT --node NODE
python ay-converter/analysis/bbb_5min/final_feedback.py NORMALIZED AY_FIT --output AY_POLISHED --node NODE
python ay-converter/analysis/bbb_5min/package_final.py NORMALIZED AY_POLISHED --output AY_BASELINE --node NODE
python ay-converter/analysis/bbb_5min/compact_feedback.py AY_BASELINE --output COMPACT --node NODE
python ay-converter/analysis/bbb_5min/compact_feedback.py AY_BASELINE --seed-fit COMPACT --output RECOVERED --node NODE
python ay-converter/analysis/bbb_5min/package_final.py AY_BASELINE RECOVERED --output FINAL --node NODE
python ay-converter/analysis/bbb_5min/check_levels.py FINAL
python ay-converter/verify_preview.py FINAL/part01 --fuse FUSE --record
python ay-converter/verify_preview.py FINAL/part02 --fuse FUSE --record
python ay-converter/verify_preview.py FINAL/part03 --fuse FUSE --record
python ay-converter/analysis/bbb_5min/finish.py FINAL --node NODE
```

The selected run predates the combined-recovery proposal in its initial
three-round compressed stage. Reproduction with newer producers may accept
additional improvements; archived PCM/register/disk hashes authenticate the
published selection. Source availability, z80/pyz80, Node, FFmpeg and Fuse are
required. The public maximum resident auto excerpt is 140.4 seconds, so this
long audition splits only after continuous fitting. Movie AYH2 adds +60 T per
skipped field; resident ordinary fields cost 1166/1206 T versus previous974 T
(+192/+232), excluding ULA/HALT/IRQ and disk latency. Full counts are in
[CHIP_MODEL.md](../../CHIP_MODEL.md).

Verify every worktree byte and committed Git/LFS object with
`python ay-converter/analysis/bbb_5min/verify_archive.py --revision HEAD`.
