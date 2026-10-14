# Source-independent audio SNR research

2026-10-14. Requested in a separate worktree, then explicitly clarified:
improve the generic algorithm for arbitrary sources, not a particular song.
Branch `codex/audio-snr-research`, worktree `.worktree/audio-snr-research`,
starts at main `13819086`. The main disk remains unchanged.

## Active +5-dB goal: original-clock controls

The user now requests at least5 dB on the entire song, checks against speed
flutter, AM and added background, automatic program conversion, a C or Go
implementation of the slow encoder and retention of Python as its reference.
The following completed host experiment advances that goal; it does not
accept a release or demonstrate the forthcoming C implementation.

`clock_control.py` freezes one algorithm for all nine sources: instruction-
derived Pentagon timing, Lanczos16 prior, PCM beam32/64 or joint IMA/PDM
beam32 with128-sample horizon,64-sample commit and0.1 regularization. The
desired waveform remains the original uniform8-kHz PCM, not the resampled
prior. Only analytic search queries are rounded (maximum1.763 ns); final
rendering uses exact clocks, the unchanged filter and fixed100-ms edges.
There is no fitted gain, delay or clock. Whole-song results below are host
predictions until qualified by separate complete own-clock execution.

| Complete source | Clock compensation | Joint IMA/PDM |
|---|---:|---:|
| Quiet440 |3.872 dB |5.185 dB |
| Loud3000 |7.456 dB |8.155 dB |
| Steps |9.959 dB |2.617 dB |
| Quiet997 |-3.051 dB |-2.371 dB |
| Multitone |15.612 dB |17.327 dB |
| Speech |19.380 dB |21.692 dB |
| Entertainer |17.043 dB |19.445 dB |
| Whole sea-foam song |18.825 dB |20.250 dB |

The song baseline is-3.085228288 dB: joint gain23.335544175 dB exceeds the
requested5 dB and reaches the20-dB scalar gate, but artifact acceptance is
still unproven. Silence has no SNR: baseline absolute noise RMS0.0526984
becomes0.0155139/0.0154867. Its dominant line changes from about2661 to3991
Hz; the lower total floor alone cannot prove absence of added background.
The physical clock is still7981.5726 Hz, with the same sparse page/bank
holds. Corrected fundamental timing is distinct from a uniform physical
sample clock, whose schedule has not changed.

`artifact_diagnostics.py` independently measures original-clock error,
absolute silence/noise spectra, average drift, source-correlated AM/delay,
unfitted hum lines and every physical interval. Eleven calibration tests
include injected AM/FM/hum, constant drift, coverage and strict JSON.
Fits are diagnostic only; short records with fewer than three cycles and
poorly correlated old streams are marked inconclusive. Joint versus simple
compensation has one SNR/RMS regression (steps),28 numerical AM increases,
24 delay increases and21 error-line increases. These disclose numerical
changes, not an invented audibility threshold. Legacy drift makes90
modulation comparisons per candidate inconclusive.

The [independent audit](evidence/encoder-audit/README.md) rules out a wrapper
or filter bug and retains all eight wider-beam/regularization controls.
An ideal compensated DAC reaches only8.193 dB on loud3000: over99.996%
of its error lies above4 kHz in shifted ZOH images. Narrowing the filter
would conceal the loss. More beam width alone is insufficient. A universal
fallback and better PDM/clock handling remain necessary.
The quieter midpoint table can potentially fit by relocating only311
probe bytes and256 bounce bytes into694 bytes of startup padding, then
placing the worker atBC40; this is arithmetic feasibility, not execution.

Do not promote either candidate unconditionally. All Z80 hot instructions
remain unchanged:423/449-T ordinary,14-T page and243/267-T bank extras,
delta0. Preserve Python as an executable reference while the full C encoder
and automatic conversion entry point are developed and checked.

[Host controls](evidence/clock-joint/report.json),
[complete artifact diagnostics](evidence/clock-diagnostics/report.json).

```powershell
python audiobook-beeper/experiments/song-snr/clock_control.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --output audiobook-beeper/experiments/song-snr/evidence/clock-compensation `
  --scratch .tmp/clock-compensation --method compensation
python audiobook-beeper/experiments/song-snr/clock_control.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --output audiobook-beeper/experiments/song-snr/evidence/clock-joint `
  --scratch .tmp/clock-joint --method joint
python audiobook-beeper/experiments/song-snr/artifact_diagnostics.py `
  --corpus-evidence audiobook-beeper/experiments/song-snr/evidence `
  --cache .tmp --scratch .tmp/artifact-diagnostics `
  --output audiobook-beeper/experiments/song-snr/evidence/clock-diagnostics
