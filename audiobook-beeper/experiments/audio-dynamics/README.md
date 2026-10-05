# Gentle source dynamics

2026-10-05. The user requests louder source audio with normalization and mild
compression after reporting vibration in the complete IMA4 disk. The shared
[implementation and controls](../../AUDIO_DYNAMICS.md) now apply by default
to ordinary IMA3, IMA4 and mu-law input. The Spectrum player is unchanged.

## Completed preparation evidence

[`preparation/report.json`](preparation/report.json) authenticates the original
decoded track against the previous full-disk cache and confirms that
`--dynamics off` recreates **all five former prepared PCM streams byte for byte**.
Gentle processing preserves 5340776 decoded samples /667.597 seconds and raises
whole-track RMS by 4.066736 dB at the same 0.8515625 peak. The retained first
five parts' RMS gains are 5.4545, 5.3514, 5.4387, 4.9662 and 5.3177 dB.
These are source-level improvements, not promised output-SNR gains.

- [First eight seconds, previous peak-only source](preparation/before-first8.wav)
- [Same source with gentle dynamics](preparation/gentle-first8.wav)

Both files retain their actual prepared levels; no extra listening gain is
applied. They are pre-IMA source references, not Spectrum output.

Thirty focused tests pass, covering real FFmpeg filtering, compressor
behavior, streaming parity, exact off mode, sample count/polarity/peak/silence,
prepared-PCM bypass, CLI routing and existing series/clock/search contracts.
The initial test incorrectly expected total RMS to increase even for a
sustained high-amplitude tone; the actual requirement is reduced dynamic
contrast and raised quiet passages. Replace that assumption with direct
behavioral checks and separately verify the real audiobook's positive gain.
The CLI harness also now accepts the IMA3 command's successful SystemExit(0).
Neither test adjustment changes the production quality or timing gates.

## Completed full-disk build

The public converter ran with one bounded waveform attempt and no
additional clock-refinement pass; existing compensation candidates remain
eligible. No native/Fuse check is skipped:

```powershell
python audiobook-beeper/convert_audio.py "path/to/audiobook.m4a" --codec ima4 --disk-mode single --dynamics gentle --attempts 1 --no-refine-clock --no-recording --output build/ima4-normalized --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

`precompute.py` can prepare independent later parts through the same public
converter function. Source, tools and producer hashes must match the running
conversion; only fully completed part results can be adopted. This changes
host scheduling, not encoding settings or final-volume verification.
Parts 3..5 were precomputed and adopted; the serial driver encoded parts 1..2
and performed all final volume checks. The earlier 15.884-dB first-part
compensation result was partial; the final selected waveform search improves
that part further. Part 3 retains compensation pass 2 because its waveform
candidate scores 15.604614 dB versus the control's 15.664102 dB over two loops.
Other parts select the single waveform candidate. All candidate metadata and
payloads are preserved, including lower-quality controls.

The [new independently bootable disk](../../../ZX-audiobook-IMA4-normalized-full-disk.trd)
retains **113.712 source seconds** in five parts and fills all 2560 sectors
(655360 bytes). Its SHA-256 is
`e734494907b00ba0e5bbb36b65f37152710fd73ac06efc0865f728a0037b8004`.
The old complete disk and preferred historical direct disk remain unchanged.

| Part | Peak-only disk SNR, dB | Conditioned disk SNR, dB | Difference, dB |
| --- | ---: | ---: | ---: |
| 1 | 11.448644 | 18.212893 | +6.764249 |
| 2 | 12.842333 | 18.260997 | +5.418664 |
| 3 | 13.266120 | 15.674295 | +2.408175 |
| 4 | 13.527789 | 18.946754 | +5.418965 |
| 5 | 10.333552 | 15.139674 | +4.806122 |

Each SNR uses that disk's own prepared 8-kHz PCM8 reference and the same fixed
clock/float64 measurement filter. Intentional compression is not counted as
coding error. These are complete end-to-end results, not a controlled estimate
of the compressor alone: stream selection and recording-dependent ULA timing
also differ. The new bounded run uses one waveform attempt, versus three in
the historical run. The 20-dB goal remains unmet; the converter correctly marks
`complete: true`, `quality_gate_passed: false`, `preview_only: true`.

Complete native and fresh cold Fuse execution verify **14565211 PDM bits**,
**910326 predictor/index observations**, memory guards, bank order, four
automatic transitions, loading UI and END OF AUDIO. Every output time is within
**1 T** of an independently qualified reference; the limit remains 8 T with no
startup exclusions. Parts 2 and 5 need additional full two-loop controls in
natural ready phases 987 and 988; five and one earlier phase rejections are
preserved. No trace reuse or timing-gate relaxation is used in this new run.

Speed errors are +0.041952%..+0.041995%, well within 2%. First preparation takes
27.388691 s and reload gaps are 22.750465, 22.570542, 22.810440 and 21.031193 s
in Fuse. All 2585 sector calls occur outside active audio. Approximately
128-kHz useful PDM output and resident capacity are retained. Physical hardware
and a fresh normal-speed Windows endpoint capture are not tested in this run.

## Remaining cyclic distortion and listening output

[`output-comparison.json`](output-comparison.json) reuses the preceding
vibration diagnostic without changing its filter or fitting delivered audio.
Field-folded error-power ratios remain 4.293, 4.793, 3.057, 3.844 and 3.202;
early/late profile correlations are 0.859..0.914. Thus stronger signal and
better SNR **do not eliminate periodic distortion**. Fitted field-rate AM is
0.126..0.340% except part 3 at 2.558%; that diagnostic is higher than its old
0.032% control. Linearized delay indicators are 0.192..0.407 us. These fits are
not a pitch tracker or proof of perceived flutter being fixed. Further timing
work remains separate from this completed source-conditioning change.

- [First eight seconds of actual full-disk PDM output, reconstructed with the measurement filter](conditioned-output-first8.wav)
- [Complete first resident part through the same filter](release/verification/cold-0001/part-01-output.wav)

No additional playback normalization or gain is applied to these WAVs.

## Evidence and reproduction

`archive_release.py` preserves selected streams, assembly, exact producer
snapshots, complete selected native/Fuse traces, final volume execution and
all search metadata/payloads. `artifact-hashes.json` authenticates 1051 files.
`compare_output.py` authenticates both historical and new evidence before
comparing quality and cyclic-error indicators. `postflight.json` records the
successful byte-identical rebuild from the archived selected streams.

```powershell
python audiobook-beeper/experiments/audio-dynamics/reproduce.py --output build/normalized-rebuild --build-only --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

Omit `--build-only` to repeat complete execution checks. The completed build-only
check authenticates the archive and reproduces disk bytes; it does not claim
an extra execution run beyond the original complete public conversion.

Ordinary IMA4 cost remains 423 T/sample, page/bank extras 14/140 T, all deltas 0.
No physical-hardware result, carrier reduction or constant-clock redesign.
