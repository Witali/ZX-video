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
| 16 | Combine adjacent byte-state stores: SDCC-ADDR, our mapping | Streaming begin clears input_needed/finished; prove AF/HL liveness, layout and IRQ-visible ordering | Optional measured word_state_init: −4 T/block, −1 byte; both guarded modes pass |
| 17 | Carry-based bounded increment/decrement: ETUDES-BOUND | Only for a proven input domain with dead result flags; fix the source's lower-bound error | Inapplicable: exact lengths and modulo ring index, no saturating contract |
| 18 | Branch threading, tail calls and merged fall-through: 80CC-OPTIONS | Shorten helper/finish dispatch; CALL+RET → JP requires identical return-stack/continuation ownership | Existing tail calls retained; one-byte merge +8/+13 T rejected |
| 19 | Preinitialized data and bulk initialization: SDCC-RMW, SDCC-ADDR | State/table startup instead of per-byte code; account for writable copies, relocations and transported bytes | Constants already emitted; repeated mutable resets retained |
| 20 | Comparison orientation and reuse of existing flags: ETUDES-CMP, 80CC-DESIGN | Equality/bounds checks; only commute when the actual Z/carry/sign/overflow contract permits | Optional measured restore_compare: −5 T/demand, −2 bytes; both guarded modes pass |
| 21 | Counter-width proof and register cost: 80CC-DESIGN | Loop-local bounds and complete spill costs; include short escaped LZSA2 word encodings and alternate loops | Local bounds already used; global byte-range/role assumptions rejected |

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
[SECOND_PASS.md](SECOND_PASS.md); all items10–29 are complete and authenticated
in [second_pass_verification.json](second_pass_verification.json).

| ID | Additional technique and source | Application and required proof | Status |
| --- | --- | --- | --- |
| 22 | Residue-entry unrolled copy: Grauw, WikiTI | Extend item01 from a 16-byte prefix to the entire long run; AF retained, nonzero count, private writable code, exact thresholds including dispatch, short escaped word forms | Rejected: real21 blocks +8767 T, +112 code/+2 stack bytes;95 blocks exact |
| 23 | Bit-phase-specialized Elias paths: upstream ZX0 Mega | Selectively expand length/offset paths beyond current Fast; measure real bit-phase distribution, EOF and code/stack reservations | Optional673-byte one-shot Mega: real364 blocks −6.147% vs equal-ABI Fast;417 full cases/IRQ/relocation |
| 24 | Distance-1 match as repeated-byte fill: our derivation from loop sources | Avoid redundant history reads on long runs; include seed/dispatch/remainder costs, overlap, flags, output/input limits and suspension | Rejected: real21 +3816 T,51 slower blocks;95 blocks/IRQ exact |
| 25 | Stack-word exchange: SHIAR, MDL patterns | EX (SP),HL instead of exchange/pop/push where DE is dead; preserve continuation/IRQ stack ownership | Already in Standard;1024 live-DE counterexamples retain other saves |
| 26 | Byte displacement without a spare pair: WikiTI, our variant | Add A to HL while retaining DE; compare with actual register-pressure cost and any already-zero scratch high byte | Rejected: guard22 ->52 T,863 carry errors; signed offsets/live A retained,1824 checks |
| 27 | Counter-loop form: Grauw, WikiTI, optimizer rules | DJNZ or split counters only where B is available; CPI fusion also reads RAM/advances HL; preserve live flags and exact bounds | No eligible free B; real LDI refill count and CPI frontier counterexamples,513 checks |
| 28 | Synchronous feature-specific profile: upstream ZX0/LZSA | For fully resident blocks without yield/paging, remove coroutine checks/state; keep a separate explicit caller contract | Optional resident Fast: LZSA218 bytes/real −5.112%, ZX0207/−10.986%;95/417 full blocks, IRQ/relocation |
| 29 | Compact shared length/nibble helpers: upstream LZSA2 small | Optional size profile; retain standard fields, short-word escapes, exact EOD and coroutine/IRQ rules; measure speed penalty | Optional137-byte resident Small, −81 bytes/+14.948% real CPU vs Fast;95 blocks/IRQ exact, corrected EOF |

