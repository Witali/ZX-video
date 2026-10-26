# AY-only TRD music menu

[ZX-Music-Menu.trd](../ZX-Music-Menu.trd) boots on **Spectrum128 + Beta Disk**
and plays the complete existing instrumental arrangements of **Lumière
(3:42)** and **Alicia (2:38)** using AY. The ULA beeper stays silent.

Click either title with a Kempston mouse, or press **1/2**, to start or switch
songs. **7/6** move the selection while the current song continues; **Enter**
starts the selection. **Space** stops. Re-selecting a song restarts it. The
menu and cursor remain active through playback and EOF. The playing song is
green when a different title is selected in blue.

Text uses the standard Spectrum ROM font, `PRINT AT` control bytes and
`RST 10h` on stream 2. Startup restores `CHARS=3C00h` and clears the screen
with ROM `CLS`. No font bitmap is included. Live selection/status changes
use attributes and the cursor; ROM printing finishes before loading the
songs and does not run during audio playback.

Both songs load into RAM once at startup. The cache is **39,304 bytes** in
three uncontended data banks `(0,4,6)`. Switching or restarting needs no disk
access. Fuse measures about 6.1 seconds for the initial cache load. The disk
uses **219 data sectors**, has **2325 free**, and is independently bootable.

## Sound and click repair

AY supplies lead, piano accompaniment and bass. The original inner
accompaniment voice is omitted, as in the previous AY mode. All source
JSON/playlist/note identities are preserved. Lead and piano use tone
generators with software attack/decay/release levels. Bass uses the shared
repeating **triangle envelope (shape 14)** when its integer period stays
within **18 cents** of the target; other notes use the finer tone generator.
Only one channel owns the shared envelope.

The repair prepares period/shape registers **before channel volumes and
envelope enables**, retains a positive unused envelope period, and silences
channels before chip reset. Connected triangle notes preserve phase. Short
string/cello articulation gaps receive release bridges of at most 65 ms;
piano levels have a softer trajectory. Note-on positions and total duration
remain unchanged. Envelope restarts fall from 111 to 37 for Lumière and from
53 to 15 for Alicia. See the [diagnosis and bounded measurements](CLICK_REPAIR.md).

This triangle is AY's stepped, nonlinear DAC envelope. A complete up/down
cycle has 64 internal steps: `f = 1,773,450 / (512 * envelope_period)`.
Channel C's period-1 ultrasonic tone gate halves the baseband amplitude
after filtering. Register updates follow the 50.021-Hz ULA field rate.
The selected triangle notes have a maximum 16.982-cent tuning error; the
triangle is active for 8328 Lumière fields and 5429 Alicia fields.

The earlier [bounded timbre screen](reports/ay-only/timbres.json) compared
normalized 12-harmonic spectra with the existing CC0 cello sample: square
distance 0.266106, triangle 0.249832, saw 0.408128. Triangle was approximately
6.1% closer than square in that spectral comparison. This is not a whole-song
perceptual score. The AY timbres differ from the sampled source players;
physical filtering and chip variants can affect their sound.
[Music and sample provenance](SOURCES.md).

Actual repaired Fuse sound excerpts: [Lumière](previews/lumiere-ay.wav) and
[Alicia](previews/alicia-ay.wav). Their [capture reports](reports/click-fix/final/verification.json)
bind the final disk and WAV hashes. Physical-board audio and subjective
listening approval are not claimed.

## Build and reproduce

Python 3.12+, NumPy, Pillow and pyz80; native checks additionally use the
independent `z80` package. Run from the repository root:

```powershell
python -m pip install numpy Pillow pyz80==1.3.0 z80==1.2.0
python music-menu/build.py
python -m unittest discover -s music-menu -p test_player.py -v
python music-menu/verify.py
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --song lumiere
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --song alicia
python music-menu/record.py --fuse C:/Tools/Fuse/fuse.exe --song lumiere --seconds 12
python music-menu/record.py --fuse C:/Tools/Fuse/fuse.exe --song alicia --seconds 12
python music-menu/preview.py --fuse C:/Tools/Fuse/fuse.exe --rom C:/Tools/Fuse/roms/128-1.rom
```

Output goes to ignored `build/music-menu-click-fix/`: disk, assembler input,
listing and binary, streams, complete native/Fuse reports and traces,
recordings and a framebuffer PNG. `--rom` is optional for a Fuse screenshot;
it additionally authenticates glyphs against the user's local 16-KiB ROM.
The ROM is never copied into the project or disk. Native preview instead
requires `--rom` and explicitly uses a ROM-output stub.

