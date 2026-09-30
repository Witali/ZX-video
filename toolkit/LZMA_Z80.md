# Specialized LZMA1 decoder for Z80

Measured 2026-09-30 against `08cd640`. This completes the requested native
assembly experiment. The optimized decoder is correct on the saved fixture
but is too slow for the current video player. It is not integrated or released.

## Implementation

[lzma_z80.asm](lzma_z80.asm) decodes raw LZMA1 with `lc=0, lp=0, pb=2`, a
16-KiB dictionary limit, an exact output size of 0..15872 bytes and a required
end marker. These are the existing `lzma1_extreme_lc0` archive parameters.
It supports ordinary and matched literals, all four repeat distances,
short repeats, lengths through 273, modeled/direct distance bits and EOS.
It does not decode `.xz`, LZMA2, `.lzma` headers or arbitrary properties.
Encoding remains on the PC. No compressed bytes or image/audio data change.

The implementation follows Igor Pavlov's
[LZMA specification, 2015-06-14](https://raw.githubusercontent.com/welovegit/LZMA-SDK/master/DOC/lzma-specification.txt).
The Z80 source is newly written; no third-party decoder source is vendored.

Optimizations:

- Specialize the probability arrays to four position states and one literal
  context: 1943 two-byte entries, **3886 bytes**, including the unused leading
  distance-tree entry. The format is unchanged; unreachable model entries
  are omitted. This is a different internal layout from the generic SDK's
  probability allocation cited in the earlier PC assessment.
- Keep 32-bit multiplication halves in `HL/HL'` and operands in `DE/DE'`;
  switch with `EXX`. Unroll the eleven probability bits and omit the initial
  zero shift. `FAST_MUL=0` retains a working loop baseline in the same source.
- Use `(HL)` and absolute addressing, with no IX/IY memory operands or
  self-modifying code. Use byte rotations for the probability's right shift
  by five. Copy validated matches with overlap-safe `LDIR` directly into the
  output/history buffer; no separate dictionary or staging copy is needed.

## Measured comparison

Same 192-frame montage, 323940 decoded bytes, 21 independent blocks of at
most 15872 bytes. All 42 native video decodes match the archived source.

| Metric | Loop baseline | Optimized |
| --- | ---: | ---: |
| Decoder code bytes | 1345 | 1464 |
| Probability bytes | 3886 | 3886 |
| Scalar state/configuration bytes | 64 | 64 |
| Decoder CPU T-states, all 21 blocks | 2901892750 | 2305838368 |
| Adaptive binary symbols | 1290161 | 1290161 |
| Multiplication T-states, including its RET | 1584342528 | 988288146 |
| Maximum observed stack, including entry return | 14 | 14 |

The optimization saves **596054382 T, or 20.5402%**, for 119 extra code bytes.
The stream remains **133084 bytes / 520 sectors**, including block headers:
10.66% smaller than Fast ZX0, 14.11% smaller than LZSA2.

For comparison, the existing resumable LZSA2 decoder takes **19844626 T** on
these exact decoded blocks. This LZMA implementation takes **116.19 times**
as many decoder cycles. At 3.5 MHz its decoder alone requires 658.81 seconds
for the 192-frame fixture: a theoretical decoder-only ceiling of 0.2914 fps,
before frame construction, disk, paging, interrupts or contention. This is
not measured playback fps. The existing 22.54-million-T heuristic delivery
break-even allowance from the PC assessment is exceeded by roughly 100x.

**Decision:** keep the native decoder as a tested standalone experiment;
do not replace ZX0/LZSA2 or generate release TRDs with it. This rejects this
implementation/profile for the playback target, not every possible LZMA
implementation or occasional non-realtime use. Return to packet-copy work.

## Instruction timing proof

Timings use the [Zilog Z80 instruction table](https://www.zilog.com/docs/z80/um0080.pdf).
Let `h=popcount(prob)`, for the eleven-bit probability. The multiplication
routine includes its RET but excludes its caller's unchanged 17-T CALL.

| Component | Z80 T-states |
| --- | ---: |
| Initialize HL/HL' with two LDs and two EXX | 28 |
| Double 32-bit result: ADD HL,HL; EXX; ADC HL,HL; EXX | 34 |
| Add 32-bit operand with the same exchange pattern | 34 |
| BIT register / SLA or RL register | 8 |
| Conditional JR, taken / not taken | 12 / 7 |
| DEC A / LD A,n / RET | 4 / 7 / 10 |

- Optimized: `28 + 10*34 + 11*(8+12) + h*(34-5) + 10`
  = **598 + 29h T**.
- Baseline: initial five-bit probability alignment costs
  `7 + 5*(8+8+4+12)-5 = 162 T`; load the eleven-step counter costs 7 T.
  The main loop costs `11*(34+8+8+12+4+12)-5 + 29h`.
  Including initialization and RET gives **1060 + 29h T**.
- Difference: **-462 T per adaptive bit**, independent of its probability.
  Both variants' measured whole-block differences equal `462 * bit_count`.
  For valid nonzero eleven-bit inputs the routine ranges are 627..917 T
  optimized and 1089..1379 T baseline.

[The benchmark](benchmark_lzma_z80.py) independently checks the timing table
instruction by instruction on an 856-byte fixture: 594104 baseline and
450793 optimized instructions (1044897 total), with the same totals as the
native emulator's unrestricted runs. It also executes 8188 multiply cases
per variant: every probability 1..2047, with zero, one, maximum and seeded
random 21-bit operands. Products and absolute timing formulas all agree.

These counts include initialization, probability updates, range decoding,
bounds checks, memory writes and termination. They exclude physical memory
contention, player packet work, ROM, disk latency, paging and ISR costs.
The synthetic interrupt test is recorded separately and never added to the
decoder-only comparison. The main player's hot path changes by **0 T**.

## ABI and RAM contract

Call `lzma_decode` with HL=input address, DE=output address, BC=exact output
length. Store the exclusive input limit at `input_end` first. On return,
`A=0, carry=0` means success; `A=1, carry=1` means invalid input or size.
`input_ptr` and `output_ptr` retain progress. Errors restore the entry stack
pointer before RET; partial output and models are invalid after an error.
The next call initializes the entire state again.

Caller responsibilities: allocate nonoverlapping input, output, code,
probabilities, scalar state and stack; keep these regions mapped for the
entire call. The decoder checks compressed-input bounds, output capacity,
history distances, EOS, final range-code zero and exact input consumption.
It does not provide a checksum. All BC/DE/HL registers in both sets and the
main AF are clobbered; IX, IY and AF' are preserved. No DI/EI or paging
instructions occur in the decoder. An ISR must preserve all registers it
uses, including alternate BC/DE/HL, and restore paging. Calls are not
reentrant and there is no cooperative yield API yet.

Standalone test allocation (end addresses exclusive):

| Region | Addresses | Bytes |
| --- | --- | ---: |
| Compressed input capacity | 4000..8000 | 16384 |
| Optimized decoder | 8000..85B8 | 1464 |
| Probabilities | A000..AF2E | 3886 |
| State and caller configuration | B000..B040 | 64 |
| Reserved test stack | BEF0..BFF0 | 256 |
| Output, also history | C000..FE00 | 15872 |

The component allocation is 37926 bytes. **This is not a Spectrum player
memory map:** input occupies the primary screen area in the flat test RAM.
No RAM is inherited from another disk. A production allocation would have
to retain both screens, player code, AY/IRQ, TR-DOS workspace, producer
slots and disk buffers within the full 128-KiB budget. No such allocation,
in-place input/output overlap, paging contract or sustained disk delivery
has been accepted for LZMA. Its measured CPU cost already rejects integration.

## Verification and reproduction

[Saved report](lzma_z80_benchmark.json), [dependency pins](requirements-lzma-z80.txt).
The script verifies the existing raw/compressed archive hashes; it does not
re-encode the video or build complete disk variants. It records source and
binary hashes, per-block output hashes, cycles and executed path counters.

Per variant, verification also covers:

- 17 independent liblzma-generated cases: empty input, a literal, short and
  long overlapping repeats, all byte values, incompressible input, matched
  literals, length boundaries and distance 15840.
- 27 required failures: all truncated prefixes of a small stream, invalid
  initial byte/code, trailing input, wrong output sizes and size above limit.
  Another 64 seeded bit flips all fail, agreeing with liblzma.
- Read guards reject uninitialized history and reads outside allowed regions.
  Write guards protect the entire code/input and other RAM; output and stack
  writes are tracked. IX/IY/AF' and stack restoration are checked on errors
  as well as success. Non-page-aligned input/output also decode exactly.
- Synthetic IM1 interrupts at the CPU emulator's 100000-T frame events:
  53 baseline and 42 optimized interrupts preserve the result and ABI.
  The ISR saves both register sets; observed stack usage is 28/30 bytes.
  This is **not** a 50-Hz AY, Spectrum contention, IM2 or TR-DOS test.

```text
python -m pip install --target .tmp/lzma-z80-packages --only-binary=:all: --no-deps -r toolkit/requirements-lzma-z80.txt
# Add .tmp/lzma-z80-packages to PYTHONPATH.
python toolkit/benchmark_lzma_z80.py
```

The script assembles both variants with [pyz80](https://github.com/simonowen/pyz80)
and executes their machine code using [kosarev/z80](https://github.com/kosarev/z80).
Intermediate binaries, symbol exports and listings stay in
`.tmp/lzma-z80-build`; all reproducing sources are tracked. Use `--smoke`
to omit the archived video blocks and `--output` for a temporary report.
The default report has `complete=true` for this component experiment and
`release=false`. No full-movie timing, quality, cold-boot or TRD claim follows.
