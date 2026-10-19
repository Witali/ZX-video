# Retaining useful16-bit predictor precision: bounded architecture audit

2026-10-19. This audit changes no player, converter, C encoder or Python
reference. Its generated kernels are standalone feasibility probes. None is
a bootable Spectrum implementation or an accepted audio-quality update.
The complete-source input/state-precision experiment is separate evidence.

## Current loss and register ownership

IMA already reconstructs an exact signed16-bit predictor. The live player
keeps its unsigned-biased representation in IX, initialized to32768, and
updates all16 bits with `ADD IX,BC`. Source storage is still four-bit IMA.
Only the later modulator lookup loses precision: `LD A,IXH`, followed by the
256-byte `pcm_high` map, selects64 bins. IXL's eight bits and IXH's lower two
bits do not influence ordinary uncentered input selection. Adding a PCM bias
changes bucket boundaries, without recovering those ten bits.

Main BC is the00FE/10FE output port, D is16, E is the compact feedback offset,
HL is packet lookup/dispatch, IX is predictor and IY is SECOND. Alternate HL
is the IMA row, BC is its delta and DE the compressed cursor. AF' preserves
the nibble phase/code. SP is a lookup pointer, so live PUSH/CALL is unsafe.
There is no unused persistent16-bit register pair in that architecture.
Main A/F/HL can be scratch during the lookup stage; the other registers
cannot be reused without restructuring or saving their live values.

## Measured literal arithmetic kernels

