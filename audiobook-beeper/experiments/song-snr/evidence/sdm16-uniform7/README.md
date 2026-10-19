# Full16-bit first order with uniform seven-pulse timing

2026-10-19. A new standalone176-byte native kernel proves a useful mechanism:
compressed IMA can feed a genuine full16-bit first-order modulator with
seven equally spaced outputs per448-T sample. This is a CPU/precision proof,
not a bootable disk, a sound-quality result or an all-clone release. Original
player, Python/C encoders, converter and previous evidence are unchanged.

## Exact modulation and physical-time weighting

The common source-independent accumulator seed is32767. For each signed
PCM16 predictor p, U=p+32768 is held for seven decisions:

```
sum = accumulator + U
bit = (sum >= 65536)
accumulator = sum & 65535
```

Every actual native OUT is64 T after the preceding OUT. Therefore the
physical area error telescopes exactly:
`sum(64*(U/65536-bit)) = 64*(final_accumulator-initial_accumulator)/65536`.
This is genuinely time-weighted first order because all holds are equal;
there is no substitution of unweighted decisions onto the old30/148 schedule.
All16 predictor bits affect the recurrence. A common-seed native witness
with signed inputs37/38 changes the first emitted bit.

The PCM period is448 T. At the Pentagon3.584-MHz clock this means8000
samples/s and56000 decisions/s. It reduces decision rate from the current
player; neither a lower noise floor nor a modulation-order increase follows
from the CPU proof. Masking output to0/16 preserves the EAR-only contract;
MIC and border remain0.

## Counted pipeline and live registers

Each pulse executes ADD HL,DE11, SBC A,A4, AND C4, OUT(FE),A11:30 T. Each
following gap is34 T. Instruction counts follow the [Zilog Z80 CPU manual](https://www.zilog.com/docs/z80/um0080.pdf)
and are independently verified by actual native output timestamps.

Main HL is the16-bit accumulator; DE holds the entire current input until
the final gap. C is16; main B and IY are free. IX holds the next predictor.
Alternate HL is the IMA row, DE the compressed cursor and BC its delta.
AF' temporarily preserves the prepared nibble between gaps1 and2. Decode
uses the existing shift/add IMA rounding and an89×16×4-byte table. It updates
IX without overwriting the held current DE.

| Gap after pulse | Total | Low phase useful/free | High phase useful/free |
| --- | ---: | ---: | ---: |
|1: fetch, extract, save nibble|34|34 /0|34 /0|
|2: restore code, select decoder SP|34|26 /8|26 /8|
|3: POP delta/row, discard dead SP|34|28 /6|28 /6|
|4: update IX|34|23 /11|23 /11|
|5: source cursor|34|0 /34|14 /20|
|6: reserved future work|34|0 /34|0 /34|
|7: latch next DE and loop|34|16 /18|26 /8|

Total useful decode/control is127/151 T, leaving111/87 T in the respective
gaps. This free time is distributed, not a single unrestricted budget.
Gap3's6-T filler writes SP from main HL only after both POPs have finished.
SP is reset from the decoder row before any future POP. No PUSH/CALL or RAM
writes occur, and interrupts must stay disabled. Gap7 copies IX to DE only
after the seventh output. Startup primes the first low IMA nibble before
the timed section, then enters high_packet with its source cursor still
pointing at that byte.

## Verification

The final producer run completed in8.463501 s. An8192-sample mixed reference
stream was greedily IMA encoded with unchanged reference code and guarded
against raw predictor saturation. Native execution verifies8190 samples,
57330 output bits and all next predictor/index states; two source samples
remain available for the prefetch pipeline. Every actual hold is64 T and
every sample period448 T. The compressed source crosses ordinary256-byte
pages without a timing branch, and stays inside one physical16-KiB bank.

Seven full-range constant vectors and the37/38 witness also pass. Predictor,
held input, accumulator, IY, mask register and complete RAM guards pass.
The native bit bytes and callback timestamps are retained in
`uniform7/trajectory-bits.u8.gz` and `trajectory-times.u32.gz`, along with
the exact IMA input and uncompressed hashes. The first callback is at29 T;
subtracting that fixed origin gives times0,64,128,... without fitting a clock.

## Why the old long hold is not a free weighted correction

A second literal kernel handles the old `[30×10,148]` durations with exact
area feedback. It stores signed24-bit q and receives the signed24-bit product
`h*(U-32768)`. It chooses `y=(q+h*(U-32768)>=0)` and updates
`q_next=q+h*(U-65536*y)`.

For any U in0..65535 and h in30/148, `-74*65536 <= q <74*65536` is invariant.
The true intermediate can need25 signed bits. The native implementation
uses the ADC overflow flag to disambiguate its wrapped24-bit sign. Simply
treating that wrapped sign as the decision would be incorrect.

All917504 native cases pass: every16-bit input, seven boundary/interior q
values and both durations. These include17713 true25-bit intermediates.
All four sign/overflow paths cost78 T and preserve their declared live state.
Eleven inner decisions alone need858 T, excluding product formation, loads
and IMA decode. This concrete weighted implementation is rejected for448-T
playback. That is not an impossibility bound for every arithmetic algorithm.

## Open integration and acceptance work

The uniform kernel is a feasible ordinary-time mechanism. Resident-bank
mapping, descriptor prefetch, boundary handling, loader/boot, end marker and
the final sample/teardown are not implemented. No compressed-source bank
wrap, TR-DOS or actual Fuse timing is claimed. The free gaps are intended
for a separately counted resident-bank implementation.

The448-T period targets Pentagon timing. Other clone clocks and ULA waits
need their own proof; at3.5 MHz,448 T is7812.5 Hz and already exceeds the
existing2% source-rate allowance. Do not infer all-clone compatibility from
the flat CPU run. Full-source SNR, silence/tones, AM/FM, background, uniform
emulator clocks and seamless RAM residency remain release requirements.

Reproduce with the repository Python dependencies:

```powershell
python audiobook-beeper/experiments/song-snr/sdm16_uniform7.py --output .tmp/reproduce-sdm16-uniform7
```

`sdm16_uniform7.py` in this evidence freezes the producer.
`report.json`, assembly listings/binaries and `manifest.json` record the
executed scope. The manifest includes every retained file except itself.
