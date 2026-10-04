# Speex mode 3 on a 3.5 MHz Z80

## Latest result: exact Speex improved; separate VQ playback meets nominal CPU timing

The selected exact default is **`pure-r33`**. Both the initial [TODO](TODO.md)
and six-item [follow-up worklist](FOLLOWUP_TODO.md) are complete, with reports
and focused commits. Original generators and evidence remain reproducible.
The exact decoder retains Speex mode-3 packets and emits identical PCM8.
The active [throughput worklist](THROUGHPUT_TODO.md) follows the user's
clarification: consecutive OUT samples are acceptable. Measure average CPU
throughput; no uniform per-sample output schedule is required.

| Stage | Full speech T-states | T/sample |
| --- | ---: | ---: |
| Original assembly | 4536172045 | 24273.181 |
| 1. Exact 24-bit excitation | 4128347261 | 22090.899 |
| 2. Cached innovation tables | 3936652302 | 21065.134 |
| 3. Coefficient tables | 3089519959 | 16532.106 |
| 4. Compact LPC/interpolation | 2759257254 | 14764.861 |
| 7. Immediate product offsets | 2684505254 | 14364.861 |
| 8. Faster coefficient preparation | 2527353474 | 13523.938 |
| 9. Port-only exact output | 2510789186 | 13435.302 |
| 15. Register-based table construction | 2235799352 | 11963.824 |
| 16. Omit zero partial-product bytes | 2164784952 | 11583.824 |
| 18. Combined-register signed products | 2042203676 | 10927.888 |
| 19. Signed24 shift by byte extraction | 2017535516 | 10795.888 |
| 20. Register-held innovation tables | 1973053274 | 10557.862 |
| 22. Zero-feedback state copy | 1961694254 | 10497.080 |
| 23. Inline products and POP table reads | 1863554410 | 9971.931 |
| 24. Pre-negated coefficient-table step | 1850951266 | 9904.491 |
| 26. Register-held pitch accumulation | 1834745357 | 9817.773 |
| 27. Shared long-period history cursor | 1790761749 | 9582.415 |
| 28. Constant pitch-gain chains | 1693838136 | 9063.774 |
| 29. Direct signed24 pitch results | 1680861924 | 8994.338 |
| 30. Shorter synthesis shift | 1675816164 | 8967.338 |
| 31. Two-part general word products | 1635360657 | 8750.860 |
| 32. Shared Q14 coefficient magnitude | 1630001442 | 8722.182 |
| 33. Sign-specific Q14 combination | 1618979214 | 8663.202 |

Round 33 uses **35.52% fewer T than round 09**, 2.802x faster than original
assembly. Internal PCM16 and emitted PCM8 stay exact. Real time still fails
by **19.802x** against 437.5 T/sample: 23.36 seconds of speech needs 462.57
seconds of nominal CPU time. No pacing is added to this Speex decoder.
The below-9000 target is met; the **next intermediate target remains below
8500 T/sample**, requiring about 1.88% additional saving on unchanged speech.
Sign-specific Q14 combination saves 11022228 T (0.676%), with eight more code
bytes. Every Q14 input saves at least 30 nominal T versus round32. Next remove
64 cancelling EXX pairs in changed-page table construction; the estimated
512-T/page saving has not been executed. See the [current report](rounds/33/REPORT.md).

Current [image](rounds/33/player.ihx), [decoder](rounds/33/decoder.s),
[filter](rounds/33/filter.s) and [map](rounds/33/player.map) are under
`rounds/33`. Entry/count/status, input-bank order and port contract below
remain unchanged. Code is `8000..A355` (9046 bytes), state `B000..B410`
(1041), stack reserve `BF00..BFFF`. The PCM16 output buffer is removed;
`_last_pcm16` exposes the existing feedback sample for verification. All
code writes are forbidden during playback. Retained standalone product
helpers patch four operands only when invoked by primitive tests. The filter
borrows SP for table reads, preserves caller IX/IY and runs with IRQ disabled.
Tables still occupy **16010 useful bytes in a 16384-byte arena**;
code/state/input are additional RAM. Gain triples now hold routine pointers.

