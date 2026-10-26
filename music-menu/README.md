# AY-only TRD music menu

[ZX-Music-Menu.trd](../ZX-Music-Menu.trd) boots on **Spectrum128 + Beta Disk**
and plays the complete existing instrumental arrangements of **LumiÃ¨re
(3:42)** and **Alicia (2:38)** using the AY chip. The ULA beeper stays silent.

Both songs load into RAM once at startup. **Click either card with a Kempston
mouse, or press 1/2**, to start or switch songs immediately. **7/6** move the
selection while the current song continues; **Enter** starts the selection.
**Space** stops. Re-selecting a song restarts it. The menu and cursor remain
active throughout playback, and EOF leaves the menu ready for another choice.
The current song is green when a different card is selected in blue.
There is no mode key or beeper output path.

The cache is **40,081 bytes**, in three uncontended data banks `(0,4,6)`.
No disk access is needed for a switch or restart. Fuse measures about 6.1
seconds from the first cache read to ready; this is startup loading, not a
pause each time a melody is selected. The disk uses 222 data sectors and has
2322 free. Its 640-KiB image remains independently bootable.

## Sound and waveform selection

AY supplies three musical roles: lead, piano accompaniment and bass. The
original inner accompaniment voice is omitted, as in the previous AY mode.
All source JSON/playlist/note identities are preserved. Lead and piano use
tone generators with separate software attack/decay/release levels. Bass
uses the shared repeating **triangle envelope (shape 14)** on notes whose
integer envelope period stays within **18 cents** of the target; the other
notes use the more finely tuned tone generator. R13 restarts only on a
new selected bass note, never on every field. Only one channel owns the
shared envelope.

This triangle is the AY's stepped, nonlinear DAC envelope, not a programmable
linear waveform oscillator. A full up/down cycle has 64 internal steps:
`f = 1,773,450 / (512 * envelope_period)`. AY channel C's period 1 ultrasonic
tone gate halves the envelope's baseband amplitude after low-pass filtering;
all sound is generated inside AY, with register updates at the ULA field
rate. There are no CPU pulse-width or PCM-volume loops.

The [bounded timbre screen](reports/ay-only/timbres.json) compared normalized
12-harmonic spectra with the existing CC0 cello sample: square distance
0.266106, triangle 0.249832, saw 0.408128. Triangle is closer in this stable
spectral comparison, approximately 6.1% below square; this is not a whole-song
perceptual quality score. Integer-period tuning is checked separately.
The selected triangle notes have a maximum 16.982-cent error. Triangle is
used for 8077 LumiÃ¨re fields and 5294 Alicia fields. These arrangements have
new AY timbres and are not audio-equivalent to the source sampled players.
[Music and sample provenance](SOURCES.md).

Actual Fuse listening excerpts: [LumiÃ¨re](previews/lumiere-ay.wav) and
[Alicia](previews/alicia-ay.wav). Physical analogue filtering and chip
variants can affect the ultrasonic-gated envelope level. No physical-board
sound or subjective listening approval is claimed.

## Build and reproduce

