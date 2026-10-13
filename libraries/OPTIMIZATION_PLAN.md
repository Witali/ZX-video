# Z80 codec optimization checklist

Authorized 2026-10-13. Branch `codex/z80-codec-tricks`, worktree
`C:/Work/ZX-video/.worktree/z80-codec-tricks`, baseline `6168ba14`.
Continue this checklist in order; complete and record one bounded experiment
before opening the next. The objective is faster exact ZX0/LZSA2 processing
with a reproducible regression check, not merely fewer instructions in an
isolated snippet. Preserve the standard compressed formats and decoded bytes.

## Queue

| ID | Technique and source | Application to investigate | Status |
| --- | --- | --- | --- |
| 01 | [Unrolled LDI](https://zx-pk.ru/threads/22089-memcpy-bystraya-peresylka-dannykh.html) | Long literal/match copies; existing ZX0 bank-ring refill | Optional measured LZSA2 candidate; already in ZX0 |
| 02 | [Register copies instead of PUSH/POP](https://zx-pk.ru/threads/33945-optimizatsiya-z80-koda-dlya-mandelbrota.html#post1138545) | All six BC/DE/HL directions, including intervening independent code/calls; distinguish live saves | Already present; full interleaving audit retains live saves |
| 03 | [RES/SET instead of accumulator masks](https://zx-pk.ru/threads/33945-optimizatsiya-z80-koda-dlya-mandelbrota.html) | Offset/length fields and aligned addresses; check all live flags and A | Inapplicable: live flags/value or multi-bit masks |
| 04 | [INC L instead of INC HL](https://zx-pk.ru/threads/21702-optimizatsiya-v-hl.html) | Input windows and word reads; prove page crossings and preserve carry | Already present in page-aware ZX0; unguarded replacement rejected |
| 05 | [Fast jump tables](https://zx-pk.ru/threads/30694-vyravnivanie-utrambovyvanie-i-vpikhivanie-koda-bystrye-tablitsy-perekhodov-i-sjasm.html#post1020767) | LZSA2 dispatch; compare existing S/P branches, count complete entry work and table padding | Rejected: every class slower with live HL preserved |
| 06 | [Power-of-two table placement](https://zx-pk.ru/threads/33945-optimizatsiya-z80-koda-dlya-mandelbrota.html#post1138932) | Decoder lookup/history bounds; preserve actual history and nonwrapping EOF | Optional measured ZX0 bank table; history masking rejected |
| 07 | [POP/PUSH bulk transfer](https://zx-pk.ru/threads/22089-memcpy-bystraya-peresylka-dannykh.html#post640226) | Literal copying only where overlap/order/IRQ contracts permit; retain AY registers | Rejected for current overlap/live-register/private-stack ABI |
| 08 | [Constant data embedded in instructions](https://zx-pk.ru/threads/22089-memcpy-bystraya-peresylka-dannykh.html#post640483) | Constant fills/dictionaries; count compiled code and on-disk bytes, not only execution | Inapplicable to runtime standard-format literals |
| 09 | [Carry converted to a mask](https://zx-pk.ru/threads/20455-ispolzovanie-steka-i-preryvaniya.html#post559684) | Offset signs, bounds and wrap corrections; preserve ZX0 bit/LZSA2 nibble reservoirs | Inapplicable: ADC/rotate paths already cheaper |

Each item ends as **adopted**, **optional measured candidate**, **already
present**, **rejected**, or **inapplicable to the current ABI**, with concrete
code/measurement evidence. Do not force a trick where its preconditions fail.
The forum snippets are starting points; timings use
[Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf).

## Experiment protocol

1. Save the precise baseline revision, generator options, emitted region
   bytes/hashes, input hashes and complete caller/register/memory contract.
2. State the transformation and prove its bounds, flags, overlapping matches,
   input-frontier, EOF and suspension behavior. Keep comments in generators.
3. Count each changed path before/after from the instruction table. Record
   absolute totals and deltas, code/state bytes, stack, tables and bank placement.
4. Replay complete identical blocks in the independent Z80 core, including
   lengths/offset boundaries, random valid streams, output demands, source
   overlap and register-preserving interrupts. Report slower blocks and slices.
5. Keep compressed size/sectors in the comparison. Run library and toolkit
   regression checks appropriate to the changed path. Preserve existing default
   profiles until a replacement satisfies their full application requirements.
6. Separate native instruction counts from ULA/IRQ, TR-DOS and physical disk
   latency. A player-default change requires the actual 128-KiB allocation and
   complete producer/consumer/publication/Fuse checks from AGENTS.md. Component
   evidence cannot qualify a movie or a release disk.
7. Save a reproducible report, update this checklist and root CHANGELOG.md,
   then commit only that completed experiment. Keep rejected/interrupted work
   and its reason. No automatic merge, push or unrelated codec/movie sweep.

## Retained baseline evidence

- [Extraction report](verification.json): 31 exact decoder profiles, 77 tests,
  two exact producer variants and isolated package checks.
- [Current timing assumptions](TIMING.md): consistent endpoints and separate
  deterministic/physical costs.
- [24 complete streaming edge cases](evidence/streaming_lzsa2.json): six native
  input placements per case, EOF, guards, sectors and interrupts.
- `toolkit/row_lzsa_evidence/video.stream.gz` and `video.raw.gz`: 21 complete
  real LZSA2 blocks, 323940 decoded bytes, a component fixture rather than a
  release qualification. Authenticate the input hashes before reusing it.

## Results

The first nine-item pass is complete. [Corrected item01](LONG_COPY.md)
adds optional LZSA2 byte-form long copies:95 complete native blocks, both
42-case/six-placement streaming modes, real CPU gain24026 T (0.124%),
+87 ordinary/84 streaming core bytes. Short escaped16-bit encodings exposed
an initial regression; retain its reports and corrected kernels.

[Items02–09](TRICK_AUDIT.md) include all six BC/DE/HL transfer directions
and intervening independent commands/calls, bit/flag/page counterexamples,
an inferior saved-HL jump table and rejected overlap/stack/code-data masks.
Item06 adds an optional aligned ZX0 bank table:108 ->87 T per paging call,
+121..245 bytes,64 complete native banked blocks/all16 profiles, IRQ/AY checks.

Both new profiles preserve compressed bytes and default opcode/label layouts.
No movie/TRD has been rebuilt or newly qualified. The next milestone requires
selecting an application/profile with a fitting RAM reservation and complete
actual delivery/publication evidence; this pass does not start it automatically.