Speed candidates have priority over compact profiles. The source's upstream
percentages and raw core sizes do not qualify our coroutine/streaming ABI.
The [saved report](evidence/web_research_2026-10-14.json) records source hashes,
current profile sizes and exclusions. Defaults and compressed formats unchanged.

## Item30 — unconditional branch speed policy (2026-10-19)

**Decision: optional measured `fast_jumps=True` / `--fast-jumps`.** Continue
from main `dbde780c` in `.worktree/codec-speed-pass3`, branch
`codex/codec-speed-pass3`. Unconditional JR is 12 T / two bytes; JP is 10 T /
three bytes, with the same register/flag/stack contract. Conditional branches
retain their policy, including their 7-T untaken paths. ZX0 Standard has two
eligible sites; Turbo and Mega have one startup site each. ZX0 Fast already
uses absolute jumps and receives no additional gain. LZSA2 Fast has one
16-bit-offset site and, in coroutine modes, one post-yield return site.
Small retains its independent compact implementation.

The [full-block report](evidence/fast_jumps.json) records 1,631 comparisons
across seven profiles: three ZX0 profiles with 417 blocks each, plus resident
and ordinary coroutine LZSA2 with 95 blocks each, both alone and combined with
applicable prior long-copy/near-literal/restore-compare options. Inputs are the
same authenticated real, directed and seeded streams. Every candidate also
passes relocation to 9103h and register-preserving IM1 replay. No slower block
or ordinary coroutine slice is observed.

| Profile | Real blocks | Previous CPU T | New CPU T | Difference | Code bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| ZX0 Standard | 364 | 201,490,104 | 199,405,316 | -2,084,788 (-1.034685%) | 68 -> 70 |
| ZX0 Turbo | 364 | 160,653,056 | 160,652,328 | -728 | 126 -> 127 |
| ZX0 Mega | 364 | 146,422,274 | 146,421,546 | -728 | 673 -> 674 |
| LZSA2 Fast resident | 21 | 17,767,606 | 17,765,094 | -2,512 (-0.014138%) | 218 -> 219 |
| LZSA2 ordinary coroutine | 21 | 19,412,006 | 19,407,004 | -5,002 (-0.025768%) | 384 -> 386 |

The largest relative gain belongs to compact Standard's Elias loop, not to
Fast or Mega. Turbo/Mega save exactly 2 T per block, so their one-byte growth
is only an explicitly selected speed/space tradeoff. Existing compact profiles
remain available. No measured layout adds a rounded 256-byte code region sector.
Stack, state and compressed payload sizes are unchanged. Actual boot packing
and physical delivery remain unmeasured.

The [authenticated integration summary](evidence/fast_jumps_verification.json)
retains both CALL and direct guarded modes: 63 complete cases per mode,
including 21 real blocks and all 18 legal short word encodings, each with six
input placements. Producer-plus-decoder totals: 29,619,154 ->29,614,150 T and
27,402,683 ->27,397,679 T (-5,004 each). Producer work, waits and slices match;
each mode reads the same 772 sectors exactly once. No slower block/slice is
observed. IRQ placement is a correctness check; deterministic totals exclude
injected IRQs, ULA, ROM and physical disk latency.

**Retained rejected attempt:** expanding two cold CALL-guard retry jumps grows
its wrapper by two bytes. Its helper would end at 7D51h, exceeding the 7D50h
producer origin by one byte (the original ends at 7D4Fh). CALL construction
rejects this before decoding. The direct trial passes 63 cases but is not the
final common policy. Retain its full report, failure log and
[exact discarded code](tests/fixtures/fast_jumps_cold_retry_rejected.json).
The final option leaves cold retries unchanged and preserves the original
wrapper/state extent. The summary script reproduces the rejection. Its initial
two-byte-overrun assertion was corrected against the one-byte original headroom.

All 22 library and 67 toolkit tests pass (89), including new reservation,
16-bit-offset, gamma, overlap, relocation and CLI/export regressions. All 31
old decoder byte/address/label profiles and six upstream resources remain exact.
Both original producer variants retain code, labels and timing rows. Independent
wheels install without converter imports and export all old resident profiles
plus five optional profiles exactly; no external encoder rerun is claimed.
Initial system-TEMP access and sparse-import setup failures were resolved and
are recorded in the summary. This completes item30. Player adoption, physical
timing, movie qualification and repository migration remain separate work.

