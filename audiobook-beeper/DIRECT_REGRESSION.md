# Preferred direct IMA4 disk: historical audit

2026-10-05. The user reports that
[`ZX-audiobook-IMA-ADPCM-direct-test.trd`](../ZX-audiobook-IMA-ADPCM-direct-test.trd)
sounds good and asks where later sound changed. The evidence identifies a
substantial preparation change; it does **not** establish a blanket regression
in the later IMA4 decoder or justify reverting all its clock corrections.

The preferred disk is the original `b359f53` checkpoint from
2026-10-03 17:50:37 +02:00, restored without modification in `6ce7f55` to retain
the public YouTube link. Its SHA256 is
`9ce319e8b9352a96ed965d87ff3d1d8698df7d788221563758d306d23c053013`.
The current `direct_player.build_disk(packed, ..., model=None)` reproduces
**all 655360 bytes exactly** from the archived packed payload. The old algorithm
is still available; it has not been overwritten by later experiments.

## Where behavior changed

| Checkpoint | Relevant change |
| --- | --- |
| `b359f53`, October 3 | Preferred direct IMA4 disk: 16 PDM pulses/sample, about 128.05 kHz, original feedback table. Speech starts at source second 60. |
| `83abfc5`, October 3 | Measured pulse weights replace native-only weights in an experimental feedback table. Source PCM and IMA bytes remain identical. |
| `66c0ced` / `4a819df`, October 3 | Offline sample-clock compensation, then stable repeat phase. These address timing distortion; they do not change the IMA recurrence. |
| **`d4a980d`, October 3, 19:22:07 +02:00** | **The new generic converter uses peak normalization and omits the original speech gain/limiter and 70/3800-Hz preprocessing. It starts at second 0 by default.** |
| `acf1682` / `d695850`, October 4 | Direct packed IMA3 becomes available and then the general default. A default new conversion is therefore not necessarily the four-bit format of the preferred disk. |
| `e3a9dc2` and later quality work | Overlapping waveform search reduces measured error on the original prepared speech, without extra Z80 work. |

This audits major saved checkpoints, not every intermediate commit. It does
not identify a universal first bad commit from a listening report alone.

## The largest preparation difference

The old pipeline applies `highpass=f=70` and two `lowpass=f=3800:p=2` filters,
normalizes to 0.65, then uses:

```text
volume=4,alimiter=limit=0.85:attack=5:release=100:level=0:latency=1
```

This boosts quiet speech and limits loud peaks. It changes dynamics, rather
than merely turning the complete recording up. See
[`build_ima.py`](build_ima.py) and the saved
[`preparation.json`](ima-preview/preparation.json). The original normalization
window is 28.864 seconds; the final direct player retains a shorter prefix.

The generic converter's ordinary preparation uses one fixed peak gain to
109/128, standard FFmpeg mono/resampling, and 10-ms edge fades. FFmpeg still
applies resampling anti-alias filtering: removal of the explicit voice filters
does **not** mean that downsampling has no low-pass filter.

For a controlled source-position comparison, this audit decodes second 60
again and applies the current peak-only preparation to 23.344 seconds plus
the 128-sample guard. Both prepared references peak at 109/128. Excluding
100 ms at each edge, their RMS levels are:

| Preparation | RMS, normalized to full scale |
| --- | ---: |
| Archived speech preparation | 0.195821 |
| Current prefix peak-only preparation | 0.075033 |

The old speech is **8.332 dB louder RMS**. Quiet speech is consequently more
exposed to PDM noise in the generic preparation. This is a plausible contributor
to the reported preference, not a proof that output SNR falls by exactly
8.332 dB. Filtering, limiting, fades and normalization windows differ; this
comparison does not isolate the limiter alone. Full-disk mode additionally
normalizes the complete selected track once, not each resident excerpt.

The last full IMA4 disk also starts at second 0 rather than 60. Comparing its
10.33–13.53-dB scores directly with older speech scores confounds source and
preparation changes with player changes.

## Same-source player comparison

