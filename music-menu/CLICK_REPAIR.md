# AY control discontinuity and Fuse counter audit

The 2026-10-26 repair starts from `c7b3c794`, after the user reported
periodic clicks and small stutters in Fuse. The original full traces already
showed no missed Spectrum fields or playback disk reads. This separates
target delivery timing from control-signal artifacts and host audio work.

The old compiler set the unused envelope period to zero for 3028 Lumière
fields and 2592 Alicia fields. The published Fuse AY loop increments its
counter during a zero period, breaks without subtracting it, and can consume
the accumulated counter when a nonzero period returns before R13 resets it.
The [bounded audit](reports/click-fix/audio-pass/analysis.json) predicts bursts
of 3047/167 loop iterations in one renderer step during the first 16 seconds.
This is an algorithm-level explanation, not a measured sound-card underrun.
The new stream retains a positive envelope period, parks the disabled noise
generator at 31, and mutes before resetting/parking the chip. The same audit
has maximum 1 iteration and no accumulated-counter restorations.

The old numerical register order also enabled R10's envelope bit before
R11/R12/R13 were prepared. New mask slots explicitly encode
`0,1,2,3,4,5,6,7,11,12,13,8,9,10`: oscillator/envelope state precedes channel
volume/enabling. Existing delta records are not interchangeable with this
schema. A lookup table at 8C00h maps slots to actual AY registers.

Short string/cello articulation gaps receive legato release bridges of at
most 65 ms, without moving note-on positions or changing score files. Connected
triangle notes preserve their running envelope phase instead of resetting
it. Restarts drop from 111 to 37 for Lumière and 53 to 15 for Alicia; envelope
mode edges drop 221→73 and 105→29. Piano attack/decay and isolated releases
also use a softer level trajectory. Tone tuning and the 18-cent triangle
selection limit remain unchanged.

The 16-second same-phase DAC diagnostic excludes ordinary square-wave edges:
it measures a command immediately before/after at the same chip phase.
Squared step sums change 0.997522→0.255382 / 0.911343→0.201647, reductions
of about 74%/78%. Maximum normalized steps change 0.333333→0.102780 and
0.211775→0.102780. These are control-discontinuity proxies, not audible-click
counts, SNR or a perceptual quality score. The baseline logical streams
exactly reproduce their saved pre-repair frame hashes.

Seven tests, complete independent Z80 foreground replays and both full
Fuse cold-boot/switch/EOF runs pass for the audio repair. Every actual AY
transaction matches the new stream, including register order and mute
ordering. No ULA field is skipped and there are no disk reads after ready.
The three-bank cache is 39304 bytes (40081 before),219 data sectors.
The later ROM-menu change is separately qualified with the final artifact.

Deterministic CPU counts use the project instruction table. The byte reader
and sustained field remain 75 T and 92 T with caller. New records cost
`1452+164*w` T, versus `1452+142*w`: +22 T per written register for the aligned
register lookup. A one-/three-write audio field is 1657/1985 T versus 1635/1919,
deltas +22/+66 T. A cross-bank byte still adds 185 T. Mute is 1164 T versus 951,
delta +213 T. IRQ body 18 T and hardware entry 19 T are unchanged. Native fixtures
check 0/1/3/13/14 writes and a boundary in a value list; ROM, ULA and disk costs
remain separate. Both full Fuse runs measure maximum foreground 22489 T of
70908 and command-to-first/all-initial AY writes 2155/5288 T.

Reproduce the audit with:

```powershell
python music-menu/analyze_clicks.py --node C:/Tools/Node/node.exe
python music-menu/build.py
python -m unittest discover -s music-menu -p test_player.py -v
python music-menu/verify.py
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --song lumiere
python music-menu/verify.py --fuse C:/Tools/Fuse/fuse.exe --song alicia
```

The audit uses the existing vendored Ayumi renderer without changing it.
Its register event times use the independently measured decoder paths,
rounded to 44.1 kHz sample positions. The Fuse counter model approximates its
32-T renderer step; full runtime publication checks remain separate.

Reference: [published Fuse sound.c AY loop](https://raw.githubusercontent.com/speccytools/fuse/master/sound.c).
