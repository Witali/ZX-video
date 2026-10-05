# Full IMA4 disk: reported vibration

2026-10-05. The user identifies `ZX-audiobook-IMA4-full-disk.trd` specifically,
SHA256 `a7e4fb4f289b036b2f84e2032938894767875db3b1e70fbe19d79780af106aa7`.
This investigation records **all five parts** at 100% speed in installed
Program Files Fuse 1.9.0, Spectrum 128/Beta Disk, 44.1-kHz/16-bit sound.
Sparse ready/exit markers observe all transitions and END OF AUDIO. WASAPI
captures the Realtek speaker endpoint at 48 kHz; no microphone or saved
Windows/Fuse settings are used or changed. The complete run takes 237.657 s
including loading and capture finalization; capture has no discontinuity
warnings. This is a new ordinary playback/endpoint check, not a replacement
for the earlier complete bit/state verification.

## What is reproducible

The previously authenticated complete pulse output contains **cyclic error
power tied to the Spectrum field**, whose exact modeled frequency is
3546900/70908 = **50.021154 Hz**. In 128 phase bins per field:

| Part | Error power max/min | Correlation of early/late power profiles | Endpoint delay range, ms |
| --- | ---: | ---: | ---: |
| 1 | 2.801 | 0.872 | 0.0417 |
| 2 | 4.259 | 0.890 | 0.0208 |
| 3 | 4.886 | 0.925 | 0.0208 |
| 4 | 3.803 | 0.853 | 0.0417 |
| 5 | 4.682 | 0.843 | 0.0417 |

The repeatable profile is evidence of periodically varying reconstruction
error, not proof of an equivalent voice-pitch excursion. Strong error-spectrum
bins include about 3.85, 3.90, 4.15 and 4.20 kHz, separated by approximately
the field rate. ULA-dependent pulse holds and a table using average weights
are consistent with this pattern. The specific perceptual symptom cannot be
identified solely from these statistics.

A separate small-signal fit estimates only 0.032–0.252% coherent voice AM and
0.455–1.605 microseconds of coherent delay amplitude at the exact field rate.
Removing those fitted terms reduces error power by only 0.00014–0.00128 dB.
Thus a strong simple 50-Hz voice modulation is not supported by this test;
cyclic **noise/distortion** is a better current explanation. Nonstationary
or faster effects are not excluded. Known injected 2% AM /20-us delay and
a constant-gain/delay negative control validate the estimator numerically.

The endpoint-vs-internal comparison uses 20-ms speech windows, local integer
delay and diagnostic gain fits. Accepted-window delays vary by only 1–2
48-kHz samples, with no large persistent slip. This does not prove perfect
host transport or absence of faster artifacts; the endpoint also changes
frequency balance. Do not describe it as proof that Windows is uninvolved.

The source remains quiet relative to the PDM error: total reconstruction SNR
is roughly 10.33–13.53 dB. Values recalculated from archived PCM16 WAVs differ
from the original float64 scores by less than 0.0003 dB. The earlier conclusion
about lost speech conditioning remains relevant, but is not a complete flutter
fix. The user's subsequent request explicitly authorizes normalization and
gentle dynamic compression as the next bounded change.

## Evidence and replay

- [Complete diagnostics](analysis.json), including all 20-ms accepted windows.
- [First eight seconds from the speaker endpoint](speaker-first8.wav).
- [Same interval from Fuse's internal sound generator](internal-first8.wav).
- `capture/capture.fmf.gz`: complete internal audio and movie markers.
- `capture/loopback.wav.gz`: losslessly compressed complete PCM16 endpoint
  recording. Original float32 endpoint samples remain in the local build area;
  this analysis explicitly uses the PCM16 capture, not those float samples.
- `capture/report.json`, `stdout.txt`, `debugger.txt`: settings, tools, timing
  markers, no-warning capture status. The manifest authenticates retained files.

Listening files retain their original recorded level and have no corrective
filter, time stretch, or fitted gain. Replaying endpoint audio traverses the
output chain again. It is not a microphone measurement of a physical speaker.

With the existing project packages and local `.tmp/host-audio-packages`
SoundCard installation on PYTHONPATH, from the worktree root:

```powershell
python audiobook-beeper/experiments/ima4-flutter/record.py --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --disk ZX-audiobook-IMA4-full-disk.trd --output .tmp/flutter-capture
python audiobook-beeper/experiments/ima4-flutter/analyze.py --capture audiobook-beeper/experiments/ima4-flutter/capture --output .tmp/flutter-replay --ffmpeg C:/Tools/ffmpeg.exe
```

The recorder is intentionally pinned to this exact disk hash and its known
addresses. Keep other applications silent during loopback capture. Archived
replay checks every original input against the full-disk artifact manifest
and requires all five ordered ready/exit pairs and the terminal marker.

The initial recording attempt lacked the local SoundCard path and stopped
before launching Fuse. Adding the already installed package resolved it. An
exploratory SciPy spectrum command likewise lacked SciPy; the final analyzer
uses NumPy only. Neither failed command produced valid measurement evidence.

No player, disk, codec or timing changes in this investigation. Ordinary
423 T/sample and page/bank extras 14/140 T remain unchanged, all deltas 0.
No physical-hardware test and no claim that the reported vibration is fixed.