The final exact binary passes **1094880 complete-stream samples**, arithmetic,
memory guards, instruction audits and a fresh default-build identity check.
All **1343488 Q14 cases** pass with exact instruction costs and register/
memory contracts; unchanged unsigned helper evidence is reused. All 93440 real
Q14 operand pairs match; isolated costs reconcile with the full saving.
See [standard verification](rounds/33/unpaced-checks.json),
[Q14 signs and observed costs](rounds/33/q14-sign-checks.json),
[prior unsigned word domains](rounds/32/q14-product-checks.json),
[prior exhaustive byte/word products](rounds/31/word-product-checks.json),
[prior exact synthesis shift](rounds/30/synthesis-shift-checks.json),
[prior exact constant products](rounds/29/constant-pitch-checks.json),
[prior sum/address checks](rounds/29/direct-pitch-checks.json),
[complete coefficient-domain checks](rounds/24/coefficient-step-checks.json),
[200187 pitch-sum checks](rounds/26/pitch-accumulator-checks.json),
[prior feedback/filter contracts](rounds/23/inline-checks.json), and
[generic product/register checks](rounds/26/s8-domain-checks.json). Its sound
matches the previously supplied exact Speex comparison. Reports for initial
rounds are linked from [TODO](TODO.md), [FOLLOWUP_TODO](FOLLOWUP_TODO.md) and
[THROUGHPUT_TODO](THROUGHPUT_TODO.md).

The follow-up also implements three distinct alternatives:

| Candidate | CPU T/sample | Stored bytes / PCM8 ratio | Decision |
| --- | ---: | ---: | --- |
| Exact Speex round 33 | 8663.202 | 23360 / 8:1 | Selected exact decoder; too slow |
| Approximate Speex round 10 | 11781.204 | 23360 / 8:1 | Rejected: still too slow, added error |
| Periodic wave/noise round 11 | 222.625, kernel only | 54320 / 3.440:1 | Not selected; loading/pacing unimplemented |
| PVQ3x1024 round 12 | 90.418 before pacing | 80974 / 2.308:1 | Previous nominal CPU baseline |
| PVQ3x1024 round 13 | 83.751 before pacing | 80974 / 2.308:1 | Selected separately; unchanged sound, 7.373% fewer T |
| PVQ4x1024 round 14 | 69.313 before pacing | 62528 / 2.989:1 | Rejected: raw SNR loss 3.655 dB exceeds one-dB gate |

The [selected PVQ assembly player](rounds/13/REPORT.md) reads the complete memory
stream and emits every sample on its alternating **437/438-T schedule**,
including bank switches and tail. It uses 4614 table bytes, 935 code bytes,
one state byte and 256 reserved stack bytes, plus five input banks. Raw
source SNR is 23.510 dB (periodic wave: 9.897 dB); raw waveform SNR is not
a perceptual speech score. PVQ is a different format, not faster Speex.
**ULA contention and physical hardware remain unverified**, particularly
the contended input banks of a Spectrum 128. No release TRD is claimed.
The [completed PVQ target](NEXT_TARGET.md) records the achieved <=84-T
unchanged-sound target and the rejected four-sample compression experiment.

To build and check the selected version:

```powershell
python audiobook-beeper/speex-port/build.py --skip-host
python audiobook-beeper/speex-port/verify.py --native-only --restore-fixture
python audiobook-beeper/speex-port/check_round.py --variant pure-r33
python audiobook-beeper/speex-port/check_q14_sign.py
python audiobook-beeper/speex-port/check_unpaced.py --variant pure-r33 --previous pure-r32 --check-default
```

The stream checks require the host-generated fixtures: build host DLLs
as described below and run `check_streams.py --variant pure-r33` to generate
them. Keep the pure-r32 build/report/operand archive and archived random-packet fixtures
available for `check_unpaced.py`. Retain the same Python runtime. `finish_followup.py`
reproduces the historical round09 checkpoint. `final_checks.py` reproduces historical
round-04 LPC evidence and needs `pure-r3` and `pure-r4` builds explicitly.
Historical `save_evidence.py` refreshes **baseline** snapshots only; round
reports are archived separately with `report_round.py`.

Run `check_approx.py` after building `--variant pure-r10-approx` for its
quality experiment, `wavetable_experiment.py` for the periodic kernel, and
`pvq_improve.py` for selected round13 VQ playback. They regenerate listening
WAVs under `build/speex-port/` (round13: `pvq-r13/preview.wav`). The latter
reuses the archived compressed input and book; it does not retrain or change
the sound during timing optimization. `pvq_port.py` reproduces historical
round12. `pvq_four.py` reproduces the rejected round14 format/quality trial
and its `pvq-r14/preview.wav`; it does not replace the selected variant.

