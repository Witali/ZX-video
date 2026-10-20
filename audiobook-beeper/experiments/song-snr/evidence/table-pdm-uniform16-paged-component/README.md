# Uniform resident PCM8 with one bank transition

This component runs the unchanged 64-level integral PDM model with sixteen
equally spaced outputs per PCM sample. It includes a real native CPU memory
window switch from source bank0 to source bank1. It does not implement a
general bank sequence, a complete song, EOF, a loader or a release disk.

The main run verifies 1,536 initial PCM8/feedback cases, each crossing the
bank, and a 32,766-sample trajectory crossing all ordinary pages and the one
bank boundary. All **647,136 actual speaker writes** match the table oracle,
every speaker interval is **28 T-states**, and each sample is **448 T-states**.
The separate `table-pdm-uniform16-paged-boundaries` supplement positions every
initial cell directly at the bank-decision sample. Its 1,536 cases cover all
384 effective PCM-level/feedback cells and add 122,880 exact speaker writes.
It authenticates the original component manifest, preserved here as
`initial-manifest.json`; the final manifest also covers this documentation.

## Register and memory layout

Main BC=10FE supplies the speaker port and high output byte B=16. Main DE is
the source cursor; HL holds lookup scratch and then the next FIRST pointer.
IX, IY, I and alternate AF remain preserved and available to later work.
Alternate HL=10FE is constant: H=16 supplies the one alternate-register high
speaker output, and L=FE restores alternate C before the next sample.
Alternate BC starts at7FFE and temporarily becomes7FFD for paging. Alternate
DE is scratch. SP is a lookup cursor, never a call stack; IRQs stay disabled.

Each four-byte record contains FIRST and specialized SECOND pointers.
SECOND is specialized by the low eight PDM bits and successor feedback
offset. FIRST saves its selected SECOND pointer into its own final JP
operand. There are 97 FIRST bodies, 151 SECOND variants, and 194 permissible
self-modified operand bytes. Every other fixed RAM byte and all source RAM
remain unchanged by the CPU. The callback replaces only the physical source
window after the explicit7FFD write.

The kernel occupies15,346 bytes at8000..BBF1. The PCM mapping occupies256
bytes atBF00, and the lookup allocation occupies4000..7FFF, with1,536 used
record bytes. Total allocated fixed memory is31,986 bytes;782 bytes remain
between the code and map. A cold loader and further runtime support are not
included in that budget and cannot be assumed to fit there.

## Exact schedule

| Gap after output | Instructions | T-states | Next speaker OUT T |
|---|---|---:|---:|
| 0 | POP HL; INC DE | 16 | 12 |
| 1 | LD (own final JP operand),HL | 16 | 12 |
| 2 | EXX; LD C,L; EXX; NOP | 16 | 12 |
| 3 | LD L,E; LD H,D; two NOPs | 16 | 12 |
| 4 | LD L,(HL); set A to next bit; LD SP,HL | 17 | 11 |
| 5 | LD H,map-high; set A to next bit; LD SP,HL | 17 | 11 |
| 6 | LD H,(HL); set A to next bit; LD SP,HL | 17 | 11 |
| 7 | INC SP; patched JP SECOND | 16 | 12 |
| 8 | LD L,successor-offset; LD A,R | 16 | 12 |
| 9 | LD SP,HL; POP HL | 16 | 12 |
| 10 | LD A,D; AND E; INC A; EXX | 16 | 12 |
| 11 | JP Z,bank; LD A,next bit | 17 | 11 |

On an ordinary path, gap12 returns to the main registers with EXX and three
NOPs (16T); gaps13 and14 have four NOPs each (16T); gap15 has three NOPs and
JP(HL) (16T). The next speaker instruction always completes a28T interval.

On the bank path, gap12 loads alternate BC=7FFD and the next speaker bit
(10+7T, followed by an11T speaker OUT). Gap13 loads static alternate
DE=19C0 and the next speaker bit (10+7T, followed by an11T OUT). Gap14
performs the separate paging OUT and EXX (12+4T, followed by a12T speaker
OUT). Gap15 loads main D=BF, executes an untaken RET C, and JP(HL)
(7+5+4T, followed by a12T speaker OUT). AND E clears carry; INC A and all
intervening bank operations preserve it, so RET C never reads the lookup SP.

FIRST has already prefetched the final old-bank PCM byte before detection
finds DE=FFFF. Paging therefore occurs while playing the penultimate old
sample. The following FIRST plays the already selected final old sample;
its INC DE changes BFFF toC000 before fetching the new bank's first byte.
This is a PCM-byte lookahead proof, not a compressed IMA-nibble proof.

The original player ordinary period was449T; this component uses448T.
The previous measured bank additions were243T, or229T after the earlier
cached-byte change. This integrated static component adds0T at its bank
transition. These comparisons involve moving decoding out of playback and
do not establish a drop-in optimization of the old compressed player.

## Preserved failed attempt and next requirement

`table-pdm-uniform16-paged-component-attempt-1` preserves the initial code and
failure: placing the unplayed guard at the second bank'sFFFF triggered a
third-bank lookahead before the harness stopped. The successful bounded run
ends with its guard atFFFE. No EOF suppression or final-bank guarantee is
claimed. `attempt-index.json` authenticates this failed attempt.

Dynamic descriptor reading remains unresolved. IY is free, but LD SP,IY
costs10T before POP DE can replace the static metadata immediate. The bank
gaps are already full: detection16T; branch/bit17T; port/bit17T;
metadata/bit17T; paging/EXX16T; source-high/RET/dispatch16T. FIRST gap2 now
restores the alternate port and also has no free cycles. Descriptor pointer
advancement and end/refill decisions must be explicitly scheduled rather
than charged as zero CPU work. The static two-bank result alone does not
solve those requirements.

Reproduce the main run with `table_pdm_uniform16_paged.py --output <fresh>`.
Run the supplement with `table_pdm_uniform16_paged_boundaries.py --component
<main-evidence> --output <fresh>`. The native manifests freeze source, assembly,
lookup, results and the trajectory. Physical Fuse/hardware paging, Spectrum
or Scorpion contention, full-song audio quality, precision16/live IMA,
cover/progress, cold boot and independent TRD operation remain unproved.
