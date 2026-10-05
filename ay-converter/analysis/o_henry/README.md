# O. Henry speech through the current AY converter

Completed 2026-10-05 against `ec0676d`. This is a bounded listening trial of
the current music preset on the familiar O. Henry recording. No converter
or player algorithm changes: persistent components, held note pitch and
chip-model noise colour fitting remain at 50 Hz, one state every 20 ms.

## Listen

- [Independent Spectrum 128 + Beta Disk TRD](../../../ZX-audiobook-OHenry-AY50-test.trd)
- [Original followed by AY](evidence/comparison/original-then-ay.wav): original
  starts at 0 seconds; after a one-second gap, AY starts at **25 seconds**.
- [Normal-speed Fuse output, two full loops](evidence/release/fuse-preview.wav)
- [Original excerpt](evidence/release/original-preview.wav)
- [Full spectrogram](evidence/comparison/spectrogram-full.png),
  [4..8-second detail](evidence/comparison/spectrogram-4-8s.png),
  [short-window detail](evidence/comparison/spectrogram-attacks-4-8s.png)

The source is the same supplied 1977 O. Henry audiobook used by the earlier
[pitch-aware voice trial](../../../audiobook-ay/PITCH_AWARE_PREVIEW.md).
Take **source seconds [60,84)** directly from its original M4A, not the
prepared beeper PCM8. This is 24 seconds /1200 states, not the entire book.
Full input SHA-256:
`a34f27c44c0df7f817814df2c43eb3c58d2d415e0892434c99dc23b6b2d2e779`.
The [build report](evidence/release/report.json) records the source filename,
complete producer hashes and artifact hashes. The input M4A stays external.

The comparison uses one RMS gain per complete section and common peak
headroom; it does not mix the original into the AY output. It preserves
physical Fuse playback timing. The ordinary emulator recording retains its
original gain. These files are emulator audio, not a physical sound-card or
Spectrum recording. Listening acceptance is still pending.

## Measured result and limits

The [independent state and spectral audit](evidence/comparison/comparison.json)
checks every exported state against packed AY9 and R0..R10, all recorded
artifact/producer hashes, and source identity. There are 488 estimated
component lifetimes with zero channel migrations. Noise is enabled in 1049
of 1200 states: 1023 mixed with tones and 26 noise-only. No active tone is
disabled by noise. The existing 93-candidate noise fit selects R6 1..31 and
shared-volume changes of 0, -1 or -2; it changes 925 noise periods and 978
shared levels relative to this input's heuristic estimate. This is not a
new speech-specific optimization or a comparison against the old voice disk.

Both complete recorded Fuse loops are compared to the original with 20-ms
hops, unpooled 50..8000-Hz bins and one global RMS match. Only the known
clock ratio, `50 * 70908 / 3546900`, maps playback to the source grid. There
is no fitted local time warp or gain. A physical loop lasts 23.989850 seconds.

| Hann window | Loop 1 cosine | Loop 2 cosine | Loop 1 log MAE, dB | Loop 2 log MAE, dB |
| --- | ---: | ---: | ---: | ---: |
| 512 samples /23.22 ms | 0.69129 | 0.69429 | 9.08048 | 9.24588 |
| 2048 samples /92.88 ms | 0.68728 | 0.68603 | 8.81341 | 8.82414 |
| 8192 samples /371.52 ms | 0.75628 | 0.75632 | 8.09250 | 8.08278 |

Visual inspection of the full and detailed spectrograms shows preserved
pauses and parts of the low-frequency contour, but stronger diffuse noise
and missing/altered upper harmonic detail. The music preset's note selection
and pitch holding can also distort speech intonation. Spectral cosine is
not a percentage of intelligible words. Earlier rejected speech experiments
remain historical evidence; this trial does not supersede the accepted
IMA3 beeper speech reference or establish intelligibility.

## Complete disk verification

The [execution proof](evidence/release/verification.json) covers native Z80
and cold-boot Fuse playback of **two complete loops: 2400 fields and 26400
register writes**, all exact, no missed or duplicate fields. The payload
occupies 13200 resident bytes in bank 0 (10800 packed bytes). Fuse reads 52
payload sectors during startup, zero during playback; loading-screen
show/hide checks pass. The TRD uses 96 sectors including BASIC and player.

No player hot path changes: **974 ->974 T ordinary work, delta 0 T**;
1079 T on the first field after restart, also unchanged. Native execution
observes 2399 ordinary fields and one restart field. Counts exclude ULA,
HALT wait, ROM execution and physical disk latency; Fuse separately checks
actual register-write timestamps. Generated title/configuration and binary
hash differ from the longer music fixture. No physical hardware test or new
unit-suite run is claimed; this task exercises the full new data in both
execution verifiers and reuses the converter's existing regression evidence.

Root and archived TRD SHA-256:
`aa2013bab38a3fbffecb97f1069b570d17e9fefa591c075da58c4000b84169d1`.

## Reproduce

Use the converter's documented dependencies plus Matplotlib for these plots.
From the repository root, with the recorded source available:

```powershell
$source = (Get-Content ay-converter/analysis/o_henry/evidence/release/report.json -Raw | ConvertFrom-Json).source
python ay-converter/convert_audio.py $source --output build/o-henry-ay --start 60 --duration 24 --title 'O HENRY - AY VOICE' --profile music --noise-fit chip --ffmpeg 'C:/Tools/ffmpeg.exe' --node 'C:/Program Files/nodejs/node.exe' --fuse 'C:/Program Files (x86)/Fuse/fuse.exe'
python ay-converter/analysis/o_henry/inspect_preview.py --directory build/o-henry-ay --ffmpeg 'C:/Tools/ffmpeg.exe' --output build/o-henry-comparison
```

The build output must be new or empty. Adjust executable/input paths for
the local machine. The inspection helper audits complete execution before
creating the paired listening file and figures; it cannot promote an
unverified model WAV to a verified disk. Decision: retain this unchanged
converter trial for user audition; do not start another tuning experiment
until that listening result supplies the next target.
