# Source-independent audio SNR research

2026-10-14. Requested in a separate worktree, then explicitly clarified:
improve the generic algorithm for arbitrary sources, not a particular song.
Branch `codex/audio-snr-research`, worktree `.worktree/audio-snr-research`,
starts at main `13819086`. The main disk remains unchanged.

## Completed diagnostic stage

The current TRD hash is `226388fb795ac70cfd940545a9eb73e3e81b6c7e96533dc6deb0c215257338ea`.
Authentication confirms only twelve cover bytes differ from the fully executed
`14504d22...` seamless control. Whole-source clocks/PCM/IMA are authenticated
against that archive. The two complete Pentagon clocks match exactly.

The complete90-second song's fixed-clock SNR reproduces-3.085228288 dB.
Ideal source values on its actual clock give-3.000930738 dB; ideal uniform-clock
IMA4 gives22.147802123 dB. Timing dominates the unfitted total score.
The legacy PDM-only diagnostic is16.108757076 dB. Song-measured weights improve
that diagnostic in a frozen-clock prediction, but are explicitly rejected as
universal presets. Those pilot results remain in `evidence/study`.

The generic controls use instruction-derived449-T Pentagon timing, including
the26-T dispatch delay at slot7 (20 becomes46 T), page extra14 T and bank
extra243 T. The entire source-independent timeline reproduces every timestamp
of the saved complete Pentagon song run. No audio-dependent timing calibration
is used for the generic presets. They are frozen before inspecting holdouts.

All nine inputs are evaluated in full: development silence, quiet440-Hz tone,
loud3000-Hz tone and steps; holdout quiet997-Hz tone, multitone, O. Henry speech,
unrelated Entertainer music and the complete sea-foam song. Source preparation,
level and bandwidth remain unchanged. Every input uses the same PCM-error
IMA beam32/block64; no waveform-optimized stream is silently substituted.

| Source | Legacy total diagnostic | Duration midpoint | Duration zero /half recent |
|---|---:|---:|---:|
| Quiet440 | -7.36 dB |8.39 dB |3.95 dB |
| Loud3000 |20.998 dB |18.883 dB |18.866 dB |
| Steps | -0.360 dB | -0.262 dB | -0.227 dB |
| Quiet997 | -13.55 dB |2.90 dB | -2.98 dB |
| Multitone |13.47 dB |19.26 dB |19.43 dB |
| Speech |10.84 dB |20.36 dB |19.83 dB |
| Entertainer |7.35 dB |18.23 dB |17.43 dB |
| Sea foam |15.18 dB |20.36 dB |20.44 dB |

These are **host shared-clock total-error diagnostics**, not fixed8-kHz release
scores or new Spectrum execution. Silence has no SNR: legacy absolute filtered
noise RMS0.052698 becomes0.003691 with duration midpoint or0.015514 with the
zero-origin variants. No fitted delay/gain/clock or narrowed filter is used.
All measurements retain the established f64 70-Hz/two4500-Hz filter,768-kHz
integration and fixed100-ms edge exclusions. Stage errors are not additive.

The duration-aware midpoint control improves PDM-only SNR on speech10.97 to
21.97 dB and Entertainer7.38 to18.78 dB. However, codec and PDM errors can
partially cancel: reducing PDM error alone reduces total SNR on loud3000.
Forty-five complete comparisons identify five regressions. A universal update
cannot be justified by the best song or average PDM score. Generic joint
IMA/PDM waveform optimization and a measured original fallback are indicated.
The finite corpus is evidence, not proof of gain for every possible waveform.

## Memory feasibility

Dictionary closure covers every one of64 input bins and every reachable state,
not only patterns observed in the current audio. The legacy dictionary uses
18 states,128 FIRST/86 SECOND patterns and14144 resident bytes before its
worker at14336. Zero-origin alone needs19 states, overlapping protected RAM.
Instruction-duration controls retain18 states but exceed the current worker
start: midpoint15424 bytes, zero15168, zero/half recent14656. Blind table
replacement is therefore rejected. The half-recent case may fit after moving
the loading-only worker within the same16-KiB code bank; this needs an explicit
build and complete own-clock execution before any measured improvement claim.

## Evidence and reproduction

[Generic full report](evidence/general/report.json),
[all comparisons](evidence/general/comparison.csv),
[decision/regressions](evidence/general/decision.json),
[whole-song error budget](evidence/study/report.json).
WAV pairs use the same fixed0.5 export gain; the measurement itself is unscaled.
Five tests validate numerical chunk integration against the existing full
renderer, silence/total-error semantics, exact complete Fuse-clock reproduction
and universal state/dictionary bounds. All current Z80 instructions remain
unchanged:423/449 T ordinary,14 T page,243/267 T bank extras, delta0.

With NumPy, FFmpeg, z80 and pyz80 available:

```powershell
$env:PYTHONPATH='audiobook-beeper;toolkit;audiobook-beeper/experiments/song-snr'
python audiobook-beeper/experiments/song-snr/study.py --repository C:/Work/ZX-video `
  --output fresh-pilot --scratch .tmp/snr-pilot
python audiobook-beeper/experiments/song-snr/general.py --repository C:/Work/ZX-video `
  --output fresh-general --scratch .tmp/snr-general
python audiobook-beeper/experiments/song-snr/summarize.py fresh-general
python -m unittest discover -s audiobook-beeper/experiments/song-snr -p test_study.py
```

The existing complete native/Fuse proofs qualify the control only. These host
predictions do not qualify a new TRD, a20-dB release, every clone or physical
hardware. Main promotion remains outside this research milestone.