## Original implementation and baseline evidence

**Working assembly decoder; real-time target failed.** This experiment reads
Speex frames from RAM and writes unsigned PCM8 directly to port `0xFB`.
The complete speech fixture matches the upstream fixed-point decoder at every
PCM16 sample and every PCM8 port write. It takes 1296.05 seconds of nominal
3.5 MHz CPU time to decode 23.36 seconds of speech: **55.48 times the available
budget**. It is a correctness reference and a measured attempt, not a usable
real-time player. Output intervals are not paced to 8 kHz. There is no PDM.

## Assembly and supported input

- [decoder.s](assembly/decoder.s): packet parsing, excitation, LSP interpolation,
  LPC reconstruction, banked RAM reader and entry point.
- [filter.s](assembly/filter.s): ten-tap synthesis, exact multiplication and
  direct PCM8 `OUT` instructions.
- [player.ihx](assembly/player.ihx) and [symbols](assembly/player.map): assembled
  load image and addresses. The image contains tables and code, not input audio.
- [make_decoder.py](make_decoder.py) and [make_asm.py](make_asm.py) generate the
  unrolled assembly and tables. **No C code or C runtime is linked into the
  baseline `pure-fast` target.** SDCC is used only as the assembler/linker driver.
- [decoder.c](decoder.c), [player.c](player.c) and [reference.c](reference.c)
  preserve a host oracle and the initial compiled-C timing baseline.

Supported input is narrowband **mode 3, 8 kbps CBR**, mono 8 kHz: exactly
20 bytes per 160-sample/20-ms frame. Pack frames consecutively, MSB first,
including the five-bit narrowband/mode prefix in each frame. This is a raw
packet stream, not an Ogg `.spx` file. Other modes, wideband, DTX, packet loss,
in-band control and container parsing are unsupported. Callers must supply
the complete declared number of frames; no external byte-length is passed.

The reference is Speex 1.2.1 fixed point with decoder perceptual enhancement
and high-pass filtering disabled. Its 40-sample output delay is retained;
there is no extra flush frame. The native tests compare both PCM16 and its
conversion `unsigned_pcm8 = (signed_pcm16 >> 8) + 128`.

The specialization and codebooks derive from Xiph.Org Speex under
[LICENSE.speex](LICENSE.speex). The original archive URL and SHA-256 are saved
in [source.json](evidence/source.json). The host reference compiles unmodified
upstream decoder sources, independently of the specialization.

## RAM and entry contract

This allocation uses Spectrum **128K** banking. On an unbanked 48K Spectrum,
only an input fitting one 16-KiB window can be used without changing the reader.
The nominal CPU comparison uses the requested 3,500,000 Hz clock.

| Address/bank | Purpose | Bytes |
| --- | --- | ---: |
| `4000..5F71`, fixed bank 5 | Losslessly packed integer cosine | 8050 |
| `6000..60FF`, fixed bank 5 | Signed-nibble pair sums | 256 |
| `6100..64FF`, fixed bank 5 | Quarter-square multiplication | 1024 |
| `6500..71FF`, fixed bank 5 | Expanded LSP, pitch, energy and innovation tables | 3328 |
| `8000..A789`, fixed bank 2 | Baseline assembly code | 10122 |
| `B000..B75C`, fixed bank 2 | State, frame buffer and scratch | 1885 |
| `BF00..BFFF`, fixed bank 2 | Reserved stack; initial SP=`BFFE` | 256 |
| `C000..FFFF`, banks 0,1,3,4,6,7 | Consecutive compressed input | Up to 98300 |

Table payload is **12658 bytes (12.36 KiB)**, with an occupied span of 12800
bytes including alignment gaps. This meets the 16-KiB **table** budget;
code, state, stack and compressed input require additional RAM. Tables occupy
screen RAM. The program disables maskable interrupts and does not use ROM,
TR-DOS, AY, the screen or an interrupt handler.

To run:

1. Load every Intel HEX record at its absolute address with fixed banks 5 and 2
   visible at `4000` and `8000`. Keep 128K paging unlocked.
