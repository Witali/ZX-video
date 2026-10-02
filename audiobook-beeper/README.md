# Beeper PDM audiobook preview

The user rejected the YM2149 speech test as unintelligible and requested a
different path: **one-bit PDM on the beeper, at least 40 kHz**. This subproject
supports both a precomputed noise-shaped bitstream and direct conversion of
unsigned PCM8 to PDM in Z80 registers. Both write ULA port FE bit 4 directly.
They do not fit the voice to tone generators.

## Additional experiment: live PWM

[Try the PWM disk](../ZX-audiobook-IMA-ADPCM-PWM-test.trd) on **Fuse / Spectrum
128 / Beta Disk**. It independently boots, preloads the same 115456 IMA bytes,
decodes them on the Z80 and loops without a PCM or pulse buffer. The primary
PDM disk below remains unchanged. This PWM experiment does **not** meet the
older 40 kHz PDM-output target.

[ima-pwm-player.asm](ima-pwm-player.asm) emits two PWM periods per source
sample, with 16 pulse widths. Two complementary NOP ladders give a 4-T width
step: high 68..128 T within a 226-T period. IMA decoding runs between edges.
Main L retains the current width while A decodes; IYL retains the next width.
The only RET is provably untaken after AND clears carry. The source explicitly
encodes ED71 (`OUT (C),0`) because pyz80 lacks its mnemonic: this assumes the
standard **NMOS Z80** used by the target Spectrum 128, not a CMOS replacement.
Python only prepares constants/table/screen data and packages the independently
assembled binary. Guarded IMA additions must never require saturation.

Measured over two full Fuse cycles: **15606.400 PWM periods/s**, **7803.200
PCM samples/s**, first loop 29.591941 s. The source remains 8000 Hz / 8-bit mono
before IMA encoding; playback is 2.46% slower, so pitch is correspondingly lower.
This first candidate does not resample or alter the cached audio to hide that.
PWM carrier frequency is not the same quantity as PDM port writes per second:
PWM has two output edges per period; the PDM baseline writes 48287.384 bits/s.

| CPU timing, excluding ULA and startup ROM/disk | Uniform PDM | PWM |
|---|---:|---:|
| Ordinary sample, T |438|452 (+14)|
| Extra at a non-bank page edge, T |74|0|
| Extra at a bank edge, T |361|89 (final121)|
| Full loop, T |101175126|104372968 (+3197842)|

The final-bank overhead is **121 T**, including 32 T to reset the IMA seed;
other seven bank transitions cost 89 T. Thus the exact PWM loop is
`452*230912 + 7*89 + 121`. ULA adds 1173527 T over the two measured loops.
Normal periods are mostly 226 or 228 T, with longer bank transitions; no claim
of perfect wall-clock PWM timing or 40 kHz output follows. Code occupies 1484
bytes within the unchanged 1536-byte code reserve; all 128 KiB allocations and
451 preload sectors remain unchanged, with no playback disk reads.

- [Actual Fuse recording, first-loop-length prefix](experiments/ima-pwm16/result-preview.wav)
  has no added filter, gain or pitch correction and begins at the ready marker.
- [PWM with the common listening filter](experiments/ima-pwm16/pwm-bandlimited-preview.wav)
  and [PDM with that same filter](experiments/ima-pwm16/pdm-bandlimited-preview.wav)
  use 70 Hz HP and two 4.5 kHz two-pole LPs. PWM's fixed AC slope is compensated
  by 226/64, then both use the same 0.793961 gain; peaks are not independently
  normalized. The PWM modulation range is about 10.96 dB quieter before this
  compensation. The two files retain their actual playback speeds.
- [Full verification](experiments/ima-pwm16/verification.json),
  [build/audio report](experiments/ima-pwm16/report.json), and
  [delivery checks](experiments/ima-pwm16/delivery.json).

The filtered, measured-schedule SNR is 13.5337 dB versus 11.7832 dB for PDM.
This modest improvement includes quantization, edge timing and phase error;
it is **not a perceptual quality guarantee**. A 15.6 kHz PWM carrier can itself
be audible. Keep PWM as a listening experiment and PDM as the main option.
No RC model or physical hardware measurement is involved.

Native checks cover 1847297 exact edges, all 461824 predictors/indices, widths,
periods, bank sequence and protected memory across two loops. Cold Fuse checks
all selectors/states/timings, latches, startup stack and disk reads; normal-speed
Fuse recording confirms both wraps and continuous sound. Component tests cover
11124 unclipped transitions across both nibbles and all 16 widths, including
hostile initial flags. Existing general/uniform PDM disks rebuild identically;
packaging the separately assembled PWM binary reproduces the tested disk.

