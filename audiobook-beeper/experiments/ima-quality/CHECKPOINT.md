# Paused quality milestone

The user explicitly requested saving progress and pausing on 2026-10-04.
Do not resume automatically. All study process trees and their Fuse children
were stopped. The music3 recording completed just before termination.

Worktree: `C:/Work/ZX-video/.worktree/lpc-ima-preload`.
Branch: `codex/lpc-ima-preload`. This checkpoint is local; no merge or push
was requested for this change. Main and the public YouTube disk are untouched.

## Saved results

Three additional root TRDs have complete two-loop native/Fuse checks and
normal-speed recordings: music3 19.165090 dB, music4 19.897558 dB, speech4
22.164431 dB. Their prior scores were 19.031203, 17.237725 and 21.010690 dB.
Both music files remain below-target listening previews. See `results.json`.

Speech3's second host candidate is fully trace-verified at 20.659504 dB
against 20.436321 dB before. Its other candidate's full trace was interrupted,
so final selection/normal-speed recording and root promotion are unfinished.
Speech4's extra refinement finished host encoding (22.552121 dB estimated
on the previous clock), but its own full Fuse trace was interrupted. Do not
use that estimate as the final score; the earlier 22.164431-dB disk remains
the saved verified result.

The two unfinished runs are archived under `paused/`, including completed
host streams, completed candidate evidence and partial traces. A raw
interrupted trace is compressed as `fuse-trace.txt.partial.gz`, explicitly
not a completed check. Original local caches remain under `build/ima-quality`.
The snapshot does not invent completion markers for interrupted stages.

## Resume only after the user requests it

1. Read this study's README, `TASK_BRIEF.md`, and saved identities. Do not
   repeat the 24 prefix probes or completed full host searches.
2. With unchanged producer/tool hashes, rerun `run.py --resume` for
   `speech3-verified`, using `--case speech3 --attempts 2` and the original
   `--reuse-search build/ima-quality/speech3` argument. The stage helper
   authenticates completed stages and renames interrupted ones before retry.
3. Resume `speech4-refined` with `--case speech4 --attempts 1` and
   `--clock build/ima-quality/speech4-verified/disk-encode-2`. This repeats the
   winning width-512/.03/horizon-128 search settings; the host output is saved.
4. Use **`C:/Program Files (x86)/Fuse/fuse.exe`**. The tools-directory SDL
   binary timed out in these debugger probes. Never reuse its incomplete
   player verification. The unchanged FFmpeg executable is recorded in the
   identities and logs.
5. Finish complete native/Fuse checks and normal-speed recordings, keep the
   best measured result including earlier fallbacks, then archive/audit.
   Update README/results/changelog and manifest before the next commit.

If source hashes change, do not bypass identity checks. Reuse authenticated
host stages with `--reuse-search` into a fresh output directory, preserving
the exact clock and plan. The archive retains the original producer identities
and final source snapshots separately.

Fourteen focused tests already pass. The short IMA3 single-volume CLI reaches
EOF and the IMA4 CLI correctly rejects a worse refinement. Further testing
is needed only for new code changes or unresolved failures. No Z80 hot path
changed: IMA3/IMA4 remain 427.375/423 T/sample, delta zero.
