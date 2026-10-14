# Standalone loading UI

The optional `stream-audio-ui.asm` and `stream-audio-ui-helper.asm` modules supply a centered ten-cell loading label, three dot phases and a light-gray loading bar. Their `audio_ui_begin_playback` entry changes the label to `PLAYING` and clears the bar with the existing green playback attributes before live audio starts. A separate clock-proved player path must advance that bar during playback.

The initial 287-byte single chunk was split at routine boundaries to make room for playback commands. The final public-entry chunk is 153 bytes at `808A..8123`. The helper chunk, including four mutable bytes and new paused-redraw/end-clear entries, is 185 bytes at `B940..B9F9`, leaving seven bytes before the worker at `BA00`. Total UI size is 338 bytes. The supplied playback-module budget is 514 bytes, including the full maximum 39 records of ten bytes each (390 bytes). Startup UI plus that budget is 667 bytes, leaving 27 bytes before the first resident table at `8340`. This is arithmetic against the supplied integration budget; the full builder must assemble and check its actual playback module and all layout bounds. Both chunks have no `ORG` and also assemble and execute with the public chunk at `8100..8199` and helpers at `B800..B8B9`.

Nine tests execute the real assembled instructions on coherent physical-bank Z80 models for Spectrum 128, Scorpion 256, Pentagon 512 and Pentagon 1024. They check entry from the highest ordinary page, Scorpion high-latch clearing, exact glyph geometry, all 32 bar cells, frame deadlines and wrap, delayed-read behavior, paging and interrupt returns, protected screen/audio boundaries, scratch-register limits, split relocation, paused global progress redraw, end-label clearing and the returning font printer. The test font is synthetic and ROM FRAMES values are injected explicitly. This proves routine behavior, not actual floppy cadence or a full audio disk release.

## Integration contract

| Entry | Intended call site | Return |
|---|---|---|
| `audio_ui_begin_loading` | After the cover is visible, once per loading batch | Normal bank 0, EI |
| `audio_ui_sector_tick` | After a physical sector has been read and copied | Suppressed calls preserve paging/IFF; displayed updates return bank 0, EI |
| `audio_ui_draw_loading_bar` | Existing loading-only bar-render call | Normal bank 0, EI |
| `audio_ui_begin_playback` | Before starting or resuming live audio | Normal bank 0, DI |
| `audio_ui_redraw_playback_bar` | While paused/refilling or after final mute, after setting a global `cache_bar` | Normal bank 0, DI; preserves fill count |
| `audio_ui_clear_label` | After final mute, before the existing end-of-audio message | Normal bank 0, DI; preserves final fill, disables loading ticks |

Every public entry clobbers AF/BC/DE/HL and preserves IX/IY and alternate registers. Callers must preserve their loading-loop values and use an ordinary fixed loading stack. The existing `cache_restore` ABI must be linked in fixed bank 2; `cache_bar` is bounded to `0..32`. Loading uses its original sector-derived fraction. Playback's global fraction is calculated by the player; a refill caller may paint `PLAYING` with `audio_ui_begin_playback`, set the required global fill and call `audio_ui_redraw_playback_bar`. The loader must remap its destination before the next sector copy.

The centered label occupies row 20, columns 11 through 20: pixel bytes `D08B..D794` and attributes `DA8B..DA94`. The row-22 bar uses attributes `DAC0..DADF`. Display bank 7 is protected through `DAFF`; its audio payload begins at `DB00`. The printer copies `3C00 + 8*ASCII` ROM glyphs and returns at NUL. It avoids the existing terminal printer's HALT loop.

Dot phases advance when at least 25 low-16 ROM FRAMES have elapsed. At 50 Hz the target is approximately 0.5 seconds. A blocked read can delay the next observation; the next completed read advances one phase without replaying several stale phases. Frame count is unrelated to source samples and does not schedule audio. Actual read/IRQ cadence remains an integration check.

The existing end-of-audio message starts at column 0. Integration must call `audio_ui_clear_label` before writing that message, so that the `PLAYING` suffix does not remain visible. The optional UI must be selected only by an explicit model flag; historical default bytes and metadata need a separate builder proof. Place the public chunk in startup padding, the helper chunk at `audio_ui_resident_origin=resident_end`, and independently assert the public chunk is below `FIRST`, helpers are below the worker, and the worker remains below `BFFF`.

No loading-UI routine may run during live PDM. This module adds no live call and no beeper output, so its live instruction change and intended deterministic hot-path delta are zero. That premise does not replace complete integrated timestamp and audio comparisons. No original source, encoded audio, disk image, C encoder or Python reference was read or altered by this standalone proof.

## Reproduction

Run from the worktree root with the existing project Python dependencies on `PYTHONPATH`:

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/.worktree/ay-auto-mix/.tmp/python-deps;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper;C:/Work/ZX-video/.worktree/audio-snr-research/toolkit;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper/experiments/song-snr'
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' audiobook-beeper/experiments/song-snr/evidence/audio-ui-loading/reproduce.py
```

`report.json` describes the measured scope and limits, `tests.log` contains the complete test result, and the two assembly directories hold linked fixtures, listings and labels. `producers/` preserves the executed module, tests and unchanged cache/harness sources. `manifest.json` authenticates all files in this directory, including this README, except the manifest itself and Python cache files. Raw and LF-normalized SHA-256 identities are recorded. The assembled fixture includes explicit padding before its unchanged `cache_restore` test stub because a second assembler ORG alone does not add bytes to the raw object.
