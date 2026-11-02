# Autoplay, repeated-note articulation and AY envelope audit

Release date: 2026-11-02. Baseline: `67b19924`, TRD SHA256
`80da9ca73e81cd38c65842d066fed930850d449e6b3a31fc0a494ab41b9ef607`.
The rebuilt independently bootable TRD is
`3ae7d156f12baba8f551f893dc50d4fcd1d5331495ae0167ab59c95ba3209e71`.

After caching both songs, the player enables interrupts directly before
HALT and starts Lumiere on the first ULA field. It reuses ordinary choose
and menu completion code. The following fields use the existing loop;
there is no recurring autoplay condition. Browser users still press the
website's Play disk button to start the machine and enable browser audio.
No Spectrum keypress is needed. Stop, restart, selection and EOF behavior
remain available.

## What the envelope audit found

The previous click repair bridged adjacent string events, including distinct
same-pitch notes. At all 61 close repeated-lead boundaries in Lumiere,
volume stayed at 13 across the boundary. The notes therefore sounded tied.
The source arrangement itself contained distinct events.

The generator now ends the preceding release two ULA fields before the next
onset, disables its legato bridge and gives the following note a fresh soft
80-ms attack. Two actual zero-volume fields separate these events:
**39.983 ms** at the existing 50.021-Hz field clock. The same rule fixes four
Alicia boundaries. Explicit score ties have already been merged into one
event and remain continuous. Note-on grid, pitches, source score identities,
playlist and total durations are unchanged. The intentional early release
is separate from the unchanged rounded-grid timing error below 10 ms.

Lead and piano amplitude envelopes are software levels in R8/R9. Tests check
monotonic attack/release around a synthetic repeat, actual silent fields at
every repeated source boundary, and continuity across a true tie. They also
check stream replay, generator-before-volume write order and R13 sentinel
handling. These are control-rate envelopes, with one level per ULA field.

Bass uses the **shared hardware shape-14 envelope as an audio waveform**, not
an independent ADSR for every note. Registers 4/5/10/11/12/13 remain identical
to the baseline at every field of both songs. Its 37/15 explicit restarts,
8328/5429 triangle fields and maximum 16.982-cent pitch error are unchanged.
Unused envelope period stays positive; the other channels never enable ENV.
The shared envelope cannot independently control three note amplitudes.

## Noise percussion within three AY voices

All three channels already carry notes. Quiet hat/brush pulses use only
literal piano rests on B, without replacing a pitched event. They disable
B's tone and enable its noise for one field (19.992 ms), changing only
R6/R7/R9. A/C mixer bits, their volumes and the shared bass envelope stay
unchanged. Noise periods 4/12 and levels 5/7 give alternating accents.

Candidates follow absolute quarter-note positions, including Alicia's
meter/tempo changes. A hit uses a free field on the rounded beat or the
preceding field next to an actual piano note. Some accents therefore occur
slightly early; exact advances and every hit are retained in build metadata.
This is sparse percussion, not a fourth independently available voice.
Lumiere contains **295 hits**, Alicia **174**.

## Complete execution and timing

Both songs pass complete independent native Z80 execution and cold Fuse
1.9.0 real128/TR-DOS execution. The first run plays all 11,105 Lumiere fields
automatically with no commands; the second tests three live switches and
all 7,886 Alicia fields. All actual AY writes match, no ULA field is skipped,
schedule drift is zero, EOF mutes and leaves the menu active. There are
168 startup TR-DOS reads and zero reads after ready.

Measured maximum complete foreground work, including contention and live
switching, is **22,489 of 70,908 T** per field; initial automatic foreground
is 19,685 T in Fuse (19,356 plain native T). One-time autoplay control adds
CALL 17 + JP 10 = **27 T**. EI/NOP reorder costs zero extra T. HALT/IRQ
waiting and disk loading are separate from deterministic CPU accounting.
Instruction timings come from [the instruction table](../libraries/Z80_TIMINGS.md).

The decoder still costs `1452 + 164*w` T per new record before its 41-T
caller, plus 185 T on a bank-crossing byte. Held service including caller
remains 92 T, mute 1164 T and IM2 entry plus handler 37 T. Every per-call
before/after difference is zero. Additional musical events increase total
audio CPU, including choose/its external CALL, as follows:

| Song | Baseline T | New T | Difference |
| --- | ---: | ---: | ---: |
| Lumiere | 9,880,537 | 10,501,777 | +621,240 |
| Alicia | 5,928,394 | 6,139,315 | +210,921 |

UI, ULA waits/contention, IRQ and ROM/disk costs are excluded from these
totals and covered separately by Fuse. Streams grow from 39,304 to
**42,865 bytes**, still in uncontended banks 0/4/6. Disk usage grows from
219 to **233 sectors**, leaving 2311 free. Initial cache loading measures
23,164,532..23,189,018 T (about 6.54 seconds in Fuse). All eight 128-KiB
banks retain the allocation described in the main README.

## Reproduction and retained evidence

[Build](reports/autoplay/build.json), [native execution](reports/autoplay/native.json),
[note/envelope audit](reports/autoplay/note-envelope-audit.json),
[CPU comparison](reports/autoplay/timing-comparison.json),
[complete Lumiere Fuse run](reports/autoplay/fuse-lumiere.json) and
[Alicia with switches](reports/autoplay/fuse-alicia.json) bind the actual disk.
The traces retain numeric debugger events only; full raw traces remain in
ignored build output. The evidence index records both hashes.

Run the main README commands. To reproduce the CPU comparison, also build
and native-verify `67b19924` in a separate output directory, then run:

```powershell
python music-menu/audit_timing.py --baseline-output build/music-menu-baseline
```

Actual Fuse captures are 36 seconds for Lumiere (including repeated F#4
notes around 30 seconds) and 12 seconds for Alicia. Capture reports record
WAV hashes, bass frequency and clipping counts. These are real software
sound-generator recordings, not physical-chip or subjective listening proof.

The [browser-core integration smoke](reports/autoplay/web-smoke.json) binds
the same TRD and pinned core. Before any key input it observes 2189 AY data
writes and 1,995,380 nonzero samples. Separate 3.1-second excerpts have
nonzero left/right energy for both songs and peaks below 0.346; swapping a
disk preserves mapped memory and PC. A separate normal-speed built-in
browser check reaches the visible PLAYING state from Play disk without
Spectrum keypresses, with no captured console warnings/errors. This is
browser integration coverage; complete ULA timing qualification is the
independent Fuse result above.

## Alicia follow-up

The same articulation and sparse-noise changes already apply to Alicia.
Its four repeated C5 boundaries occur at source seconds **54.190981,
71.777188, 118.328912 and 135.915119**. The complete cold-Fuse trace above
verifies their actual AY writes, including the two silent lead fields.
The 174 noise accents use piano rests and preserve the bass envelope.

An additional actual **59.985-second Fuse capture** has zero clipped samples
and a 65.356636-Hz measured initial bass peak (65.354142-Hz target).
[Capture report](reports/autoplay/alicia-60s-recording.json).
The [8-second audition](previews/alicia-repeat-ay.wav) copies source seconds
50..58 without processing, with the first rearticulated C5 about 4.19 seconds
into the clip. [Source/output hashes and slice](reports/autoplay/alicia-repeat-excerpt.json).
The remaining three repeats are covered by complete execution, not by this
partial audio excerpt. No further target code/data or CPU cost changed.
