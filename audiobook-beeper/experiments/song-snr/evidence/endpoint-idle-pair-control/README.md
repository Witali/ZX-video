# Endpoint-consistent source-independent idle-pair control

Date: 2026-10-14. Decision: **reject unconditional promotion**. The complete nine-source host experiment is preserved; no new Fuse run or release promotion is warranted for this rejected candidate.

The valid endpoint pair restores speech, *The Entertainer* and the matched song slightly, but the song remains 0.137209677 dB below the best half-joint control. Steps, multitone and loud3000 regress versus matched. Silence is noisier than both earlier idle variants, and tonal/background and AM/FM acceptance remain unresolved. Exact endpoint labels and nominal area balance are mechanism evidence, not universal quality or absence of audible artifacts.

## Frozen selection, endpoints and table scope

The same `endpoint_idle_pair_words=[0x670D,0x969C]` is used for every source. Source-free selection first enumerated all 65,536 words, filtered the 224-on-T words deriving state 16â†’17 and the 225-on-T words deriving state 17â†’16, and then evaluated all 238Ã—238 = 56,644 endpoint-valid pairs with the unchanged prior analytic filter/variance objective and deterministic symmetry tie. No audio influenced selection, and no other pair was tried on this corpus. The selection report was finalized before any input read: [source-free selection proof](../endpoint-idle-pair-selection/report.json).

The new helper and independent player hooks passed their source-free/short functional proofs before this host run. Final helper SHA256 is `607e3aab7bc15c99c262730c735fa7f0c1ea451d36f25326db499d8ee0ea0c0d`. The independent reference uses its own literal override and Fraction recurrence, not the primary helper. The separate [player proof](../endpoint-idle-pair-player/report.json) records seven tests, exact default image/metadata, malformed-model guards, eight before/after native runs across four profiles and the maximum 2392-sector cold-load bound. These are not complete new candidate audio/Fuse proofs.

Only packet cells `[32,16]` and `[32,17]` change. Every other word and every successor remain identical to the original all 64-bin table. State 16 emits `0x670D` with 224 on-T; state 17 emits `0x969C` with 225 on-T. The original successor cycle 16â†’17â†’16 is also derived correctly from the exact q/recent rule. Over two ordinary packets, 449 of 898 T are on: exactly 50% nominal area.

An independent exact-Fraction certificate is generated before source reads in [frozen-fraction-endpoints.json](frozen-fraction-endpoints.json). It preserves the original endpoint epsilon exactly as `Fraction(1,10**12)` and reports every slot. The recurrence is `weight=16*hold/449; u=1/2+q/weight+recent/2; recent=u-bit; q+=weight*(1/2-bit)`. Endpoint quantization is `qcode=clip(floor(8*q+8.5+epsilon),0,15); recentcode=clip(floor(recent+1+epsilon),0,1); next=2*qcode+recentcode`.

| State/word | q endpoint | Recent endpoint | Derived/stored next |
| --- | --- | --- | --- |
| 16 / 0x670D | 8/449 | 1715169511331/12628951695360 (â‰ˆ0.135812500729) | 17 /17 |
| 17 /0x969C | -8/449 | -1708438613281/4209650565120 (â‰ˆ-0.405838581339) | 16 /16 |

Endpoint consistency replaces the earlier paired control's invalid retained label. It does not force the filtered waveform to zero, remove periodic page/bank excursions, or establish whole-source quality.

## Common encoder, source and measurement

Model: `duration_zero`, `pcm_origin=0`, `extent=1`, `beta=0.5`, `pcm_quantization_bias=512`, `compact_stream_loader=True`, and the one frozen endpoint pair. The standalone C waveform encoder, beam width 32, horizon 128, commit 64, regularization 0.1 and Lanczos-16 compensated prior are unchanged. C search and accepted-prefix replay use the same new table. There is no per-source selection or fitted source clock, gain or delay.

