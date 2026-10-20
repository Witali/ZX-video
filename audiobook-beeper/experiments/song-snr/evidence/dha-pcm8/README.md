# Resident PCM8: counted 8 x 56-T native kernel

The standalone [kernel](kernel.asm) retains all 256 unsigned PCM8 levels and
executes eight first-order output decisions at exactly 56 T each: 448 T per
PCM sample, or 8 kHz PCM / 64 kHz output at Pentagon 3.584 MHz. This is a
bounded CPU mechanism for audio decoded into RAM while loading. It performs
no DHA decoding during playback and changes no existing player or encoder.
The [report](report.json), [reproducer](uniform8.py), assembled bytes/listing
and saved resident-bank trajectory retain the proof.

Each pulse is `ADD HL,DE` 11 + `SBC A,A` 4 + `AND C` 4 + `OUT (FE),A` 11
= 30 T. `DE=PCM8<<8`, `HL` is a persistent modulo-65536 accumulator and
`C=16`; the only output values are 0 and 16, keeping MIC and border zero.
With uniform holds the accumulator identity is also exact in physical time:
`56*sum(target/65536-bit) = 56*(final_accumulator-initial_accumulator)/65536`.
The source contributes eight bits, rather than the existing six-bit table
quantizer. This makes no quality claim for the lower output decision rate.

Every gap has exactly 26 T, including the loop jump:

| Gap | Actual work | Useful T | Free T |
| --- | --- | ---: | ---: |
| 1 | EXX / LD A,(DE) / EX AF,AF' / EXX | 19 | 7 |
| 2..6 | padding | 0 each | 26 each |
| 7 | EXX / INC DE / EXX | 14 | 12 |
| 8 | EX AF,AF' / LD D,A / JP packet | 18 | 8 |

The free slots are separated by output deadlines; their sum is not one
contiguous budget. AF' owns the prefetched byte from gap 1 through gap 8.
Main HL/DE/C and alternate DE are live; main A/F are scratch. Main B/IX/IY,
SP/I and alternate BC/HL are preserved and available to a future handoff.
No CALL, PUSH, stack lookup, RAM write or interrupt occurs. `LD A,R` appears
only as padding whose A/F values are dead before the next output.

Native `z80.Z80Machine` execution covers all 65,536 input-byte / accumulator
high-byte pairs, with the low accumulator byte fixed to a nonzero canary
0x5A. Every pulse bit and accumulator state matches the independent integer
recurrence; the low byte is invariant because all targets are multiples of
256. This also proves that lower accumulator bytes cannot change the
eight-bit result. A common-phase 127/128 witness flips an actual output
bit, demonstrating retention of the input's least significant bit.

The additional 16,383-sample sequence emits 131,064 outputs, exercises all
source pages and preserves all guarded registers and RAM. Its final source
byte is prefetched; the cursor then wraps, and execution stops before any
out-of-bank read. No bank handoff is implemented. Across all directed and
trajectory cases, 655,368 native output events pass; all consecutive holds
are 56 T and all complete packets are 448 T. The emulator callback observes
the first output at 29 T; the instruction completes at 30 T. This fixed
one-T observation offset is recorded, with no clock fitting or drift.

The absolute packet cost is 448 T, a difference of -1 T from the released
449-T Spectrum packet, and zero from the optional 448-T experiment. The
other project's DHA firmware reports 800 T per live-decoded sample at
20 MHz; the numerical difference is -352 T because decoding has moved to
loading. This is not a drop-in optimization of that decoder. At Scorpion
3.5 MHz the unchanged kernel would run at 7812.5 Hz; no clone adaptation is
claimed.

Run from this directory after setting the existing test dependencies:

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/.worktree/audio-snr-research/.tmp/runtime;C:/Work/ZX-video/.tmp/lzma-z80-packages;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper;C:/Work/ZX-video/.worktree/audio-snr-research/toolkit;C:/Work/ZX-video/.worktree/audio-snr-research/audiobook-beeper/experiments/song-snr'
& 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B uniform8.py
```

DHA decoding, whole-song RAM allocation, bank handoff, all-clone clocks,
loading/progress UI, EOF, bootable TRD, Fuse/physical playback and audio
quality remain unproved here. The kernel is first order; no second-order
or full-16-bit source claim is made.
