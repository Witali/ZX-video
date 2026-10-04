# Shared IMA3 / IMA4 quality search

2026-10-04. The user requested better quality for both algorithms after the
comparison of their PC encoders and Spectrum players. This study changes
the PC search and candidate selection. It does not change Z80 instructions,
PDM feedback, table layout, or the IMA decoding recurrence.

**Paused at the user's explicit request on 2026-10-04.** Code and completed
evidence are saved; this is not a completed four-case release milestone.
See [CHECKPOINT.md](CHECKPOINT.md) before resuming. No background work remains.

## Changes

- Both converters default to `--quality best`. Finish a bounded search even
  when the pilot already meets the requested SNR. Preserve earlier verified
  candidates and select by the worse of two complete measured loops.
- IMA3 retains the strongest previous search (width 1024, horizon 256,
  commit 64, PCM prior .03) and also searches with a weaker .003 prior.
  This lets the filtered PDM waveform contribute more to the choice of codes.
- IMA4 now uses the same waveform-aware objective and overlapping commits,
  considering all 16 IMA codes. Its first two searches use width 256 /prior
  .1 and width 512 /prior .03, both with horizon 128 and commit 64.
- IMA4 repeats the winning waveform search once on that candidate's new
  measured clock. Changing codes changes data-dependent ULA waits; the
  archived pilot clock alone cannot certify the new output. Recalibrate and
  execute the refined disk, retaining the earlier winner if it is better.
- Host scores only choose up to two candidates for complete disk execution.
  `--attempts 3` adds an optional third host candidate. This is the best of
  the verified candidates, not an exhaustive optimum over possible streams.
- `--quality balanced` retains the previous workflow. Both best modes mark
  a completed below-target result as a preview and return Python exit code 2.
  Silence has no meaningful SNR and does not trigger unnecessary searches.

Spectrum still reads packed IMA3 or IMA4 into RAM, decodes directly to PDM,
and needs no intermediate PCM/PDM buffer or IMA3-to-IMA4 conversion. All
additional work happens on the PC. The optional exact native search kernel
from the [encoder-speed study](../waveform-speed/README.md) remains in use.

## Measurement scope

The four full comparisons keep 186880 identical prepared samples per case:
23.344 seconds of audio and 128 silent samples. Music uses the unchanged
[normalized Entertainer reference](../entertainer-normalized/README.md).
Speech uses the [accepted IMA3 overlap reference](../ima-3bit-overlap/README.md)
and the previous [IMA4 waveform study](../ima-waveform/README.md).
The IMA4 speech baseline was already manually optimized; it is not a plain
greedy encoder. Within each content pair, the exact PCM8 source hashes match.

SNR is the lower of two complete Fuse port-trace measurements against the
unchanged PCM8 /8-kHz reference, filtered with
`highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2`. The same fixed 100-ms
edge exclusions apply before and after. No fitted gain, delay or time
stretch is allowed. These numbers describe the prepared mono reference and
comparison filter, not fidelity to the original full-band recording.

Actual Fuse sound-generator WAVs are also retained as `result-preview.wav`.
They are separate from the filtered trace used for scoring. They are not
microphone or physical sound-card recordings, nor new user listening
acceptance. Boundary-energy comparisons in each `comparison.json` are
diagnostics, not a universal test for absence of audible flutter.

## Results

See [results.json](results.json) for the audited before/after measurements,
disk hashes, verified bit counts and speed errors. All published images
are additional independently bootable, looping listening previews; the
previous accepted images and public YouTube-linked filename are preserved.

| Case | Previous SNR | Saved SNR | Coverage at pause |
| --- | ---: | ---: | --- |
| Entertainer IMA3 | 19.031203 dB | 19.165090 dB | Complete two-loop checks and normal-speed recording |
| Entertainer IMA4 | 17.237725 dB | 19.897558 dB | Complete checks and recording, including refinement |
| Speech IMA4 | 21.010690 dB | 22.164431 dB | Complete initial search/checks/recording; final refinement interrupted |
| Speech IMA3 | 20.436321 dB | 20.659504 dB | One candidate fully trace-verified; comparison and recording unfinished |

Music remains below the 20-dB goal and is labeled as a listening preview.
The saved root images are
[music IMA3](../../../ZX-music-Entertainer-quality-IMA3.trd),
[music IMA4](../../../ZX-music-Entertainer-quality-IMA4.trd), and
[speech IMA4](../../../ZX-audiobook-quality-IMA4.trd).
The new speech IMA3 candidate is preserved under `paused/` with its evidence;
it has not been promoted to a root release filename.

## Rejected and partial attempts