```

## Complete original-clock execution controls

All nine simple-compensation controls now complete36 native runs on all four
RAM profiles and10 independently cold Fuse runs (all nine on512K, song also
on1024K). Joint speech and the whole song add eight complete native runs and
three cold Fuse runs. Every new Pentagon interval matches the source-independent
schedule. Both full-song candidates on512/1024 match the authenticated old
song trace byte for byte for all11,526,111 relative source OUT timestamps.
Maximum introduced physical timing change is0 T. No live disk reads, RAM
copies or refills occur on512/1024; maximum hold remains277 T (77.288 us).
Native128/Scorpion still exercise three/one song refills, respectively.

Own complete clocks reproduce the host scores exactly: song compensation
18.825070524 dB and joint20.250315887 dB (+23.335544175 versus actual legacy).
Joint speech is21.692333986 dB. These are strict unfitted original-clock
scores, not just PDM diagnostics. The song clears the scalar20-dB/+5-dB gates;
the separately recorded background/modulation counterexamples still prevent
an unconditional release.128/Scorpion functional checks do not establish
their waveform quality from a stream compensated for Pentagon timing.

Research song TRDs: compensation SHA`787e3d4e...`, joint SHA`ccab8724...`.
All images retain independent boot, complete source, title, progress display,
one-disk IMA storage and all-RAM loading. Current main stays`226388fb...`.
No physical-hardware or subjective cure is claimed.

[Actual compensation scores](evidence/clock-compensation/actual-quality.json),
[actual joint scores](evidence/clock-joint/actual-quality.json),
[joint full execution](evidence/clock-joint/sea_foam/verification/execution.json),
[exact old/new1024 clock](evidence/clock-joint/sea_foam/verification/pentagon1024/timing-comparison.json).

```powershell
python audiobook-beeper/experiments/song-snr/execute_clock.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --jobs 3
python audiobook-beeper/experiments/song-snr/execute_clock.py `
  audiobook-beeper/experiments/song-snr/evidence --stage clock-joint `
  --source speech --source sea_foam `
  --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --jobs 2
python audiobook-beeper/experiments/song-snr/measure_clock.py `
  audiobook-beeper/experiments/song-snr/evidence --scratch .tmp/clock-actual
python audiobook-beeper/experiments/song-snr/measure_clock.py `
  audiobook-beeper/experiments/song-snr/evidence --stage clock-joint `
  --source speech --source sea_foam --scratch .tmp/clock-joint-actual
```

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

## Complete executable feasibility prototype

The same source-independent preset is compiled for speech, Entertainer,
sea foam, loud3000, silence and quiet997. No model parameter is chosen per
source. It is the duration-aware zero-origin/half-recent control whose wider
dictionary can fit after moving the loading-only worker fromB800 toBA00.
Resident tables end atB940, worker/bounce/descriptors atBF86 for the song.
The fixed16-KiB bank,91,392-byte ordinary audio budget, extended capacities,
cover, source duration and packed IMA bytes remain unchanged.

Legacy `layout` retains its14336-byte budget; the stream builder explicitly
grants14848 bytes. Wider unsupported dictionaries still fail. Full one-TRD
capacity2392 audio sectors is cold-loaded and checked on1024K with the new
worker. A fresh default build matches the current main TRD byte for byte.
The generated assembly uses the configured worker origin and preserves its
routine/memory comments. No live instruction sequence changes: ordinary
423/449 T, page extra14 T, bank extra243/267 T, all deterministic deltas0.

Twenty-four complete native runs verify every bit, predictor/index, exact
continuous hold, code/table guards and refills across all four RAM models.
Seven complete cold Fuse prototype runs cover all six sources on Pentagon512
and the full song on1024. Two additional cold Fuse legacy speech/music runs
provide new actual before controls; the authenticated earlier song trace is
the third actual before. All own timestamps match the source-independent
instruction schedule, with no dropped source pulse. The complete song stays
seamless on512/1024. Physical hardware and fresh128/Scorpion Fuse quality are
not qualified by this prototype.

| Actual Pentagon before/after | Legacy PDM diagnostic | Prototype PDM diagnostic | Gain |
|---|---:|---:|---:|
| Speech |10.9683 dB |21.1843 dB |10.2160 dB |
| Entertainer |7.3795 dB |17.8849 dB |10.5054 dB |
| Sea foam |16.1088 dB |25.3202 dB |9.2114 dB |

These are the PDM reconstruction error relative to decoded IMA on each actual
sample clock. Full shared-clock total diagnostics become19.8349/17.4318/
20.4408 dB. Strict unfitted fixed8-kHz scores remain-3.2578/-3.2741/-2.9873 dB:
the source-clock problem remains. The20-dB release gate is not relaxed.
Actual prototype silence noise RMS is0.015514; quiet997 remains-2.9808 dB
total on the shared clock. Loud3000 is18.8663 dB there, confirming the
earlier counterexample against the legacy host diagnostic20.9978 dB.

[Own-clock scores](evidence/prototype/quality.json),
[complete main prototype runs](evidence/prototype/report.json),
[additional complete stress runs](evidence/prototype/subset-report.json),
[legacy byte-identical rebuild](evidence/legacy-rebuild.json).
Before/after WAVs retain the same fixed0.5 export gain. See speech and
Entertainer under `evidence/legacy-controls` and `evidence/prototype`.
All TRDs are research previews, with one disk each and the same cover.

The decision remains to reject an unconditional table replacement. A generic
encoder can adapt the encoded stream to each input using the same fixed
algorithm and retain the measured original when an attempted improvement
regresses. That selection/joint optimization is a next mechanism, not an
implemented or universally proven default in this study.

```powershell
python audiobook-beeper/experiments/song-snr/prototype.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --jobs 3
python audiobook-beeper/experiments/song-snr/measure_prototype.py `
  audiobook-beeper/experiments/song-snr/evidence --scratch .tmp/snr-prototype
python -m unittest discover -s audiobook-beeper/experiments/song-snr -p test_worker_budget.py
```

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
