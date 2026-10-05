# 30-dB IMA investigation — PC simulation only

2026-10-05. The user requested at least 30 dB, explicitly retained the
current IMA compression and fragment duration, and requested simulation
before another Z80 implementation. **30 dB total SNR was not reached.**
No new player, TRD, table layout, default modulator or CPU hot path is changed
by this investigation. The prior noisier SD2 disk is a separate
[completed experiment](../sigma-delta2-128/README.md).

The best whole-fragment simulations are **21.227136 dB with IMA3** and
**24.639507 dB with IMA4**, both using second-order feedback at exactly
128000 decisions/s, full-precision state and gain 1. These are ideal-clock
PC results, not Spectrum/Fuse or physical-hardware results.

- [IMA3 model WAV](ima3-best-preview.wav), [same-gain reference](ima3-reference-same-gain.wav)
- [IMA4 model WAV](ima4-best-preview.wav), [same-gain reference](ima4-reference-same-gain.wav)
- [Error budget](evidence/assessment/report.json), [all candidates and failures](evidence/simulation/report.json)
- [Independent verification](evidence/simulation/verification.json), [artifact hashes](manifest.json)

## Reference and controls

Use all 186880 unchanged prepared PCM8/8-kHz samples: 23.344 seconds of
speech plus 128 silent samples, identical to the accepted overlap reference.
PCM hash: `ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
IMA3 uses 70080 resident bytes and IMA4 93440 for this duration. The headerless
IMA decoder recurrence and alphabets are unchanged; IMA3 stores the eight
even IMA nibbles in three bits, with no decoder-side IMA4 conversion.

SNR is signal divided by **total reconstruction error including distortion**,
after the established `highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2`
filter on both signals. Exclude only the fixed first/last 100 ms. Do not fit
gain, phase, latency or time stretch, change bandwidth, denoise the source,
or select favourable speech intervals. Declared modulator gain scales the
reference by the same known factor. Both winning models use gain 1.
The four linked listening WAVs additionally use the same fixed 0.5 gain
(-6.02 dB) to prevent clipping of brief filter/PDM transients. This does not
enter SNR calculations. The initial full-scale WAV export triggered the
archive's clipping assertion; the selected output/reference pairs were
re-exported and checked. Intermediate sweep WAVs in the evidence directory
retain their original unattenuated debug export and may clip; use the linked
verified previews for listening. All scores use unclipped floating audio.

| Complete-reference control | IMA3 | IMA4 |
| --- | ---: | ---: |
| Previously verified disk, first Fuse loop | 20.436321 dB | 22.174289 dB |
| Fresh PCM-error encoding, ideal multilevel DAC | 21.770813 dB | 25.841827 dB |
| Same encoding + ideal SD2, gain 1/2 | 20.299764 dB | 22.800424 dB |
| Same encoding + ideal SD2, gain 1 (selected) | **21.227136 dB** | **24.639507 dB** |
| Modulator alone, relative to selected decoded IMA | 30.827692 dB | 30.921171 dB |

The first row reproduces each previous disk's **own** complete saved Fuse
clock and validates the original score within 1e-8 dB. Its sample timing is
not the ideal uniform clock of the later rows. The IMA4 disk's existing
worst-of-two-loop release score is 22.164431 dB. Do not call the simulated
24.639507-dB result a verified replacement for that disk.

For diagnosis only, the identical PCM through full-scale ideal SD2 without
IMA reaches **31.691681 dB**. This is not a proposed no-IMA storage format;
the user's IMA/duration constraint remains in force. It demonstrates that
the high-precision modulator can cross 30 dB in this model while the complete
IMA path does not. Quoting the modulator-only number as total quality would
be wrong. The recorded data already contain source noise, which is not
counted as a new playback error.

## Bounded search and rejected attempts

1. [assess.py](assess.py) separates sample-clock reconstruction, IMA PCM16,
   packet input selection and actual old PDM on saved timelines. It then
   encodes fresh streams with a 64-state PCM-error beam and tests ideal
   damped/second-order feedback. The old waveform-compensated streams are
   deliberately not treated as codec-only upper bounds: their PDM can cancel
   part of the deliberate PCM distortion.
2. [simulate.py](simulate.py) adds a PC-only filtered-error IMA search:
   width 128, horizon 128, commit 64, signed 16-bit predictor and unchanged
   index transitions. A six-state linear filter and quadratic cost score
   reconstruction error efficiently. This heuristic merges equal decoder
   states even when filter histories differ; it is not globally optimal.
   It performs worse (21.232667 /23.500713 dB before PDM), so reject it.
   Search times are 60.218 /83.375 seconds. Preserve the failed streams.
3. For each of the four streams, test beta .5 and .75 at gain 1, and true
   second order (beta 1) at gains .5, .625, .75 and 1: **24 full-source
   configurations**, of which 22 finish and two exceed the declared state
   bound. Do not clip unstable integrators to obtain a favourable score.
   Both rejected full-gain filtered-search streams are recorded. The best
   retained streams are the simpler PCM-error encodings with SD2 gain 1.

The state equation is `u=x+q+beta*recent`, `recent=u-bit`, `q+=x-bit`.
For beta=1, `q=e_previous-e_older`, giving
`u=x+2*e_previous-e_older`. The winning finite-clip state peaks are 6.815552
and 5.570068 DAC units; this does not prove stability for arbitrary audio.
The earlier small Spectrum tables, input quantization and memory/cycle
limits are absent here. A future port must prove those separately and
recheck the complete output at real OUT timestamps.

An initial assessment stopped at the IMA4 metadata's omitted `pcm_bins` key.
Restore its established 64-bin default and repeat in a new output directory;
the partial report/log are retained as a failed run, not a complete result.

## Verification and conclusion

[verify_simulation.py](verify_simulation.py) checks all 186880 decoded samples
of each of the four encoded streams against FFmpeg IMA WAV. Every selected
SD2 decision (2990080 per codec) matches a separate integer two-history
recurrence at the **selected gain 1**. The selected SNR is independently
re-rendered and reproduced within 1e-8 dB. A first-five-second numerical
check changes pulse-area integration from 192 to 768 kHz: deltas are
+0.003579 dB /-0.021757 dB. This is convergence evidence for that prefix,
not a proof of real analog performance or stability on every possible input.

Keep the current main player. The best tested complete IMA4 model is still
5.360493 dB short of 30; another modulator-order change alone has not closed
the gap. At this point the decoded IMA error is larger than the modulator's
added error. The next useful PC investigation would need a materially better
joint IMA encoding/output model, with decoder, duration and storage fixed.
These bounded results do **not** prove that 30 dB is impossible for all such
algorithms or signals. Do not start a Z80 port from an unachieved PC target.

## Reproduce

Use the repository Python environment with NumPy and FFmpeg; Fuse and a
Z80 assembler are not called by these three simulation commands:

```powershell
python audiobook-beeper/experiments/snr30-ima/assess.py --output build/snr30-assess --ffmpeg <ffmpeg.exe>
python audiobook-beeper/experiments/snr30-ima/simulate.py --assessment build/snr30-assess --output build/snr30-sim --ffmpeg <ffmpeg.exe>
python audiobook-beeper/experiments/snr30-ima/verify_simulation.py --assessment build/snr30-assess --simulation build/snr30-sim --ffmpeg <ffmpeg.exe>
```

Use new output directories and keep completed reports. The source snapshots
and manifest authenticate this study independently of the earlier paused
encoder-quality milestone; that milestone has not been resumed.