```powershell
python -m unittest discover -s audiobook-beeper -p test_ima_pwm.py
python audiobook-beeper/build_pwm.py --output build/ima-pwm --fuse <fuse.exe> --ffmpeg <ffmpeg.exe> --record
# Reassemble from the prepared assembly directory, then package separately:
python -m pyz80.pyz80 --obj=player.bin --lstfile=player.lst -s '.*' ima-player.asm
python audiobook-beeper/pack_ima.py build/ima-pwm --output build/ima-pwm/repacked.trd
```

## Current test: uniform timing with the original PDM model

Use [uniform-timing TRD](../ZX-audiobook-IMA-ADPCM-uniform-test.trd) on
Spectrum 128 with Beta Disk/TR-DOS. It retains the original accumulator PDM
model, six pulses per sample, the same IMA bytes, all 128 KiB RAM allocation
and endless playback. The RC-feedback experiment is retained as research
only; it is not used in this disk.

[ima-uniform-player.asm](ima-uniform-player.asm) redistributes IMA work and
uses flag-safe 5/6/9-T instructions where their exact duration is useful.
The ordinary native interval is now **73 T for every pulse**, rather than
72..74 T. Low/high sample costs become 438/438 T instead of 439/437 T, so the
ordinary average stays 438 T. Page overhead falls 76 ->74 T, bank overhead
362 ->361 T; a full native loop costs 101175126 T versus 101176020 (-894 T).
Maximum native hold falls 79 ->77 T. The intentionally short paging slot
retains headroom for two contended port writes.

Safe 5-T `RET C` instructions are never taken: comments identify each carry
clear and native tests cover both nibble paths. Six-T `INC SP` changes only
a dead table cursor before its replacement; 9-T `LD A,R` reads into dead
scratch A after publishing the sample. Playback still never uses the stack
for a real return, call or interrupt. The same separately compiled binary
can be packaged by [pack_ima.py](pack_ima.py).

To free scheduling space, this variant omits predictor saturation only after
the host checks **all 230912 raw IMA additions**, including the seed: none
clips (-29878..30985). Both the builder and separate packer reject streams
requiring saturation. The general saturating player below remains available
for other inputs. The transition table contains clean, untagged row pointers.

| Complete two-loop Fuse 128 measurement | Before | Uniform candidate |
|---|---:|---:|
| Average PDM writes/s | 47702.626 | **48287.384** |
| Actual decoded samples/s | 7947.667 | 8045.093 |
| Interval standard deviation, T | 2.5544 | **1.1910** |
| Longest actual interval, T | 85 | 85 |
| Minimum instantaneous PDM writes/s | 41728.235 | 41728.235 |
| Extra ULA wait T over two loops | 3751657 | **1257540** |

The first loop lasts 28.702241 s, with all source samples retained. Playback
is now 0.56% faster than the intended 8 kHz source, compared with 0.65% slower
before. ULA waits still prevent perfectly equal wall-clock pulse intervals:
about 78.75% are exactly 73 T. First-loop interval spread drops 53.37%; the
worst rare bank/ULA pause does not worsen. PDM frequency increases 1.226%.
The modeled midscale idle tone falls 9.66 dB, while speech reconstruction
SNR improves modestly 11.5066 ->11.7832 dB at the same input level and filter.
These are measured-schedule metrics, not a claim that all noise is removed.

- [Actual Fuse audio, first loop](experiments/ima-uniform73/result-preview.wav).
- [All-bit native/Fuse verification](experiments/ima-uniform73/verification.json).
- [Timing and idle-tone comparison](experiments/ima-uniform73/timing-comparison.json).
- [Build report](experiments/ima-uniform73/report.json) and
  [delivery checks](experiments/ima-uniform73/delivery.json).

All 2771911 PDM bits, 461824 PCM16 predictions and indices, paging latches,
startup stack bounds and two seamless wraps pass. There are 451 startup
sector reads and zero playback reads. Native transition tests additionally
cover 11124 safe low/high cases, with unchanged memory and 438-T paths; the
general decoder's 4272 cases and random two-loop regression also pass.
Cold boot is independent of previous disks. Physical hardware is untested.

```powershell
python audiobook-beeper/test_ima_uniform.py
python audiobook-beeper/build_uniform_ima.py --input audiobook-beeper/ima-preview --output build/ima-uniform --fuse <fuse.exe> --ffmpeg <ffmpeg.exe>
python audiobook-beeper/compare_uniform_ima.py --before audiobook-beeper/ima-preview --after build/ima-uniform --ffmpeg <ffmpeg.exe>
```

