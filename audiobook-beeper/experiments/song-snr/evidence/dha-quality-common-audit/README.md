# Common-model DHA quality completion audit

Audit date: 2026-10-20. This preserves the completed quality jobs and their
terminal-exit provenance. It introduces no new codec or audio experiment.
The nine original `dha-quality-common/{source}` folders remain byte-exact;
no encoder, filter, scorer or native player was rerun for this audit.

[report.json](report.json) authenticates nine quality manifests, their 36
artifacts, every source/IMA/container/decoded-WAV identity and all 1,195,520
source samples. All DHAF header/frame CRCs, frame/sample counts and every
PCM16 fallback sample are independently rechecked against the original
source and decoded output. The nine copied manifests retain the original
artifact identities. The exact score producer is saved under `sources/`.

`execution/` preserves the pre-run song hashes, aggregate execution record
and each of the eight remaining jobs' original stdout, stderr and terminal
exit JSON. All eight exits are zero, stderr is empty, and total recorded
execution time is 18.686 seconds. Their original records contain no explicit
execution timestamp; the audit date does not assign one retrospectively.
Historical absolute command paths remain unchanged in those records.

The song's five pre-existing files, including its manifest, match the hashes
captured before the other eight jobs. The verification script resolves the
historical paths by filename, so temporary folders and the original checkout
location are not needed for later verification.

All scores use the complete original uniform-8-kHz source, unchanged filter
and fixed 100-ms edges, with no fitted level, delay or clock. These are ideal
multilevel-DAC scores; they do not include a one-bit adapter or Spectrum
transport. The model is the common speech/Entertainer-trained model, hash
`199a17a9967bfbb941099039f32a47192af8933faf37cf015047abb51bfb9a7b`.

| Source | DHA / IMA bytes | DHA fallback / all frames | DHA / IMA filtered SNR dB |
| --- | ---: | ---: | ---: |
| Song | 1,411,268 / 360,192 | 171 / 176 | 37.925 / 22.149 |
| Silence | 2,892 / 8,448 | 0 / 5 | undefined / undefined |
| Quiet 440 Hz | 3,149 / 8,448 | 0 / 5 | 6.539 / 30.359 |
| Loud 3 kHz | 34,536 / 8,448 | 4 / 5 | exact / 19.470 |
| Steps | 34,536 / 8,448 | 4 / 5 | exact / -0.257 |
| Quiet 997 Hz | 2,894 / 8,448 | 0 / 5 | 0.001 / 23.834 |
| Multitone | 34,536 / 8,448 | 4 / 5 | exact / 21.245 |
| Speech | 211,803 / 93,440 | 24 / 46 | 23.321 / 25.592 |
| Entertainer | 37,817 / 93,440 | 1 / 46 | 16.362 / 27.545 |

`exact` means zero filtered error with nonzero signal, mathematically infinite
SNR, and bit-exact unfiltered samples after the fixed edges. The scorer
serializes that result as JSON `null`; it must not be confused with silence,
where both reference signal and error are zero and SNR is undefined.

The song score includes 699,904 raw fallback samples out of 720,384. All
fallback bytes are charged, so the high score is not evidence of efficient
predictive compression. Quiet tones, speech and Entertainer regress against
the same frozen IMA baseline. No universal quality or new player is accepted.

Recheck from this folder using only the Python standard library:

```powershell
python -B verify.py
```

An alternate checkout can be supplied with `--evidence-root PATH`, pointing
to its `audiobook-beeper/experiments/song-snr/evidence` directory. Do not pass
`--capture-from` again: it is a one-time import of existing temporary logs,
and refuses to overwrite retained files. `manifest.json` covers every audit
artifact except itself. The immutable nine score folders are read only.
