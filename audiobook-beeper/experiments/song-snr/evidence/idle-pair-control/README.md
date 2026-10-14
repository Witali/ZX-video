# Source-independent zero-mean idle-pair control

Date: 2026-10-14. Decision: **reject unconditional promotion**. This is a completed host experiment, not a release disk or a complete new emulator proof. No Fuse run was performed for this candidate.

The candidate loses full-source SNR/RMS on five sources versus the matched centered control. Speech loses 0.245886 dB and *The Entertainer* loses 0.520855 dB. Silence is 4.395344 dB noisier than the previous one-word idle control, and the approximately 3991 Hz silence line returns. Exact nominal zero-mean pulse area does not establish universal quality, correct noise-shaping state semantics, or absence of added background.

## Frozen mechanism and unchanged measurement

The source-free analytic selection enumerated 424 words with 224 on-T and 424 words with 225 on-T: 179,776 ordered pairs. The frozen pair is `idle_pair_words=[0x569A,0x56AD]`, assigned to input bin 32 at feedback states 16 and 17 respectively. The same pair is used for every source. No audio influenced selection or tie-breaking, and no alternative pair was tried on this corpus.

Only `words[32,16]` and `words[32,17]` change. Every other packet word and every successor remain unchanged; the original successor cycle is 16 → 17 → 16. The two ordinary packets have 224 + 225 = 449 on-T out of 898 T, exactly 50% nominal area. The independent rational regeneration and two-cell comparison are recorded in [idle-pair-silence-diagnosis.json](idle-pair-silence-diagnosis.json). Preserving successor bytes is a table-scope fact, not proof that the modified words derive those endpoints under the original q/recent recurrence. Root's separate exact-Fraction endpoint analysis supplements this distinction.

Common model: `duration_zero`, `pcm_origin=0`, `extent=1`, `beta=0.5`, centered `pcm_quantization_bias=512`, and `compact_stream_loader=True`. Search uses the same standalone C encoder, beam width 32, horizon 128, commit 64, regularization 0.1, and Lanczos-16 compensated prior as the preceding controls. C search and prefix replay share the table; the independent playback reference spells out its own literal override.

Quality uses the complete original uniform 8 kHz source, unchanged f64 listening filter (70 Hz high-pass and two 4500 Hz low-pass pairs), one continuous filter run, and fixed 100 ms edge exclusions. There is no fitted source clock, delay, gain, normalization, changed bandwidth, or source-specific setting. Reference/output float64 arrays are unscaled; exported listening WAVs use the same fixed 0.5 gain. Every source and encoded payload has an authenticated identity.

The six generated sources contain 16,896 samples each. Speech and *The Entertainer* contain 186,880 samples each. The full song contains 720,384 samples, retaining all 720,000 musical samples; the existing silent guard is preserved. The final 128-sample settling guard was already silent and was not overwritten to hide dropped content.

## Complete corpus results

All nine sources were encoded and fully rendered in a fresh **99.592166 s** host run. This time includes preparation, workset serialization, C execution, filtering and artifact diagnostics; it excludes disk assembly and emulator execution. No cached resume is presented as a conversion benchmark.

Unfitted original-clock SNR in dB:

| Source | Compensation | Half-joint | Matched centered | One-word idle | Zero-mean pair |
| --- | ---: | ---: | ---: | ---: | ---: |
| quiet440 | 3.871973 | 5.185187 | 7.183904 | 7.183489 | 7.183489 |
| loud3000 | 7.455600 | 8.155355 | 8.082355 | 8.086511 | 8.092602 |
| steps | 9.958784 | 2.616812 | 2.456251 | 2.061835 | 1.925453 |
| quiet997 | -3.051346 | -2.370523 | 0.840043 | 0.840043 | 0.840790 |
| multitone | 15.611740 | 17.327370 | 17.258909 | 17.294429 | 17.292132 |
| speech | 19.380055 | 21.692334 | 22.056546 | 21.866089 | 21.810661 |
| entertainer | 17.043144 | 19.445475 | 19.589737 | 19.228961 | 19.068882 |
| sea_foam | 18.825071 | 20.250316 | 20.110901 | 20.100940 | 20.105056 |

Silence has no finite signal/noise SNR. Absolute unscaled noise RMS is:

| Compensation | Half-joint | Matched centered | One-word idle | Zero-mean pair |
| ---: | ---: | ---: | ---: | ---: |
| 0.015513939 | 0.015486738 | 0.015513939 | 0.002300011 | 0.003815023 |

The pair's song is 0.005845 dB below matched centered, 0.145260 dB below half-joint and 0.004116 dB above one-word idle. Versus matched, the other losses are quiet440 0.000415 dB, steps 0.530797 dB, speech 0.245886 dB and entertainer 0.520855 dB. Versus compensation, steps lose 8.033331 dB.

