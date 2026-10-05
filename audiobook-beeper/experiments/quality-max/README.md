# Bounded quality search for all active audio codecs

2026-10-05. The user requests maximum quality for IMA3, IMA4 and mu-law.
Complete the pending IMA3 comparison and a third IMA search, then add a
waveform-aware PC encoder for the existing mu-law player. Keep all resident
capacities, stream formats, modulation kernels and verified fallbacks.
The subsequent request for **128-kHz mu-law** is a separate next milestone;
the mu-law disks in this archive still run at approximately64 kHz.

## Complete results

All scores below use a fixed8-kHz source, actual full Fuse OUT timelines,
768-kHz integration, float64 filtering (70-Hz high-pass and two4500-Hz
two-pole low-pass stages),100-ms edge exclusions and no fitted delay, gain
or time stretch. Report the worse of two complete loops. IMA cases share
186880 PCM8 samples; mu-law uses its121088-sample PCM16 prefix, so its
number is not a like-for-like codec ranking against the longer IMA input.

| Codec / candidate | Minimum SNR, dB | Decision |
| --- | ---: | --- |
| IMA3 previous accepted | 20.431992 | Retained control |
| IMA3 completed first paused candidate | 20.577603 | Valid, lower score |
| IMA3 completed second paused candidate | **20.655388** | Select and record |
| IMA3 new third, prior.1 | 20.375154 | Reject for quality |
| IMA4 prior overlap winner | **22.174535** | Retain and record |
| IMA4 new horizon256 /prior.003 | 9.849028 | Reject; host estimate21.282149 did not survive its own clock |
| Mu-law ordinary control | -3.347765 | Fixed-clock score includes accumulated timing mismatch |
| Mu-law first-clock Lanczos control | 6.533228 | Separate timing-only control |
| Mu-law joint two-clock beam8 | 9.608146 | Valid, lower score |
| Mu-law joint two-clock beam32 | **10.295781** | Select and record |

The original mu-law **9.672027-dB** figure used source samples following
the actual output boundaries. It is preserved as a separately named
diagnostic, **not** the baseline for the fixed-clock improvement above.
The selected mu-law stream's modulator-only diagnostic is12.308472 dB;
the older control's is9.677665 dB. These have different decoded control
signals. Do not add their differences to a codec-only SNR or claim30 dB.

The IMA3 selected disk is the previously trace-qualified second candidate,
authenticated by its stage hashes and byte-identical current rebuild. Its
normal-speed recording and stable rescoring now complete the paused case.
Original legacy SNR values remain20.436321 ->20.659504 dB. IMA4 retains
the byte-identical previous winner; no IMA4 quality gain is claimed.

## Algorithm changes

Both IMA `best` profiles now default to three searches and execute **all**
requested candidates. A low host ranking is not sufficient to reject a
stream before its own clock is known. `--attempts 1/2` and the earlier
`--quality balanced` remain available. IMA3 stays the default codec.

Mu-law `best` retains ordinary G.711 and timing-compensated fallbacks.
It searches all256 bytes with overlapping windows, an analytic six-state
filter and both measured loop clocks. The control prior uses the actual
hold centers; using the unretimed PCM prior was a failed initial prototype.
Only the committed prefix advances the filter. Small guard levels close
the exact accumulator state to32768 without changing Spectrum instructions.
The byte stream remains valid raw G.711; ordinary decoding returns the
waveform-optimized control signal rather than a nearest-level source copy.

Precomputing every2048-residue x256-code transition accelerates the PC
search. These tables never go on the disk or Spectrum. Native and NumPy
searches match; all transition entries are checked against independent
cumulative arithmetic, and every reachable residue's guard closure is
tested. Search is heuristic and bounded, not proof of a global optimum.

## Failed and limited probes

The initial unretimed-prior, first-clock prototype gave minimum4.897807
and5.618310 dB at beams8/32. Both passed complete executable checks but
are superseded. Short8192-sample PC screens tried priors.003/.03/.1/.3
and beams1/8/32; these are preliminary estimates, not release scores.
Keep their reports and the two frozen old modules in the archive.