All original uniform 8 kHz sources, filters and guards are retained. Scoring uses the continuous f64 listening filter (70 Hz high-pass and two 4500 Hz low-pass pairs) and fixed 100 ms edge exclusions. The complete 720,000 musical samples of the song remain inside the unchanged 720,384-sample padded source. The existing final 128-sample settling guard was already silent and was not overwritten to discard music. Source/packed identities, coverage assertions and original source hashes are preserved. Float64 reference/output arrays are unscaled; every listening WAV uses the same fixed 0.5 gain.

Unchanged before pipelines were reused as authenticated unscaled arrays rather than regenerated. All reference arrays match exactly, and every cached before error RMS matches its saved full-source score.

## Complete corpus results

The fresh full host run took **100.833500 s**, including preparation, serialization, C search, continuous filtering and artifact diagnostics. This is not a cached-resume benchmark and excludes disk assembly/emulator execution.

Unfitted original-clock SNR in dB:

| Source | Compensation | Half-joint | Matched centered | One-word idle | Earlier zero-mean pair | Endpoint pair |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| quiet440 | 3.871973 | 5.185187 | 7.183904 | 7.183489 | 7.183489 | 7.183904 |
| loud3000 | 7.455600 | 8.155355 | 8.082355 | 8.086511 | 8.092602 | 8.081291 |
| steps | 9.958784 | 2.616812 | 2.456251 | 2.061835 | 1.925453 | 2.395081 |
| quiet997 | -3.051346 | -2.370523 | 0.840043 | 0.840043 | 0.840790 | 0.840043 |
| multitone | 15.611740 | 17.327370 | 17.258909 | 17.294429 | 17.292132 | 17.236763 |
| speech | 19.380055 | 21.692334 | 22.056546 | 21.866089 | 21.810661 | 22.060791 |
| entertainer | 17.043144 | 19.445475 | 19.589737 | 19.228961 | 19.068882 | 19.626525 |
| sea_foam | 18.825071 | 20.250316 | 20.110901 | 20.100940 | 20.105056 | 20.113106 |

Absolute unscaled candidate error/noise RMS and preserved source lengths:

| Source | Samples | RMS |
| --- | ---: | ---: |
| silence | 16896 | 0.006652683887 |
| quiet440 | 16896 | 0.009801474234 |
| loud3000 | 16896 | 0.142518589713 |
| steps | 16896 | 0.170826733774 |
| quiet997 | 16896 | 0.010226589275 |
| multitone | 16896 | 0.038494790938 |
| speech | 186880 | 0.015221141811 |
| entertainer | 186880 | 0.013670827300 |
| sea_foam | 720384 | 0.033658277839 |

Silence has no finite signal/noise SNR. Candidate silence RMS 0.006652683887 is 7.354504 dB below matched, but 9.225338 dB above one-word and 4.829994 dB above the earlier zero-mean pair.

The song is 20.113106210 dB: +0.002205562 versus matched, +0.012166097 versus one-word, +0.008050338 versus earlier pair, -0.137209677 versus half-joint, and +1.288035686 versus compensation. Speech improves 0.004245 dB and *The Entertainer* 0.036788 dB versus matched; steps lose 0.061170 dB, multitone 0.022146 dB and loud3000 0.001064 dB. Quiet440 differs by only -1.82e-9 dB, which is disclosed as a numerical SNR loss rather than an audibility claim.

The original authenticated song is -3.085228 dB on the unchanged original-clock metric; this candidate is +23.198334 dB versus that original. This includes removal of accumulated clock drift and is not an isolated PDM denoising gain. The same-clock controls remain the artifact/codec comparison basis; inapplicable old drift fits are missing evidence, not proof of absence.

## Artifact regressions and silence spectrum

All detailed comparisons are in [report.json](report.json) and each source's five baseline diagnostic files. Counts disclose increases above the existing arithmetic tolerance 1e-10, **not an audibility threshold** or universal acceptance criterion:

| Baseline | SNR losses | RMS increases | Applicable AM increases | Applicable delay increases | Coherent-line increases | Inconclusive modulation comparisons |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| compensation | 1 | 1 | 28 | 25 | 16 | 33 |
| joint | 4 | 4 | 33 | 27 | 18 | 33 |
| matched-centered | 4 | 3 | 42 | 22 | 16 | 33 |
| idle-cycle | 3 | 3 | 34 | 25 | 13 | 33 |
| idle-pair | 3 | 4 | 37 | 29 | 14 | 33 |