## Previous test: general IMA ADPCM decoded directly to beeper PDM

[IMA ADPCM test disk](../ZX-audiobook-IMA-ADPCM-test.trd) holds **230912 samples**
in **115456 compressed bytes**, exactly 2:1 against the requested unsigned
8 kHz /8-bit mono PCM. A complete loop takes **29.054 seconds** in Fuse 128;
the source excerpt is 28.864 seconds starting at 01:00. The actual decoded
sample rate is 7947.667 Hz. All eight RAM banks are used. There is no expanded
PCM/PDM buffer, no disk access during playback, and the excerpt repeats.

Use Spectrum 128 + Beta Disk/TR-DOS, normal speed, beeper audio enabled.
The initial preload takes about 26 seconds in the tested Fuse setup. Run
`RUN "boot"` from TR-DOS if needed. Reset to stop.

- [Commented, authoritative ASM source](ima-player.asm),
  [assembler listing](ima-preview/assembly/player.lst),
  [assembled binary](ima-preview/assembly/player.bin).
- [Actual Fuse sound](ima-preview/sound-128/fuse-preview.wav).
- [Before](ima-preview/noise-before-preview.wav) and
  [after](ima-preview/noise-after-preview.wav), with matched reference loudness.
- [Complete verification](ima-preview/verification.json),
  [noise comparison](ima-preview/noise-comparison.json),
  [build report](ima-preview/report.json).

The first-order PDM loop is now **40 T instead of 48 T per pulse**. The main
BC/DE remain dedicated to the output; EXX is needed only around table work.
Ordinary native holds are **72..74 T**, versus 56..81 T in the first working
IMA version. Low/high nibble decoding takes **439/437 T**, average 438 T,
versus 439/453 T, average 446 T (-8 T/sample), and the earlier PCM8 player's
441 T/sample (-3 T/sample). Extra pulses cover page and bank transitions.
Exact loop cost is `438*N + 76*(pages-banks) + 362*banks` = **101176020 T**,
versus 102995498 T (-1819478 T). Instruction counts and register contracts
are documented beside the assembly. ROM/disk startup time is excluded.

Cold Fuse adds ULA contention: average PDM **47702.626 writes/s**, minimum
**41728.235 writes/s**, maximum hold **85 T**. Two complete loops check every
one of **2771911 output bits**, 461824 predictors and step indices, the paging
latches and startup stack guard. No runtime sector reads occur. The separate
native tests cover 4272 predictor/index/nibble cases and two full loops of
nonrepeating random nibbles. FFmpeg independently decodes all 230912 samples
exactly; the format uses standard IMA-WAV shift/add rounding, low nibble first.

The 4-bit stream is lossy. Its predictor retains 16 bits and only its high
byte feeds PDM. Input remains 8 kHz /8-bit mono; the original file is 44.1 kHz
stereo AAC. Before encoding, quiet speech receives 4x gain and a lookahead
peak limiter at 0.85 (5 ms attack /100 ms release, delay compensated).
This changes loudness dynamics; it does not restore missing information.

Measured-schedule reconstruction gives PDM SNR **-1.075 ->11.507 dB**.
At unchanged speech level, the ASM change alone gives **+1.394 dB**; the
remaining improvement comes from raising speech above the modulation noise.
The largest modeled idle tone in 1..8 kHz falls **10.716 dB**. Comparison WAVs
match speech RMS, use common attenuation and the same 70 Hz highpass /two
4.5 kHz lowpasses. These are reconstruction metrics, not a physical-speaker
test or a claim that all noise is gone. ADPCM's own SNR is 22.412 dB against
the conditioned PCM8 input.

RAM: code/table reservation 7424 bytes (1322 code, 5696 table plus padding),
screen 6912, TR-DOS workspace/stack 1280, ADPCM 115456; total **131072**.
Code/tables stay at 8000..9CFF; bank-2 audio at 9D00..BFFF, bank-5 audio at
6000..7FFF. The loader SP is 6000. Playback repurposes SP as a read-only table
cursor with interrupts disabled; no playback PUSH/CALL/RET is permitted.

### Separate assembly and disk packaging

The ASM is the maintained source. Python writes data constants, the lookup
table and screen, runs the external **pyz80 1.3.0** assembler, then reads the
resulting binary. It neither generates nor patches Z80 instructions.
The saved assembly directory contains every input for a separate rebuild:

```powershell
cd audiobook-beeper/ima-preview/assembly
python -m pyz80.pyz80 --obj=player.bin --lstfile=player.lst -s '.*' ima-player.asm
cd ../../..
python audiobook-beeper/pack_ima.py audiobook-beeper/ima-preview --output build/ima-test.trd
```

