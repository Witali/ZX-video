# Best measured song disk snapshot

2026-10-14. The user requested a playable disk with the best parameters
already achieved. `ZX-music-Sea-Foam-SNR20-RAM-auto.trd` contains the complete
main song from the sea-foam cartoon, the existing title screen, loading
progress and automatic RAM detection. This is a separately named snapshot
of the measured half-joint variant; the previous root disk remains intact.

The automatic C conversion uses the same source-independent settings as
the previous complete run: mono PCM at 8000 Hz, continuous IMA4, PCM beam32
with64-sample blocks, waveform beam32,128-sample horizon,64-sample commits,
regularization0.1 and the instruction-derived `duration_zero_half_recent`
model (beta0.5, recent extent0.5, PCM origin0). No experimental idle-word,
idle-pair or centered-quantizer override is enabled. Original Python
encoders remain available as the executable reference.

The full prepared source has720,384 samples (90 seconds of main content
plus its original silent padding), producing360,192 packed bytes. The
disk uses the ordinary RAM area first and then paged banks. Pentagon512
and1024 hold the whole song and have no disk reads or reload pauses during
audio. The128-KiB and Scorpion256 fallback require refills; this snapshot
does not qualify their waveform quality against the Pentagon measurements.

The fixed original-clock, unchanged-filter score is **20.250315887 dB SNR**
on both independently cold-booted complete Pentagon runs, with no fitted
gain, delay or source clock. Every11,526,111 source pulse and720,382 decoded
predictor/index samples was verified through EOF. The title appeared before
audio and progress was verified. Native and actual intervals agree; the
player hot path has not changed (ordinary423/449 T, page extra14 T, bank
extra243/267 T; delta0 T). The largest resident hold is277 T/77.288 us.
TR-DOS ROM and physical-disk loading time are separate from those counts.

The freshly generated complete TRD must equal the authenticated previous
disk byte for byte, SHA256
`ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074`.
`delivery.json` records this check, copied-file identities and reused full
execution reports. `generated/report.json` records the new automatic
conversion and its external elapsed time. Full execution evidence is in
`../clock-joint/sea_foam/verification/`; no new unchanged Fuse run is claimed.

The broader artifact acceptance remains false: residual tonal noise and
corpus/modulation regressions still need research. Neither22 dB nor absence
of audible flutter/background on physical hardware has been established.
The user-requested disk snapshot does not complete the saved quality goal.

Reproduce in a fresh output directory:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/automatic-conversion/benchmark.py `
  --output .tmp/reproduce-achieved-disk
```

This runs the public `convert_snr_audio.py` program on the authenticated
entire prepared song with its original cover and checks the resulting TRD
against the previously fully played bytes. C performs the slow encoding;
the frontend also assembles the bootable disk and saves source, packed audio,
model parameters, producer snapshots and unchanged-filter measurements.