2. Split the raw compressed bytes into 16-KiB chunks and load them in physical
   banks **0,1,3,4,6,7**, in that order. A packet may cross a bank boundary.
3. Write the frame count as an unsigned little-endian word at `B000`. Valid
   counts are 0..4915. The supplied speech fixture has 1168 frames/23360 bytes.
4. Jump to `8000`. Entry initializes state and its own stack. All registers are
   clobbered. The program halts at `_complete`; it does not return to BASIC.
5. Read status at `B002`: 0=finished, 1=unsupported frame prefix,
   2=frame count exceeds six-bank capacity. Invalid count produces no paging
   or PCM writes; invalid prefix produces no samples for that frame.

`OUT (0xFB),A` requires a DAC that decodes the **low eight port-address bits**.
The high address byte equals the sample in A, as specified by the Z80
instruction. It is not a fixed 16-bit I/O address. Silence is 128. The paging
writes to `0x7FFD` are separate. Patch the immediate DAC port if needed and
revalidate against the actual peripheral; hardware has not been tested.

## Complete measurements

The input is the existing 186880-sample `ima-waveform/source-preview.wav`
speech control. Encoding produces 1168 frames/23360 bytes, or 16:1 relative
to mono PCM16. Matching the reference measures decoder correctness, not
losslessness relative to the original speech.

| Implementation | Full-stream T-states | T/sample | Delta from preceding row |
| --- | ---: | ---: | ---: |
| Compiled-C baseline | 10083761163 | 53958.482 | — |
| Complete assembly, ordinary quarter-square multiply | 5033419430 | 26933.965 | -5050341733 |
| Complete assembly, zero/8-bit operand fast paths | 4536172045 | 24273.181 | -497247385 |

Baseline assembly saves 5547589118 T versus the C baseline. The fast operand
paths save 9.88% versus ordinary assembly on this input, but are slightly
slower for full-width operands. This is input-dependent, not a universal
worst-case improvement. A signed 16x16 multiply costs 50..1310 T across the
saved test set; an unsigned 8x8 multiply costs 142 or 145 T including return.

At 8 kHz, each sample has 437.5 T and each frame 70000 T. In the baseline
speech run, synthesis alone uses 13259.530 T/sample, LPC reconstruction
3874.784 T/sample, and the remainder 7138.867 T/sample. Even a free synthesis
filter would leave this implementation far outside the available budget.

First output is at 883960 T. Actual port intervals span **2627..1431069 T**;
186879 of the subsequent 186879 samples miss the 8-kHz deadlines anchored at
the first output. Maximum accumulated lateness is 4453527504.5 T. Buffering
one or two frames cannot fix this sustained throughput deficit.

These are deterministic CPU counts, including parsing, memory writes,
paging instructions and DAC writes. **ULA contention, interrupt service,
ROM/disk latency and physical hardware are not included.** Contended table
reads can only make the existing deadline failure worse. No disk image or
release player is produced.

The instruction-table audit in [check_primitives.py](check_primitives.py)
uses the repository's Zilog UM0080 timing table, adding DI/EI and output
instructions. It independently sums every executed instruction in the first
complete frame and compares each instruction with the CPU emulator:

| Assembly variant | First-frame T | Instructions | Delta |
| --- | ---: | ---: | ---: |
| Ordinary multiply | 4282588 | 525410 | — |
| Fast operands | 2361219 | 269199 | -1921369 T |

Full-stream timing uses native emulator ticks and recovers instruction
overshoot when its countdown reaches zero; it does not assume that a timing
budget ends exactly at an instruction boundary. Saved `.u64.gz` files contain
one little-endian uint64 timestamp for every DAC output. Events are recorded
at the emulator's I/O callback; a constant intra-instruction offset does not
change intervals.

## Verification and reproduction

Saved evidence includes all three binaries/maps, full timing reports,
port-event traces, compressed packets and independent PCM16 reference, with
[SHA-256 manifest](evidence/manifest.json). Results are in
[pure-fast/report.json](evidence/pure-fast/report.json),
[primitives.json](evidence/primitives.json) and
[stream-checks.json](evidence/stream-checks.json).

Checks completed:

- All 186880 speech PCM16 samples and PCM8 outputs match unmodified libspeex
  for the C baseline and both complete assembly variants.
