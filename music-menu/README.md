# Expedition 33 Demo

[Expedition-33-Demo.trd](../Expedition-33-Demo.trd) is an independently
bootable **Spectrum128 + Beta Disk** demo with eighteen native illustrations,
the complete existing AY arrangements of **Lumiere** and **Alicia**, and an
automatic looping playlist. The complete demo was reviewed before publication.
The ULA beeper remains silent.

The first Lumiere city picture appears before PLAYER and its caches load.
That picture stays visible throughout loading. Music then starts on the first
ULA interrupt, with pictures enabled. Every illustration, including the first,
cycles with a six-second hold and a roughly one-second petal/mosaic dissolve.
The common title bitmap stays still; the native BORDER follows each scene.
The menu is prepared behind the shadow screen and never appears unless a key
is pressed. Pictures and controls execute on the actual Spectrum, not a browser
overlay. [Artwork, references and native previews](artwork/README.md).

- Any key while pictures are visible opens the menu without stopping music.
  That complete press/release is swallowed, including Space.
- In the menu, **1/2** or a title click starts/restarts a song. **7/6** navigate;
  **Enter** plays the selection. **Space** stops and cancels the automatic next song.
- **I** or the checkbox toggles pictures. **M** returns to pictures when enabled.
  Starting a song also returns to pictures when enabled.

Both full songs loop in order. The silence between Lumiere and Alicia is
150 fields, about 3.00 seconds. Alicia already contains 208 trailing silent
fields, about 4.16 seconds, which are retained; no additional pause is added.
The entire original timeline and every active field are preserved. Fixed-volume
voices receive a gentle 8-field entry and 40-field ending. AY's hardware-ENV
bass is retained exactly because that envelope is its oscillator waveform,
not an independent amplitude control. This is not an overlapping crossfade.

AY retains the previous three parts: lead, piano accompaniment and bass.
The original inner accompaniment was already omitted in the established AY
arrangement; this change does not claim a fourth simultaneous AY channel.
The existing two-field repeated-note articulation, true ties, noise accents
in piano rests and shape-14 bass phase handling remain. [Sound provenance](SOURCES.md)
and [earlier articulation audit](AUTOPLAY_ARTICULATION.md) record that baseline.

## Resident memory and compression

All disk reads finish before music begins. The demo uses 362 data sectors
with 2182 free. Immutable song and picture inputs total **68,348 bytes**.
Switching songs, opening the menu and changing images require no disk access.

| Physical RAM | Allocation |
| --- | --- |
| 5, fixed 4000..7FFF | Display, BASIC/TR-DOS workspace; first-stage loader/stack at startup |
| 2, fixed 8000..BFFF | Code, tables, footer, incoming image, grammar/CPU stacks, IM2 |
| 7 | Complete 6912-byte stock-ROM menu snapshot; remaining bank space reserved |
| 0/4/6/1/3 | Five 16KiB cache banks, 81,920-byte capacity; 68,348 bytes used |

All eight 16KiB banks are accounted for. The incoming column-major illustration
is A000..B67F (5760 bytes), pending grammar children B700..B717, CPU stack below
BD00, IM2 jump BDBD and vectors BE00..BF00. The shared 1024-byte title bitmap is
9C00..9FFF. The stack and artwork buffers do not overlap. Cache packing keeps
each complete picture input within one bank. The menu bank is never overwritten.

Both original AY delta streams remain the canonical record format:
`duration U8, mask LE16, changed register values`; duration zero is EOF. Register
order is `0,1,2,3,4,5,6,7,11,12,13,8,9,10`, preserving generator-before-volume
writes. A shared byte-pair grammar stores the complete final 42,933-byte stream
in **10,586 bytes plus a 508-byte dictionary**. Maximum expansion depth is eight.
Every byte round-trips exactly; no note, part or duration is removed by compression.

Eighteen illustrations omit their common footer before compression. Actual
complete-block comparisons include initialization and exact EOF:

| Decoder | Code + caller stack | Packed art | Total plain CPU T for all 18 |
| --- | ---: | ---: | ---: |
| ZX0 Standard | 68 + 6 = 74 B | 57,762 B | 8,764,639 |
| ZX0 Gamma-JP | 69 + 6 = 75 B | 57,762 B | 8,683,227 |
| **ZX0 SMC, selected** | **74 + 4 = 78 B** | **57,762 B** | **8,254,277** |
| LZSA2 compact EOF | 136 + 8 = 144 B | 60,195 B | 5,881,154 |