Create the output parent directory first. The packer consumes `player.bin`
without invoking an assembler. An edited binary needs fresh native/Fuse checks
and updated symbols before claiming the saved timing verification.

Full rebuild (Python with NumPy, Pillow, z80 and pyz80 installed):

```powershell
python audiobook-beeper/build_ima.py --output build/ima-new --ffmpeg <ffmpeg.exe> --fuse <fuse.exe>
python audiobook-beeper/test_ima.py
python audiobook-beeper/record_pcm.py build/ima-new --output build/ima-sound --fuse <fuse.exe> --machine 128
```

`--speech-gain 1` retains the former input level. Use a fresh directory unless
resuming the same build. Source authentication uses `source-format.json`.
This remains a resident preview, not a two-minute/full-book disk streamer.

### Higher PDM rate: CPU feasibility study (2026-10-02)

The verified disk above still uses six ordinary pulses per PCM sample.
[Probe ASM](ima-rate-probe.asm), [runner](probe_ima_rate.py) and
[saved results](ima-rate-probe.json) explore eight to ten pulses without
changing that release. This is a CPU microbenchmark, not a new playable TRD.

The exact current IMA payload needs **zero predictor saturations** across
230912 samples, with raw sums in **-29878..30985**. A host-side build guard
can therefore authorize a decoder without saturation for this payload and
its exact initial predictor/index. This is not true of arbitrary IMA data:
for example, predictor 32760, index 0 and code 7 produces 32771 before the
required clamp to 32767. Recheck the decoded recurrence after every encoding
change; bounding input PCM peaks alone does not prove that IMA cannot
overshoot. A future integrated builder must reject unsafe streams or select
the general saturating player, and preserve/reset the checked initial state.

Without saturation, table row pointers need no sign tag. Remove BIT/RES on
that tag and the sign/clipping branches, allow PDM to own the main accumulator
for most of the sample, and use `LD D,IXH` (8 T) instead of `LD A,IXH` plus
`LD D,A` (12 T). Seven of eight pulses now use **32 T rather than 40 T**;
the one saved-A pulse remains 40 T, with another 8 T of AF swaps around the
address calculation. No prediction precision or compressed samples change.