- The final assembly also matches six 3200-sample inputs: silence, impulses,
  low/high tones, deterministic noise and abrupt level changes.
- A complete 4915-frame/786400-sample silence input validates all six bank
  transitions and the maximum accepted input length against libspeex.
- Every CPU write in those runs stays within allocated state or the reserved
  stack. Input, tables and code remain unchanged. Unsupported prefixes, zero
  frames and excessive frame counts pass the separate control checks.
- Both assembly variants pass all 65536 unsigned 8x8 pairs, 10400 signed
  16x16 pairs, all 25737 cosine angles, 3000 Q14 cases and 12 saturation edges.
  This is not an exhaustive proof for every possible Speex bitstream.

For an offline assembly build, Python 3.12+ and SDCC's `sdasz80`/linker are
sufficient; committed tables avoid any download. Commands are from the
worktree root (supply your tool paths). The saved build used SDCC 4.6.0
revision 16555 and the native checks used Python 3.12.14:

```powershell
python audiobook-beeper/speex-port/build.py --skip-host --variant pure-fast --sdcc C:/path/to/sdcc.exe
python audiobook-beeper/speex-port/build.py --skip-host --variant pure-asm --sdcc C:/path/to/sdcc.exe
```

Native verification uses the same `z80==1.2.0` runtime with address marks and
I/O callbacks as the repository's other CPU harnesses. The instruction
audit imports the existing timing harness and also requires `pyz80==1.3.0`
and NumPy. Set `PYTHONPATH` to that installed runtime when necessary:

```powershell
python audiobook-beeper/speex-port/verify.py --native-only --restore-fixture --variant pure-fast
python audiobook-beeper/speex-port/verify.py --native-only --variant pure-asm
python audiobook-beeper/speex-port/check_primitives.py
```

To recreate the independent reference, run `build.py --host-only --vcvars
C:/path/to/vcvars64.bat`, then `verify.py --host-only --source <mono-pcm8-8k.wav>`.
The Windows host build uses MSVC and downloads the hash-checked official
Speex 1.2.1 archive. `USE_ALLOCA` avoids upstream scratch-pointer truncation
on Windows x64. `check_streams.py` recreates the additional signals with
those host DLLs. `build.py --skip-host --variant z80` and
`verify.py --native-only --variant z80` reproduce the compiled-C baseline.
`save_evidence.py` deliberately refreshes the tracked snapshots after checks.

## Simpler sinusoidal synthesis: a separate design

The user's proposed sine-table approach can make the **sound generator**
cheap. It does not preserve this exact CELP decoder. Speex encodes spectral
envelope plus adaptive and innovation excitation, rather than a ready list
of oscillator amplitudes. See the official
[CELP model](https://speex.org/docs/manual/speex-manual/node9.html) and
[narrowband structure](https://speex.org/docs/manual/speex-manual/node10.html).

A plausible alternative uses 16 pre-scaled 256-sample sine tables: 4096 bytes
total. For each oscillator, keep a 16-bit phase and step; select the table page
for amplitude and sum four samples with peaks limited to +/-31 each. One
straightforward, unrolled oscillator costs:

```asm
ld hl,(phase)     ; 16 T
ld de,(step)      ; 20 T
add hl,de         ; 11 T
ld (phase),hl     ; 16 T
ld l,h            ;  4 T: top eight phase bits
ld h,table_page   ;  7 T: immediate, updated when amplitude changes
ld a,(hl)         ;  7 T
add a,c           ;  4 T
ld c,a            ;  4 T: accumulated output
                  ; 89 T per oscillator
```

Four such oscillators plus `LD C,128`, `LD A,C`, `OUT (0xFB),A` and `JP loop`
cost **388 nominal T/sample**. This is an instruction-table estimate for an
uncontended generator only, not a measured Speex decoder. Noise, envelope
updates, parameter decoding and stable 437/438-T output scheduling still need
budget. Three oscillators leave more room for them. Four tones are a severe
speech approximation; phase continuity, consonants and voice timbre require
listening tests, not just cycle arithmetic.

Another possibility is to construct a short waveform for one pitch period
and loop through it. Reading it is cheap; constructing and changing it on
the Z80 remains a separate CPU cost. Constructing it on the PC moves that cost
out of the player but changes the stored format. Neither alternative has
been implemented or validated by this exact-decoder experiment.