The four matched SNR-loss counters include quiet440's tiny numerical change; three matched RMS increases are the loud3000/steps/multitone losses. All increases remain explicit even when total SNR improves. Music cyclic fits can reflect source/codec structure rather than uniquely identify transport speed. Silence has no AM/FM carrier reference; short generated sources lack three cycles of the 0.2436 Hz bank period; steps and quiet997 can fail waveform/fundamental coherence. Each baseline has 33 inconclusive comparisons; those cannot count as passes. Known-tone amplitude/phase and average drift are reported separately with short-window response limitations.

Modulation probes retain bank 0.2436 Hz, 2/5/10/25 Hz, page 15.589 Hz, mains 50/100 Hz, horizon 62.356 Hz and commit 124.712 Hz. All modulation/transfer fits are diagnostic only and never modify SNR, source, clock or export gain.

The silence approximately 3991 Hz three-bin cluster retains 31.7827% of total spectral noise power; the strongest full-band carrier is near 11972.46 Hz with 35.3363%. Both residual lines are recorded, including energy above 4500 Hz. Lower RMS than matched and exact zero-mean area do not establish absence of additional background relative to previous idle controls. [endpoint-idle-pair-silence-diagnosis.json](endpoint-idle-pair-silence-diagnosis.json) authenticates constant packed0/decodedPCM0/index0, the exact cycle/table/endpoint certificate and full error bands/20â€“22050-Hz peaks.

## Closure, timing coverage and limits

All64 input bins close over the same 18 feedback states. Candidate dictionary counts are 139 FIRST and 98 SECOND patterns, 12,110 unrolled pattern-code bytes. The resident estimate is 15,424 bytes, compact worker origin 0xBC40; the separate functional max-capacity proof verifies the worker through 0xBFBC below 0xBFFF. The entire successor-table SHA is unchanged; the independent rational literal override matches all 64 candidate rows.

No CPU/clock retiming is requested. Ordinary hot paths retain 423 T for 128/Scorpion and 449 T for Pentagon, page extra 14 T, and bank extra 243 T (267 T for Scorpion), with delta 0. The host score uses the unchanged instruction-derived Pentagon timeline. The short native proofs check functionality and bounds; no complete new candidate Fuse run/every-timestamp actual audio comparison, physical-hardware test or 128/Scorpion audio-quality claim follows from this phase. The reproducible execution phase is implemented but was not run for this rejected quality candidate.

## Reproduction and manifest scope

Use the committed phase's sources/dependencies or restore the exact archived measured producers when later code changes. From the research worktree, with existing Python/NumPy/SciPy, compiler/OpenBLAS and FFmpeg, use fresh destinations to preserve this evidence:

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/.worktree/ay-auto-mix/.tmp/python-deps;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper;C:/Work/ZX-video/.worktree/audio-snr-research/toolkit;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper/experiments/song-snr'
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' audiobook-beeper/experiments/song-snr/endpoint_idle_pair_control.py audiobook-beeper/experiments/song-snr/evidence --phase host --output .tmp/reproduce-endpoint-idle-pair --scratch .tmp/reproduce-endpoint-idle-pair-render
```

[producer-snapshot.json](producer-snapshot.json) and `producer-source/` preserve 22 exact versions before inputs, including the new helper, independent player reference, C source and full-band PSD helper. The final driver's rejection wording is separately authenticated; its measured version remains archived unchanged. [artifact-manifest.json](artifact-manifest.json) authenticates 135 measured/archive files, nine source/unscaled-array identities and 45 baseline inputs, plus exact source/table/epsilon/selection/C binary/BLAS identities and separately linked functional proof hashes. Every full source, byte stream, prior, reference, clock, filter, gain and diagnostic remains preserved. Main/default disk identity is unchanged.

This README is explanatory and outside the frozen measured-output manifest. The manifest excludes itself to avoid a self-referential hash. Final disposition metadata changes only the report and final driver wording; all pre-input producer bytes and measured audio/diagnostics are unchanged. No new model, pair, retiming, encoding or Fuse run was performed during finalization.