The authenticated original song is -3.085228 dB on the unchanged original-clock metric, so this candidate is +23.190284 dB against that original. That comparison includes repairing accumulated clock drift; it is not an isolated proof of a 23 dB PDM denoising gain. The same-clock controls in the table remain necessary for codec/artifact acceptance. Legacy modulation fits broken by drift are missing evidence, not absence of modulation.

## Artifact comparisons and applicability

[report.json](report.json) and every source's comparison reports retain all numerical changes. Counters below disclose increases above the existing arithmetic tolerance of 1e-10; this tolerance is **not an audibility threshold** or a universal safety gate.

| Baseline | SNR losses | RMS increases | Applicable AM increases | Applicable delay increases | Coherent-line increases | Inconclusive modulation comparisons |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Compensation | 1 | 1 | 24 | 24 | 19 | 33 |
| Half-joint | 5 | 5 | 27 | 28 | 17 | 33 |
| Matched centered | 5 | 5 | 34 | 23 | 20 | 33 |
| One-word idle | 4 | 5 | 28 | 22 | 16 | 33 |

Modulation probes cover bank 0.2436 Hz, 2/5/10/25 Hz, page 15.589 Hz, mains 50/100 Hz, horizon 62.356 Hz and commit 124.712 Hz. Fits are diagnostic only. Silence has no AM/FM reference; the short generated sources do not observe three bank-period cycles; steps and quiet997 can fail waveform/coherence or fundamental-power applicability. These missing estimates cannot count as passes. Music fits can correlate with source structure and codec error rather than uniquely identify transport speed. Known-tone phase/amplitude diagnostics and average drift are stored separately, with their window-response limitations.

Silence RMS is 12.184498 dB below matched centered but 4.395344 dB above one-word idle. The pair's strongest approximately 3991 Hz three-bin cluster accounts for **61.58%** of total spectral noise power; matched centered has approximately 97% at a higher absolute level. The one-word control has no dominant line at or below 4500 Hz; its strongest full-band carrier is near 15963 Hz. Thus zero-mean area changes spectral structure and brings back an in-band line compared with one-word idle. The full error bands and 20–22050 Hz peaks are saved, including residual carriers above the listening cutoff; lower total RMS is insufficient to claim absence of added background.

## Closure, timing and verification limits

Source-independent closure over all 64 input bins remains 18 feedback states. The candidate uses 138 first-byte and 98 second-byte dictionary patterns: 12,068 unrolled pattern-code bytes. The resident-size estimate is 15,424 bytes, giving compact worker origin `0xBC40`; the worker endpoint requires assembly/native proof. The complete successor-table hash equals the original table.

No hot-path instruction or clock change is requested: ordinary CPU counts remain 423 T for 128/Scorpion and 449 T for Pentagon, with page-extra 14 T and bank-extra 243 T (267 T for Scorpion). This host phase uses the unchanged instruction-derived Pentagon timeline. No complete new native/Fuse candidate audio run, actual timestamp comparison, physical-hardware test, or 128/Scorpion audio-quality claim follows from this phase. The execution phase remains implemented but is not warranted for this rejected quality candidate.

## Reproduction and authentication

Run from the audio research worktree with the existing Python/NumPy/SciPy, compiler/OpenBLAS and FFmpeg dependencies. Use a fresh output/scratch path to preserve the saved experiment:

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/.worktree/ay-auto-mix/.tmp/python-deps;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper;C:/Work/ZX-video/.worktree/audio-snr-research/toolkit;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper/experiments/song-snr'
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' audiobook-beeper/experiments/song-snr/idle_pair_control.py audiobook-beeper/experiments/song-snr/evidence --phase host --output .tmp/reproduce-idle-pair --scratch .tmp/reproduce-idle-pair-render
```

[producer-snapshot.json](producer-snapshot.json) and `producer-source/` archive 22 exact pre-input producer versions, including the independently implemented reference and full-band PSD helper. The final driver's rejection wording was added after measurement; [artifact-manifest.json](artifact-manifest.json) authenticates that final source separately from the unchanged measured driver archive. The native combined C source, executable and matrix-library hashes are recorded. The manifest authenticates 125 output/archive files, nine source/unscaled-array identities and 36 inputs from the four compared baselines. Main/default disk identity is unchanged.

This README is an explanatory document **outside the manifest's measured-output snapshot**. The manifest also excludes itself to avoid a self-referential hash. Root's separately authored exact-Fraction endpoint supplement is additional mechanism evidence; its own authentication is separate from the frozen host-output snapshot. All 124 non-report measured/archive files remain byte-identical after final rejection metadata was recorded. No source, encoded bytes, filter, gain, prior, clock or diagnostic was changed by finalization.
