# Online TRD player for GitHub Pages

A static disk library with a locally vendored ZX-Dream emulator, AY/beeper
sound, Beta Disk and a 128K configuration. It does not need a backend or a
third-party emulator iframe. Disk bytes are fetched only when played, and
checked against their SHA-256 identity before insertion.

## Build and preview

Use Node.js 22 or newer and Git LFS. From a complete checkout:

```powershell
git lfs pull
node web/tools/build.mjs
node web/tools/serve.mjs
```

Open the printed local address. Build output is `.tmp/web-site`, not `web/`.
The builder replaces that task-owned output directory on each invocation.
It copies an explicit allowlist of static assets and every **tracked** TRD;
it never publishes the repository directory, logs, media sources or Git data.
It rejects LFS pointers, invalid geometry, images differing from committed
bytes, and mismatches against the curated catalogue. Existing catalogue
coverage gaps are shown as uncatalogued experiments, not silently omitted.

For a sparse worktree, an optional third argument supplies materialized
images from another local checkout. Every image must still match this
worktree's committed identity:

```powershell
node web/tools/build.mjs .tmp/web-site C:/Work/ZX-video
```

## Use

Select a root disk or switch to all project disks. Search matches filenames,
paths and descriptions; media filters narrow the list. **Play disk** inserts
into drive A and resets to TR-DOS. If TR-DOS displays its prompt, press Enter
to start the disk's `boot` file. Some archived fixtures are not bootable.

For a running multi-disk program, select the next image and use **Insert
without reset**, then confirm the program's prompt. This preserves RAM and
the original timeline; **Restart** always restarts the currently mounted
disk, even if a different library entry is selected. Swap is manual.

Click the screen for the emulated keyboard; Shift and Alt map to Caps Shift
and Symbol Shift. Enter, Space, 1 and 2 are also available as touch controls.
Playback pauses when the tab becomes hidden; use Resume on return. The
browser requires a user click before audio starts. Use Copy link to share
the selection; shared links do not autoplay. A local TRD is read in the
browser and never uploaded.

TR-DOS uses the emulated floppy controller rather than a ROM fast-load
trap. A disk that preloads its full audio cache can take about a minute to
start; the loading screen remains visible during that time.
A spinner beside the machine status follows the floppy controller's busy
state, including subsequent reads during playback. It also appears while
the browser fetches and authenticates a selected image.

## GitHub Pages

`.github/workflows/pages.yml` builds and deploys the allowlisted artifact
with GitHub Actions. In repository **Settings → Pages → Build and deployment**,
choose **GitHub Actions**. The workflow runs on main changes to the website,
catalogue or disks, and can also be run manually on main. A pull request
only builds and validates; it does not deploy. See
[GitHub's custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

For this repository the expected project URL is
`https://witali.github.io/ZX-video/` once Pages is enabled and the workflow
succeeds. Relative asset and disk paths also support a custom domain.
The workflow materializes LFS before building: Pages must serve actual TRDs,
not Git LFS pointer text.

## Verification scope

The web adapter does not change the Z80 player, nominal frame deadlines or
release disk contents. Browser playback is a preview, not a replacement for
the full Fuse/native timing, sound and EOF checks in the project evidence.
See [credits, pinned source and ROM notices](vendor/README.md).

The deterministic integration smoke is also run in CI:

```powershell
node web/tools/check-emulator.mjs
```

It boots the real music-menu TRD through the real ROM/controller/core,
matches the fourteen title glyphs against the stock ROM font, checks actual
nonzero synthesized audio, and verifies that disk insertion preserves the
mapped memory and CPU program counter. It does not measure browser output
devices or qualify a complete movie's deadlines.
