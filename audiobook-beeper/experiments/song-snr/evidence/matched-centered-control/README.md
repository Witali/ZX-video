# Complete matched centered-quantizer control: rejected

2026-10-14. One frozen duration_zero table, full extent1, origin0, compact
loader and PCM16 bias512 is used for all nine complete sources. The C search,
committed replay and player reference share the centered semantics. Search
width32, horizon128, commit64 and regularization0.1 remain unchanged. Source
bytes, gain, length, original8000-Hz reference, f64 listening filter and fixed
100-ms edges stay identical. No fitted gain, delay or clock enters SNR.

The fresh whole host corpus takes91.324658 s including preparation, workset
serialization, standalone C, complete rendering and diagnostics. TRD assembly
and emulator execution are separate; no new Fuse run or release is claimed.

| Source | Unfitted SNR, dB |
|---|---:|
| Quiet440 |7.183904 |
| Loud3000 |8.082355 |
| Steps |2.456251 |
| Quiet997 |0.840043 |
| Multitone |17.258909 |
| Speech |22.056546 |
| Entertainer |19.589737 |
| Complete sea-foam song |20.110901 |

Song improves23.196129 dB over the authenticated legacy fixed-clock baseline,
but loses0.139415 dB against half-joint. Speech/Entertainer/quiet tones improve
against half-joint, while four non-silent SNR and five absolute-RMS results
regress. Steps remain7.502533 dB below compensation. The report discloses22 AM,
33 delay and15 coherent-line increases against half-joint;33 modulation
comparisons are inconclusive. Numeric changes are not an audibility threshold
or a proof of extra hum in music.

Silence RMS0.015513939 remains dominated by a3991-Hz line, approximately97%
of spectral error power. The source, packed stream, predictor and index are
all exact digital zero. The centered input stays bin32, while feedback
alternates16/17 and packets6ad5/952a spend223/226 of449 T high. Therefore this
carrier arises from the neutral PDM state cycle, independently of the floor
lookup discontinuity fixed by centering. `neutral-silence-diagnosis.json`
records the complete decoded proof and recurrence.

Reject unconditional quality promotion. Keep the centered C/player option as
tested experimental functionality and preserve this unsuccessful full control.
The separate player evidence covers short native operation and default
compatibility, not these nine actual clocks. Instruction-count baselines stay
423/449 T ordinary,14 T page,243/267 T bank, delta0; ULA/disk/hardware remain
separate. Main and the original Python remain unchanged; the goal stays active.

```powershell
python audiobook-beeper/experiments/song-snr/matched_centered_control.py `
  audiobook-beeper/experiments/song-snr/evidence --output NEW_EMPTY_FOLDER `
  --scratch .tmp/matched-reproduction --cache .tmp --phase host
```

The cache supplies authenticated unscaled comparison arrays, not candidate
encoded data. The driver can regenerate missing comparisons from saved streams.
`report.json` has all measurements and decisions; `artifact-manifest.json`
authenticates the measured outputs, producers, frozen inputs, executable/BLAS,
comparison inputs and exact unchanged default disk. Diagnostic fits are
separate from unfitted SNR and cannot prove universal artifact absence.
