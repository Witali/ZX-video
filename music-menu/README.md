# TRD music menu for Spectrum 128

[ZX-Music-Menu.trd](../ZX-Music-Menu.trd) is an independently bootable
Spectrum 128 + Beta Disk jukebox with the complete existing instrumental
arrangements of **Lumière (3:42)** and **Alicia (2:38)**. Insert the disk
and boot TR-DOS / `boot`. It needs 128 KiB RAM and AY.

Click a song with a Kempston mouse, or press **1 / 2** to load and play it.
**7 / 6** select the previous/next song; **Enter** starts the selection.
**M** changes the sound mode in the menu. **Space** stops and returns to
the menu. EOF mutes both outputs and returns automatically. A held mouse
button or mode key does not repeatedly activate its command.

The default **AY + PWM** mode gives the beeper a sine-wave lead and AY
three accompaniment voices. **AY** uses lead, piano accompaniment and bass
on its three hardware channels. The imported inner accompaniment voice is
omitted in AY mode. These are new Spectrum arrangements of the existing
notes, with new timbres and quantized envelopes; they are not copies of
the source projects' sampled sound. [Sources and limitations](SOURCES.md).

The loading indicator remains visible while the selected version loads.
The measured selection-to-ready time is about 10.8 seconds for Lumière and
6.6 seconds for Alicia in Fuse's emulated disk model. All data stays in RAM
afterward: no disk reads interrupt a song. The disk contains four sound
versions in 944 data sectors; 1600 sectors remain free.

## Build and verify

From the repository root, with Python 3.12+, NumPy, Pillow and pyz80:

```powershell
python -m pip install numpy Pillow pyz80==1.3.0 z80==1.2.0
python music-menu/build.py
python -m unittest discover -s music-menu -p test_player.py -v
python music-menu/verify.py
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --variant 0 --pulse-fields 50
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --variant 1
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --variant 2 --pulse-fields 50
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --variant 3
python music-menu/record.py --fuse C:/Tools/Fuse/fuse.exe --song lumiere --seconds 12
python music-menu/record.py --fuse C:/Tools/Fuse/fuse.exe --song alicia --seconds 12
python music-menu/preview.py
```

Generated output goes to ignored `build/music-menu/`, including a disk,
assembler source/listing/binary, RLE data, build metadata, native report,
complete Fuse traces, listening WAVs and an actual Z80 menu framebuffer PNG.
The root disk and [saved reports](reports/verification.json) identify the
retained build. No sibling project, MIDI file, online service or instrument
download is needed. Pillow's font version affects screen pixels; the saved
build records the actual tool versions and source hashes.

## Verification coverage and audio limits

The complete four-version independent Z80 replay checks 37,982 fields,
154,341 AY writes, every DDS parameter, bank boundary, duration, phase and
stack balance, all 16 pulse widths, EOF muting, keyboard commands, mouse
counter wrap, clicks, debouncing and the integrated menu loop.

All four versions also cold boot and finish in Fuse 1.9.0, with real TR-DOS
ROM, floppy latency, ULA I/O contention and interrupts. Every AY write and
DDS change matches the generated stream. No ULA field is skipped, no song
schedule drifts, and no disk read occurs during playback. The final AY mute
and return to the menu are observed. Fuse selects through a debugger jump
to the normal `choose` entry after cold boot; native port-input tests cover
the actual keyboard/mouse selection path. This is not a physical-machine
test or a qualification for other clones or 48K machines.

PWM is a working first version with audible-quality limitations. Its
ordinary period is 242 CPU T (nominal 14.6566 kHz before overhead), with
16 high widths of 25..85 T. Real ULA contention and field work disturb the
carrier. The first 50 fields of each hybrid song measure rising intervals
up to 1521 T (about 0.429 ms); those pulse traces are bounded excerpts,
while song/IRQ/register checks cover the complete songs. The effective
sample clock is slightly lower than the nominal DDS clock, so exact beeper
tuning is not claimed. Periodic service noise can be heard; use AY mode
for a comparison without this software carrier. The two retained
[Lumière](previews/lumiere-hybrid.wav) / [Alicia](previews/alicia-hybrid.wav)
excerpts are actual Fuse sound output, with no clipped PCM samples; no
SNR target, listening approval or physical-board audio quality is claimed.

## Memory and CPU accounting

RAM5 holds the 6912-byte display plus BASIC/TR-DOS workspace. RAM2 holds
the fixed 16 KiB player image: code/config below 8C00h, two aligned NOP
ladders at 8C00h/8D00h, screen template 9000h..AAFFh, 16 waveform/volume
pages AB00h..BAFFh, stack below BD00h, IM2 jump BDBDh and vector table
BE00h..BF00h. The six other banks `(0,4,6,1,3,7)` provide 98,304 resident
song bytes. Lumière uses five; Alicia uses three. There is no streaming read
buffer. The allocation accounts for all eight physical banks independently
of host emulator storage.

A record is `duration LE16, DDS step LE16, wave page U8, AY R0..R10 U8[11]`.
Zero duration marks EOF. RLE only merges identical control states; records
are 16 bytes, so a bank boundary cannot split one. Absolute source times
are rounded to the actual 128K field clock (3,546,900 / 70,908 Hz); note
boundary error stays below 10 ms, without per-pattern rounding drift.

Instruction counts use the [project timing table](../libraries/Z80_TIMINGS.md):

| Path | CPU T | Previous standalone AY50 path | Difference |
| --- | ---: | ---: | ---: |
| Sustained field, no new record | 176 | 974 | -798 |
| New row, same bank | 1214 | 974 | +240 |
| New row after bank 0/4/6/1 | 1304/1329/1354/1379 | 1091 bank change | +213/+238/+263/+288 |
| Ordinary PWM sample | 242 | No equivalent PWM path | New functionality |
| IM2 handler, entry excluded | 46 | EI+RETI = 18 | +28 |
| IM2 hardware entry + handler | 65 | 19+18 = 37 | +28 |

These are CPU entry-through-exit components, with equal explicit exclusions;
the old AY50 player has different stream/loop behavior. They do not imply a
whole-player speedup. A sustained field is 135 T before `tick_done`, plus
41 T after it. A new row is 300 T to `ay_loop`, 10*78+73 = 853 T for eleven
writes, then 16 T pointer store, 4 T record event and 41 T tail = 1214 T.
Finding the next bank adds 90+25*i T for zero-based outgoing bank index i.
IRQ uses EX AF 4 + LD A,n 7 + store 13 + EX AF 4 + EI 4 + RETI 14 = 46 T;
AF' is scratch, main AF and other register pairs are preserved.

PWM setup through the rising OUT costs 106 T, JP/high/low ladders together
use a fixed 60 T of NOPs, and the remaining instructions total 76 T:
106+60+76 = 242 T. The rising-to-falling interval is 10+4*q+4+11 = 25+4*q T.
These calculations exclude ULA WAITs, IRQ service, field service, HALT and
TR-DOS/physical disk time. [Native](reports/native.json) and complete
[Fuse](reports/verification.json) measurements retain those distinctions.

The first prototype masked IRQ during high pulses. Its complete Lumière
run missed 3861 ULA fields (maximum 20-field IRQ gap), so it was rejected.
Replacing that DI with an equal-cost NOP keeps the 242-T ordinary period
(delta 0 T) and lets the short ULA INT window be serviced at either level.
[Rejected-attempt report](reports/rejected-masked-irq.json) retains its
identities and measurements; the intermediate binary was not retained.
