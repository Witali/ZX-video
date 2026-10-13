# Automatic tone, noise and mixed AY fitting

Completed 2026-10-13 from baseline `3002f6a7`. The user requested automatic
selection of tone, noise or simultaneous tone/noise, closer source matching,
one converter for movies and audio, and reuse of repeated spectral patterns.

## Shared conversion

`ay-converter/engine.py` is the canonical sound engine. The standalone
`convert_audio.py` calls it directly; `toolkit/convert_video.py` invokes
`encode_pcm.py` in an isolated process so older toolkit imports cannot shadow
the current analyser. Both default to `auto`; `music` retains the preceding
tracked/chip-noise fit, and `legacy` retains the original square-aware analyser.
The movie options are `--ay-profile` and `--node`; standalone uses `--profile`.
The original movie noise-step/tuning options remain applicable to `legacy`.

AY9 remains nine bytes, with the existing six-bit mixer extension. Both modern
movie players consume R0..R10 through their existing IRQ/resident streams.
Archival interleaved players reject the marked format instead of silently
playing the wrong noise route. The standalone folder remains self-contained.

## Search and proportions

The persistent tracker keeps the three components on their hardware channels.
The mixer stage searches 374 candidates: the preceding fitted stream, pure
tones, and noise-only/mixed modes at all 31 R6 periods with shared-volume
offsets -3..+2. One carrier is selected by the existing tracker, or the weakest
channel when weaker broadband evidence appears. A mixed candidate requires a
tracked tonal component. The other channels' pitches and levels are preserved.

Every candidate is rendered continuously by the unmodified YM2149 Ayumi model
at 44100 Hz, then low-pass resampled to 22050 Hz. The search compares
512/2048/8192-sample Hann windows over 50..8000 Hz with narrow 50-Hz power
smoothing. A fixed source/model RMS gain and weak mode/period/level transition
penalties avoid per-frame gain fitting and unnecessary chatter. Every state
still lasts exactly 20 ms; there are no sub-tick events.

AY combines binary gates with AND and gives the combined channel one DAC
level. Independent tone/noise gains are unavailable. This is a bounded search
over actual achievable proportions, not a globally optimal arrangement.

The chosen sequence changes the noise-generator history. Render the complete
proposal again and compare **unpooled** multiresolution log-magnitude error
against the seed and pure-tone streams. Export the lowest-error complete
stream. Do not accept candidate estimates alone as proof of improved output.

## Measured excerpts

[Full report](evidence/results.json), [authenticated archive](evidence/manifest.json).
All intervals are eight seconds. Reference and listening previews use one
global RMS match, without local gain, time warping or pitch alignment.

| Recording/source interval | Previous `music` mean log MAE, dB | Automatic, dB |
| --- | ---: | ---: |
| The Entertainer, 0..8 s | 8.75613 | 8.35282 |
| O. Henry recording, 8..16 s | 8.74940 | 7.78872 |
| Movie, 60..68 s | 7.42225 | 7.07508 |
| Movie, 170..178 s | 6.34678 | 5.75762 |
| Movie, 430..438 s | 6.92900 | 6.62787 |

The selected error falls in every case, by 4.35..10.98% of the previous numeric
error. This is not a perceptual fidelity percentage. Some magnitude/chroma
proxies regress: for example, The Entertainer's 2048-sample magnitude cosine
changes 0.84080 ->0.83187. Keep these results and the auditions, rather than
claiming every metric improved or that speech intelligibility is established.

The comparison WAVs contain original at 0..8 s, preceding music fit at
9..17 s and automatic fit at 18..26 s:

- [Music comparison](evidence/entertainer/comparison.wav)
- [O. Henry comparison](evidence/o-henry/comparison.wav)
- [Movie music](evidence/movie-60/comparison.wav)
- [Movie detail](evidence/movie-170/comparison.wav)
- [Movie effects](evidence/movie-430/comparison.wav)

Normal-speed Fuse recordings are saved alongside the three verified audition
disks. No original PCM is mixed into their synthesized output.

## Reuse and verification

Spectral-pattern reuse normalizes the peak, restores each state's original
intensity, and checks the full vector within 1e-7 before reusing its sparse fit.
The cache is bounded to 2048 entries. Synthetic amplitude-scaled repeats pass
the uncached comparison; these real excerpts contain zero matches at that
strict threshold. Broad frequency-bin resemblance alone does not authorize
unchecked substitution.

The persistent mixer cache includes exact PCM context, initial registers,
routing, analysis/renderer source hashes and versions. It stores selected
registers, not live chip phase. The musical search took 144.7363 seconds cold
and 0.03178 seconds on an exact repeat, producing identical registers. These
times exclude preceding analysis/noise-colour fitting. Changes to inputs or
code invalidate the entry.

Twenty-two standalone and 44 toolkit tests pass, including all 64 mixer values,
legacy compatibility, changed-register IRQ timing, unseen noise phase, cache
identity and audio/movie parity. All five complete excerpts pass native Z80
execution through two loops: 4000 ticks and 44000 writes. Music, O. Henry and
effects each pass cold Fuse through two complete loops, with exact registers,
no missing/duplicate fields and normal-speed recordings.

The ordinary standalone field remains **974 T before and after, delta 0**;
bank boundary remains 1091 T and loop restart 1079 T. Movie IRQ work remains
367+83*n T for changed registers, 377 T for an unchanged state, with 24 T at
EOF. New data can change n and compressed size; the report records these
CPU-only estimates separately from total delivery. No Z80 instructions or
RAM allocation changed. ROM, disk latency, ULA and IRQ entry are excluded
from those instruction-table counts.

The ordinary public commands produce identical 25 AY states from one 0.5-s
video. Its complete 10-fps movie test passes cold Fuse: five exact screens,
34560 screen bytes, all 25 AY ticks, zero nominal misses, maximum publication
deviation 1 T and no underrun. This is a bounded integration fixture, not a
full-film release gate. Existing root movie disks are unchanged.

## Reproduction

```text
python ay-converter/analysis/auto_mixer/probe.py --source-root REPOSITORY --output OUTPUT --node NODE --ffmpeg FFMPEG
python ay-converter/analysis/auto_mixer/check_archive.py
python -m unittest discover -s ay-converter -p test_*.py
```

Saved NPZ inputs retain the exact PCM context and export interval. Producer
snapshots authenticate the saved public CLI report; later CLI label/import
cleanup and toolkit pickle/legacy-format guards do not change the measured
registers or Z80 instructions. Physical hardware and complete rebuilt-film
timing/capacity have not been tested for this new audio.