Python 3.12+, NumPy, Pillow and pyz80; the native checks additionally use the
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
python music-menu/preview.py
```

Output goes to ignored `build/music-menu-ay-only/`: disk, assembler input,
listing and binary, delta streams, complete native/Fuse reports and traces,
recordings and an actual Z80 framebuffer PNG. Rebuilding needs no sibling
repository, sample download, MIDI, Node.js or external instrument bank.
Only re-running `probe_timbres.py --sample-folder <original-sample-folder>`
needs the existing cello WAV and its pinned manifest; it saves measurements,
not the sample audio. The retained report records the exact sample identity.

## Complete playback and live-menu verification

[Current build](reports/ay-only/build.json),
[native CPU](reports/ay-only/native.json) and
[complete Fuse evidence](reports/ay-only/verification.json) bind the exact
retained disk and player. Five tests cover original score identities,
delta/R13 restart contracts, complete foreground/menu replay, cached switching,
held-key debouncing, mouse wrap and clicks during playback, stop, EOF, all
register states, stack balance and a record crossing a physical bank boundary.

Each of two Fuse 1.9.0 runs cold boots the real TR-DOS loader, plays 100 ticks
of one song, switches to the other for 100 ticks, switches back and finishes
the entire selected song through EOF. Both complete songs pass: **18,991
full-song fields**, plus 400 preliminary fields, four switches and exact
verification of every actual AY data-port write. ULA interrupts never skip
a field, no song schedule drifts, and there is no disk read after ready.
The visible menu/cursor foreground runs on every field. Maximum measured
foreground work, including ULA contention and switching, is 23,741 T versus
a 70,908-T field. The menu command reaches song start within 1371 T after
dispatch (about 0.387 ms); input polling itself is once per field.
The actual first AY data write occurs within 1920 T (0.541 ms) of dispatch;
all registers of the new initial state are published within 4767 T (1.344 ms).

Fuse injects commands at the real menu dispatch point; no loader, audio
instruction or cached byte is patched. Native tests independently exercise
the keyboard and mouse port decoding. This is emulator verification, not a
physical-machine or other-clone qualification. The project's unrelated
[pre-existing catalogue coverage gap](reports/catalog-coverage.json) remains
recorded separately.

## Stream, memory and CPU accounting

RAM5 contains the 6912-byte display plus BASIC/TR-DOS workspace. RAM2 holds
the 16-KiB player image, screen template at 9000h..AAFFh, stack below BD00h,
IM2 jump at BDBDh and vector table at BE00h..BF00h. Old waveform tables and
PWM code are removed. Up to 98,304 cache bytes are available in the six
other banks; the two actual streams need only banks 0/4/6. All eight physical
banks are accounted for independently of host emulator memory.

A record is `duration U8, changed-register mask LE16, values in register
order`. Duration 0 is EOF; long holds split at 255 fields. Mask bits 0..12
update ordinary state; bit 13 explicitly restarts the envelope. The host
R13 sentinel 255 is never sent to the chip. The byte reader pages across
FFFFh even in the middle of a mask/value list. Each song table entry stores
its cache bank index and start address. Switching resets the chip and its
stream cursor without loading anything. Absolute note boundaries are rounded
once to `3,546,900 / 70,908` fields/second, with less than 10 ms error and no
per-pattern drift.

The [instruction table](../libraries/Z80_TIMINGS.md) supplies deterministic
CPU counts, independently cross-checked against actual assembled execution:

| Component | New CPU T | Previous player | Difference |
| --- | ---: | ---: | ---: |
| Sustained audio service with caller, UI excluded |92|176|-84|
| New row with 1 changed register, UI excluded |1635|1214|+421|
| New row with 3 changed registers, UI excluded |1919|1214|+705|
| IRQ body |18|46|-28|
| IM2 entry plus body |37|65|-28|
| Byte reader |75|No equivalent|New format|
| Boundary extra per crossing byte |185|Different record format|New format|
| Ordinary unchanged UI work |3907|Not active during playback|New feature|

These are component comparisons with explicitly different stream/features,
not a claim that the whole new foreground is faster. A held `music_tick`
is 13+4+7+4+13+10=51 T; its main caller costs 41 T, giving 92 T.
A new delta record costs **1452+142*w T** for `w` changed registers, plus 185 T
per bank crossing and 41 T for its main caller. Header 365 + mask loop
(13*77+72)=1073 + NOP 4 + RET 10 =1452 T; a written bit adds 147 T of
fetch/select/output and replaces a 12-T branch by 7 T, net 142 T.
The normal reader is 16+4+4+12+7+6+16+10=75 T. Boundary work adds 185 T.
Native fixtures check write counts 0/1/3/13/14 and an actual boundary inside
a value list. IRQ is EI 4 + RETI 14, plus 19 T hardware entry.

ULA WAITs, HALT, physical disk and ROM time are excluded from those CPU
components. The separate complete Fuse results include actual ULA/ROM/disk
behavior. Old PWM build reports and hybrid excerpts remain as historical
comparison evidence under `reports/` and `previews/*-hybrid.wav`; Git commit
`1b5ae95f` retains their exact original TRD. They are not modes on this disk.
