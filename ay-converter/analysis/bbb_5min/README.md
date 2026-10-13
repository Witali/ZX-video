# First five minutes of Big Buck Bunny as AY audio

Requested 2026-10-13, baseline `e7450386`. Source interval is exactly
0..300 seconds, with one second of following analysis context and no movie
edit. The shared `auto` engine analyses the full timeline once, preserving
component tracking across the two resident disk boundaries. All 15000 states
last 20 ms and specify three voices plus one shared noise generator. The source
audio is 48-kHz AAC 5.1 starting at zero; FFmpeg performs its mono downmix.
Before any harmonic/noise analysis, normalize the selected 0..300-second PCM
peak to -1 dBFS with one scalar, also applied to the following context. The
mono source peak is 1.520940 (+3.64224 dBFS), so gain is 0.58598684
(-4.64224 dB). The normalized peak is 0.89125094 with zero clipped samples.
Dynamics are preserved. This is sample-peak normalization at 22050 Hz, not
LUFS, a limiter or oversampled true-peak processing. `--normalize-peak-db`
controls the target; default is -1.

The resident limit is 8934 states, so the output uses two independently
bootable one-shot disks, each 7500 states /150 seconds. All disk data loads
before playback. Swap disks manually; the continuous five-minute WAV has no
swap gap and keeps chip phase across 150 seconds. Each cold-booted disk starts
its own chip phase, while its complete register stream remains exact.

`build.py` retains the canonical component analyser and hardware renderer.
Following the user's speed request it defaults to the task-local analytic
20-candidate mixer instead of the 374-candidate reference. Ordinary public
converter defaults remain unchanged by this audition. `--full-mixer` selects
the reference for a separately authorized comparison.

Broadband spectral power is matched to the tracker's 31 sinc colour templates.
The already completed chip-noise colour fit is retained on existing carriers.
For the shared DAC level, solve the tracker's quadratic physically constrained
balance: noise-only M=N; mixed M=(4*T+sqrt(2)*N)/3. Quantize to the chip DAC,
then check levels -1/0/+1 and period scales 1/2, 1, 2 in each noisy mode. Together
with seed and pure tones this gives 20 full chip renders. A 20-state Viterbi
path keeps the original 20-ms grid, followed by a complete proposal render.
Independent unpooled comparison against seed and pure tones retains the best
whole stream. This can miss the full-search optimum.

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

Independent candidate waveforms are distributed over six Node processes, and
independent objective columns are evaluated in a joined six-thread pool. The
canonical cost body, FFT batches and reduction order remain intact; each job
writes a separate column. A canonical loop-structure change fails explicitly.
Bounded index gathering produces the identical zero-padded FFT windows without
copying the whole five-minute signal for each 128-state batch; the source/model
gain multiplication is hoisted once per waveform with identical sample values.
Its fixture compares all 465 noise/mixer candidate waveforms against the
sequential tools at every searched period, mode and volume delta. All are
byte-identical, including varying routing and silent carriers. A second
fixture compares every noise/mixer cost value, final register and metadata
field against the sequential objective; both cost matrices match byte-for-byte,
including the bounded window gather and hoisted gain multiplication.

The initial render-only and column-pool attempts were interrupted for excessive
full-PCM copies; their logs remain evidence of incomplete attempts. A bounded
full-search attempt was interrupted when the user requested analytic proposals.
The first 20-candidate, unnormalized build passed both native disks and the
first cold Fuse disk. The second Fuse run was interrupted at the user's input
normalization request; that build is superseded, not a qualified final set.
Its report/log remain evidence. A complete noise stage is reusable only when
source/PCM hashes, every reapplied change and the baseline gain match exactly.
Normalization changes the PCM hash, so the final run calculates both noise and
mixer stages afresh. No unnormalized cache/snapshot is used in the final set.

The full conversion and both disks must finish their checks before this
audition is considered complete. This is an audio audition, without a rebuilt
movie or a physical-hardware listening claim. Spectral proxies do not establish
perceptual fidelity or intelligibility.

## Reproduction

```text
python ay-converter/analysis/bbb_5min/build.py --source SOURCE.mov --output OUTPUT --node NODE --ffmpeg FFMPEG --workers 6
python ay-converter/verify_preview.py OUTPUT/part01 --fuse FUSE --record
python ay-converter/verify_preview.py OUTPUT/part02 --fuse FUSE --record
python ay-converter/analysis/bbb_5min/finish.py OUTPUT --node NODE
```

Python requires the standalone requirements, including `z80` and `pyz80` for
the assembled native checks. Use Spectrum 128 plus Beta Disk/TR-DOS in Fuse.
Player instructions, RAM layout and timing paths are unchanged: ordinary
974 ->974 T, delta 0; near boundary 992 T, bank change 1091 T, exact-boundary
EOF 1007 T, loop restart 1079 T. These instruction counts exclude ULA/HALT,
ROM/disk latency and interrupt entry. Actual playback must be checked separately.
