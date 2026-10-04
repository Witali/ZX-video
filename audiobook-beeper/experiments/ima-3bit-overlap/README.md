# Speech boundary-error correction, 2026-10-04

The user reported voice vibration in the latest sequential speech TRD.
The unchanged 186880-sample, 8-kHz PCM8 reference is used throughout this
experiment. The final test contains the same excerpt twice, with a disk
loading pause, then `END OF AUDIO`; it is not a full-book conversion.

## Cause and correction

The waveform encoder previously committed all 128 samples of each search
window. Its final decisions lacked future filter-response costs. On the old
final disk, error power relative to signal power in the first eight samples
after a boundary was about 1.84 times the interior value. Repetition every
roughly 16 ms is a plausible source of audible roughness. Average SNR alone
did not reveal this defect.

The encoder now searches 128 samples but commits only 64. It carries the
exact IMA predictor/index, PDM feedback and analog-filter state of the
accepted prefix, and reconsiders the future. The automatic converter passes
`--commit-size 64` for all its waveform-search widths. The 256-sample third
attempt also commits 64. Historical direct probes keep their old behavior
unless that option is supplied.

There is no player modification. Both final part binaries and every decoder,
PDM and screen table match the old sequential disk byte for byte. Only the
audio payload and disk-series identity differ. Native phase costs remain
417/413/458/413/417/446/409/446 T, mean **427.375 T/sample, delta 0 T**;
page/bank extras remain +14/+140 T. The 13312-byte fixed reservation,
70080-byte reference payload and maximum 94458-byte packed capacity remain
unchanged. ULA contention, disk/ROM time and normal audio capture are measured
separately; these are not physical-hardware tests.

## Bounded search and full verification

The 4.096-second active-speech probe plus 128 silent guard samples compared:

| PC search | Host SNR | Elapsed time |
| --- | ---: | ---: |
| 128-sample horizon, commit 128 | 21.371719 dB | 20.938 s |
| 128-sample horizon, commit 64 | 21.600309 dB | 41.468 s |
| Same overlap, extra quantized filter-history states | 21.584004 dB | 62.125 s |

Select the ordinary overlapping search. The additional history states cost
50% more time and slightly reduce this probe's SNR, so they are rejected.
These are host-only probes, not disk quality claims. See `probes/report.json`
and [probe.py](probe.py). Full encoding took 236.812 seconds on this host.

The full new looping qualification checks every native/Fuse output and
predictor/index over two cycles: 5981841 PDM writes, SNR **20.436321 /
20.436366 dB**, mean speed **-0.299133%**, phase errors **0/0 T**, mean PDM
**127652.961 Hz**. See `qualified/native.json`, `qualified/fuse.json` and
`qualified/quality.json`. The original filter, fixed 8-kHz source clock and
100-ms end exclusions remain unchanged: no fitted gain, delay or time stretch
is used for quality acceptance.

The independently bootable final sequential disk is additionally executed
through both parts and EOF, including loading UI and automatic transition.
Every one of its 5980094 live bits passes native/Fuse checks. Both final
parts measure **20.436046 dB**, with **-0.271723%** mean speed error, zero
runtime disk reads and a **19.818222-s** loading pause. Boundary/interior
noise-power ratio falls from **1.835306/1.839939** to **0.999314** at 128
samples; at 64 samples it is **0.993068**. Boundary error power itself falls
about **47%**, rather than merely being masked by higher interior noise.
See `verification/report.json` and [comparison.json](comparison.json) for its
actual per-part SNR, timing and boundary-error measurements. The comparison
recovers the old disk's exact times from its archived trace and uses the
new disk's saved actual times. It folds error by both 128 and 64 samples to
check that overlap does not merely move the bursts to a new boundary rate.
This diagnostic's threshold is specific to the unchanged speech fixture,
not a universal quality gate for arbitrary music or silence.

Use [the corrected disk](../../../ZX-audiobook-IMA3-overlap-test.trd),
[normal Fuse capture](normal/result-preview.wav), and
[original prepared source](../ima-3bit-direct/source-preview.wav).
The [old normal Fuse recording](diagnostics/baseline-normal-preview.wav) is
also retained for listening comparison. FMF drops the last incomplete frame
on exit; only a portion of the silent guard is omitted in the normal WAV.
Complete source playback and exact final outputs are covered by the full
trace, not inferred from that listening capture. Remaining IMA/PDM noise is
not claimed to be eliminated; subjective listening acceptance is separate.

## Diagnostic detour

An initial comparison of normal Fuse audio against trace reconstruction
gave a misleading -6.55-dB fitted residual because the normal audio clock
was assumed exact. Local Fuse sound-source inspection and FMF chunk counts
identified the Blip_Buffer fixed-point clock factor: 815/65536 at the selected
44100-Hz setting, approximately 44108.33 samples per emulated second. A
diagnostic-only clock correction plus stationary transfer/delay fit raised
that residual to 27.66 dB; this is **not** source SNR or a release metric.
No correction or fitted filter is applied to the delivered WAV, disk or
acceptance scores. Script snapshots/reports are retained in `diagnostics/`;
their `.tmp` paths describe the original investigative run. Neither the
external emulator nor its settings were modified. This constant small clock
offset does not explain the encoder's periodic boundary-error bursts.

The first archived-trace comparison rejected abbreviated Fuse `com`/`pr`
commands while extracting event widths. Adding those aliases fixes that
diagnostic parser; the successful comparison uses the entire original trace.

## Reproduction

Use project Python dependencies and put `audiobook-beeper` and `toolkit` on
PYTHONPATH. Start from the repository root:

```powershell
python audiobook-beeper/experiments/ima-3bit-overlap/reproduce.py --reference audiobook-beeper/experiments/ima-3bit-direct --output build/overlap --fuse "path/to/fuse.exe" --ffmpeg "path/to/ffmpeg.exe"
python audiobook-beeper/experiments/ima-3bit-overlap/compare.py --directory build/overlap
python -m unittest audiobook-beeper/test_ima_lookahead.py audiobook-beeper/test_ima3_series.py -v
python audiobook-beeper/experiments/ima-3bit-overlap/audit.py
```

The first command performs encoding, complete looping qualification, final
disk assembly, complete sequential verification and normal sound capture.
The comparison checks source identity, boundary-error reduction, final SNR
and byte-identical player/table binaries against the archived baseline.
Eight unit tests also pass, including exact rolling state against an
exhaustive four-sample horizon, invalid commit sizes, a synthetic boundary
burst and the existing five disk planning/CLI cases. For arbitrary input,
run `convert_ima3_audio.py` normally; no new user option is required.
The final command checks the checked-in archive and release against
`artifact-hashes.json`; it does not repeat emulator execution.
