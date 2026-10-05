# Compact mu-law TRD preview

```powershell
python audiobook-beeper/convert_audio.py "input.m4a" --codec mulaw --output "build/mulaw" --ffmpeg "path/to/ffmpeg.exe" --fuse "path/to/fuse.exe"
```

`--codec ulaw` is an alias. IMA3 remains the default. The new profile writes
one independently bootable `audiobook-preview.trd` containing a looping
resident prefix. It is an **experimental first-order PDM control**, not the
PC-only second-order 128-kHz model. The default now searches for a better
stream on the PC; it does not implement sequential mu-law volumes.

The PC decodes the input through FFmpeg to mono 8 kHz, applies one fixed
gain (peak 109/128), 10-ms edge fades, then quantizes to PCM16 before standard
G.711 mu-law encoding. It never quantizes through linear PCM8 first.
One byte represents each source sample: 64 kbit/s, 2:1 relative to PCM16.
The resulting `soundtrack.mulaw` is ordinary raw G.711, without a custom
predictor, headers or sample-dependent decoding state. With `--quality best`
(default), the byte choices optimize the *filtered beeper output*, so an
ordinary G.711 decoder reproduces the modulator's control signal. It is
not the nearest-level mu-law encoding of the original PCM.

`--duration N` selects an initial prefix, bounded by RAM. `--prepared-pcm`
instead preserves a mono PCM8/PCM16 8-kHz WAV exactly, requiring 8192..121088
samples, a multiple of 256, and 128 final silent samples; do not combine it
with `--duration`. Normal input is padded to at least 8192 samples. The last
128 samples are a loop guard. Waveform search uses at most64 of these to
close the accumulator with small levels of at most132/32768 (0.403%); no
audible-source samples are replaced by guard data. Output directories must be empty.
`--no-recording` skips only the normal-speed sound-generator capture, never
the complete native and cold-Fuse checks. `--quality balanced` preserves
the ordinary G.711 control. This profile has no SNR-based success exit code;
`report.json` explicitly states whether 30 dB was achieved.

## Offline quality search

The control supplies two complete measured clocks. `best` retains this
verified fallback, executes a Lanczos16 timing-compensated ordinary G.711
control, and searches two overlapping waveform variants: beam8 /horizon16
/prior.1 and beam32 /horizon32 /prior.3, both committing8 samples. All256
G.711 byte choices are available. The filter states of both measured loops
contribute to the objective; the control prior follows their real hold
centers. Only committed filter history propagates across search windows.

All2048 reachable16-bit residues have256 precomputed eight-pulse transitions
on the **PC only**. Nothing is added to the Spectrum tables. Small guard
levels return the exact accumulator to32768 at each wrap without adding
instructions. Every resulting disk gets two fresh native/cold-Fuse loops,
every-bit/state checks, memory/paging/UI checks and a speed check. Selection
uses the lower fixed8-kHz-reference SNR of the two loops, with float64
filtering and no fitted time shift, resampling or gain. Historical diagnostics
using actual sample boundaries remain separately named; their scores must
not be confused with the stricter fixed-clock metric. This is a bounded
search, not proof of the best possible stream for every recording.

See [the quality follow-up](experiments/quality-max/README.md) for new results.
The numbers below preserve the original ordinary-encoder control study.

## Spectrum data path

1. BASIC loads the separately assembled `PLAYER.C`. It installs the shadow
   screen, displays “Loading audio data” and a 32-step progress bar.
2. The loader reads sector-aligned G.711 bytes into the available banks.
   It hides the message and bar after all audio reads. Every disk boots
   independently; no previous disk's RAM or prebuilt PCM is needed.
3. Playback fetches one mu-law byte ahead of the current source sample.
   Two 256-byte lookup planes restore the **exact 16-bit decoded level**,
   biased by 32768 for the unsigned modulator. Small low-amplitude levels
   are preserved; this is not a high-byte-only approximation.
4. A two-byte stack staging slot transfers the next level into DE. Eight
   PDM decisions per sample use a continuous 16-bit modulo accumulator HL.
   Carry from `ADD HL,DE` becomes the beeper bit. There is no full decoded
   PCM or PDM buffer and no disk access while playing.
5. The final source pointer wraps to the first bank. Error state continues
   through the silent guard; the demonstration loops until reset.

## RAM allocation

