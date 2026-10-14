# Completed-read loading animation

The loading dots now advance once per 16 completed physical sector reads. This replaces the ROM FRAMES clock that failed in the full Fuse disk run committed as `8db960a`: Pentagon 512 observed FRAMES only advancing from 35 to 37 over 59.15040625 seconds, and Pentagon 1024 from 35 to 36 over 59.7696328125 seconds. Both runs saw only the one-dot phase. Those failed results and their producer snapshots remain unchanged in [audio-ui-emulator/frames-phase-control.json](../audio-ui-emulator/frames-phase-control.json) and [audio-ui-loading](../audio-ui-loading/README.md).

`audio_ui_begin_loading` initializes the one-byte `audio_ui_sector_count` to 16. Each active `audio_ui_sector_tick` decrements it after a completed read/copy. Reads 1 through 15 return without paging or changing IFF; read 16 resets the countdown and paints the next phase. The label cycles `LOADING.`, `LOADING..`, `LOADING...`, then returns to one dot. An inactive tick leaves all UI state, paging and IFF unchanged. A blocked read counts once when it completes. The cadence depends on actual sector latency and does not imply a fixed duration in seconds.

Ten tests execute the assembled Z80 routines on coherent Spectrum 128, Scorpion 256, Pentagon 512 and Pentagon 1024 physical-bank models. Native memory-read tracing proves that none of the UI entries reads ROM FRAMES. The tests verify every read through the 16-read boundary, phase wrap at reads 32/48, carry boundaries through 513 reads, arbitrary or frozen FRAMES, inactive ticks, highest-page entry, Scorpion high-latch clearing, protected audio memory, scratch-register limits, exact glyph/bar geometry, paused green redraw and end-label clearing. The test font is synthetic and disk completion events are injected. Full integrated disk execution, actual animation cadence and final sound preservation remain separate checks.

The startup chunk is 136 bytes at `808A..8112`; the resident helpers are 184 bytes at `B940..B9F8`. This leaves eight bytes before the worker at `BA00`. The three mutable bytes are loading-active, dot phase and sector countdown. With the supplied 514-byte playback module, including the maximum 39 ten-byte records (390 bytes), startup use is 650 bytes and leaves 44 bytes before `FIRST=8340`. These are standalone layout checks against a supplied playback budget; the actual builder must retain its independent bounds. Split relocation also executes successfully at startup `8100..8188` and resident `B800..B8B8`.

`audio_ui_bar_complete` labels the existing RET following the 32-cell attribute loop. Its position and opcode are checked (`audio_ui_bar_next+11`, `C9`, preceded by `DJNZ`). This permits a mapped bank-7 screen capture without adding instructions.

## Integration contract

| Entry | Call site | Return |
|---|---|---|
| `audio_ui_begin_loading` | Once per loading batch after the cover is visible | Normal bank 0, EI; countdown 16, dots 1 |
| `audio_ui_sector_tick` | Exactly once per completed physical read/copy while loading | Early/inactive calls preserve paging/IFF; displayed update returns bank 0, EI |
| `audio_ui_draw_loading_bar` | Existing loading-only bar renderer | Normal bank 0, EI |
| `audio_ui_begin_playback` | Before starting or resuming audio | Normal bank 0, DI; `PLAYING`, green empty bar |
| `audio_ui_redraw_playback_bar` | While paused/refilling or after final mute, after setting global fill | Normal bank 0, DI; preserves `cache_bar` |
| `audio_ui_clear_label` | After final mute, before the terminal message | Normal bank 0, DI; clears label, preserves final fill, disables loading ticks |

All public entries clobber main AF/BC/DE/HL and preserve IX/IY and all alternate registers. Loading-loop callers must preserve their values. Link the established `cache_restore` routine in fixed bank 2 and keep `cache_bar` in `0..32`; remap the destination before the next sector copy. No UI entry in these modules may run during live audio. The user-approved playback progress path remains a separate approximately four-second bank-boundary mechanism; this change touches only cold/loading animation and its mutable state.

The centered ten-cell row-20 label uses pixels `D08B..D794` and attributes `DA8B..DA94`; the row-22 bar uses `DAC0..DADF`. Loading uses gray filled `3F`, empty `07`; playback uses green filled `24`, empty `04`. Bank-7 audio starts at `DB00` and is guarded against UI writes. The NUL-returning printer uses the existing `3C00+8*ASCII` ROM font convention. End rendering must clear the centered label before writing the existing message at column 0.

The loading modules contain no live hook or beeper output. Their live instruction change and intended deterministic live delta are zero. This premise does not replace whole-disk output/timestamp checks. No audio source, encoded payload, TRD, encoder C code, Python audio reference or measurement filter was opened or changed by the standalone proof.

## Reproduction and authentication

Run from the current worktree root:

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/.worktree/ay-auto-mix/.tmp/python-deps;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper;C:/Work/ZX-video/.worktree/audio-snr-research/toolkit;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper/experiments/song-snr'
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' audiobook-beeper/experiments/song-snr/evidence/audio-ui-loading-sectors/reproduce.py
```

`report.json` records scope, source identities and bounds; `tests.log` holds the complete result. Both assembly directories contain explicit-padding linked fixtures, listings and labels. `producers/` preserves the executed module/helper/tests and unchanged cache/harness sources. `manifest.json` covers every file in this evidence directory except itself and Python caches, including this README, using raw and LF-normalized SHA-256 identities. The prior frame-clock reproduction belongs to its frozen `8db960a` source state; running its old driver against later modules would overwrite historical evidence and must be avoided.