The [prefix probes](diagnostics/probe/results.json) and
[speech4 retry](diagnostics/probe-speech4/results.json) compare six searches
on 8192 active samples plus the silent guard. More retained filter-history
bins (16 or 64) made the tested search slower without improving those
prefix scores. A stronger PCM prior helped four-bit music but not the
three-bit references; use format-specific plans instead of assuming that
more width or less regularization always helps. Prefix scores are not
full-disk results.

The first probe stopped on an archived speech4 WAV that was still an LFS
pointer. Materialize the existing objects with `git lfs checkout` and rerun
that case; the first 18 completed prefix results remain valid. No source
audio was changed.

The tools-directory SDL Fuse repeatedly timed out after 180 seconds in the
first debugger phase probe. Program Files Fuse completed a probe of the
same disk. Keep both tool hashes and failed logs; reuse only authenticated
host-search outputs and rerun all disk checks with Program Files Fuse.
The observed timeout's underlying cause is unresolved; it is not evidence
of broken playback. The control phase probe alone is not a release check.

A restricted [guard experiment](diagnostics/guard-probe.json) tried to close
the PDM state to 16 using the last 16 silent codes, only codes 0/2/8/10,
and predictors within +/-32. It did not find a closure for either IMA3
case or four-bit music. Speech4 already closed with zero codes. Do not adopt
this change or infer that a broader closure algorithm is impossible.

The one-second CLI IMA4 refinement is worse than its first waveform result;
the converter correctly retains the earlier verified candidate. This is
saved alongside the full-case refinements, including candidates that lose.
The first archive diagnostic used uint32 arithmetic for sample-time scaling
and rejected nonmonotonic times. Convert to int64 before calculating those
diagnostics. This affected no encoder, disk, or SNR verification.

## Validation and cycle accounting

Each of the three saved root disks passes a cold Spectrum 128 + Beta Disk boot, two
complete native and Fuse loops, every predictor/index and PDM-bit comparison,
memory guards, paging and uncontended output-port checks, loading-message
checks, and zero disk reads during playback. FFmpeg independently checks
the standard IMA recurrence. A second full loop must repeat its exact field
phase; any cold first-loop transient is limited to and reported within 3 T.
Normal-speed Fuse recordings cover two wraps and verify paging again.

Ordinary IMA3 decoding remains **427.375 T/sample**, IMA4 **423 T/sample**;
each delta is **0 T**. Both retain page/bank extras **+14/+140 T**. Native
cycle totals include stream-specific silent phase filler, so those totals
can differ without a changed hot path. Per-case `comparison.json` records
the old/new totals; `fuse.json` separately records ULA waits and startup
sector reads. ROM execution and disk loading are not folded into CPU costs.
Physical Spectrum hardware has not been tested.

The [final test log](diagnostics/logs/build-quality-tests-final.log) contains
14 passing tests: five quality-selection contracts and nine existing series
tests. The actual short CLI runs cover default IMA3 single-volume playback
through EOF and IMA4 waveform search plus a losing refinement. Both completed
their correctness/speed checks but missed 20 dB, so preview status is correct.
The PowerShell runner reports generic nonzero status for Python's explicit
quality exit; the CLI contract tests check code 2 directly.

## Reproduction and provenance

Install/use the existing Python dependencies and put `audiobook-beeper` and
`toolkit` on PYTHONPATH. The converter commands in
[CONVERTER.md](../../CONVERTER.md) automatically perform search, calibration
and verification. For these exact baseline-controlled comparisons:

```powershell
python audiobook-beeper/experiments/ima-quality/probe.py --output build/probes --ffmpeg path/to/ffmpeg.exe
python audiobook-beeper/experiments/ima-quality/run.py --case music3 --attempts 2 --output build/music3 --ffmpeg path/to/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/experiments/ima-quality/run.py --case music4 --attempts 2 --output build/music4 --ffmpeg path/to/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/experiments/ima-quality/run.py --case music4 --attempts 1 --clock build/music4/disk-encode-1 --output build/music4-refined --ffmpeg path/to/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

Use `speech3`/`speech4` for speech. The speech4 refinement starts from
`disk-encode-2`, its measured winner, and repeats that search's settings.
The generic IMA4 converter performs this selection automatically.
`--reuse-search` authenticates input/tool/critical-producer hashes and saved
host stages, then **reruns** all disk checks. It never reuses another tool's
player verification. `--resume` requires unchanged run identity and sources.

[archive.py](archive.py) copies selected disks and audits complete evidence;
[collect.py](collect.py) retains supporting diagnostics and final sources.
[artifact-hashes.json](artifact-hashes.json) authenticates the saved archive.
Original invocation identities, candidate snapshots and the final source
snapshot have distinct scopes: orchestration evolved while independent
jobs ran, while the encoder core, player, calibration and verifier routines
were unchanged. History directories retain initial IMA4 results superseded
by refinement. Per-host reports retain search times; concurrent runs are
not a controlled encoding-speed benchmark.
