# Static uniform PDM bank-bridge component

This experiment proves a short Z80 I/O bridge in isolation. It does not prove a
complete 448-T sample, full song, disk, descriptor reader or physical memory map.
Run `table_pdm_uniform16_bank.py --output <fresh-directory>` using the repository's
Python/pyz80/z80 environment. The frozen producer is `producer.py.gz`.

The key detail is that an immediate `OUT (FE),A` takes 11 T-states, while the
ordinary `OUT (C),r` takes 12. The interval is counted through the *next* output
instruction. Three temporary immediate speaker outputs allow the alternate
registers to hold the paging port and metadata. A separate `OUT (C),D` to 7FFD
then fits between real speaker writes without using a ULA/paging port alias.

| Interval body | Body T | Next speaker instruction T | Speaker interval T |
|---|---:|---:|---:|
| EXX; LD A,bit; INC BC | 17 | 11 | 28 |
| LD BC,7FFD; LD A,bit | 17 | 11 | 28 |
| LD DE,metadata; LD A,bit | 17 | 11 | 28 |
| OUT (C),D to paging port; EXX | 16 | 12 | 28 |
| EXX; LD D,E; EXX; NOP | 16 | 12 | 28 |
| EXX; XOR A; LD E,A; EXX | 16 | 12 | 28 |

The six intervals occupy 168 T-states; this is redistributed real CPU work.
The previous measured legacy tail added 243 T-states to a bank transition, or
229 T-states after the earlier cached-byte/page-tail improvement. Comparing
those complete-path additions to this component does not establish an
integrated player speedup. Other decode, lookup and pointer work must fit too.

Main BC, DE, HL, IX, IY and SP are preserved, as are alternate HL, alternate AF
and I. Main A/F are scratch. The alternate BC becomes 7FFD. Metadata initially
loads alternate D with the page byte and E with the next source high byte;
the last two gaps restore alternate DE to `(next_source_high << 8)`. The old
packed source byte and decoder delta must already have been consumed/cached,
so replacing alternate DE/BC cannot lose source data. No stack or RAM
workspace is used. The descriptor operand is host-patched before execution.

The full native run enumerates all 128 seven-bit speaker patterns, all 256
page-byte values, and every next-source high byte C0..FF: 2,097,152 Cartesian
cases. A further 128 cases retain main BC=10FE instead of 00FE. Every case has
seven speaker writes and one distinct paging-port write. All six measured
speaker intervals are 28 T-states. Testing all page-byte values verifies CPU
byte wiring; it does not authorize every value as a legal physical bank map.

The initial quick harness stopped at an intermediate emulator frame event
after repeated short cases. This was a runner issue, not a timing failure.
The failed producer and artifacts are retained separately in
`table-pdm-uniform16-bank-component-attempt-1`. The final runner resumes until
the explicit completion breakpoint.

Next integration must reserve these slots in a full 16-output sample and
supply real metadata while IY remains occupied. Then verify actual source
order through every page/bank, EOF and refill paths, UI, physical Pentagon
paging, full-track output timing, and audio quality. Spectrum/Scorpion
contention and 1FFD paging are outside this component.
