# Score and implementation provenance

Imported on 2026-10-26 at the user's request from their local projects.
No network retrieval, source recording, MIDI binary, sample bank or old ROM
is required to rebuild this disk.

The two JSON files are exact copies of `audio/assets/scores/expedition-33/score.json`
and `alicia-score.json` in `z80-tester`. [Import reference](reports/import-reference.json)
records their SHA-256 identities and the complete expanded four-role timelines.
The adapted [arranger](arrangement.py) was checked against the original
`audio/music/expedition-33/sampler/src/build.py` functions, including every
playlist occurrence, tied note, fractional duration, transposition and new
accompaniment fill. Its normalized source hash is saved in the same report.
[balance.json](balance.json) copies the original project's role balance
(SHA-256 `057f11d2cf6c0899b25268699c06ec94f709e9e2fb0bf9aca09f2a625367086c`).

Lumière and Alicia are by Lorien Testard and Alice Duport-Percier. The
source arrangements credit the VGLeadSheets transcriptions by
[Nicholas Pinelli for Lumière](https://vgleadsheets.com/view/clair-obscur-expedition-33/lumire)
and [Jer Roque for Alicia](https://vgleadsheets.com/view/clair-obscur-expedition-33/alicia).
These are the existing simplified instrumental adaptations, with newly
written accompaniment, fixed-tempo fermatas/ritardando and octave changes
already described in the imported scores. They are not original orchestral
recordings. The compositions and transcriptions are not CC0.

`z80-tester`'s PWM8080 engine and MicroMusic's i8080 PWM / UM88 examples
informed the software pulse-width, wavetable and compact-event approach.
Their firmware and MCU drivers are not copied. This Z80 player is new:
16-bit single-voice DDS and complementary NOP ladders on the Spectrum beeper,
with three AY accompaniment channels. The beeper uses a generated sine,
with 16 volume pages and 16 pulse widths; no recorded instrument is included.
AY mode assigns its three channels to lead, piano and bass, omitting the
inner accompaniment voice. Hybrid retains all four arranged musical roles.
The 50-field quantization, AY square waves, sine lead and new envelopes
change the sound; preservation of the imported notes is not a claim of
audio equivalence to the source players.

The builder reuses this repository's BASIC/TRD directory writers from
`audiobook-ay/player.py` and `toolkit/`. The target ROM read sequence follows
the existing standalone AY player. No movie decoder or other player is modified.
The [Z80 timing reference](../libraries/Z80_TIMINGS.md) and
[Zilog manual](https://www.zilog.com/docs/z80/um0080.pdf) supply instruction counts.
Kempston mouse port/counter/button conventions were checked against the local
Fuse `peripherals/kempmouse.c` implementation (X increments right, Y up,
active-low buttons). Fuse and the independent `z80` Python CPU retain their
own licenses and are external build/verification tools.
