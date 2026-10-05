# Local worktree recovery archives

`2026-10-05/*.zip` preserves local files from the 64 removed linked checkouts.
These archives are **local only**, excluded by the existing repository ZIP
rule. They are not disposable build caches. Keep them until their fixtures,
tools and experiment outputs are no longer needed or have another verified copy.

Each archive contains:

- `manifest.json`: original branch, exact commit, file paths, sizes and SHA-256.
- `files/`: all ignored/local files inventoried before removal, at their original
  relative paths. Tracked files are recovered from the recorded Git commit.

The [cleanup inventory](../docs/maintenance/2026-10-05-repository-cleanup.json)
records each archive's own SHA-256 and original worktree. Check this hash before
recovery, extract into a new temporary directory, and verify the file hashes
from `manifest.json`. Do not overwrite an existing working tree blindly.

To recover a complete old experiment, create a new branch/worktree under
`.worktree/<name>` at the recorded commit, then copy the reviewed `files/`
contents into it. For example, substitute the recorded commit for `<head>`:

```powershell
git worktree add -b codex/recover-experiment .worktree/recover-experiment <head>
Expand-Archive -LiteralPath local-worktree-archive/2026-10-05/experiment.zip -DestinationPath .tmp/recover-experiment
```

Restore only after confirming that the destination is new and that the selected
archive matches the desired experiment. The original external audiobook input
is outside this repository and was not moved or deleted. The five retained
worktrees are listed separately in the cleanup report and are not archived here.