Rebuilding needs no sibling repository, sample download, MIDI, Node.js or
external instrument bank. Re-running `probe_timbres.py --sample-folder
<original-sample-folder>` needs the existing cello WAV and pinned manifest;
it saves measurements, not sample audio. The click diagnostic uses Node.js
and the existing vendored Ayumi renderer; see [its invocation](CLICK_REPAIR.md).

## Complete playback and menu verification

[Current build](reports/click-fix/final/build.json),
[native CPU](reports/click-fix/final/native.json) and
[complete Fuse evidence](reports/click-fix/final/verification.json) bind the
retained disk and player. Seven tests cover score identities, register order,
restart/delta contracts, complete foreground/menu replay, cached switching,
held-key debouncing, mouse wrap/clicks, stop, EOF, register states, stack
balance and records crossing physical bank boundaries. Native tests use
explicit ROM read/text stubs; real ROM behavior is checked separately in Fuse.

Each of two Fuse 1.9.0 runs cold boots the real TR-DOS loader, plays 100 ticks
of one song, switches to the other for 100 ticks, switches back and finishes
the selected song through EOF. Both complete songs pass: **18,991 full-song
fields**, plus 400 preliminary fields and four switches. Every actual AY
data-port write matches the stream. No ULA field is skipped, there is no
accumulated song drift, and no disk is read after ready.

The visible menu/cursor foreground runs every field. Maximum measured work,
including ULA contention and switching, is **22,489 T of 70,908 T**. Dispatch
reaches song start within 1584 T, the first AY write within 2155 T (0.608 ms),
and the complete initial state within 5288 T (1.491 ms). Input is polled once
per field. Fuse commands are injected at menu dispatch; loader/audio code
and cached bytes are not patched.

The [actual cold-boot screen check](reports/click-fix/final/menu-verification.json)
authenticates all **125 displayed characters** against stock ROM glyphs.
The [pre-existing catalogue coverage gap](reports/catalog-coverage.json)
remains recorded separately. Target timing and control-step diagnostics do
not establish the absence of host sound-card underruns on every computer.

## Stream, memory and CPU accounting

RAM5 holds the 6912-byte display plus BASIC/TR-DOS workspace. RAM2 holds
the fixed 16-KiB player image, ASCII/control text, stack below BD00h, IM2
jump at BDBDh and vector table at BE00h..BF00h. There is no screen template.
Up to 98,304 cache bytes are available in the other six banks; actual streams
use only banks 0/4/6. All eight physical banks are accounted for.

A schema-3 record is `duration U8, changed-slot mask LE16, slot values`.
Duration 0 is EOF; long holds split at 255 fields. Slot-to-register order is
`0,1,2,3,4,5,6,7,11,12,13,8,9,10`. Slot 10 explicitly restarts R13; the host
R13 sentinel 255 is never sent to AY. Earlier numerical-order streams are
incompatible. The reader pages across FFFFh inside mask/value lists. Each
song entry stores a cache-bank index and address. Absolute note boundaries
are rounded once to `3,546,900 / 70,908` fields/second, with less than 10 ms
error and no per-pattern drift.

The [instruction table](../libraries/Z80_TIMINGS.md) supplies deterministic
CPU counts, cross-checked against assembled execution:

| Component | Repaired CPU T | Previous AY-only CPU T | Difference |
| --- | ---: | ---: | ---: |
| Sustained audio service with caller, UI excluded |92|92|0|
| New row, one changed register, with caller |1657|1635|+22|
| New row, three changed registers, with caller |1985|1919|+66|
| Mute routine |1164|951|+213|
| IRQ body |18|18|0|
| IM2 entry plus body |37|37|0|
| Byte reader |75|75|0|
| Extra per bank-crossing byte |185|185|0|
| Ordinary unchanged UI work |3907|3907|0|

A held `music_tick` costs 51 T plus its 41-T caller, giving 92 T. A new
record costs **1452+164*w T**, plus 185 T per bank crossing and 41 T for the
main caller. Header 365 + mask loop `(13*77+72)=1073` + NOP 4 + RET 10
gives 1452 T. Each write adds 164 T; the new aligned register lookup adds
22 T versus the previous 142-T write path. Reader and IRQ costs are unchanged.
Native fixtures check write counts 0/1/3/13/14 and a boundary inside a value
list. The ROM-text change adds **0 T to playback hot paths**; ROM output is
startup-only. ULA waits, HALT, disk and ROM execution remain separate from
these deterministic components and are included where applicable in Fuse.

Historical hybrid/PWM evidence remains under `reports/` and
`previews/*-hybrid.wav`; `1b5ae95f` retains its original TRD. The previous
AY-only disk is at `c7b3c794`, with evidence under `reports/ay-only/`. The
intermediate audio-repair checkpoint is under `reports/click-fix/audio-pass/`.