The generated `.asm`, binary, assembler listing and every output event are
retained. Instruction counts use the [Zilog Z80 CPU manual](https://www.zilog.com/docs/z80/um0080.pdf)
and are independently executed with the native Z80 harness. IXH/IXL accesses
use the same existing eight-T undocumented register instructions as the
current player. These are concrete implementations, not universal lower
bounds for every possible modulator.

| Concrete first-order kernel | T states per pulse |16 pulses | Complete low/high sample |
| --- | ---: | ---: | ---: |
| ADD HL,DE11; SBC A,A4; AND16 7; OUT(FE),A11 |33|528|623 /639|
| ADD HL,DE11; SBC A,A4; AND C4; OUT(FE),A11 |30|480|575 /591|

The complete counts include the actual table-decoder instruction context:
95 T for a low nibble,101 T for a high nibble including INC DE, plus a10-T
high-to-low jump. Decode is interleaved by EXX with a new direct-modulation
allocation: main HL is accumulator, DE is the full16-bit step and C is16.
BC used by decoding is alternate BC, so main C survives. `LD C,16` costs7 T
once during setup, rather than once per sample. The unrolled accumulator
uses every predictor bit and produces only EAR0/16; MIC and border stay0.
The seven native vectors cover unsigned inputs0,1,32767,32768,32769,65534,
65535. Full accumulator recurrence, outputs, predictor and register guards
pass. Two complete samples take1262 T or1166 T respectively. Both concrete
16-output variants exceed the existing423/448/449-T ordinary period before
adding paging, UI or physical contention.

A third bounded kernel shows why this is not an impossibility argument:
eleven30-T pulses plus the decoder can fit448-T source packet spacing.
LD A,R+NOP provides13 T before the low pulses; LD A,R+two NOPs provides17 T
before the high pulses. A/F are overwritten before meaningful use. Low/high
entry segments take438/458 T because the closing jump belongs to the next
output interval; the measured first OUT of all four packets is exactly448 T
apart. Its holds are `[30,30,30,30,30,30,30,30,30,30,148]`.

That variant has an88-kHz decision rate at an8-kHz Pentagon source clock,
with a148-T decode hold. The accumulator is not duration-weighted, so
decision-index density is not proof of correct analogue area at those
nonuniform holds. It needs a different waveform model and quality study;
no claim of better sound, stable full-player paging or all-clone timing is
made. Page/bank work, interrupts, loading and UI are intentionally absent
from these standalone arithmetic probes. No new parameter sweep was run.

Dropping the AND to advertise26 T would output00/FF, changing border/MIC
and electrical drive. That is not the same EAR-only output contract.

No stable, full-range, full16-bit second-order arithmetic kernel is
implemented here. Two error coordinates, intermediate width, overload
handling and duration weighting need their own concrete design and counts.
The first-order examples do not establish a lower bound or impossibility
for all second-order implementations.

## Fractional input contribution at packet boundaries

An alternate hypothesis preserves the low bits in a small residual while
retaining table modulation. For unsigned predictor U, the low-ten-bit part
adds `16*(U&1023)/65536` to packet q. In q units of1/8 this is
`(U&1023)/512`. A9-bit fraction f therefore accumulates the lost portion;
`divmod(f+(U&1023),512)` yields a carried q correction0/1/2 and the new f.
This would inject correction at a packet boundary. It is not identical to
using full precision in every decision inside that packet, and it does not
remove the current feedback-state rounding.

The literal spill implementation needs116 T to update two RAM bytes using
only main A/F/HL. Its three-page feedback map needs22 T, for138 additional
T per sample. It preserves predictor IX, IY, BC/DE and all alternate state.
All524288 possible9-bit-fraction/low-ten-bit pairs are checked with separate
integer byte arithmetic;5120 native cases cover all1024 low values at five
fractions and all three carry outcomes. Every native case takes138 T and
passes its register guard. This concrete implementation exceeds even the
26-T pacing slack; adding it directly would give561 T on128/Scorpion or
586/587 T with the retained448/449 Pentagon pacing. It is not a proof that
a redesigned selector cannot be faster.

Exhaustive source-independent closure over all64 bins and each correction
0/1/2 reaches24 states from seed16. Existing six-byte cells would need144
bytes per page and collide with decoder rows beginning at offset128.
This16-byte overlap occurs before considering cache workspace restrictions.
The native map reserves three aligned256-byte pages and the fraction needs
two fixed RAM bytes. Thus the hypothesis needs both selector and table-layout
redesign; it cannot be inserted unchanged into the current player.

## Actual full-input model-B table dimensions

The audit executes the new standalone C model B on all2097152 combinations
of65536 signed PCM16 inputs and32 seeds. Input ordering and SHA256, C source
and executable SHA256, C statistics and timing are recorded. Enumeration
took0.609193 s in the saved run. The complete word/successor arrays are in
`model-b-all-pcm16-cells.npz`, with explicit signed input and seed axes.
The model uses the existing449-T table weights, beta0.5 and quantized32-state
interface. This catalogue is authoritative for that C counterfactual, not a
formal exact-arithmetic or stability proof for another model/order.

Closure from seed16 remains18 states. Merely extending the existing table
nevertheless needs7077888 bytes for65536×18 six-byte records. There are3006
distinct word/successor pairs and5383 constant intervals across the18 input
functions. A simple interval bound plus16-bit pointer format needs21532
bytes for bounds, and18036 bytes for the current six-byte dispatch records,
before code or decoder data. A straightforward8+8-bit hierarchy with four-
byte leaves deduplicates to3746 leaves and needs3845120 bytes including top
pointers. These are specified formats, not optimal compression bounds.

The generated output bytes also require138 FIRST and124 SECOND patterns,
or13732 code bytes at the current42/64-byte strides. Following the current
layout literally puts `pcm_high` atB900 and resident data end atC240:576
bytes beyond bank2 before reserving any loader/worker. The table cannot be
substituted into the current direct layout, even though state closure stays
at18. A hierarchical implementation needs a different representation and
counted selector; the dimensions do not rule out every such redesign.

Stored raw PDM is also not a seamless substitute: the complete prepared
720384-sample song would need1440768 bytes at16 bits per sample, exceeding
a1024-KiB machine before code/screens and exceeding one TRD. The current
360192-byte IMA storage should remain the source representation.

## Reproduction and scope

Run with the repository's Python dependencies and installed C compiler:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/sdm16-architecture/generate.py --output .tmp/reproduce-sdm16-architecture
```

The generator reads frozen player/encoder sources and writes only evidence
under its requested output; it does not alter them. `sources/` captures the
audited versions. `manifest.json` records every retained artifact except
itself. The first residual harness run stopped at an internal native-frame
event; continuing the same CPU handle to its explicit completion breakpoint
corrected observation without changing generated instructions.

No complete-source SNR, AM/FM, background-noise, Fuse or physical-hardware
acceptance follows from this architecture audit. Those requirements remain
open in the overall research goal.