| Physical bank | Audio range through C000 | Audio bytes |
| --- | --- | ---: |
| 0, 4, 6, 1, 3 | C000..FFFF each | 81920 |
| 7 | DB00..FFFF; first 6912 bytes are the shadow screen | 9472 |
| 2 | C800..FFFF; first 2048 bytes are resident code/table/stack | 14336 |
| 5 | C000..DBFF and E000..FFFF | 15360 |

Audio **121088** + shadow screen **6912** + bank-2 resident **2048** +
TR-DOS variables/load stack **1024** = **131072 bytes**. Full capacity is
15.136 nominal seconds including the guard, or 15.120 seconds of source.
The level table is 512 bytes inside the resident allocation. The playback
stack only writes 87FE..87FF. The load-time stack remains below 6000;
5C00..5FFF is never filled with audio. No bank needs uninitialized data.

## Instruction timing and actual results

Counts use the [Z80 instruction timing table](https://www.zilog.com/docs/z80/um0080.pdf).
The pulse is ADD HL,DE 11 + SBC A,A 4 + AND n 7 + OUT (C),A 12 = **34 T**.
Interleaved work after the eight OUTs costs 19,19,19,19,22,21,21,20 T.
Ordinary OUT-to-OUT intervals are **53,53,53,53,56,55,55,54 T**, totaling
**432 T/source sample**. Compared with IMA3's 427.375 T/sample this is
**+4.625 T**, but generates eight rather than sixteen decisions and removes
the IMA decoder and large feedback tables. This is a different modulator,
not an equal-quality optimization.

A source page boundary adds 35 T (INC B 4, LD A,B 4, CP n 7, JP Z 10,
JP 10). A bank boundary instead adds 116 T: the first four instructions
25, JP (IX) 8, LD BC 10, LD A 7, OUT 12, LD BC 10, LD IX 14, LD A 7,
LD (nn),A 13, JP 10. Prefetch places the extension one sample before the
section's last output sample. These counts exclude ULA waits and disk/ROM
execution. The full native loop takes 52327300 T; every measured native
interval matches the table. Ordinary IMA3 page/bank extras were 14/140 T;
this profile's differences are +21/-24 T at those events, with different
source packing and boundary frequencies.

For the original audiobook prefix, Program Files Fuse 1.9.0 /Spectrum 128
+ Beta 128 measures **64119.013 Hz PDM**, **8014.877 Hz source rate**,
**+0.185958% speed error**, and 15.107991/15.107820-s loops. Both complete
loops verify every bit, decoded level and accumulator state (1937409
outputs including the next loop's first). Memory, paging, 473 startup
sector reads, message hiding and all 32 progress steps pass. Startup audio
reads take 18.508372 emulator seconds; this is separate from native CPU
cost. A normal-speed Fuse sound-generator recording also completes.

**Quality limitation:** minimum total filtered SNR is **9.672027 dB**;
mu-law alone is approximately **39 dB**. First-order modulation dominates
the error. Keep this disk as a functional codec/control preview, not as a
quieter replacement or a 30-dB result. There is no physical-hardware test.

## Does second order help?

The same new 15.136-s payload, full decoded precision, unchanged float64
70-Hz high-pass plus two 4500-Hz two-pole low-pass filters, no gain/delay fit:

| Ideal uniform PDM clock | First order | Second order |
| --- | ---: | ---: |
| 64 kHz | 10.053453 dB | 11.536644 dB |
| 128 kHz | 17.130225 dB | 27.185326 dB |

These are **PC controls**, not executable Z80 kernels. At 128 kHz second
order gains 10.055 dB; at 64 kHz it gains only 1.483 dB on this input. The
earlier 30.920091-dB PC result used a different, longer PCM8 reference; do
not attribute it to this new PCM16 prefix or to the real TRD. At 128 kHz
only 27.710 T/decision are available; at 64 kHz 55.420. Neither allows
assuming that the exact multiword two-state recurrence fits. Its measured
peak exceeds two DAC units on this prefix, so wrapping both states at
16 bits would change the algorithm. A faster SD2 implementation still
needs its own timing, stability and actual-output proof.

Measurements integrate the exact output holds at 768 kHz and filter in
float64. Real-player reference samples follow the same observed sample
boundaries; playback speed is reported independently. Listening WAVs use
the same fixed 0.5 gain for source and reconstruction, with no fitted gain.
See [saved evidence and reproduction](experiments/mulaw-trd/README.md).
