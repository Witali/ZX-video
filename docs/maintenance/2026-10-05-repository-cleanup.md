# Repository consolidation, 2026-10-05

The user authorized merging useful completed branches into `main` and removing
their old worktree directories. The initial audit covered 77 local branches
and 70 registered checkouts. Main started at `92fb920f`; integration was
published as `59e77ecc`. The primary checkout is retained and returns to main.

## Integration decisions

| Topic | Decision |
| --- | --- |
| O. Henry AY audition | Merge the verified 24-second listening trial and its evidence. Speech acceptance remains pending. |
| Speex optimization | Merge the completed exact decoder and separate PVQ research. Round 40 is still 18.195 times over the average real-time budget. It does not replace IMA/PDM. |
| Integer contours | Merge the isolated host format study, tests and negative size results. No Z80 player or release is claimed. |
| Per-volume Huffman | Already patch-equivalent to `042f9ce6`. Reconcile history without changing the current tree or reverting later improvements. |
| Other original topic tips | Already ancestors of the published main. No speculative player changes were promoted. |

Documentation conflicts preserve the accumulated history and current task
requirements. The Huffman reconciliation has exactly the same tree as its
first parent. Existing IMA/PDM and movie player code remains unchanged.

## Removed and retained

- Removed **64** linked worktrees with ordinary `git worktree remove`.
- Deleted **71** unused merged local topic refs with `git branch -d`.
- Retained the integration/recovery ref `codex/repository-cleanup` and remote
  branches. Speex's remote topic ref was updated to its tested tip.
- Preserved all **64,981** ignored/local files from removed checkouts in
  **64** local ZIP archives, including source fixtures, tools and measurements.
  Every file was checked by SHA-256 inside its archive and again against its
  source before removal. No broad clean, forced removal or history rewrite ran.
- Removed checkouts contained **37,951,068,368 logical file bytes**. Their
  local archives occupy **8,383,967,872 bytes** and preserve 12,344,220,480
  source bytes. These are file-length totals, not measured disk free space;
  updating the primary checkout also materialized the newer main contents.

Five linked worktrees remain intentionally:

| Worktree | Reason |
| --- | --- |
| `compression` | A nested ZX0 Git checkout needs separate dependency review. |
| `generic-converter` | One temporary directory cannot be read, including outside the sandbox. |
| `lossless-volume` | Two temporary directories cannot be read. |
| `three-disk-quality` | Two nested codec repositories and four unreadable temporary directories. |
| `streaming-zx0-player` | Three untracked research files. Isolated costs are complete; selection and full playback qualification are unfinished. |

Their branch tips and files are untouched. The primary checkout's unrelated
`.codex-remote-attachments` files are also unchanged. Permissions, ownership,
nested repositories, remote branches, stashes and Git/LFS object storage were
not cleaned. Two older sampled reflog commits were superseded by amended
commits already in main; the report records the content comparison.

## Verification

- AY: authenticate all 20 artifacts and producer/verifier source hashes;
  rerun both complete native loops, **2,400 fields / 26,400 exact writes**.
  Work remains **974 T** normally, **1,079 T** at restart, delta **0 T**.
  Reuse the authenticated complete cold-Fuse trace; no fresh hardware run.
- Speex: rebuild from the merged source and execute all **186,880** speech
  samples with exact PCM16/PCM8, guards and the recorded **1,487,605,573 T**.
  The image matches archived round 40 SHA-256 `f49f4304…1320f24`, so its
  extended arithmetic/fixture evidence remains applicable. The previous
  round costs 1,518,690,395 T; delta **-31,084,822 T**. This is research CPU
  timing, without ULA/physical disk latency, not real-time qualification.
- Contours: all **4** unit tests pass on the combined tree.
- Huffman: authenticate all three full trace files and reproduce the saved
  timing summary exactly. Its **4,154** missed deadlines and **2,801** missed
  AY fields remain a failed release result, not a newly approved player.
- Parse every added/changed Python file and verify the preferred YouTube-linked
  TRD, normalized full IMA4 disk and AY audition hashes after the main checkout.

The original plotting command could not run because that runtime lacked
Matplotlib. The independent AY hash/native check above completed instead;
no new plots are claimed. Archived linker map trailing spaces remain intact.

The [machine-readable report](2026-10-05-repository-cleanup.json) contains
every removed path, branch tip, archive hash, retained exception and check.
Local execution logs and scripts remain in `.tmp/repo-cleanup-2026-10-05/`.

## Recovering historical local inputs

See [the archive guide](../../local-worktree-archive/README.md). ZIP payloads
are local only and are intentionally excluded by the existing `*.zip` rule.
Tracked code, release disks and committed evidence remain on GitHub.
Historical scripts may name removed sibling worktrees; restore the relevant
archive/checkpoint or pass the corresponding explicit input/tool paths.
The current audio/video converter entry points do not depend on those removed
worktree paths. No new codec or playback experiment is started by this cleanup.
