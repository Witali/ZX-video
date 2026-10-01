# Live PCM paging correction

The user reported that the live disk became silent after about one second
in Fuse, with Spectrum 128 selected. The original image remains in
`pcm-live-preview`; its SHA-256 starts `12163ecf5f206ac6`.

An explicit `--machine 128 --beta128` sound-enabled run completed two loops.
A second run without an explicit machine argument reproduced the failure:
FMF timing code A, the first bank audible, then silence. A separate debugger
trace shows that writes intended for 7FFD reached **1FFD**, while the 7FFD
latch stayed at 10h. The `10FD..17FD` shortcut is ambiguous on an extended
port decoder. The exact automatically selected model was not established;
the observed latch behavior, rather than an assumed model name, identifies
the cause. The CPU continued running.

The corrected player keeps 7FFD in BC' and switches with `EXX` (4 T),
`LD E,n` (7 T), `OUT (C),E` (12 T), `EXX` (4 T): **27 T**, replacing
the old **26 T** sequence. This is **+1 T per bank**, +6 T for the unchanged
82944-byte excerpt. The conversion kernel remains 32 T; the ordinary four
sample block remains 1764 T. Native playback is 36579030 T per loop.
Instruction timing follows the [Zilog manual](https://www.zilog.com/docs/z80/um0080.pdf).

The [corrected short build](pcm-live-fixed/report.json) and
[complete verification](pcm-live-fixed/verification.json) check two full loops
plus the next bit: 1658881 exact PCM/PDM outputs, all bank latches and no
runtime disk reads. Spectrum 128 actual PDM averages 78783.428 Hz, minimum
51404.348 Hz, loop duration 10.528161 seconds. Canonical port contention is
included in those measurements, separately from deterministic CPU cost.

The [normal-speed audio capture in automatic mode](paging-fix-evidence/fixed-short-auto/report.json)
also completes two loops, preserves 1FFD, updates 7FFD correctly and contains
signal in every half-second window. [Listen](paging-fix-evidence/fixed-short-auto/fuse-preview.wav).
This is Fuse's sound generator recording, not a physical speaker measurement.
The [diagnostic archive](paging-fix-evidence/diagnosis/report.json) preserves
the original success, reproduced failure and latch trace, with their scripts.

Reproduce the sound-enabled check with:

```powershell
python audiobook-beeper/record_pcm.py audiobook-beeper/pcm-live-fixed --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output build/fixed-audio --machine auto
```

The user subsequently requested filling all usable RAM with audio. The short
build is retained as the isolated paging correction baseline for that work.
