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
The [authenticated final summary](optimization_verification.json) records
79 observed unit tests, exact original resources and raw code-sector estimates.
No movie/TRD has been rebuilt or newly qualified. The next milestone requires
selecting an application/profile with a fitting RAM reservation and complete
actual delivery/publication evidence; this pass does not start it automatically.

## Additional research queue (2026-10-13)

The user requests further forum pages and recalls a compiler named like
`x80cc`. [Additional survey](FORUM_RESEARCH.md) records 15 topics/54 pages,
explicit partial coverage, source post links and the unconfirmed 80cc naming
hypothesis. The first nine decisions above remain complete. The following
12 candidate groups require their own sequential codec experiments; primitive
screening does not mark them adopted or fully audited.

Source group names below link to [the survey's source list](FORUM_RESEARCH.md#source-groups-for-candidates-1021).
The proposed codec sites are our inferences from those sources.

| ID | Technique and source group | Application and required proof | Status |
| --- | --- | --- | --- |
| 10 | Branch choice and helper placement: ETUDES-JUMP, 80CC-OPTIONS | Move optional LZSA2 long-copy helper to remove its trampoline; retain 7-T untaken word path, JR bounds and full core reservation | Optional measured near_literals profile: −10 T/call, −3 bytes |
| 11 | Reuse loaded values across independent code: SDCC-RMW, 80CC-OPTIONS | Repeated state/history loads and spills; prove source immutability, liveness at both endpoints and every control-flow edge | Required nibble/page reloads retained; safe caching +22/+8 T |
| 12 | Direct known-address access: SDCC-ADDR | Remove temporary HL/IX/IY construction only when the pointer is dead; include complete setup/save costs | Already direct for fixed state; live input pointer retained |
| 13 | In-place memory arithmetic: SDCC-RMW | Indexed shift instead of load/modify/store only when A is dead; audit nibble/bit reservoir ownership | No indexed state site; input mutation rejected, no speed gain |
| 14 | Rotate/mask decomposition and narrow constant shifts: ETUDES-SHIFT, 80CC-OPTIONS | Offset/nibble extraction; prove discarded bits, carry and S/Z/P/V/N/H requirements | Existing rotations retained; slower nibble path/unproved word narrowing rejected |
| 15 | Running pointers and reused address calculations: 80CC-OPTIONS | Avoid recalculating state addresses across a loop; retain BC copy count and suspension state | Running pointers already present; unconditional guard cache +26 T rejected |
| 16 | Combine adjacent byte-state stores: SDCC-ADDR, our mapping | Streaming begin clears input_needed/finished; prove AF/HL liveness, layout and IRQ-visible ordering | 30 → 26-T primitive; codec pending |
| 17 | Carry-based bounded increment/decrement: ETUDES-BOUND | Only for a proven input domain with dead result flags; fix the source's lower-bound error | 233 corrected value cases pass; codec pending |
| 18 | Branch threading, tail calls and merged fall-through: 80CC-OPTIONS | Shorten helper/finish dispatch; CALL+RET → JP requires identical return-stack/continuation ownership | Pending codec experiment |
| 19 | Preinitialized data and bulk initialization: SDCC-RMW, SDCC-ADDR | State/table startup instead of per-byte code; account for writable copies, relocations and transported bytes | Pending codec experiment |
| 20 | Comparison orientation and reuse of existing flags: ETUDES-CMP, 80CC-DESIGN | Equality/bounds checks; only commute when the actual Z/carry/sign/overflow contract permits | Pending codec experiment |
| 21 | Counter-width proof and register cost: 80CC-DESIGN | Loop-local bounds and complete spill costs; include short escaped LZSA2 word encodings and alternate loops | Pending codec experiment |

Existing default profiles remain exact. The new queue contains ideas to
evaluate, not additional accepted gains or a new player release.

## Other-site speed/size research (2026-10-14)

The user prioritizes speed, then code size, and asks for sources outside
zx-pk.ru. [Survey and priority](WEB_RESEARCH.md) connects Grauw, SHIAR,
WikiTI, z80 Heaven, ticalc, MDL, SDCC/z88dk and upstream decoder sources to
current library paths. Seven primitive groups pass6604 native cases; these
are conditional snippets, not completed codec/streaming/IRQ experiments.
Item20 now has a concrete LZSA2 `sync` proposal: restore HL with ADD HL,DE
after subtraction instead of reloading target, 35 ->30 T and6 ->4 bytes;
S/Z/PV/C agree, H/N differ. The authorized second pass is tracked in
[SECOND_PASS.md](SECOND_PASS.md); items10–15 are complete, item16 is next.

| ID | Additional technique and source | Application and required proof | Status |
| --- | --- | --- | --- |
| 22 | Residue-entry unrolled copy: Grauw, WikiTI | Extend item01 from a 16-byte prefix to the entire long run; AF retained, nonzero count, private writable code, exact thresholds including dispatch, short escaped word forms | 543 primitive copy cases; codec pending |
| 23 | Bit-phase-specialized Elias paths: upstream ZX0 Mega | Selectively expand length/offset paths beyond current Fast; measure real bit-phase distribution, EOF and code/stack reservations | Source inspected; codec pending |
| 24 | Distance-1 match as repeated-byte fill: our derivation from loop sources | Avoid redundant history reads on long runs; include seed/dispatch/remainder costs, overlap, flags, output/input limits and suspension | 768 exact16-byte probes; codec pending |
| 25 | Stack-word exchange: SHIAR, MDL patterns | EX (SP),HL instead of exchange/pop/push where DE is dead; preserve continuation/IRQ stack ownership | 96 primitive cases; already present at some ZX0 sites; audit pending |
| 26 | Byte displacement without a spare pair: WikiTI, our variant | Add A to HL while retaining DE; compare with actual register-pressure cost and any already-zero scratch high byte | 4608 primitive cases; codec pending |
| 27 | Counter-loop form: Grauw, WikiTI, optimizer rules | DJNZ or split counters only where B is available; CPI fusion also reads RAM/advances HL; preserve live flags and exact bounds | DJNZ256 lengths; caller applicability pending |
| 28 | Synchronous feature-specific profile: upstream ZX0/LZSA | For fully resident blocks without yield/paging, remove coroutine checks/state; keep a separate explicit caller contract | Standard/Turbo already available; additional Fast/LZSA profiles pending |
| 29 | Compact shared length/nibble helpers: upstream LZSA2 small | Optional size profile; retain standard fields, short-word escapes, exact EOD and coroutine/IRQ rules; measure speed penalty | Raw134-byte source inspected; adapted profile pending |

Speed candidates have priority over compact profiles. The source's upstream
percentages and raw core sizes do not qualify our coroutine/streaming ABI.
The [saved report](evidence/web_research_2026-10-14.json) records source hashes,
current profile sizes and exclusions. Defaults and compressed formats unchanged.