Reproduction uses `z80==1.2.0`, the authenticated fixtures listed in the report,
and TMP/TEMP inside the worktree:

```powershell
python -m unittest discover -s libraries/tests -v
python libraries/tests/measure_fast_jumps.py --output libraries/evidence/fast_jumps.json
python -c "import gzip;from pathlib import Path;[(Path('.tmp')/('lzsa-'+k)).write_bytes(gzip.decompress((Path('toolkit/row_lzsa_evidence')/('video.'+k+'.gz')).read_bytes())) for k in ('stream','raw')]"
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/lzsa-stream --raw .tmp/lzsa-raw --output .tmp/fast-jumps-call-before.json
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/lzsa-stream --raw .tmp/lzsa-raw --fast-jumps --output .tmp/fast-jumps-call-after.json
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/lzsa-stream --raw .tmp/lzsa-raw --direct-header --output .tmp/fast-jumps-direct-before.json
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/lzsa-stream --raw .tmp/lzsa-raw --direct-header --fast-jumps --output .tmp/fast-jumps-direct-after.json
```

`tests/summarize_fast_jumps.py --stream-directory .tmp --library-tests 22
--toolkit-tests 67 --output libraries/evidence/fast_jumps_verification.json`
also consumes the indexed rejected-trial evidence, successful test logs,
both wheel smoke reports and `compare_producer.py` output. Its report indexes
the full gzip archives and embeds wheel results. Preserve their checkpoint
and source hashes when reauthenticating a historical run.

## Item31 — measured conditional Fast branches (2026-10-19)

**Decision: optional measured intermediate step; the 10% goal stays active.**
The new user request starts from `f5a0362c`, including item30. Full real token
and native branch profiles show that short matches dominate; do not recycle
old gains, weaken coroutine features, change inputs, or use Standard as the
primary baseline. Keep the separately recorded Mega baseline in view.

`branch_tuned=True` / `--branch-tuned` selects JR/JP forms from the complete
real-input frequencies. Both instructions preserve flags; their 7/12 versus
10 T costs depend on taken frequency. The generator uses an injected private
assembler per call and retries an out-of-range selected JR as JP. No global
assembler mutation is used in the public packages. Metadata and generated
assembly identify the option and its performance tradeoff. Defaults and all
upstream resources stay exact; Small and non-Fast ZX0 profiles stay independent.

All 1,024 main profile comparisons use unchanged inputs: Fast ZX0 resident
and 256-byte-demand coroutine each replay 417 complete blocks, and LZSA2
resident/coroutine each replay 95. Every candidate also passes relocated
9103h code and register-preserving IRQ execution. The public package results
match the previously frozen independent candidate byte/address/label maps.