The final full mu-law searches take70.359 /287.735 s, while IMA third
searches take744.141 /612.328 s for IMA3/IMA4. These are this machine's
observed search times, not isolated speedup benchmarks: several independent
jobs ran concurrently. The discarded older mu-law beam32 took467.025 s,
but its objective, clock count and implementation also differ.

## Execution and resource evidence

All new streams pass two complete native/cold Program Files Fuse1.9.0
Spectrum128 +Beta128 loops, every output bit and decoder state, full memory
guards, paging, loading UI and no playback disk reads. IMA also checks
independent IMA decoding and exact repeat phase; mu-law uses the unchanged
free-running first-order schedule and jointly optimizes its first two
phases. This does not prove phase invariance over arbitrary later loops.
The three selected images have fresh normal-speed two-loop recordings.

| Kernel | Ordinary T/sample before -> after | Page /bank extras | Selected speed error |
| --- | --- | --- | ---: |
| IMA3 | 427.375 ->427.375, delta0 | 14 /140 T | -0.299133% |
| IMA4 | 423 ->423, delta0 | 14 /140 T | -0.043270% |
| Mu-law | 432 ->432, delta0 | 35 /116 T | +0.185960% |

Counts exclude separately measured ULA, TR-DOS and disk latency. No extra
Z80 tables, PCM/PDM audio buffers or payload bytes are required. The
capacity accounting remains251888 samples for IMA3,186880 for IMA4 and
121088 for mu-law. IMA previews deliberately retain the same comparison
source, rather than silently changing their duration. All disks boot cold.
No physical Spectrum or sound-card-loopback measurement is claimed.

Fifteen unit tests pass (`test_mulaw_waveform`, `test_quality_search`,
`test_mulaw_player`, `test_g711_codec`). A complete one-second ordinary-WAV
conversion through the public `--codec mulaw` CLI also passes every stage,
chooses its measured fallback/candidate automatically, and gives12.837995 dB
with+0.893622% speed error. Its shorter clip is a separate integration test.

## Reproduction and files

Use the project's Python environment and PYTHONPATH for `audiobook-beeper`
and `toolkit`; supply the existing FFmpeg and Program Files Fuse paths.

```powershell
python audiobook-beeper/ima_waveform_encoder.py --input audiobook-beeper/experiments/ima-3bit-overlap/qualified --output build/quality-max/ima3-host --width 1024 --regularization .1 --block-size 256 --commit-size 64 --ima3 --ffmpeg <ffmpeg>
python audiobook-beeper/ima_waveform_encoder.py --input audiobook-beeper/experiments/ima-quality/speech4/selected --output build/quality-max/ima4-host --width 512 --regularization .003 --block-size 256 --commit-size 64 --ffmpeg <ffmpeg>
python audiobook-beeper/experiments/quality-max/run.py --stage ima3 --host build/quality-max/ima3-host --output build/quality-max/ima3 --fuse <fuse> --ffmpeg <ffmpeg>
python audiobook-beeper/experiments/quality-max/run.py --stage ima4 --host build/quality-max/ima4-host --output build/quality-max/ima4 --fuse <fuse> --ffmpeg <ffmpeg>
python audiobook-beeper/experiments/quality-max/run.py --stage mulaw --output build/quality-max/mulaw-joint --fuse <fuse> --ffmpeg <ffmpeg>
python audiobook-beeper/experiments/quality-max/archive.py --verify
```

[Machine-readable results](results.json) and [hash manifest](manifest.json)
cover selected disks, rejected streams, assembly, full traces, recordings,
source snapshots and reports. Root `ZX-audiobook-max-IMA3.trd`,
`ZX-audiobook-max-IMA4.trd` and `ZX-audiobook-max-mulaw.trd` are the selected
previews. Source snapshots are gzip-compressed normalized LF text; the
failed prototype additionally preserves its two changed modules. Old
archives, manifests and the YouTube-linked TRD remain unchanged.
