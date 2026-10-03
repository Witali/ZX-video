# Bootable packet PDM experiment

Acceptance update, 2026-10-03: the user requires playback speed/pitch within
**+/-2%** of the original. This delivered experiment fails that gate as well
as the 20-dB SNR goal; do not treat it as the accepted final player.

Use [the separate TRD](../ZX-audiobook-IMA-ADPCM-packet-test.trd) with
Spectrum 128 and Beta Disk/TR-DOS, without turbo. Start the boot program
(`RUN` in TR-DOS if automatic disk boot is disabled). Loading takes about
26 seconds in the checked Fuse setup. **Loading audio data** disappears
before playback. The excerpt repeats; reset stops it.

[Actual Fuse audio](experiments/ima-packet/result-preview.wav),
[original PCM8 source](experiments/ima-packet/source-preview.wav),
[filtered port reconstruction](experiments/ima-packet/packet-bandlimited-preview.wav),
[complete report](experiments/ima-packet/report.json).

The input is 186880 mono unsigned 8-bit samples at 8000 Hz (23.36 seconds),
encoded as 93440 bytes of standard four-bit IMA ADPCM. Playback decodes IMA
on the Z80 and emits 16 one-bit decisions per sample, using compact sequences
of constant OUT instructions. It does not expand the recording into a PCM
or PDM buffer. A 32-state integral-feedback table selects the two code
sequences and the next state. The table accounts for the ordinary, unequal
instruction intervals; it cannot predict ULA waits or page/bank extensions.

The measured stock Fuse128 average is **116245.69 outputs/s** and
**7265.36 samples/s**. The first loop takes **25.72223 seconds**. This plays
about 9.18% slower/lower than the 8000-Hz source; no pitch correction is
applied. The longest hold is 192 T (54.13 microseconds) at a bank boundary:
the average is not a minimum instantaneous frequency guarantee.

Total reconstruction SNR is **17.2551 dB**, modulation-only SNR 18.0449 dB,
and codec SNR 25.1981 dB. These use actual full-loop Fuse output timestamps,
the existing 70-Hz high-pass and two 4.5-kHz low-pass listening filters, and
the full source except 0.1 seconds at each edge. Each reference follows its
actual sample boundaries; there is no fitted gain, delay or tempo correction.
The native CPU model without ULA gives 20.4512 dB on this shorter excerpt,
but that is **not achieved in Spectrum128 emulation**. The WAV is a separate
normal-speed capture of Fuse's sound generator, with no added filter/gain.
No physical computer or speaker has been measured.

## Memory and repeat

| Allocation | Bytes |
|---|---:|
| IMA in banks 0, 4, 6, 1, 3 | 81920 |
| IMA at bank 7 DB00..FFFF | 9472 |
| IMA at bank 2 B800..BFFF / paged F800..FFFF | 2048 |
| Shadow screen in bank 7 | 6912 |
| Bank 5: decoder, packet table, stack/TR-DOS workspace | 16384 |
| Bank 2: startup, compact codebooks, pointer tables/padding | 14336 |
| Total | 131072 |

The decoder occupies 4000..563F, the packet table 6000..7FFF. The screen
uses bank 7, leaving fixed bank 5 available for tables. Startup stack is
below 6000; live playback uses SP as a read-only lookup cursor and disables
interrupts. All 420 decoder/table/audio sectors load before playback.
There are no runtime disk reads. The self-contained TRD occupies 512 file
sectors, excluding its 16 directory/system sectors.

The last 20-ms fade is followed by 128 silent samples; the encoder must end
at predictor=0/index=0. This lets the two-sample-ahead decoder pass through
the loop without a reset or a missing sample. Modulator state is continuous.
The source prefix otherwise matches the earlier prepared audiobook excerpt.

## Counted instruction timing

The authoritative [ASM](packet-player.asm) is compiled by external pyz80;
[Python](packet_player.py) emits constants/data and packages the resulting
binary. Only patterns present in the complete table are compiled: 156 first
and 82 second sequences. Second-sequence indices avoid 40..7F so the high
byte of OUT (C),D/0 never selects a contended port address. ED71 assumes the
original NMOS Z80 zero-output behavior.

Instruction counts use standard Z80 timings: OUT (C),r/ED71=12,
LD A,n+OUT (FE),A=7+11, EXX/EX AF/one-byte register operations=4,
LD SP,HL=6, POP=10, ADD IX,BC=15, LD A,IXH=8, LD r,(HL)=7,
JP cc/JP nn=10, JP (HL)=4, LD A,(IY+d)=19, INC IYL/IYH=8.
The first eight holds are 36/28/28/31/27/23/23/16 T (212 total).
The second eight are 31/23/27/28/33/30/35/49 T (256 total).
Both nibble paths take **468 T**, verified instruction-for-instruction by
continuous native execution. Low-tail JP+NOP+NOP adds 18 T to the old
450-T probe; high-tail INC IYL plus JP adds 8 T to its 460-T path. Mean
cost increases by 13 T over that probe and 34.75 T over the previous
433.25-T/eight-output live feedback player, while doubling output count.

A non-bank 256-byte boundary adds 18 T. Each bank handoff adds 131 T
(180-T final hold), including paging and the self-modified next-bank jump.
The decoder pipeline causes this extension at output sample `2*end_byte-3`.
The complete loop is `186880*468 + 358*18 + 7*131 = 87467201 T`.
Fuse adds 7532826 ULA T-states across two loops; ROM execution and physical
disk latency are excluded from these playback counts and occur at preload.

## Verification and reproduction

[Verifier](verify_packet.py): all 2048 table entries match an independent
exact rational recurrence; two continuous native and cold Fuse loops check
5980161 output bits and 373760 predictors/indices. Native checking also
compares every hold, all paging, fixed RAM and paged payload/screen guards.
Fuse checks loading attributes, shadow selection through all reads, paging
latches, every actual output instruction/value and all output timestamps.
An independent FFmpeg IMA WAV decoder agrees on all 186880 input samples.
Normal-speed FMF capture covers two wraps and has signal in every complete
half-second window. Full trace is retained locally in `.tmp/packet-disk/`;
the committed evidence includes its hash, debugger script and all timestamps.

```powershell
python audiobook-beeper/build_packet.py --output build/ima-packet --fuse <fuse.exe> --ffmpeg <ffmpeg.exe>
```

This delivers the compact, balanced version of the previously executed
kernel. The direct-second-pointer 434-T design remains unimplemented.
An initial full debugger launch exceeded Windows' command-line length
limit; a shared port stop breakpoint replaced per-codebook stop breakpoints.
No player instruction changed for that harness fix.
