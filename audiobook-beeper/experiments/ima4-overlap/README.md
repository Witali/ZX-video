# IMA4 overlapping PDM search: completed follow-up, 2026-10-05

The user chooses IMA3 for duration and IMA4 for quality, requesting the
automatic PDM search with overlapping windows in IMA4. Repository inspection
finds that the transfer already exists in `--codec ima4 --quality best`.
This follow-up completes the previously interrupted speech4 refinement,
adds a matched no-overlap control and keeps the best actual result. It does
not resume the other paused quality-study cases or modify IMA3 defaults.

**Decision:** retain the earlier verified IMA4 overlap result. Neither new
candidate improves it. The new root listening image is byte-identical to
that fallback; it is not falsely presented as a newly improved encoding.

## What the automatic encoder does

The PC searches all 16 IMA4 nibbles against the filtered PDM waveform.
It searches 128 source samples (16 ms), commits only the first64 (8 ms),
then moves forward64 and reconsiders the remaining samples with future
context. Predictor, step index, PDM state and filter state carry through
the committed prefix. This avoids forcing every search-window endpoint
to be a final audio decision. The existing second search uses beam512
and PCM-prior weight0.03. The first uses beam256 /weight0.1; a third is
optional. Complete real executions, not host estimates, select the result.

```powershell
python audiobook-beeper/convert_audio.py "input.m4a" --codec ima4 --quality best --attempts 2 --output "build/my-ima4" --ffmpeg "path/to/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

No new Z80 instruction, table, buffer, disk header or resident expansion is
needed. Ordinary IMA4 remains423 T/sample, delta0; page/bank additions remain
14/140 T. Changed streams can still change **ULA memory waits** and hence
the actual output clock. The PC must recalibrate and measure every candidate.
IMA3 remains the default and its player/data format are untouched.

## Controlled comparison

Use the unchanged186880-sample speech reference (23.344 s plus128 silent
samples), PCM8/8 kHz, SHA256
`ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
Both new searches use the previously verified winner's exact measured
PDM timeline, the same compensated PCM prior, beam512, horizon128,
regularization0.03, all16 nibbles and the same native search kernel.
Only the committed prefix differs:64 with overlap,128 without it.

| Candidate | Host estimate on previous clock | Actual legacy measurement | Stable actual measurement |
| --- | ---: | ---: | ---: |
| Previous verified IMA4, already using overlap | — |22.164431 dB |**22.174535 dB** |
| New refinement, commit64 |22.552121 dB |8.126727 dB |8.126934 dB |
| Matched control, commit128 |22.319142 dB |20.922286 dB |20.928543 dB |

Each actual score is the lower of two complete loops. Legacy measurement
uses the existing192-kHz/f32 pipeline, preserving the original comparison.
The separate stable audit integrates actual OUT holds at768 kHz and uses
float64 for the same70-Hz high-pass plus two4500-Hz two-pole low-passes.
The reference remains fixed at8000 Hz; no fitted gain, delay or time stretch.
Both exclude100 ms at each end. Do not compare these with PC-only128-kHz
sigma-delta scores as if they were the same clock or modulator.

The refined stream passes bit/decoder/timing correctness but loses quality
on its own timeline: it runs at8003.385 samples/s (+0.042307%), whereas the
previous/control loops run at7996.538 samples/s (about-0.04327%). These
average speeds are within the allowed2%, but that does not ensure waveform
alignment with the clock used to optimize codes. The changed measured
timeline, including data-dependent waits, invalidates its22.55-dB host
estimate. A predicted improvement alone must never promote a new TRD.

This matched pair does **not** prove that overlap always improves real
output: its new overlap candidate loses to the new no-overlap candidate.
The earlier verified overlap candidate remains better than both. Preserve
that bounded fallback and the failed refinement. No broader optimum or
absence of audible flutter is claimed. Boundary-energy diagnostics for64
and128 samples are saved separately, not used as a universal quality gate.

## Verification and reuse

- Both new candidates pass native and cold Program Files Fuse1.9.0
  Spectrum128 + Beta128 execution for two complete loops: every IMA
  predictor/index and PDM bit, memory guards, paging, loading UI and zero
  runtime disk reads. Native counts include source-specific silent filler;
  it is separate from the unchanged423-T ordinary kernel.
- The new overlap verifies5980181 outputs; the control5985269. Their
  cold/repeat phase deltas are[2,0] and[-2,0] T respectively. All samples
  and complete loops are covered, not only a prefix.
- The selected fallback retains its existing complete native/Fuse evidence
  and gets a new normal-speed sound-generator recording. It is not a
  physical sound-card capture or real-Spectrum test.
- Five shared quality-selection tests pass: real IMA alphabet, overlapping
  command, automatic bounded search, target handling and measured fallback
  selection. Existing defaults already implement the requested transfer;
  production encoder/player files are unchanged by this follow-up.

The saved overlap encoding finished before the earlier pause; its disk
verification had not. Its source and full clock hashes match exactly and
all stage artifact hashes pass. Later optional SD2 support changed some
producer hashes, so **the old resume identity was not bypassed**. The new
runner imports it as a frozen candidate with its original identity, checks
the unchanged search AST/native kernel and exact legacy tables, rebuilds
the disk byte-for-byte, and performs new complete native/Fuse verification.
No interrupted trace is treated as a completed check. The no-overlap host
search is new (128.531 seconds of search on this machine); the completed
overlap search is reused, not redundantly recomputed.

## Artifacts and reproduction

The [final report](evidence/report.json), [reuse audit](evidence/cached-input-audit.json),
[boundary diagnostic](evidence/boundary-diagnostics.json), full cold traces,
assembly, source snapshots and rejected streams are retained.
The [selected TRD](../../../ZX-audiobook-IMA4-PDM-search-test.trd) SHA256 is
`da533b71755fd3d33f195ff49ce9f2c8a9afbf4f285787d6eae31aa0daa0305c`.
The chosen [Fuse WAV](evidence/recording/fuse-preview.wav) is the real
sound-generator recording; stable filtered output/reference WAVs use an
equal fixed0.5 listening gain and are separate measurement artifacts.

With the existing project dependencies and `audiobook-beeper` /`toolkit`
on PYTHONPATH:

```powershell
python audiobook-beeper/experiments/ima4-overlap/run.py --output build/ima4-overlap-repro --ffmpeg "path/to/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/experiments/ima4-overlap/archive.py --verify
```

The runner checks input/tool/producer identity, authenticates completed
stages and preserves interrupted disk work. `--stage overlap`, `control`
and `finish` allow staged reproduction. Its output directory must belong
to this same experiment. No merge/push is part of the user request.
