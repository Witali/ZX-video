# Initial audio progress UI: audio passes, loading animation rejected

Date: 2026-10-14. This evidence belongs to the initial optional UI candidate
`55216119144fdb4e574bb3525b496d15c528b6f1a826da39c5070c3f57be9e1d`.
The comparison disk is the previously verified best song disk
`ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074`.
The audio acceptance is complete; UI acceptance is false. The candidate must
not be described as a finished UI release.

## Complete audio evidence

- All four complete native runs verify 11,526,111 source bits and 720,382
  predictor/index observations, with memory guards. Spectrum 128 has three
  explicit insufficient-RAM refills; Scorpion has one. Pentagon 512/1024 have
  none and retain the 277-T maximum continuous pulse hold. Native loading
  uses the established ROM stub and does not establish real IRQ animation.
- Both installed-Fuse cold captures reached `stream_finished`. The strict
  verifier passed every source bit/state, sector/page, cover, refill, and
  continuous timing check before failing its loading-phase assertion.
- [The source-clock comparison](frames-phase-control.json) independently
  compares all 11,526,111 relative source timestamps for each Pentagon.
  Every timestamp matches the prior disk, with maximum change 0 T and SHA256
  `2280bd22a0517b7ba907509a02e14f111f44014b7a0870fa663fb5e452c3ad88`.
- Exact compressed input/model and complete source clocks permit reuse of
  the prior 20.25031588676249-dB result. This verification introduces no new
  source encoding or filter fit. It does not assert a source-independent
  quality improvement, and physical hardware was not tested.
- The explicit post-source mute is separately measured at 219 T after the
  last source OUT, compared with 201 T previously: +18 T, or 5.022321 microseconds
  at 3,584,000 Hz. Source-bearing audio remains exact; raw traces through the
  terminal mute are not identical. The established final 100-ms listening
  crop excludes that teardown interval.

Full raw traces, relative clocks, and per-profile failure reports are under
[installed-full-512](installed-full-512/) and
[installed-full-1024](installed-full-1024/). Native reports and exact producer
provenance are `native-PROFILE.json` and `native-PROFILE-provenance.json`.

## Actual loading failure

Both actual captures observe only `LOADING.` phase 1. There are 68 loading
observations per model; the gray bar completes all 32 columns. Across
59.1504 seconds of observed loading, Pentagon 512 ROM FRAMES changes only
35→37; Pentagon 1024 changes 35→36 across 59.7696 seconds. TR-DOS mostly keeps
interrupts disabled, so ROM FRAMES is an unsuitable loading wall-clock timer.
The requested 1→2→3 dot cycle was not observed and the assertion remains
strict. The decision is to repair only the loading cadence in a subsequent
focused change. Green playback and terminal rendering must still receive
their full acceptance checks after that repair.

The full source clocks remain useful evidence of this candidate, but do not
replace a new full check of the subsequent UI image. No loading-phase
assertion was relaxed, and no missing phase image was fabricated.

## Emulator provenance and unsuccessful attempt

The initial portable-executable attempt was interrupted at root instruction
after 1,140.39 Fuse CPU seconds. Its saved stdout/stderr are empty, and its
report is explicitly incomplete. See
[the failed attempt](attempts/initial-full-ui-byte-hooks/report.json).
Stopping a process can discard buffered output, so empty pipes do not prove
that no debugger event occurred. The capture Python's large private-memory
allocation was predominantly the clean NumPy/verifier import allocation.

The successful complete captures use `C:/Program Files (x86)/Fuse/fuse.exe`,
SHA256 `e7aba457ea405f8e2fcab9d4bc703e9f1013453726e178d8c7333ce9685a1266`.
The unsuccessful portable build has SHA256
`014f257e854a569321e1c7a1fb473fe8fef03f3f832bc01388533734fe314d74`.
[Executable hashes](emulator-builds.json) distinguish these builds; the
different hashes alone do not establish the cause of the failed attempt.
Separate bounded READY/first-source/terminal diagnostics are saved in the
sibling `audio-ui-stage` evidence directory.

The non-UI baseline debugger script remains exactly 19,689 bytes with SHA256
`fe93b4f14b1fa4396b7b946861898bf4333240939206b61f50063cbba61e6096`.
[Its proof](default-script-proof.json) intercepts launch and compares the
actual generated script; it does not execute another baseline Fuse run.
The detailed UI script is 30,444 bytes with SHA256
`f470f3a8cabd7aabd001418f628c8c8dd42e883576e2284b207668bd10ff5c7f`.

## Source provenance and reproduction

The conversion's producer archive contains verifier `9cc226e2…`. The capture
verifier is `f6c97433bdf3a044ba6b19de9f930187f09d289e77a8e1be477cc98499c6cdd9`:
after conversion it only added a binary-authenticated fallback for the
existing loading-bar RET label. It changes neither PLAYER nor metadata.
The initial/native evidence producer `447943fc…` and installed-build producer
`3bc73451…` are preserved separately under `attempts/`.
Every complete run checks producer hashes before and after execution.

From the research worktree, with NumPy and the project's `z80` dependency:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator/verify.py --disk audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery/generated/audio.trd --metadata audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery/generated/player.json --packed audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery/generated/soundtrack.ima.gz --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --profiles pentagon512 --output NEW_OUTPUT
python audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator/summarize_phase_failure.py
```

The first command must use this initial candidate's authenticated disk,
metadata, and packed bytes. It is expected to fail the phase assertion after
recording a complete trace. Substitute `pentagon1024` for the other model.
`--native-profile PROFILE` selects a complete native run. The second command
reproduces the saved-clock and phase summaries without relaunching Fuse.
`make_manifest.py` authenticates all saved artifacts; `manifest.json` excludes
only itself and Python bytecode caches.