Instruction costs follow the [Zilog Z80 manual](https://www.zilog.com/docs/z80/um0080.pdf);
the undocumented `LD D,IXH` (DD 54) is additionally checked by executing the
assembled bytes. Deterministic ordinary sample totals are:

| Kernel | Pulses/sample | Low/high T | Mean T | Difference from current 438 T | Remaining budget at 8 kHz |
|---|---:|---:|---:|---:|---:|
| Current general decoder | 6 | 439/437 | 438 | 0 | 5.3625 T |
| Guarded, unpadded | 8 | 393/407 | 400 | -38 | 43.3625 T |
| Guarded, padded | 8 | 437/437 | 437 | -1 | 6.3625 T |
| Guarded, unpadded | 9 | 425/439 | 432 | -6 | 11.3625 T |
| Guarded, unpadded | 10 | 457/471 | 464 | +26 | -20.6375 T |

The 128K CPU budget is 3546900/8000 = **443.3625 T/sample**. The remainder
must cover ULA waits, amortized page/bank work and cadence padding; it is not
spare capacity already measured in Fuse. The eight-slot padded probe holds
are `[58,60,56,50,55,52,56,50]` T, summing to 437 T. This equalizes low/high
sample lengths but does not make individual PDM holds equal. The unpadded
variants have holds as short as 32 T. More writes alone do not establish
better audio: uneven hold times must be addressed and listening/noise checks
repeated for any integrated candidate.

All four assembled variants execute the entire real payload in **902
independent blocks of at most 128 bytes**. Every PCM16 predictor, step index,
PCM8 level, PDM bit and counted interval matches its reference, and memory
is unchanged. Each block starts with the correct IMA seed but resets the
PDM accumulator/pipeline. Real page/bank tails, seamless loops, cold boot,
ULA contention and audio quality are explicitly **not verified** here.

At unchanged approximately 8 kHz speech, eight slots target approximately
**64 kHz PDM** (about one third more than current 47.7 kHz); nine target
approximately **72 kHz**, with much less timing margin. Ten slots cannot
reach 8 kHz speech in this kernel even before contention. Removing delays
without retiming would speed up the speech, so the unpadded native rates
in the JSON are throughput measurements, not proposed playback rates.
The next practical integration target is eight slots; nine remains an
experiment requiring tighter scheduling and potentially unrolling jumps.

Reproduce using the existing Python environment with pyz80, NumPy and z80:

```powershell
python audiobook-beeper/probe_ima_rate.py
```

The script compiles the standalone ASM externally into ignored `.tmp`
build directories, checks the source stream and release hash, and writes
the JSON report. It neither rebuilds nor overwrites the current TRD.

### Additional generator: internal RC feedback (2026-10-02)

The user requested a generator that models the external capacitor and
chooses the next bit to charge/discharge it towards the desired voltage.
This changes the PDM bits themselves. It is a **host-side experiment** in
[rc_pdm_experiment.py](rc_pdm_experiment.py), not a new Z80 player or TRD.
The working live IMA disk remains unchanged.

The model uses the earlier RC parameters: R=1000 ohms, C=7.957747 nF,
tau=7.957747 microseconds, cutoff=20 kHz. It follows the
[exponential RC response](https://openstax.org/books/university-physics-volume-2/pages/10-5-rc-circuits)
exactly for each constant port hold. Target voltage is the same RC applied
to the decoded PCM8 level, including the existing three-slot output delay.
The new generator uses capacitor-voltage error `w` and feedback-area states
`e, older`. For a hold of duration `h` and desired unipolar level `x`:

```text
a = exp(-h/tau); c = tau*(1-a); k = h-c
g = (1+beta)*e - beta*older + c*w + k*x
bit = 1 if g >= k/2 else 0
older, e = e, g-k*bit
w = a*w + (1-a)*(x-bit)
```

The final candidate uses beta=0.5. Beta=0 integrates voltage error once;
beta=1 applies full second-order error feedback. Intermediate beta damps
the additional feedback. This is an ideal, unloaded circuit model; no
physical Spectrum speaker response is claimed.

Reuse the verified first-loop Fuse128 schedule: **1385955 holds over
29.054047 seconds**, approximately 47.7 kHz. The same decoded IMA stream
drives all variants. New bit generation uses those measured hold lengths
as an offline assumption; the actual timing of a future Z80 implementation
has not been measured.

| Generator | Speech-band SNR after common RC/filter | Difference from current |
|---|---:|---:|
| Current live PDM | 11.7634 dB | 0 |
| RC feedback, beta=0 | 11.7566 dB | -0.0069 dB |
| RC feedback, beta=1 | 7.9194 dB | -3.8441 dB |
| Same beta=0.5/timing, internal RC bypassed | 13.5511 dB | +1.7876 dB |
| **RC feedback, beta=0.5** | **14.1084 dB** | **+2.3450 dB** |

The internal RC model itself contributes **+0.5574 dB** versus the matched
beta=0.5 control. The total speech-band error RMS decreases about 24%.
This is not an overall noise reduction: wideband SNR after RC alone worsens
from -5.8308 to -8.8777 dB as more noise moves outside the speech band.
Metrics exclude 0.1 s at each edge and compare to decoded PCM through the
same RC, not to the original AAC. No separate loudness normalization.

- Speech-band listening: [current](rc-pdm-preview/baseline-speech-preview.wav)
  and [RC-aware](rc-pdm-preview/rc-aware-speech-preview.wav). Both additionally
  use the same 70 Hz highpass and two two-pole 4.5 kHz lowpasses.
- RC-only listening: [current](rc-pdm-preview/baseline-rc-preview.wav) and
  [RC-aware](rc-pdm-preview/rc-aware-rc-preview.wav). These have only the
  modeled 20 kHz RC and export antialiasing, so the extra hiss is retained.
- [Final report](rc-pdm-preview/report.json) includes checks, hashes,
  matched-control metrics and packed candidate bitstreams.
- Historical reports/source snapshots: [beta0](rc-feedback-preview/report.json),
  [beta1](rc-feedback-order2-preview/report.json),
  [initial beta0.5](rc-feedback-damped-preview/report.json).

Validation covers analytic charging, DC levels 0/.125/.5/.875/1, independently
summed capacitor-area error, rail limits, output lengths and clipping. Each
PCM export bin integrates the analytic RC waveform exactly, then SOXR
resamples to 44.1 kHz PCM16. Bins are centred on sample timestamps. Doubling
the export rate 705600 ->1411200 Hz changes the full candidate WAV by
0.000302 RMS before listening gain. The preliminary left-edge bin export
failed that convergence check due to its half-bin timing shift; archived
early reports precede this final export validation.

A direct 16-bit arithmetic port is costly. The separately assembled
[cost probe](rc-feedback-cost.asm) computes just `e+floor((e-older)/2)`
in **62 T**, versus no such term in the current player (**+62 T/pulse**).
[Native check](probe_rc_cost.py) verifies 2025 signed cases and exact timing;
see [cost report](rc-pdm-preview/z80-cost.json). This excludes the RC update,
quantizer, PDM output, register spills and IMA work. At the current rate
that term alone consumes another 83.38% of a 3.5469 MHz CPU. It is not a
lower bound on all implementations: a future live port needs different
fixed-point state/table design and complete native/Fuse validation. No
claim is made that the floating-point host generator fits the live player.

Reproduce into an empty directory using the project Python dependencies:

```powershell
python audiobook-beeper/rc_pdm_experiment.py --ffmpeg <ffmpeg.exe> --output build/rc-pdm --feedback-weight 0.5
python audiobook-beeper/probe_rc_cost.py
```

## Previous test: convert PCM to PDM while playing

[Live conversion TRD](../ZX-audiobook-PDM-live-test.trd) stores the actual
8 kHz /8-bit mono PCM bytes. Z80 converts them while playing, with no PDM
buffer or lookup table. All eight RAM banks provide **121344 PCM bytes
(118.5 KiB)**, with a **15.402-second** repeating excerpt after the initial
disk load. The early-silence paging bug is corrected using the full 7FFD port.
See [memory, timing and reproduction](FULL_MEMORY.md),
[actual Fuse sound](pcm-live-full/sound-128/fuse-preview.wav) and
[complete verification](pcm-live-full/verification.json).
The [original method and comparisons](PCM_LIVE.md) remain archived.

The previous disks already contained packed PDM, eight output bits per
byte; they did not expand it into a separate RAM buffer after loading.
The new disk changes the stored representation to PCM and moves modulation
from the host computer into the Spectrum playback loop.

## Previous test: 8 kHz / 8-bit source, precomputed PDM, continuous repeat

The preceding user request converted the demonstration to **8000 Hz, 8-bit mono
PCM**, raises the PDM rate, saves a TRD and repeats playback continuously.

- [Looping test TRD](../ZX-audiobook-PDM-8k8-test.trd).
- [Exact archived disk](preview-8k8-loop/audiobook-preview.trd).
- [Actual 8000 Hz / unsigned 8-bit mono WAV](preview-8k8-loop/pcm8k-preview.wav).
- [Reconstructed beeper listening WAV](preview-8k8-loop/beeper-preview.wav).
- [Complete build report](preview-8k8-loop/report.json) and
  [two-cycle native/cold-Fuse verification](preview-8k8-loop/verification.json).

Boot in **Spectrum 128 + Beta Disk/TR-DOS**, drive A, with `RUN "boot"` if
needed. Enable beeper audio and normal emulation speed. After preloading
96 KiB, the excerpt beginning at source time 60 seconds repeats from RAM.
Reset to stop. The prior 52-T disk below remains unchanged.

The complete cold-Fuse check measures **75923.916 bit/s average**, versus
66915.539 before (+13.46%). All measured intervals remain at least
**62226.316 bit/s**. The two cycles last 10.3581434 and 10.3581747 seconds;
their output schedules differ slightly with ULA phase. Both repeat holds
are 48 T (13.53 microseconds). Every one of **1572865 writes** matches the
two full bitstreams plus the first bit of the third cycle. There are 384
startup sector reads and zero runtime reads. The 640 KiB TRD occupies
428 sectors. [Delivery integrity check](delivery-8k8.json).

The original recording is **AAC, 44100 Hz, stereo, 127999 bit/s**, verified
with FFprobe; see [source-format evidence](source-format.json). AAC has no
fixed PCM word length: `fltp` is the decoder output format. In this new build,
antialiasing precedes conversion to 8000 Hz and nearest-level quantization
to unsigned 8-bit PCM. The saved 8-bit bytes are reconstructed at 192 kHz
for the modulator. PDM receives only that reconstructed signal. The TRD
stores packed **one-bit PDM**, while the listening WAV is 44100 Hz /16-bit
mono. These are different stages, not contradictory sampling rates.

The 46-T kernel has the same 30-T output operation plus 16-T housekeeping:
**368 T/byte**, versus the baseline's **416 T/byte** (-48 T/byte, -6 T/bit).
The nominal ordinary-bit rate is **77106.522 bit/s**. The final bit of each
repeat has a **48-T** deterministic hold: LD D,E 4 + NOP 4 + JP 10 + the
next 30-T output kernel. Thus a complete cycle costs `bits*46+2` T before
ULA contention; the final byte costs 370 T (-46 T versus the old 416).
No reload, interrupt, mute, or additional pause is inserted at the wrap.
The existing 20-ms audio fades remain at the two excerpt edges.

| Interval after output | 46-T path: work before next 30-T kernel |
|---|---|
| Bit 1 | INC HL 6 + padding 10 |
| Bit 2 | LD A,H 4 + OR L 4 + NOP 4 + EX AF,AF' 4 |
| Bit 3 | EX AF,AF' 4 + JR Z taken 12; or JR not taken 7 + untaken RET C 5 |
| Normal bits 4, 5, 7 | Padding 16 |
| Normal bit 6 | LD E,(HL) 7 + padding 9 |
| Normal bit 8 | LD D,E 4 + JR 12 |
| Boundary bit 4 | LD E,next-bank 7 + padding 9 |
| Boundary bit 5 | OUT (C),E 12 + NOP 4 |
| Boundary bit 6 | LD HL,next-address-1 10 + INC HL 6 |
| Boundary bit 7 | LD E,(HL) 7 + padding 9 |
| Boundary bit 8 | LD D,E 4 + JR 12; final repeat uses the 48-T path above |

The complete single-pass 46-T /8-bit conversion finished before the user
requested repetition. Its [report and artifacts](preview-8k8/report.json),
including exact compressed producer sources, are retained as evidence.
It measured 75924.035 bit/s average and 62226.316 minimum. The looping disk
is the current delivery; its two full cycles also check both repeat edges.
This is a resident demonstration, not a continuous two-minute/full-book stream.

## Original 52-T test disk and listening files

- [Root test TRD](../ZX-audiobook-PDM-test.trd).
- [Identical archived TRD](preview/audiobook-preview.trd).
- [PDM with a 4.5 kHz reconstruction filter](preview/beeper-preview.wav).
- [PDM wideband output](preview/wideband-preview.wav).
- [Prepared original with the same reconstruction filter](preview/original-preview.wav).

Mount the disk in drive A of **Spectrum 128 + Beta Disk/TR-DOS**. If it does
not autostart, enter TR-DOS and use `RUN "boot"`. Enable beeper audio in the
emulator and run at normal speed. It preloads all data, then plays once for
**11.7526065 seconds**, starting at source time 60 seconds. Reset and boot
again to replay. The file is a complete bootable 640 KiB TRD, using 428 sectors.

This is a bounded first test of the new approach, not a two-minute stream.
The final payload uses all six available data banks: **96 KiB /786432 bits**.
Longer continuous playback requires another delivery strategy; disk reads
are not attempted during this resident test.

## Original 52-T measured playback

| Property | Final speech run |
|---|---:|
| Nominal CPU loop rate | 68209.615 bit/s |
| Actual average with ULA contention | **66915.539 bit/s** |
| Lowest instantaneous rate, including bank changes | **59115 bit/s** |
| Highest instantaneous rate | 68209.615 bit/s |
| Actual output intervals | 52, 53, 55, 56 or 60 T |
| Verified speech bits | **786432 /786432** |
| Startup sector reads / runtime reads | 384 / **0** |

Every actual hold interval, including the final one, passes the >=40 kHz
gate. The independent Z80 run verifies exact bits and 52-T intervals without
ULA; the complete cold Fuse run adds real emulated memory/I/O delays. These
are full-excerpt checks, not an extrapolation from a short timing loop.

[Complete report](preview/report.json) Â·
[Native and cold Fuse verification](preview/verification.json) Â·
[Compressed actual output times](preview/output-times.u32.gz).

PDM occupies the CPU continuously. Interrupts are disabled during playback;
the old 50 Hz AY update requirement was superseded by the user's beeper PDM
request. A ROM interrupt synchronizes startup, then all sample writes run
without interrupts. AY volumes are zero; MIC and border bits remain zero.
See the [ULA output register](https://worldofspectrum.org/faq/reference/48kreference.htm)
and [128K contention notes](https://worldofspectrum.org/faq/reference/128kreference.htm).

## Signal preparation and what the WAV means

The source is the same supplied O. Henry recording, authenticated by SHA-256.
FFmpeg downmixes it to mono, applies a 70 Hz highpass and two two-pole 3800 Hz
lowpasses, and resamples to 192 kHz. Peak is normalized to 0.65; only the first
and last 20 ms are faded. Audio bandwidth and PDM clock frequency are distinct.

The second-order error-feedback modulator works in pulse-area units using
the measured slot durations. It uses fixed-seed, low-level TPDF dither to
avoid coherent idle patterns. Eight bits pack into one byte, MSB first.
The first full pilot determines the schedule. The speech run then independently
checks every bit and every interval. Cold-start phase differs by two T in the
final pair of runs: at most 0.564 microseconds, without accumulating drift.
The bounded startup allowance is three T; the >=40 kHz gate is unchanged.

The listening WAV integrates the **final measured port hold times**, then
uses two two-pole 4500 Hz lowpasses and a 70 Hz highpass. This is an explicit
reconstruction filter, **not a measured Spectrum speaker response**. The
wideband WAV omits the 4500 Hz filters, retaining audible quantization noise.
All three WAVs use the same scalar gain; no original audio is mixed into
the reconstructed beeper signal. Actual speakers and emulator sound filters
can change the sound. No physical hardware recording is claimed.

## Earlier 64-T to 52-T improvement

The first complete implementation used 64 T/bit and 80 KiB: average 54823.104
bit/s, minimum 44336.25 bit/s, 11.954084 seconds. It met the frequency gate,
but retained more reconstructed speech-band noise. Its exact source snapshots,
disk, waveform and full verification remain in [experiments/pdm64](experiments/pdm64/report.json).

One faster candidate distributes boundary work over more output slots and
uses 52 T/bit. Compare the same **[60.1,70.1)** passage, with identical filters:

| Decoder | Waveform correlation | Reconstruction SNR |
|---|---:|---:|
| 64 T/bit | 0.907986 | 6.6909 dB |
| **52 T/bit** | **0.964705** | **11.2622 dB** |

The SNR improvement is **4.5713 dB**. These measurements support choosing the
faster version; they are not listener acceptance or a percentage of speech
quality. [Comparison script](compare_previews.py) Â· [result](comparison.json).

## Original 52-T cost and shared memory contract

Instruction costs follow the [Zilog Z80 manual](https://www.zilog.com/docs/z80/um0080.pdf).
The output kernel is `RLC D` (8 T), `SBC A,A` (4 T), `AND 16` (7 T),
`OUT (FE),A` (11 T): **30 T**. Housekeeping/padding occupies another **22 T**,
giving **52 T/bit /416 T/byte**, versus **64 /512 T** initially: **-12 T/bit,
-96 T/byte**. No existing movie or AY player hot path changes.

| Interval after output | Work before next 30-T output kernel |
|---|---|
| Normal bits 1, 2, 5, 7 | 22 T padding |
| Bit 3 | INC HL 6 + LD A,H 4 + OR L 4 + NOP 4 + EX AF,AF' 4 |
| Bit 4 | EX AF,AF' 4 + JP Z 10 + padding 8 |
| Normal bit 6 | LD E,(HL) 7 + padding 15 |
| Normal/boundary bit 8 | LD D,E 4 + padding 8 + JP 10 |
| Boundary bit 5 | LD E,next-bank 7 + padding 15 |
| Boundary bit 6 | OUT (C),E 12 + padding 10 |
| Boundary bit 7 | LD HL,next-address 10 + LD E,(HL) 7 + padding 5 |

The last bit is held for 52 T before zeroing FE: padding 37 + XOR A 4 + OUT
11. Padding uses NOP, JR to the next instruction, LD A,0 and **untaken RET C**;
carry is explicitly clear wherever RET C is used. Saved AF preserves the
pointer-wrap test across the bit-4 kernel. All 256 input byte values, every
bank transition, a partial final bank, stack and code guards are checked in
the independent CPU tests. Deterministic counts exclude ULA, ROM and disk.

Physical bank 2 contains code at 8000..8FFF, the screen staging area at
9000..AAFF and stack below B800. Bank 5 retains the visible screen, BASIC and
TR-DOS workspace. Banks **0,4,6,1,3,7** supply six full 16 KiB payloads. No
RAM from an earlier disk is required. Paging finishes inside scheduled bit
slots while the current byte remains in D; no bit is skipped at a bank edge.

## Reproduction

```powershell
python audiobook-beeper/build_pdm.py "C:/Audio/book.m4a" --ffmpeg "C:/Tools/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output "build/beeper-pdm" --start 60 --kib 96
python -m unittest discover -s audiobook-beeper -p "test_*.py"
python audiobook-beeper/compare_previews.py
python audiobook-beeper/build_pdm.py "C:/Audio/book.m4a" --ffmpeg "C:/Tools/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output "build/beeper-8k8-loop" --bit-tstates 46 --pcm8k --repeat
```

Use the project's Python environment with NumPy, Pillow and the independent
`z80` core. The source must match the existing audiobook hash. A build performs
one complete timing pilot, encodes speech, then performs one complete speech
run. `--resume-render` reuses already complete, hash-matching verification if
only rendering was interrupted; it never skips incomplete playback checks.
