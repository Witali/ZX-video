# Exact second-order packet experiment — rejected for quality

2026-10-05. The user requested second-order sigma-delta at 128 kHz, with
64 kHz as a fallback. The existing IMA3 kernel executes the new tables at
**127652.961 Hz average**, but the result is noisier. Keep the accepted
damped-feedback modulator as the default. This is a saved unsuccessful
experiment, not a quality upgrade. The user also reports increased noise.

The optional [TRD](../../../ZX-audiobook-SD2-128-test.trd) and
[actual Fuse sound-generator WAV](result-preview.wav) preserve the final
guarded experiment. [Source WAV](source-preview.wav). The previous accepted
disks, including the public YouTube-linked file, are unchanged.

## Algorithm and tradeoffs

[sigma_delta2.py](../../sigma_delta2.py) uses exact integer packet state:

```
q = e_previous - e_older
u = x + q + e_previous
bit = (2*u >= Q)
e_new = u - Q*bit
q += x - Q*bit
```

This is `u=x+2*e_previous-e_older`, with a second difference of the error
and two DC zeros in **decision index**. It is not a uniform-clock physical
128-kHz DAC: actual OUT intervals are nonuniform, 12..175 T in this trace,
including bank transitions. The old beta=.5 feedback has one DC zero.
General noise-shaping background: [Analog Devices MT-022](https://www.analog.com/media/en/training-seminars/tutorials/MT-022.pdf).

For Q=64 and declared gain 3/8, all possible sequences of the admitted
input values close on 14 exact packet states. No error-state rounding,
clipping or damping is used. All 4096 padded lookup cases match a separate
two-history implementation. Only input levels are quantized: there are
25 distinct levels (20..44). The gain is 0.375, or -8.519 dB amplitude;
measurement scales the reference by that known gain, never by a fitted gain.
This coarse input precision and nonuniform timing compromise the benefit
of the higher-order recurrence.

The full-source ideal-clock controls, without IMA, score 16.713280 dB for
Q32/half gain, 19.047102 dB for Q64/3/8 gain, and 15.878505 dB for Q64/quarter
gain. Q64/half gain exceeds bank-2 code/table space; Q128/3/8 needs 30 states,
which exceed the current half-page layout. These are implementation-specific
failures, not impossibility proofs for other architectures.

## Complete results and the repeat fix

All measured disks retain the same 186880 prepared PCM8/8-kHz samples
(23.344 s of speech plus 128 silent samples). The original accepted speech
reference scores **20.436321 dB**. The same listening filter and 100-ms edge
exclusions are used throughout: 70-Hz high-pass and two two-pole 4500-Hz
low-pass sections. Scores include distortion as well as noise.

| Variant | First loop, dB | Second loop, dB | Decision |
| --- | ---: | ---: | --- |
| Old IMA codes with new SD2 tables | 2.456665 | 2.451909 | Reject |
| One new waveform search, no state reset | 11.179067 | 1.133075 | Reject; repeat regression |
| Same search, reset in final silent guard | 11.179067 | 11.179067 | Correct repeats; still reject for quality |

The single full host search used width 256, horizon 128, commit 64 and PCM
prior .003; search time was 101.485 s. Its 11.179067-dB host score did not
prove repeat quality. Both complete Fuse loops exposed the second-loop
regression. The final guard now initializes feedback before generating the
last silent packet, so the next loop starts from the same state as encoding.
No active speech packet resets its feedback. No additional encoding search
was needed. The initial run's reports and noisier recording are retained.

The guarded disk passes cold Spectrum 128/Beta startup, all 5981841 output
bits and 373760 predictor/index samples over two complete native/Fuse loops,
memory guards, paging, 32 loading progress updates and message hiding.
Both loop phases are exact (0/0 T); speed error is -0.299133%, within +/-2%.
Normal-speed Fuse recording completes both loops and verifies paging.
This is not a physical Spectrum measurement or user acceptance of SD2.

## Timing and memory

Ordinary IMA3 work remains **427.375 T/sample**, delta **0 T**; page/bank
extras remain +14/+140 T. The optional guard reset adds `LD E,n`, **7 T once
per loop**, after the final silent filler. Instruction timings follow the
[Zilog manual](https://www.zilog.com/docs/z80/um0080.pdf). Calibration reduces
filler padding from 48 to 41 T, exactly compensating this extra instruction.
Native cycle totals therefore remain 79891688 T. Complete Fuse execution
adds 6424976 ULA wait T over two loops. Disk/ROM startup is separate:
334 sector reads, 22.815238 s to sound in the normal-speed capture, and no
disk reads during resident playback. Mean 128-kHz output does not mean that
every instantaneous interval is that short.

Bank-2 code/table reservation rises from 13312 to 16128 bytes (+2816).
Packed resident audio remains 70080 bytes; no PCM/PDM buffer or IMA4
expansion is introduced. The 16384-byte bank-5 workspace/tables, 6912-byte
shadow screen, sector alignment and all decoder rows are accounted for in
player metadata. Maximum packed capacity falls from 94458 to 91641 bytes
(251888 to 244376 source samples). This is another reason not to make the
experiment the default, particularly after the user's request to retain
the current duration and compression.

## Reproduction and provenance

With the repository Python packages, FFmpeg and Program Files Fuse available:

```powershell
python audiobook-beeper/experiments/sigma-delta2-128/run.py --output build/sd2-new --fuse <fuse.exe> --ffmpeg <ffmpeg.exe>
python audiobook-beeper/experiments/sigma-delta2-128/repair_loop.py --run build/sd2-new --output build/sd2-guarded --fuse <fuse.exe> --ffmpeg <ffmpeg.exe>
python audiobook-beeper/record_pcm.py build/sd2-guarded --output build/sd2-sound --fuse <fuse.exe> --machine 128
```

The first command intentionally reproduces the original failed selection;
the second reuses its encoded data with the repeat fix and new full checks.
Do not resume a run whose producer identity changed. The archive contains
the initial identity separately from final [producer snapshots](producers).
[archive.py](archive.py) proves that final sources rebuild all three executed
disks byte for byte, then copies their own complete checks and hashes the
saved artifacts. The guarded build has its own independent proof.

Eighteen targeted tests pass, including byte-exact rebuilding of an accepted
legacy disk. An initial sandbox test could not import pyz80 in its child
process; the identical test command outside that restriction passed. No
failing test is treated as evidence of success.

The earlier IMA3/IMA4 quality study remains paused. No 64-kHz fallback was
needed to meet the requested output-rate experiment; neither rate alone
establishes the later 30-dB quality target.
