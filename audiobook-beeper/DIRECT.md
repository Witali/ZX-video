# Direct packet pointers: accurate playback speed

**Disk retirement (2026-10-04):** obsolete speech TRDs described below
were removed at the user's request. Links marked "retired" lead to the
[removal inventory](retired-disks.json), with exact paths, hashes and the recovery
commit. Measurements, WAVs and build instructions remain historical evidence.

**New user feedback, 2026-10-03:** the mean speed is accurate, but the user
hears voice flutter. [Clock-aware analysis](VOICE_TIMING.md) finds periodic
within-frame sample timing errors hidden by the earlier SNR reference.
This remains an experiment, not an accepted clean-voice release.

Use [the direct-player TRD (retired)](retired-disks.json) with
Spectrum 128 and Beta Disk/TR-DOS, without turbo. The English loading
message disappears before playback, and the audio repeats automatically.
[Actual Fuse WAV](experiments/ima-direct/result-preview.wav),
[original PCM8](experiments/ima-direct/source-preview.wav),
[complete measurements](experiments/ima-direct/report.json).

This preserves every byte of the earlier packet experiment's 186880-sample
PCM8 source and 93440-byte IMA stream. No resampling, pitch correction or
shortening is used. Two complete Fuse loops give **8003.3268 samples/s**,
only **+0.0416%** relative to 8000 Hz, and **128053.23 output writes/s**.
The first loop takes **23.35034 seconds** versus 23.36 seconds of source.
Across both loops, all 3730 sliding 0.1-second windows and 3658 one-second
windows (100-source-sample hop) meet the user's +/-2% speed limit. Worst
deviations are **0.1112%** and **0.0501%**, respectively.

Actual-timing total SNR improves **17.2551 ->18.8455 dB**. The native model
without ULA is 21.1982 dB. This is progress, not achievement of the 20-dB
goal. The same 70-Hz HP/two 4.5-kHz LP measurement follows actual sample
boundaries and excludes 0.1-second edges; no fitted gain or delay is used.
The actual WAV comes from Fuse's normal-speed sound generator. Physical
hardware has not been measured.

## Direct table and memory

The [ASM](direct-player.asm) removes the intermediate lookup of the second
code pointer. Each table entry contains first pointer, second pointer, and
DE containing D=16 plus the next compact state offset. POP HL / POP IY /
POP DE read these six bytes. Alternate DE replaces IY as the IMA cursor.
The first code sequence prepares the following packet-table cursor while
finishing the current packet, then jumps directly through IY.

The feedback recurrence still has 32 mathematical states. Exhaustive
successor closure from initial state 16, over all 64 PCM bins, reaches only
18 states: 2,4,6,8,10,12,14,15,16,17,18,19,21,23,25,27,29,31. Compact
remapping changes no decision or recurrence. All 2048 mathematical entries
are checked against an independent exact rational implementation. Only
128 first and 86 second code patterns are needed.

Each 256-byte PCM page contains 108 bytes of six-byte entries. Two IMA
decoder rows can fit at offsets 128/192. Four packet pages that would
overwrite TR-DOS workspace at 5C00..5FFF are instead placed in fixed bank 2.
A single 256-byte high-pointer table maps PCM8 to its packet page. Of the
89 IMA rows, the 25 most-used incoming indices are placed in fixed bank 2:
eight share the relocated packet pages and 17 occupy an extra 1088 bytes.
They cover **65.175%** of decoding operations for this source. Remaining
rows fit bank 5's packet-page gaps. All 89 rows remain supported.

Total RAM accounting remains 93440 audio +6912 shadow screen +16384 bank-5
tables/workspace +14336 bank-2 resident reserve =131072 bytes. Audio banks,
capacity, terminal predictor/index 0/0 and continuous modulator state are
unchanged. Startup reads 425 table/audio sectors; playback performs no disk
I/O. The resident reserve includes alignment/unused table gaps.

## Timing and complete checks

The first eight holds are **36/28/28/31/24/26/22/20 T** (215 total), and the
second eight **22/26/22/30/31/27/34/16 T** (208 total). Both nibble paths are
**423 T/sample**, down **45 T** from 468 and 10.25 T below the original
eight-output feedback player's 433.25 T. This uses the same standard Z80
instruction timing table as [the packet baseline](PACKET.md): additional
instructions are POP IY=14, JP(IY)=8, LD A,(DE)=7, INC E/D=4. Three NOPs
and JP balance the low tail's 22 T against the high tail's EXX/INC/JP/EXX.

An ordinary 256-byte page adds 14 T. A bank adds 140 T, including both
indirect jumps; the initial hand count missed one JP and was corrected
after native timing verification without changing the binary. The extension
is now on slot 14 (before the last output), sample `2*end_byte-3`.
The full CPU loop is `186880*423 +358*14 +7*140 =79056232 T`, **8410969 T
less** than the previous disk. ULA adds 7529822 T over two loops, separately
from preload ROM/disk execution. Maximum actual hold is 185 T, so average
output frequency is not a fixed instantaneous-period guarantee.

Two continuous native and cold Fuse loops check **5980161 bits /373760
predictors and indices**, complete paging and loading-message behavior.
Native checks also prove every interval and all protected RAM. FFmpeg IMA
WAV decoding independently agrees on every input sample. Normal-speed
recording covers two wraps with correct paging and signal in all complete
half-second windows. The recorder's obsolete literal date was corrected
for this 2026-10-03 capture, and future captures use the actual local date.
The full trace remains in `.tmp/direct-packet`; its hash and all output
timestamps are committed with the evidence.

```powershell
python audiobook-beeper/build_direct.py --output build/ima-direct --fuse <fuse.exe> --ffmpeg <ffmpeg.exe>
```

The first assembly attempt required explicit ASSERT statements on macro
labels for pyz80. A following native attempt detected the 10-T bank count
error described above. Both issues are resolved in the complete evidence.
