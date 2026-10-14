# Bounded actual-Fuse loader diagnostic

Date: 2026-10-14. A complete detailed UI/audio capture had been running for
several minutes, so this independent, read-only diagnostic tested whether the
actual generated Pentagon512 disk reached playback. It did not interrupt or
modify the complete capture, shared source, emulator settings or disk image.

The authenticated TRD SHA-256 is
`55216119144fdb4e574bb3525b496d15c528b6f1a826da39c5070c3f57be9e1d`.
The clean run reached `ready` and exited with the requested code 77 in
0.7677424 seconds wall time. Its observed emulator timestamp was 248372199
T-states; the remaining-sector counter was zero, bank0 was selected with
7FFD=24, loading was inactive and green playback progress was zero.
The first actual ROM-sector call and completed cover display were both
observed before `ready`. This proves that the actual Fuse loader completed;
it does not prove complete playback, every audio pulse or full UI cadence.

`diagnose.py` sets only a few checkpoints, stops at `ready`, and enforces a
60-second process timeout. `debugger.txt`, `stdout.txt`, `stderr.txt` and
`report.json` preserve the exact clean command and observations. The clean
stderr is empty. The long full trace remains separate under
`../audio-ui-emulator/` and is not replaced by this diagnostic.

The initial attempt also reached the identical `ready` timestamp, in
4.8228033 seconds wall time, but its underscored scratch-variable name caused
one debugger syntax error and suppressed the optional first-ROM checkpoint.
All initial artifacts, including the diagnostic source and stderr, are
retained verbatim under `attempt-initial-variable/`. Replacing that local
variable with `$seen` produced the clean run. No assembly or shared verifier
change was made.

Three follow-up diagnostics distinguish actual player operation from the
cost of the detailed debugging script:

- `source-start/` observes the first 100 source OUTs after READY. It passed in
  0.7990144 seconds wall time, with indices 0 through 99 and strictly increasing
  timestamps. This is a small prefix, not complete waveform verification.
- `source-start-full-script/` uses the exact 30444-byte full UI/audio script,
  changing only the source-output command's final `co` to `ex 77`. It reached
  the first source output in 18.7231981 seconds wall time, with empty stderr.
  The original script, transformed script and their hashes are retained.
  All loading/UI breakpoint definitions remain present, so they are slower
  than the minimal script but do not stall before the first source output.
- `terminal/` uses only READY and final-completion checkpoints. The actual
  song reached its end in 1.8429215 seconds wall time. The observed READY-to-end
  duration was 90.2593024554 emulated seconds, including final UI teardown.
  Bank7 was mapped at the end and all 32 observed bar attributes were 0x24.
  This proves the global playback/end path, not every bit, sample state or
  relative source timestamp. The full detailed trace is still required.

Each follow-up is separately reproducible through its `diagnose.py`, enforces
the same 60-second timeout, and saves exact stdout/stderr and commands.
None interrupted the existing full capture or changed player/codec source.

The executable identity matters: every diagnostic here used
`C:/Program Files (x86)/Fuse/fuse.exe`, while the initial long complete capture
used the distinct repository-local
`C:/Work/ZX-video/tools/fuse-1.9.0-sdl/fuse.exe`. `executables.json` records both
absolute paths, byte sizes and SHA-256 hashes. These runs establish the
installed executable's behavior. They do not establish why the other build
was slow; the complete capture must be rerun with the verified executable.

Reproduce from the worktree root with the existing bundled runtime and
PYTHONPATH used by the player tests:

```powershell
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' audiobook-beeper/experiments/song-snr/evidence/audio-ui-stage/diagnose.py
```

The script writes only this diagnostic folder. `manifest.json` authenticates
all saved artifacts except itself; it contains no caches or temporary files.