LZSA2 is faster on these inputs; ZX0 retains 2433 bytes more cache capacity.
The selected small SMC decoder prepares the next image in the background.
Its slowest complete image costs 520,905 plain CPU T, about 147 ms, safely
inside the six-second preparation window. AY continues in the ISR throughout.
These counts exclude ULA waits/IRQ overhead; neither decoder is claimed to
finish a full illustration inside one field.

## Timing and verification

The ISR preserves main registers, both AF sets and the paged input bank.
Music owns the real ULA clock; foreground decompression/copies may span fields.
The native ISR body ranges from **398 to 12,021 T**, plus 19 T for IM2 entry,
against a 70,908-T field. The previous IRQ body was 18 T because music used to
run in the foreground. These are different responsibilities, not a speedup.

The old byte reader cost 75 T. The new provider costs 252 T for a root literal
(+177), 199 T for a pending literal (+124), 362 T for an escaped root (+287),
or `296 + 193*d` T for a root symbol expanding through `d` pairs. The record
parser's old `1452 + 164*w` T formula gains the sum of provider deltas over
its `3+w` bytes. Mute is 1153 T (-11); paging adds 23 T to retain the latch.
Reveal/petal tiles cost 834/724 T; sixteen-cell batches cost 15,597/13,837 T
for the measured tile-zero fixture. See [timing counts](reports/demo/timing-demo.json)
and [instruction table](../libraries/Z80_TIMINGS.md) for exact scope and deltas.

[Native replay](reports/demo/native-demo.json) checks 19,241 fields, both full
tracks, both gaps and a 101-field return to Lumiere, with exact AY transactions.
It checks every byte of 54 completed screens, covering all eighteen pictures,
plus menu input, swallowed held Space, checkbox, manual switching and stopping.
ROM/disk/IRQ are explicit stubs in this functional test.

[Cold Fuse qualification](reports/demo/fuse-demo.json) independently executes
the actual loader, ROM, Beta Disk and ULA. Both complete tracks, pauses and the
100-field loop restart match every expected AY write. All 19,240 real ULA
interrupts are consecutive, with no skipped musical field or accumulated drift.
Maximum IRQ-entry-to-audio-complete interval is 11,866 T. It checks 532 loading
screen samples and 28,728 completed-picture samples across 54 transitions;
native replay separately checks complete screens. The menu stays hidden and
no disk read occurs after ready. Raw evidence is retained in
`reports/demo/fuse-trace.txt.gz` with its exact debugger script.

The web smoke boots the same image through the browser core, checks all eighteen
menu-title ROM glyphs after Space, stereo output for both tracks without clipping,
and preserved RAM/PC across a disk swap. Built-in-browser review also covers
loading, changing pictures, Space/I/M and the download button. The downloaded
640KiB image hashes to the exact Fuse-qualified disk. Physical hardware and
subjective listening approval remain outside these automated checks.

## Reproduction and history

Python 3.12, NumPy, Pillow, pyz80 1.3.0 and z80 1.2.0 are required. The project
ZX0/LZSA library sources are used directly; no compressor is required to rebuild
from the retained, round-trip-checked art inputs.

```text
python music-menu/build.py
python -m unittest discover -s music-menu -p test_player.py -v
python music-menu/verify_demo.py
python music-menu/verify_demo.py --fuse C:/Tools/Fuse/fuse.exe
python music-menu/audit_demo_timing.py
```

Output defaults to ignored `build/expedition-33-demo/`. To reproduce compression
with the pinned upstream CLIs, use `music-menu/measure_packing.py --zx0 <exe>
--lzsa <exe>`; the comparison LZSA fixtures are not placed on the TRD.
An initial bounded-column codec needed 54,066 bytes for fourteen pictures and
did not fit beside uncompressed songs and the menu. It was rejected; the
reproducer remains in `experiments/column_codec.py`. A BASIC SCREEN$ loading
attempt was also rejected because a subsequent TR-DOS LOAD cleared the screen.
The first-stage sector loader fixes that, with explicitly emitted padding.

Historical sound releases/evidence remain under `reports/autoplay/`,
`reports/click-fix/`, `reports/ay-only/` and their linked documents. Their older
recorders/verifiers describe those historical formats. The current demo uses
`verify_demo.py` and `audit_demo_timing.py`. Previous listening excerpts retain
their own older disk hashes; they are not represented as captures of this build.
