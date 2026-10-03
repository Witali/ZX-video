# Waveform-aware IMA encoding: 21.01 dB in the complete player

Measured 2026-10-03 on the original complete 186880-sample control excerpt.
The new [TRD](experiments/ima-waveform/audiobook-preview.trd) retains its
93440-byte IMA payload, live decoding, full resident source, loading message
and cyclic playback. Two complete cold Fuse128 loops each measure
**21.010690 dB**, compared with **18.994103 dB** for the phase-locked baseline.
Mean playback speed is **-0.043271%** from 8 kHz. This is emulator verification,
not a physical Spectrum/speaker measurement or a guarantee for every input.

## What changed

Only the PC encoder's choice of ordinary IMA codes changes. A beam search
scores the filtered PDM pulses against the unchanged original 8-kHz PCM8
reference at their measured times. It carries the IMA predictor/index, PDM
feedback state and six filter states. A regularization weight of 0.1 keeps
the control near the existing timing-compensated PCM; a short search without
this prior can drive the control close to full scale.

The search approximates the comparison filter with analytic propagation of
two Butterworth 4500-Hz low-pass pairs and a 70-Hz high-pass pair. Sixteen
hold-midpoint observations per sample are weighted by duration. Independent
sequential propagation checks the composed matrices. The baseline model
scores 19.00195 dB versus the established FFmpeg result of 18.99410 dB;
agreement validates this search approximation, not a candidate disk.
Acceptance always uses actual new port times, 192-kHz integration, the
unchanged FFmpeg filter and 44.1-kHz comparison, excluding 0.1-s edges.
There is no fitted gain, delay or pitch adjustment.

## Bounded comparisons and their limits

| Input / search | Host score on the old timeline | Actual new disk |
|---|---:|---:|
| Initial prefix, width 16, uniform prior, weight 0.00001 | 9.83315 dB | Not built; rejected |
| Initial prefix, width 32, compensated prior, weight 0.1 | 18.19550 dB | Not verified |
| Initial prefix, width 64, filter-history bins 4096 | 18.36698 dB | Not verified |
| Original full control, width 32, compensated prior, weight 0.1 | 21.99406 dB | **21.01069 /21.01069 dB** |

The initial prefix is a different, quieter source, whose verified baseline
is 15.80350/15.80023 dB. Its improved host scores do not establish 20 dB, and
no shorter/easier excerpt replaces either full input. The general converter
still uses its previous verified default; this encoder is a separate option
for experiments. Its beam merging/block decisions are heuristics, not proof
of the best achievable signal-to-noise ratio.

## CPU, memory and complete verification

The Z80 decoder and modulator instructions retain **423 T per ordinary
sample, +14 T per page, +140 T per bank**: delta **0 T** for each path.
Compressed audio remains 93440 bytes; total Spectrum RAM allocation remains
131072 bytes. No full PCM/PDM expansion and no playback disk reads are added.
The data-dependent ULA delays change, so the old output clock cannot qualify
the new stream even when every instruction count is unchanged.

Fresh phase calibration takes four probes. Its selected silent tail uses
1273 balanced output pairs, five groups and a 69-T pad: 66300 added native
T, versus the baseline's 66495 T. Native loop totals are **79122532 versus
79122727 T (-195 T)**. Actual Fuse loops both remain **82891452 T**, exactly
1169 fields, with zero repeat-phase drift. ULA waits total **7537840 T over
two loops** and are reported separately from CPU work and preload latency.
Average PDM output is **128053.56 writes/s**; it is not an evenly spaced
128-kHz clock (maximum hold 185 T, including boundaries).

Native and cold Fuse check all **5985253 PDM outputs /373760 predictors and
indices** across two full loops. RAM guards, bank latches, 425 preload
sectors, zero runtime reads and loading-message visibility pass. FFmpeg's
independent IMA decoder reproduces every source-cycle predictor. Normal-speed
Fuse recording additionally checks two wraps, paging and audible activity;
its WAV is a sound-generator capture, not a physical sound-card recording.
The numerical 21.01-dB measurement uses the documented port-event filter,
not a claim that this capture or every physical RC circuit has the same SNR.

[Full report](experiments/ima-waveform/report.json),
[measurement WAV](experiments/ima-waveform/clock-aware-output-preview.wav),
[normal-speed Fuse WAV](experiments/ima-waveform/result-preview.wav).
TRD SHA-256: `68c22d1e49273242393b009c030a86ea395ca234ea9fdf36b988edb5a2568aa6`.
The root historical disks are unchanged; use the linked new disk.

## Reproduction

Use the Python environment and executable paths in [CONVERTER.md](CONVERTER.md).
The pilot archive contains the full source, compensated prior and measured clock.

```powershell
python audiobook-beeper/ima_waveform_encoder.py --input audiobook-beeper/experiments/ima-direct-locked --output build/waveform-host --width 32 --regularization 0.1 --ffmpeg <ffmpeg.exe>
python audiobook-beeper/verify_waveform_disk.py --pilot audiobook-beeper/experiments/ima-direct-locked --encoded build/waveform-host --output build/waveform-disk --fuse <fuse.exe> --ffmpeg <ffmpeg.exe> --record
```

The disk verifier rejects nonempty output folders, snapshots its sources,
freezes the pilot's hot-row layout, recalibrates the actual new stream and
checks both complete loops. All additional search/filter computation runs
on the PC. Large raw execution traces stay in the local cache with archived
hashes; compact times, assembly, streams, reports and source snapshots are
retained for reproduction.
