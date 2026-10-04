# Sequential-disk experiment, 2026-10-04

Objective: default to one TRD, optionally retain the entire input on multiple
TRDs, and load/play consecutive full-RAM parts without altering the PDM hot
path. See [usage and timing](../../IMA3_SERIES.md). This is a complete Fuse
verification of the stated fixtures, not a conversion of the full audiobook.

| Case | Executed scope | Result |
| --- | --- | --- |
| `reload` | Two copies of the unchanged 186880-sample audiobook reference; every native/Fuse output through EOF | 5980094 live bits; 20.161979 /20.161096 dB; about -0.27172% speed; automatic pause 19.798231 s |
| `swap` | Two short parts on disk 1, one on disk 2; both cold boots, actual predecessor RAM continuation, wrong disk | Four complete part executions, 1032060 Fuse bits; 21.007942..21.011251 dB; wrong disk rejected before audio |
| `capacity` | Original speech followed by synthetic silence, 251888 prepared samples, all seven audio banks | 4030175 native/Fuse bits; RAM guards pass; zero reads during PDM; cold ready 28.608176 s; -0.271059% speed |
| `automatic-stereo` | Ordinary 2-s stereo PCM24 input through the default CLI, preparation, beam search and final disk | One TRD, all 16000 source samples retained; final disk 20.978697 dB; -0.265528% speed |
| `automatic-single` | Silent ordinary WAV through the final default CLI | One `audio.trd`; all 8000 source samples retained; maximum capacity reported as 251888; SNR correctly not applicable |
| `automatic-all` | Same silent WAV with explicit all mode | One numbered `audio-0001.trd`; all source samples retained; full final verification |

The capacity fixture deliberately does not re-encode the added silence. Its
measured 18.563389-dB total SNR is below target; it proves full-memory loading
and execution, not a quality-qualified longer recording. The generic
converter retains its per-input search and final actual-disk quality gate.
The original source is fixed; the filter and explicit 8-kHz clock are not
fitted to improve scores. Same-volume and swap loading pauses remain audible.

`ZX-audiobook-IMA3-sequential-test.trd` in the repository root is the reload
fixture: **the same 23.36-s excerpt twice**, with loading between them, then
`END OF AUDIO`. SHA-256:
`577d6691cada6e1b0b953a6ae96944a21db952e3424e75e925ed77360bb313aa`.
`final-layout/comparison.json` confirms the final zero-extra-RAM placement
produces exactly this already executed binary disk. The earlier reload/swap
metadata reserved an unnecessary extra 256 bytes; changing only that unused
reservation does not change these short-part disk bytes. Full-capacity
evidence uses the final 13312-byte reservation.

## Development findings retained

- The first controller assembly rejected string `DEFB` operands and did not
  emit trailing `DS` padding. Use `DEFM`, and end the padded image with a byte.
- The first trace parser treated Fuse's unsigned hexadecimal negative event
  markers as pulse data. Decode markers as signed while keeping RAM payloads
  unsigned, and accept Windows CR line endings. The complete captured trace
  was reanalysed after fixing the parser; no partial trace passed.
- Exact timestamp reuse failed by three T-states at the first ULA contention
  region because loading changes HALT/ROM-IRQ entry alignment. The final
  verifier bounds that difference and recomputes quality from every actual
  pulse. Observed reference deltas were -3..0 and -1..0 T; no waveform-quality
  equivalence was claimed from bits alone.
- `superseded-capacity` preserves the 251200-sample /13568-byte-reservation
  attempt: it passed complete native/Fuse execution but used 256 bytes more
  than necessary. The assembled exit is only 57 bytes, fitting the existing
  64-byte tail padding. The final 251888-sample fixture was executed afresh.

## Reproduction and evidence

Set PYTHONPATH to `audiobook-beeper` and `toolkit`, then:

```powershell
python audiobook-beeper/test_ima3_series.py
python audiobook-beeper/experiments/ima-3bit-series/reproduce.py reload --output build/reload --fuse "path/to/fuse.exe" --ffmpeg "path/to/ffmpeg.exe"
python audiobook-beeper/experiments/ima-3bit-series/reproduce.py swap --output build/swap --fuse "path/to/fuse.exe" --ffmpeg "path/to/ffmpeg.exe"
python audiobook-beeper/experiments/ima-3bit-series/reproduce.py capacity --output build/capacity --fuse "path/to/fuse.exe" --ffmpeg "path/to/ffmpeg.exe"
```

The source references already live in `ima-3bit-direct`. The fixture script
rebuilds fresh metadata with local paths. Saved metadata contains historical
absolute build paths and is not meant to be executed after relocation.
`producer-source` holds the final source snapshot; original per-run manifests
retain the source hashes actually used by the earlier CLI trials.

Complete compact raw Fuse traces, debugger commands, terminal RAM, native
reports, assembled controller/player images and final-disk waveform WAVs are
saved. Swap continuation uses actual captured banks 5/2/7 and poisons the
remaining banks; it resumes after Space has been accepted. Physical drive
swapping and the real keyboard have not been tested. The captured prompt
bitmap in `inputs/ima3-swap-screen.png` was visually inspected.

`artifact-hashes.json` authenticates evidence bytes. The final
`completion-audit.json` records coverage and the file-hash check. Normal
two-loop preview mode also reproduces the prior compact disk byte for byte;
no existing release disk is replaced.