Real gains are 1.478241% ZX0 resident (207 ->193 bytes), 1.080806% coroutine
(401 ->388); LZSA2 +fast_jumps gains 0.284885% resident (219 ->220) and
0.260782% coroutine (386 ->387). Absolute counts and endpoints are in
[TIMING.md](TIMING.md#measured-fast-conditional-branches-item31-2026-10-19).
All real blocks improve. Three directed ZX0 cases per profile are 1..4 T
slower; 17 directed LZSA2 cases are 3..8 T slower. Ordinary slices can also
be slower: retain every counterexample in the native report rather than
describing aggregate gains as universal. One shortened ZX0 coroutine branch
exceeds relative reach and retains JP; the resident branch fits.

Another 570 complete native comparisons cover six public LZSA2 combinations
with/without fast_jumps, long-copy/near-literal, and ordinary restore-compare.
Both partial-input modes pass 63 cases with six placements, including all
21 real blocks and 18 legal short word forms. Producer work/waits/slices and
772 once-only sectors per mode match the prior fast_jumps baseline. Guarded
totals improve 50,287 T each; 32/2,670 slices per mode are slower, maximum
+43 T. No real block slows overall. The wrapper/state/core extents stay exact.

All 25 library and 67 toolkit tests pass (92), with 31 exact default profiles
and six exact upstream resources. Independently installed wheels include
the new helper and preserve converter-free imports and byte-exact CLI/ORG-DB
exports. This does not promote a player default, prove physical delivery,
qualify a movie/TRD or complete the migration plan. The new 10% goal is not
achieved; this step supplies a smaller/faster compatible base for further work.

- [Complete real token mix](evidence/ten_percent_copy_mix.json), recorded
  at the frozen source checkpoint in commit `1158fd8c`.
- [Native branch frequencies](evidence/ten_percent_branch_mix.json),
  reproduced by `tests/profile_branch_mix.py`.
- [Independent candidate/native regressions](evidence/ten_percent_tuned_branches.json),
  reproduced by `tests/measure_tuned_branches.py`.
- [Public option combinations](evidence/ten_percent_tuned_combinations.json),
  reproduced by `tests/measure_tuned_combinations.py`.
- [Guarded/native/package authentication and full archives](evidence/ten_percent_branch_verification.json),
  reproduced by `tests/summarize_tuned_branches.py --directory .tmp --output libraries/evidence/ten_percent_branch_verification.json`.

For the guarded runs, use the same decompressed fixtures and `--noncanonical
--stream .tmp/lzsa-stream --raw .tmp/lzsa-raw --fast-jumps --branch-tuned`
arguments as item30, with and without `--direct-header`; save to
`.tmp/tuned-branch-call.json` / `.tmp/tuned-branch-direct.json`. Successful
unit logs and both isolated smoke results are indexed by the summary.

## Item32 — proven multi-byte Fast ZX0 literal prefix (2026-10-19)

**Decision: optional resident gain; explicit coroutine request-cost tradeoff.**
`literal_prefix=True` / `--literal-prefix` restores one safe upstream LDI before
LDIR on BC>=2. Resident cost is +2 bytes and -5 T per multi-byte literal run;
BC=1 bypasses the prefix. Deferred long/short coroutine checks share EX/LDIR,
preserving quota-before-copy and every published output frontier, but add
30 bytes and 26 T per target synchronization. All 417 blocks x four profiles
pass complete before/after, relocation and IRQ (6,672 native runs).

On 364 unchanged real blocks, resident saves 569,485 T with no slower case;
256-byte-demand coroutine saves 268,301 T overall, but two real blocks slow
617/17 T and 2,783 real slices slow at most 26 T. Preserve these regressions.
An independent protected runner forces IRQ at 28 deferred-EX checkpoints and
checks zero/repeated/single-byte demands before any output; all pass. 28 library
tests, 31 exact default profiles, six exact upstream resources and isolated
wheel/CLI exports pass. Leave flags off by default and choose hot reservations
explicitly; no player/streaming default is promoted. This does not complete
the active ten-percent goal. [Full arithmetic, evidence and reproduction](LITERAL_PREFIX.md).

## ZX0 repeat-gamma tail refill (2026-10-19)

**Decision: accept an optional three-byte intermediate optimization.**
The shared length-two LDIR path cannot simply be duplicated profitably:
its 5-T copy saving is smaller than an added join or indirect-offset fetch.
That instruction audit led to a rare repeated-match gamma continuation whose
CALL/RET is avoidable. `inline_tail_refill=True` / `--inline-tail-refill` for
Fast replaces that tail with a local refill and CALL NC ReadGammaAligned,
then the same CopyMatch1 continuation. Exact counts are -18/-5 T depending on
the stop bit, with no extra data/state/buffer and no larger stack reservation.

All four plain/branch-tuned resident/coroutine profiles pass 417 cases, each
also relocated and with IRQs. There are no slower blocks/slices; real CPU
saves 359,963 T per profile, +3 code bytes. All 31 defaults/six upstream
resources remain exact, 27 library tests pass, and the installed ZX0 wheel
exports the option independently. See [TAIL_REFILL.md](TAIL_REFILL.md) for
absolute counts, complete reproduction and the separately tracked Mega.
This component improvement leaves the 10%-per-library goal active; it does
not qualify player/movie delivery or change defaults.
