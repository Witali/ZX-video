# Z80 instruction timing desk reference

Saved 2026-10-19 for the ZX0/LZSA2 optimization work. Read this file when
counting a changed path; keep experiment totals in [TIMING.md](TIMING.md).

These are ordinary Z80 CPU **T-states**, including instruction fetches and
prefixes, without WAIT, Spectrum ULA contention, interrupt service, paging
code or disk latency. One T-state is one CPU clock, not one machine cycle.
Source for documented forms: [Zilog UM008011-0816, instruction descriptions,
printed pages 70–307](https://www.zilog.com/docs/z80/um0080.pdf#page=84).
The tables group equivalent operand forms rather than reproducing opcode maps.

Notation: `r` = A/B/C/D/E/H/L; `rr` = BC/DE/HL/SP; `qq` = BC/DE/HL/AF;
`i` = IX or IY; `n` = immediate byte; `nn` = immediate word/address;
`d` = signed byte displacement; `cc` = NZ/Z/NC/C/PO/PE/P/M.
Alternatives separated by `/` have identical costs unless shown separately.

Local cross-check on 2026-10-19: 87 representative encodings/outcomes match
`z80==1.2.0`, including both branch outcomes, indexed and undocumented examples,
and LDIR counts 1/2/17. This is a representative CPU check, not exhaustive
hardware validation of every encoding or interrupt/IO behavior.

## Loads, stack and exchange

| Instruction/form | Bytes | T |
| --- | ---: | ---: |
| `LD r,r` | 1 | 4 |
| `LD r,n` | 2 | 7 |
| `LD r,(HL)` / `LD (HL),r` | 1 | 7 |
| `LD (HL),n` | 2 | 10 |
| `LD A,(BC)` / `LD A,(DE)` / `LD (BC),A` / `LD (DE),A` | 1 | 7 |
| `LD A,(nn)` / `LD (nn),A` | 3 | 13 |
| `LD r,(i+d)` / `LD (i+d),r` | 3 | 19 |
| `LD (i+d),n` | 4 | 19 |
| `LD A,I` / `LD A,R` / `LD I,A` / `LD R,A` | 2 | 9 |
| `LD rr,nn` | 3 | 10 |
| `LD i,nn` | 4 | 14 |
| `LD HL,(nn)` / `LD (nn),HL` (unprefixed encoding) | 3 | 16 |
| `LD BC,(nn)` / `LD DE,(nn)` / `LD SP,(nn)`; reverse stores | 4 | 20 |
| `LD i,(nn)` / `LD (nn),i` | 4 | 20 |
| `LD SP,HL` | 1 | 6 |
| `LD SP,i` | 2 | 10 |
| `PUSH qq` | 1 | 11 |
| `POP qq` | 1 | 10 |
| `PUSH i` | 2 | 15 |
| `POP i` | 2 | 14 |
| `EX DE,HL` / `EX AF,AF'` / `EXX` | 1 | 4 |
| `EX (SP),HL` | 1 | 19 |
| `EX (SP),i` | 2 | 23 |

`LD HL,(nn)` and its store also have ED-prefixed aliases: four bytes/20 T.
Use the actual encoding when checking an assembler listing. There is no
ordinary `LD BC,HL`, `LD HL,DE`, `EX DE,IX` or `LD (HL),(DE)` instruction.

## Arithmetic, logical operations and flags

Here `ALU s` covers `ADD A,s`, `ADC A,s`, `SUB s`, `SBC A,s`, `AND s`,
`XOR s`, `OR s`, `CP s`. All eight share the operand timing below.

| Instruction/form | Bytes | T |
| --- | ---: | ---: |
| `ALU r` | 1 | 4 |
| `ALU n` | 2 | 7 |
| `ALU (HL)` | 1 | 7 |
| `ALU (i+d)` | 3 | 19 |
| `INC r` / `DEC r` | 1 | 4 |
| `INC (HL)` / `DEC (HL)` | 1 | 11 |
| `INC (i+d)` / `DEC (i+d)` | 3 | 23 |
| `INC rr` / `DEC rr` | 1 | 6 |
| `INC i` / `DEC i` | 2 | 10 |
| `ADD HL,rr` | 1 | 11 |
| `ADD IX,BC/DE/IX/SP` / `ADD IY,BC/DE/IY/SP` | 2 | 15 |
| `ADC HL,rr` / `SBC HL,rr` | 2 | 15 |
| `DAA` / `CPL` / `SCF` / `CCF` | 1 | 4 |
| `NEG` | 2 | 8 |

Timing equivalence does not imply flag equivalence. For example, `INC rr`
preserves flags; `INC r` changes several flags but preserves C; `ADD HL,rr`
preserves S/Z/PV. `XOR A` clears C and changes flags, whereas `LD A,0`
preserves flags. Check carry and AF' phase explicitly in the nibble readers.

## Shifts, rotates and bit operations

`ROT` = RLC/RRC/RL/RR/SLA/SRA/SRL; `b` = bit number 0..7.

| Instruction/form | Bytes | T |
| --- | ---: | ---: |
| `RLCA` / `RRCA` / `RLA` / `RRA` | 1 | 4 |
| `ROT r` | 2 | 8 |
| `ROT (HL)` | 2 | 15 |
| `ROT (i+d)` | 4 | 23 |
| `RLD` / `RRD` | 2 | 18 |
| `BIT b,r` | 2 | 8 |
| `BIT b,(HL)` | 2 | 12 |
| `BIT b,(i+d)` | 4 | 20 |
| `RES b,r` / `SET b,r` | 2 | 8 |
| `RES b,(HL)` / `SET b,(HL)` | 2 | 15 |
| `RES b,(i+d)` / `SET b,(i+d)` | 4 | 23 |

Accumulator rotates and CB-prefixed rotates have different flag behavior.
In particular, `RRCA` is 4 T but `RRC A` is 8 T.

## Jumps, calls and returns

Both times include the instruction itself, with no target routine/body.
JR supports only NZ/Z/NC/C; its displacement is -128..127 from the next PC.

| Instruction | Bytes | T: not taken | T: taken |
| --- | ---: | ---: | ---: |
| `JP nn` | 3 | — | 10 |
| `JP cc,nn` | 3 | 10 | 10 |
| `JR d` | 2 | — | 12 |
| `JR NZ/Z/NC/C,d` | 2 | 7 | 12 |
| `DJNZ d` | 2 | 8 | 13 |
| `JP (HL)` | 1 | — | 4 |
| `JP (i)` | 2 | — | 8 |
| `CALL nn` | 3 | — | 17 |
| `CALL cc,nn` | 3 | 10 | 17 |
| `RET` | 1 | — | 10 |
| `RET cc` | 1 | 5 | 11 |
| `RETI` / `RETN` | 2 | — | 14 |
| `RST 00h/08h/10h/18h/20h/28h/30h/38h` | 1 | — | 11 |

`JP (HL)` jumps to the address in HL; it does not read an address from memory.
Taken `RET cc` is **11**, not 10 T. `DJNZ` preserves flags and decrements B;
an initial B=0 wraps and normally gives 256 loop iterations.

## Block transfer, search and I/O

The repeating cost is **per iteration**, not the whole instruction.

| Instruction/form | Bytes | T |
| --- | ---: | ---: |
| `LDI` / `LDD` / `CPI` / `CPD` | 2 | 16 |
| `LDIR` / `LDDR` / `CPIR` / `CPDR`: iteration which repeats | 2 | 21 |
| Same: terminating iteration | 2 | 16 |
| `IN A,(n)` / `OUT (n),A` | 2 | 11 |
| `IN r,(C)` / `OUT (C),r` | 2 | 12 |
| `INI` / `IND` / `OUTI` / `OUTD` | 2 | 16 |
| `INIR` / `INDR` / `OTIR` / `OTDR`: iteration which repeats | 2 | 21 |
| Same: terminating iteration | 2 | 16 |

For `LDIR`/`LDDR`, copying N>0 bytes takes **21N-5 T**; initial BC=0 means
65,536 transfers, not zero. A completed `CPIR`/`CPDR` search takes 21K-5 T
for the K bytes actually compared, stopping on equality or exhausted BC.
Repeated I/O uses B: initial B=0 means 256 iterations. Do not apply the BC
rule to these instructions. These formulas exclude interruptions and waits.

## CPU control and interrupt entry

| Instruction/event | Bytes | T |
| --- | ---: | ---: |
| `NOP` / `DI` / `EI` | 1 | 4 |
| `IM 0` / `IM 1` / `IM 2` | 2 | 8 |
| `HALT` entry; each subsequent halted fetch cycle | 1 | 4 each |
| Accepted NMI entry | — | 11 |
| Accepted maskable IM1 entry | — | 13 |
| Accepted maskable IM2 entry | — | 19 |

HALT's total elapsed time depends on when it is exited. Interrupt-entry
costs exclude the current instruction and handler; IM0 depends on the supplied
opcode (a supplied RST commonly costs 13 T). EI delays maskable acceptance
through the following instruction. Pending interrupt time is not a fixed
addition to every decoder instruction.

## Undocumented forms: keep explicit

These are separate from the documented Zilog coverage. They require an
explicit target/assembler contract; timing alone does not qualify adoption.
The project's [native core](https://github.com/kosarev/z80) is `z80==1.2.0`.

| Form on the ordinary Z80 | Bytes | T |
| --- | ---: | ---: |
| `LD r,IXH/IXL/IYH/IYL` or reverse, valid register-only combinations | 2 | 8 |
| `LD IXH/IXL/IYH/IYL,n` | 3 | 11 |
| `ALU IXH/IXL/IYH/IYL` | 2 | 8 |
| `INC IXH/IXL/IYH/IYL` / `DEC IXH/IXL/IYH/IYL` | 2 | 8 |
| `SLL r` / `SLL (HL)` / `SLL (i+d)` | 2 / 2 / 4 | 8 / 15 / 23 |
| Indexed CB rotate/shift/RES/SET also copying result to r | 4 | 23 |
| `IN (C)` (flags only) / `OUT (C),0` | 2 | 12 |

Do not assume IXH/IYL mixing is encodable; one DD/FD prefix selects one index
register. With indexed-memory LD forms, H/L operands can mean ordinary H/L.
`OUT (C),0` data differs across CPU variants. Redundant/ignored DD/FD prefixes
normally cost another 4 T each, but a useful indexed form must be counted from
its own row: `(IX+d)` is not `(HL)` plus a universal four-T penalty.

## Frequent optimization arithmetic

| Sequence or decision | Absolute T and difference |
| --- | --- |
| `PUSH HL; POP BC` (also reverse/other ordinary pairs) | 11+10=21 |
| `LD B,H; LD C,L` | 4+4=8; saves 13 T and avoids stack traffic |
| `CALL helper; RET` overhead alone | 17+10=27 |
| Unconditional `JR` -> `JP` | 12 ->10; saves 2 T, costs one byte |
| Conditional JR, taken fraction p | Expected 7+5p versus JP's 10; JR wins when p<0.6 |
| N explicit `LDI` versus one `LDIR`, N>0 | 16N versus 21N-5; saves 5(N-1) before dispatch/setup |
| One `LDI` followed by `LDIR`, N>=2 | 21N-10 versus 21N-5; saves 5 before dispatch/setup |

Register-transfer replacements must preserve live registers, flags, stack
balance and intervening dependencies. AF is not interchangeable with an
ordinary byte pair. Never emit `LDI; LDIR` for N=1: the LDIR starts at BC=0.
Include selectors, joins, self-modification and synchronization in the full
comparison. Sum path frequencies on unchanged real blocks and record slower
cases; a cheaper primitive alone does not prove a faster decoder.
