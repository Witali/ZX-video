# Completed-sector loading animation: focused player proof

Date: 2026-10-14. The initial UI control, committed as `8db960a`, preserved every
source pulse but failed its actual loading-dot check: TR-DOS prevented ROM
FRAMES from advancing normally. Its evidence remains immutable under
`../audio-ui-player/` and `../audio-ui-emulator/`. This replacement changes
only the loading animation to one phase every 16 completed physical reads.
It introduces no live playback instruction or source/codec change.

Eight focused tests passed in 19.444 seconds. `report.json` contains their
results. The new actual compiled boot test observes 27 inactive cover ticks,
60 active header ticks and 1407 active audio ticks, totaling 1467 active calls.
`begin_loading` is called exactly once during that initial sequence, so the
header phase continues into the audio batch. Each pre-call countdown/phase
matches the exact 16-read recurrence. All four profiles also exercise 48 calls
with ROM FRAMES frozen at 123, observing 1/2/3/1 phases. Inactive calls preserve
the countdown, dot phase, screen, paging and either interrupt state. Decoder
registers, tables, unrelated audio banks and bank7 data from DB00 are guarded.

The seven existing proofs also pass: both last-bit handlers before/after on
all four profiles, absent/false golden disk AND metadata identity, whole-song
cold loading/command geometry, global sector fraction, refill origin redraw,
sentinel return targets, completion and maximum-capacity loading. This suite
is a native CPU/functional proof with a deterministic ROM-sector stub.
Actual read duration, visible dot cadence and every final source timestamp
are separately checked in full Fuse under `../audio-ui-emulator-sectors/`.

The focused countdown TRD SHA-256 is
`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`.
The absent and false builds still equal the authenticated ccab baseline:
`ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074`.
The model, cover, compressed source and audio RAM allocation remain the same.

## Source timing and bounds

The live bank handoff remains 277 T-states, 243 extra above the ordinary 34-T
interval. Both literal bits and all four profiles preserve the exact native
callback time: 276 T-states, one before the OUT instruction finishes. The
following dispatch is reached at 281 T-states. Scorpion retains its original
24-T addition, with 301/300/305 instruction/callback/dispatch totals. The
native proof claims no data-independent128/Scorpion ULA timing. Their green
progress redraws remain limited to existing refill pauses and completion.
`cycles.json` enumerates the unchanged before/after live instructions.

The first UI control's complete real traces separately measured the final
mute at 219 T-states after its last source output, versus 201 for the baseline:
an 18-T difference only in teardown. All 11,526,111 source-bearing timestamps
were equal. This counter replacement adds no hot instruction; its final
complete own-clock verification remains a separate requirement.

The maximum 2392-sector/612352-byte source cold-loads completely on
Pentagon1024 with 39 ten-byte command slots. Startup ends at 0x832E, leaving 18
bytes before FIRST at 0x8340. Worker ends at 0xBFE0, leaving 31 bytes before the
declared 0xBFFF bound. The resident helper ends at 0xB9F8, eight bytes before
worker origin 0xBA00. This is maximum cold-load capacity proof, not a full
maximum-length audio run. The replacement modules occupy 136 startup bytes
and 184 resident bytes; their mutable loading state is three bytes.

## Reproduction and provenance

`assembly/`, `audio.trd` and `player.json` preserve the actual linked proof
image. `producer-source/` and `producer-source.json` store exact tested source
bytes and hashes, including the fixed verifier. `manifest.json` authenticates
all artifacts except itself and includes no caches or temporary files.

From `C:/Work/ZX-video/.worktree/audio-snr-research`, choose a fresh folder:

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/.worktree/ay-auto-mix/.tmp/python-deps;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper;C:/Work/ZX-video/.worktree/audio-snr-research/toolkit;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper/experiments/song-snr'
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' audiobook-beeper/test_audio_ui_player.py --output .tmp/audio-ui-player-sectors-reproduction
```

This phase changes neither C/Python encoding defaults nor codec-quality
acceptance. It does not replace the complete final automatic conversion,
actual UI capture or full waveform verification.
