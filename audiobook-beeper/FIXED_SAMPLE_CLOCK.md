# Fixed sample clock and conversion speed

2026-10-05. The user wants equal physical duration for each sample, without
recording-specific time compensation, and a completed TRD within the retained
audio duration on the host. Shorter resident parts are acceptable; lowering
the approximately 128-kHz PDM rate is not. These are requirements for a new
player, not properties established by the current release.

## Measured baseline

The [audit script](audit_fixed_sample_clock.py) authenticates the input WAV and
all five actual output timelines from the [full IMA4 disk](experiments/ima4-full-disk/README.md).
It examines every source-bearing sample, including page and bank transitions,
but excludes the final silent guard. [Machine-readable results](experiments/fixed-sample-clock/audit.json).

| Part | Minimum sample, T | Maximum sample, T | Mean sample, T | Standard deviation, T |
| --- | ---: | ---: | ---: | ---: |
| 1 | 423 | 590 | 443.172 | 16.830 |
| 2 | 423 | 598 | 443.173 | 17.158 |
| 3 | 423 | 590 | 443.172 | 17.148 |
| 4 | 423 | 590 | 443.172 | 17.131 |
| 5 | 423 | 598 | 443.179 | 17.128 |

Thus a correct average rate does not imply equal individual sample lengths.
The existing ordinary instruction count is 423 T, with page/bank extras of
14/140 T before ULA delays. Data-dependent table placement, memory contention
and the even ULA output port all matter. Moving only the decoder rows or
padding the shorter ordinary branch cannot establish the requested timing.
Padding everything to the observed maximum 598 T would lower the mean
16-pulse output rate to approximately 94.9 kHz and violates the requirement.

On the same prepared 186880-sample / 23.36-second first part, one measured run
on the current AMD64 host and Python 3.12.14 gives:

| Existing encoder | Encoding wall time | Raw codec-only SNR |
| --- | ---: | ---: |
| Nearest IMA delta | 0.531 s | 23.611 dB |
| Beam width 32 | 13.517 s | 25.614 dB |

Both streams pass the saturation guard. These timings exclude source decoding,
table construction, assembly, disk packing and verification. The SNR values
compare decoded IMA PCM with the prepared PCM8 source; they are **not** PDM,
Fuse, filtered end-to-end measurements, or a new quality improvement claim.
One run does not establish a worst-case host performance guarantee.

Ordinary encoding is already faster than real time. Repeating three expensive
waveform searches, phase calibration and compensation for each part causes
much of the existing delay. An unconditional normal-speed two-loop recording
also cannot fit a one-audio-duration conversion budget: it must be an explicit
listening option, while automatic verification can run accelerated.

## Proposed timing contract

At the Spectrum 128 clock of 3546900 Hz, exact 8 kHz would need 443.3625 T
per sample. A strictly constant integer-T sample cannot have that exact rate.
A useful **unimplemented target** is 440 T and 16 PDM outputs per sample:

- Sample frequency: 8061.136364 Hz.
- PDM output frequency: 128978.181818 Hz, above the present nominal 128 kHz.
- Playing an unchanged 8-kHz stream would be 0.764205% faster, within the old
  2% tolerance. Prefer one ordinary input resampling at the declared playback
  rate to preserve pitch and duration; this is not waveform-specific timing
  warping or an iterative search.

This is a design budget, **not a demonstrated kernel**. The current path
already exceeds 440 T on many samples. Sixteen OUT(C),r instructions alone
cost 192 native T; all dispatch, IMA decoding, buffering, paging and actual
ULA waits must fit in the remaining budget. Equal sample totals also do not
by themselves guarantee uniform internal pulse spacing or improved SNR.

The next implementation must schedule decoding and paging ahead of the output
deadline, using a smaller audio capacity or a bounded working buffer where
necessary. Critical code/tables should avoid data-dependent RAM waits, and
port contention still needs an explicit timing schedule. A buffer can move
work away from a deadline but cannot increase the sustained Z80 CPU budget.
Preserve packed IMA disk storage unless the user authorizes a format change.

The host path should perform one codec encode and one fixed modulation model,
without a per-recording PDM parameter sweep or repeated time compensation.
Qualify the player architecture once with complete native/cold Fuse tests;
normal conversions must still validate their new streams and final volumes.
Measure the complete public CLI wall time, from source opening to a verified
TRD, against retained source duration. Do not meet the goal by excluding normal
stages or by calling an unverified image complete.

## Status and reproduction

This audit changes neither player instructions nor release data: CPU delta
0 T. The existing disk remains the current verified result. A constant-clock
player and an end-to-end faster-than-real-time converter are **not implemented
or qualified by this audit**.

With the project's Python dependencies and `audiobook-beeper` on PYTHONPATH:

```powershell
python audiobook-beeper/audit_fixed_sample_clock.py --output build/fixed-clock-audit.json
```

The output must not already exist. Saved timing evidence is reused without
launching another emulator or repeating waveform searches.
