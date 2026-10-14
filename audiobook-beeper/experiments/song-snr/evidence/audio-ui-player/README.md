# Optional audio progress: focused player proof

Date: 2026-10-14. This phase adds gray loading progress with the centered
`LOADING` dot cycle and green playback progress to the achieved 90-second
main-song disk. It preserves the existing codec, compressed source, cover,
audio-bank allocation and independent boot format. The UI remains optional;
absent and false flags preserve the authenticated previous disk and metadata.

Seven functional tests passed in 15.700 seconds. `report.json` records their
assertions, the eight before/after native bank-handoff comparisons, every cold
command record on all four profiles, the global sector fraction, refill/end
behavior, and the maximum-capacity cold-load proof. `producer-source/` stores
the exact tested producer bytes; `producer-source.json` authenticates them.
`assembly/` includes linked sources, configuration, assembly log/listing and
the complete player image. `audio.trd` and `player.json` are the focused test
image and metadata, not a substitute for the final complete emulator run.

The baseline TRD SHA-256 is
`ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074`.
The focused UI TRD SHA-256 is
`55216119144fdb4e574bb3525b496d15c528b6f1a826da39c5070c3f57be9e1d`.
Both absent and false builds match the authenticated baseline disk and its
metadata exactly. The root builder tests independently cover strict flag,
unsupported direct/compact mode and excessive short-source bar jumps.

## Exact live schedule

`cycles.json` enumerates the old and new instructions and their T-states.
The old Pentagon handoff is 71 + 206 = 277 T-states after the penultimate
source OUT. The new handoff is 46 + 207 + 24 = 277 T-states, including six
NOPs. Both add 243 T-states to the ordinary 34-T interval: the difference is
zero. The following JP(HL)/OUT interval remains 4 + 12 = 16 T-states.

The actual native output callback reports 276 T-states because it fires one
T-state before that OUT instruction completes. The following dispatch is
reached at 281 T-states. Both timings match before/after for each last-bit
variant on Pentagon512 and Pentagon1024. Spectrum128 uses the unchanged live
handler and the same totals. Scorpion retains its existing extra 24 T-states,
so its instruction/callback/dispatch totals are 301/300/305. Its difference is
also zero. These native tests prove CPU instruction scheduling; they do not
claim data-independent real ULA timing on Spectrum128 or Scorpion.

The ten-byte command is popped only after SECOND has consumed its three
lookup words; SP is dead until FIRST resets it. A shared fixed-bank2 cursor
serves both literal handlers. Each Pentagon bank handoff maps physical bank7,
writes at most two attribute bytes as 0x24 (green INK and PAPER), then restores
the next audio page before any source prefetch. It preserves the prefetched
nibble, decoder row, feedback, predictor and dispatch registers. The initial
zero-position command writes a dedicated dummy byte. The builder rejects a
source whose bar would need more than two cells at one handoff.

Playback updates occur at RAM bank boundaries, about 4.105457 seconds for a
full bank. Spectrum128 and Scorpion redraw green progress only during their
existing refill pauses and after final audio; no new live I/O is added there.
Loading dots retain their phase through initial headers and audio loading;
refill phases may restart at one dot. Completion paints all 32 green cells and
centers `END OF AUDIO`, after the original final beeper mute.

## Bounds and scope

All four profiles cold-load the actual main-song image. Its packed source is
360192 bytes/1407 sectors; it uses 24 command slots including the sentinel.
The maximum test cold-loads all 612352 bytes/2392 sectors on Pentagon1024,
using 39 ten-byte slots. Startup ends at 0x833F, one byte before FIRST at 0x8340.
The maximum worker ends at 0xBFE0, 31 bytes before the declared 0xBFFF bound.
The UI resident helper ends at 0xB9F9, seven bytes before worker origin 0xBA00.
This proves maximum cold-load capacity, not maximum-length full playback.

The tested verifier hash is 9cc226e296bb054de8bcee090445860220a255f04c3dc44ed809c75ef7372bab.
The later f6c97433bdf3a044ba6b19de9f930187f09d289e77a8e1be477cc98499c6cdd9
revision adds only a Fuse UI-capture breakpoint fallback for the existing
bar-loop RET. It authenticates that loop's opcodes and changes no disk,
assembly, native-check or cold-loading code. `verification-source-update.json`
and the saved diff record this distinction; the tested snapshot is retained.

Complete native and Fuse execution of the final automatic C-generated song
disk, exact comparison of every pulse timestamp with the old image, and real
UI screenshots are separate evidence under `../audio-ui-emulator/`. This
folder does not claim a full emulator run, physical hardware test or new
source-independent codec-quality acceptance.

## Reproduce

Run from `C:/Work/ZX-video/.worktree/audio-snr-research` with the bundled Python
runtime. Choose a fresh evidence folder to preserve this saved proof.

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/.worktree/ay-auto-mix/.tmp/python-deps;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper;C:/Work/ZX-video/.worktree/audio-snr-research/toolkit;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper/experiments/song-snr'
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' audiobook-beeper/test_audio_ui_player.py --output .tmp/audio-ui-player-reproduction
```

`manifest.json` lists every proof artifact by relative path, byte size and
SHA-256. It excludes itself and includes no Python caches or temporary files.