All four archived stages have **identical PCM bytes**, SHA256
`ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
The audit authenticates source, payload, player metadata, both native/Fuse
proofs and complete two-loop OUT timestamps against saved manifests.

Every reconstruction uses 768-kHz time integration, float64 70-Hz high-pass
and two 4.5-kHz low-pass filters, and excludes 100-ms edges. No signal-dependent
gain or delay is fitted. The measurements include distortion, not just hiss.

| Stage | Reference clock | Loop 1 / loop 2, dB |
| --- | --- | ---: |
| Preferred original | Uniform measured mean, about 8003.3 Hz | 8.317 / 7.676 |
| Measured-weight table, same IMA payload | Uniform measured mean, about 8003.3 Hz | 8.430 / 7.777 |
| Clock-compensated, phase-locked IMA4 | Fixed source 8000 Hz | 18.998 / 18.998 |
| Current selected waveform-aware IMA4 | Fixed source 8000 Hz | 22.184 / 22.175 |

**Clock definitions matter.** A small overall speed offset accumulates phase
error across 23 seconds. The earlier streams are evaluated at their measured
mean speed in this table; the compensated streams explicitly target 8000 Hz
with a silent phase-lock tail. The JSON also gives both clock definitions for
every stage, including the poor scores produced by using the wrong reference
clock. Those are not measurements of audible noise alone.

The historical original's **18.85-dB** figure follows its varying sample
boundaries and therefore excludes clock distortion. It must not be substituted
for the first row or compared directly with the new fixed-clock scores.
Within these declared conditions, the evidence does not show the later IMA4
corrections making the waveform worse. The user's listening preference remains
valid; this metric alone does not establish subjective superiority.

## Listening and reproduction

All following WAVs use the same fixed 0.8 listening gain. They are reconstructions
from actual saved Fuse port timings, not new sound-device recordings or a model
of a physical Spectrum speaker:

- [Preferred original output](experiments/direct-regression/original-output.wav)
- [Current IMA4, identical prepared speech](experiments/direct-regression/current-output.wav)
- [Fixed 8-kHz reference](experiments/direct-regression/reference-fixed-8k.wav)
- [Old prepared speech](experiments/direct-regression/source-old-conditioned.wav)
- [Current peak-only preparation, same source position](experiments/direct-regression/source-current-peak-only.wav)
- [Machine-readable results and authenticated input hashes](experiments/direct-regression/report.json)

Run from the repository root with the existing NumPy/pyz80 project environment
and materialized LFS evidence:

```powershell
python audiobook-beeper/audit_direct_regression.py --reference-disk ZX-audiobook-IMA-ADPCM-direct-test.trd --output .tmp/direct-audit --ffmpeg C:/Tools/ffmpeg.exe
```

Optionally add `--source <original-audiobook.m4a>` for the preparation comparison.
The script rejects a different reference disk, modified evidence, unequal source
PCM, incomplete two-loop proofs, or a nonidentical rebuild. It writes
`restored-direct.trd` from the **current assembler**, not by copying the TRD.
The existing public reference path is preserved. No new duplicate release is
needed because the result is byte-identical to that file.

## Decision and coverage

Keep the preferred direct disk as a sound regression reference and retain its
exact-rebuild check. Do not roll back the whole player or silently make the
old speech limiter a default for arbitrary music. Recovering this exact old
checkpoint already works. A general speech-conditioning option should be
evaluated separately on matched source audio if requested.

No production encoder, modulator, assembly or converter defaults change in
this audit. Native ordinary cost is still **423 T/sample, delta 0**; page/bank
extras remain **14/140 T, delta 0**. The preferred disk's earlier full native
and cold Spectrum-128 Fuse proof is reused because the rebuild is byte-identical:
5,980,161 output bits and 373,760 predictor/index observations, two complete
loops, memory/paging checks and independent boot. Disk/ROM latency is outside
the native hot-path count. No new emulator run or physical-hardware test is
claimed. The separate fixed-duration/fast-conversion request remains pending.

The first audit invocation encountered an unmaterialized LFS WAV and stopped
before reading audio. Materializing the three source WAVs from the local LFS
cache resolved it; the complete authenticated audit then passed.
