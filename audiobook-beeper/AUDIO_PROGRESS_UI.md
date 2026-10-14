# Clock-preserving audio progress

The delivered sector-count image is `b96763ca...`. Full installed-Fuse
playback on both Pentagon profiles verifies every source bit and relative
timestamp,92 correct loading phases and22 exact green-prefix updates. The
initial frame-clock image `55216119...` is preserved as an unsuccessful
control: actual ROM FRAMES advanced just one/two fields during roughly59
seconds of TR-DOS loading, leaving the dots at phase1.

The optional `--audio-progress-ui` converter flag adds a light-gray loading
bar, centered `LOADING` with one/two/three cycling dots, and a green playback
bar to the continuous RAM player. It uses the same source-independent C
encoder as the existing best-measured audio snapshot. The original Python
encoder remains executable with `--encoder python`.

```powershell
python audiobook-beeper/convert_snr_audio.py source.wav `
  --output output/audio --audio-progress-ui
```

The bar's existing bitmap stays unchanged during audio. Empty playback cells
use attribute `04` (green INK, black PAPER); filling a cell writes `24` (both
green). Loading uses `07` for empty cells and `3F` for solid light gray.
There is no FLASH or BRIGHT bit. The protected physical-bank7 screen ends at
`DAFF`; its audio starts at `DB00`. The decoder's normal bank5 screen memory
is a lookup table and is never used for display updates.

Pentagon512/1024 updates occur at existing RAM-bank handoffs, approximately
every 4.105 seconds for a full 16-KiB bank and 2.373 seconds for bank7's shorter
slice. The global 32-cell fraction represents the whole encoded fragment,
including previous batches. Completion paints all 32 cells after the final
mute. Spectrum128/Scorpion256 preserve their existing live paging sequence;
their playback bar updates at existing refill pauses and completion. The
loading dots advance after every16 completed sector reads, including header
reads after the cover is visible. This requires no ROM interrupt clock.
Physical read delays change its wall-clock period; there is no promised
seconds-per-dot interval or catch-up burst. No loading routine schedules or
runs during live audio.

The live Pentagon tail consumes a cold-built ten-byte command through SP,
which is dead after SECOND's three POPs and before FIRST resets it. One
shared cursor serves both literal last bits. AF' preserves the prefetched
nibble, alternate HL preserves the decoder row, and the command restores
the next source address and paging before playback continues. Two attribute
writes replace existing tail work without increasing its instruction count.

| Timing from the instruction table | Previous snapshot | UI player | Difference |
|---|---:|---:|---:|
| Ordinary128/Scorpion sample |423 T|423 T|0 T|
| Ordinary Pentagon sample |449 T|449 T|0 T|
| Normal source-page extra |14 T|14 T|0 T|
| Pentagon bank extra |243 T|243 T|0 T|
| Pentagon penultimate-to-last source pulse |277 T|277 T|0 T|
| Scorpion bank pulse interval |301 T|301 T|0 T|

The new Pentagon interval is 32 T page/bank detection + 14 T dispatch + 207 T
command/paging/release + 24 T padding = 277 T. The outgoing JP(HL) 4 T and
next FIRST OUT 12 T still form the following 16-T interval. Native callbacks
observe the release at 276 T; execution through JP(HL) takes 281 T. Both
definitions match the previous implementation. These CPU counts exclude
ULA contention, TR-DOS ROM execution and physical floppy latency.

No audio RAM capacity is lost. The maximum 2392-sector/612352-byte TRD uses
39 commands; startup ends at `832E`, resident UI helpers at `B9F8`, and the
worker at `BFE0`. FIRST remains `8340`, the worker begins `BA00`, and the final
reserved byte is `BFFF`. The builder checks these bounds. It rejects compact
loader/UI combinations and multi-bank short fragments whose 32-cell bar
would require more than two live attribute writes per handoff. The default
flag is off; absent/false produces the authenticated previous disk and
metadata exactly.

The user-requested entire sea-foam song was rebuilt through the public C
program in 60.871331 seconds. Its main waveform encoding took26.677900 seconds;
TRD assembly and artifact writing took2.195068 seconds. Source, cover,
compressed audio and decoder tables are exact; only the16-KiB PLAYER file
changes. The host score stays 20.250315887 dB with the unchanged filter,
original source clock and fixed 100-ms edge crop. Emulator execution is a
separate validation cost. This interface change does not complete the
broader research on source-independent noise and modulation artifacts.

Both complete installed-Fuse source clocks match all11,526,111 previous
timestamps exactly. The final explicit mute, after source-bearing audio,
occurs219 T after the last source pulse instead of201 T (+18 T,5.02 microseconds).
Thus the source waveform is exact; the post-source teardown interval is
reported separately and is excluded by the unchanged100-ms edge crop.

Reproduction and verification are saved in
[delivery evidence](experiments/song-snr/evidence/audio-ui-delivery-sectors/README.md),
[full execution evidence](experiments/song-snr/evidence/audio-ui-emulator-sectors/README.md),
[player cycle proof](experiments/song-snr/evidence/audio-ui-player-sectors/README.md),
and [loading routine proof](experiments/song-snr/evidence/audio-ui-loading-sectors/README.md).
