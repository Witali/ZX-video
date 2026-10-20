# Retained native timing and extraction accounting

Use the local [Z80 timing desk reference](Z80_TIMINGS.md) for instruction
costs and branch/block-repeat rules; the measurements below retain their own
historical baselines, input scope and application assumptions.

Latest optional literal-copy accounting is in [LITERAL_PREFIX.md](LITERAL_PREFIX.md):
N>=2 `LDI; LDIR` is 21N-10 T versus 21N-5 T, exactly -5 T/run; the coroutine's
fourth high/low target patch adds 26 T/request. On the same 364 real blocks,
resident savings are 569,485 T, 256-byte-demand coroutine savings 268,301 T.
Two real coroutine blocks slow by 617/17 T; maximum slower slice +26 T.
These CPU-only intermediate results preserve data/defaults and do not qualify
physical delivery or complete the goal.

2026-10-13, baseline `0085a116`. Moving implementations and sharing the
guard patcher preserves all default opcode bytes, addresses and label maps.
The extraction adds **0 deterministic T-states** to any existing decoder or
producer path. Custom absolute addresses preserve instruction opcodes and
counts; contention and paging still depend on the application's placement.

Counts below use Zilog UM0080 (the same table referenced in emitted metadata).
Conditional JP=10 T, JR=7/12 T, register logical=4 T, immediate/memory
logical=7 T, LDI=16 T, LDIR=21 T per repeating byte and 16 T on the last byte.
LDIR cannot be modeled as a constant 21 T for every byte.

| Retained path / consistent endpoints | Before extraction | Library | Delta |
| --- | ---: | ---: | ---: |
| Fast/tuned Turbo copy boundary: output high below target, through AF restore | 29 T | 29 T | 0 T |
| Fast/tuned Turbo boundary: equal high, low below target | 57 T | 57 T | 0 T |
| Fast/tuned Turbo boundary: equal target through CALL yield (excludes yield body) | 74 T | 74 T | 0 T |
| Fast/tuned Turbo boundary: high above target through CALL yield | 58 T | 58 T | 0 T |
| Fast target synchronization including RET | 112 T | 112 T | 0 T |
| Tuned Turbo target synchronization including RET | 86 T | 86 T | 0 T |
| LZSA2 available header, direct entry through token_body | 46 T | 46 T | 0 T |
| LZSA2 available header, older CALL/RET entry through token_body | 96 T | 96 T | 0 T |
| LZSA2 shared guard patcher, ordinary partial / complete, excludes caller RET | 187 / 224 T | 187 / 224 T | 0 T |
| LZSA2 shared guard patcher, direct partial / complete, excludes caller RET | 174 / 211 T | 174 / 211 T | 0 T |

The guard-patcher totals use OR A (4), LD A,n (7), JP Z (10), LD (nn),A
(13), LD HL,nn (10), LD (nn),HL (16). The complete case executes one extra
LD A,n and three extra LD HL,nn. Direct mode omits the header opcode store.
The native library test measures all four paths, including a separate 10-T RET.

Historical improvement scopes remain distinct:

- [Complete Fast ZX0 CPU comparison](../toolkit/FASTER_ZX0.md): retained
  Turbo 189573555 T -> adapted Fast 183122436 T (-6451119), 188 identical
  blocks/2965011 output bytes; producer 11831304 T unchanged. Fast may slow
  individual slices (62 of 11584, at most69 T) despite improving every block.
- [LZSA2 S/P dispatch](../toolkit/LZSA2_DISPATCH.md): 21 unchanged blocks,
  decoder 19844626 ->19412006 T (-432620). None/one-or-two/extended literal
  dispatch:54/38/50 T, versus54/58/58 before that earlier optimization.
- [Direct header improvement](../CHANGELOG.md): available guard96 ->46 T
  (-50), an earlier change already retained before this extraction.

These are CPU-only component counts, not end-to-end playback rates.
The extraction's 24-case direct streaming regression records baseline
component total4101406 T versus guarded4144763 T (+43357); guarded partial
input has extra work. That comparison is to complete-input decoding, not to
the pre-extraction streaming implementation. Do not turn it into a claimed
new regression/improvement or a disk-delivery result. ROM/disk/IRQ/ULA and
actual publication timing remain separately qualified by the application.

[Item01 long-copy counts](LONG_COPY.md) add an opt-in LZSA2 profile, with
complete native/streaming comparisons and exact path/space deltas. They do
not change this default baseline or its compression cost model.

## Additional pass, items10–29

All completed measurements/audits and precise caller contracts are in
[SECOND_PASS.md](SECOND_PASS.md), authenticated by
[second_pass_verification.json](second_pass_verification.json). Existing31
defaults still have0-T instruction delta. Optional coroutine changes: nearby
literal helper -10 T/call (-3 code bytes), adjacent streaming flag clear30 ->26 T
(-1 byte), sync restore127/132 ->122/127 T (-2 bytes). Guarded42-case/six-placement
comparisons retain exact producer work/waits and167 once-only sectors per mode.

Resident-block profiles have a distinct ABI: external bounds/allocation, full
input/history, caller stack; no yield/paging/quota. Fast LZSA2 removes331 T of
wrapper and21 T per token for the same full output request; Fast ZX0 removes
311 T plus29/57 T per copy boundary. Measured real CPU savings5.112%/10.986%
are conditional on those omitted features. ZX0 Mega's phase expansion saves
6.147% versus equal-ABI Fast at673 versus207 bytes. LZSA Small137 versus218
bytes costs14.948% more real CPU; nibble helper including CALL is40 T cached,
98 T refill (1024 native phase/value probes). Its exact-EOF correction adds3
bytes versus raw upstream134 and11 T to the word-escape tail, preventing
dummy reads; plain peak stack8 versus Fast4 bytes, including caller return.

Whole-run unroll and distance1 selector were rejected for real CPU regressions
(+8767/+3816 T). Synthetic gains and isolated primitives do not override these
measurements. Standalone rounded code-region sectors are space estimates,
not disk latency or movie/frame-publication qualification.

## Optional unconditional jumps, item30 (2026-10-19)

`fast_jumps=True` / `--fast-jumps` uses JP (10 T, three bytes) for selected
unconditional JR sites (12 T, two bytes), preserving flags/registers/stack.
Conditional branch policy and cold LZSA2 input retries remain unchanged.
Counts use the same [Zilog table](https://www.zilog.com/docs/z80/um0080.pdf)
and complete-block endpoints as the preceding passes.

ZX0 Standard's two sites include the Elias backedge: real 364 blocks
201,490,104 ->199,405,316 T (-2,084,788), code 68 ->70 bytes. All 417 blocks:
207,225,467 ->205,122,965 T (-2,102,502). Turbo and Mega change one startup
jump: exactly -2 T/block and +1 byte; Fast already uses JP. LZSA2 resident
changes one offset site: real 17,767,606 ->17,765,094 T (-2,512), 218 ->219
bytes. Ordinary coroutine adds the post-yield site: real 19,412,006 ->19,407,004 T
(-5,002), 384 ->386 total region bytes. All 95 ordinary blocks:
26,352,611 ->26,346,833 T (-5,778).

Guarded 63-case CALL producer+decoder: 29,619,154 ->29,614,150 T; direct:
27,402,683 ->27,397,679 T (-5,004 each). Decoder-only totals respectively:
27,611,498 ->27,606,494 and 25,405,362 ->25,400,358 T. Producer totals
2,007,656/1,997,321 T, 772 sector acquisitions, waits and slices stay exact.
These totals include deterministic producer instructions only; ROM/physical
latency/ULA and injected IRQ costs are excluded. Six-placement native tests
include IRQ correctness separately. Default instruction delta stays 0 T.
No stack/state/input bytes or rounded code-region sectors are added.
[Decisions and the rejected cold-wrapper expansion](OPTIMIZATION_PLAN.md#item30--unconditional-branch-speed-policy-2026-10-19),
[native counts](evidence/fast_jumps.json),
[guarded/package authentication](evidence/fast_jumps_verification.json).

## Measured Fast conditional branches, item31 (2026-10-19)

The optional `branch_tuned` policy uses the full real-input frequencies to
select JR (7 T untaken / 12 T taken, two bytes) or JP (10 T, three bytes).
The condition and flags are unchanged. Real savings are not universal savings:
directed cases and individual slices can be slower. A per-call assembler
factory retries an out-of-range selected JR as JP, with no global patches.

| Same-feature profile, real input | Previous T | New T | Difference | Code bytes |
| --- | ---: | ---: | ---: | ---: |
| ZX0 Fast resident, 364 blocks | 156,012,520 | 153,706,279 | -2,306,241 (-1.478241%) | 207 ->193 |
| ZX0 Fast coroutine, 256-byte demands | 180,610,040 | 178,657,995 | -1,952,045 (-1.080806%) | 401 ->388 |
| LZSA2 Fast resident +fast_jumps, 21 blocks | 17,765,094 | 17,714,484 | -50,610 (-0.284885%) | 219 ->220 |
| LZSA2 ordinary coroutine +fast_jumps | 19,407,004 | 19,356,394 | -50,610 (-0.260782%) | 386 ->387 |

The raw Fast ZX0 layout changes 14 branches; the coroutine retains one JP
whose target would exceed relative reach, changing 13. Three directed cases
per ZX0 profile are 1..4 T slower. Seventeen directed LZSA2 cases per basic
profile are 3..8 T slower. All retained real blocks improve. Combined prior
LZSA2 long-copy/near-literal/restore profiles also pass complete replays.

Guarded CALL/direct producer+decoder totals respectively:
29,614,150 ->29,563,863 and 27,397,679 ->27,347,392 T (-50,287 each).
The producer work stays 2,007,656 /1,997,321 T; all 772 sector reads, waits,
slice counts and code/state extents match. Each mode has 32 slower slices
out of 2,670, with a largest +43 T, while all real blocks improve overall.
See the report for separate real-slice counts. These are flat CPU/model
counts, excluding injected IRQ, ULA, ROM/disk latency and publication timing.
[Native candidate and all directed regressions](evidence/ten_percent_tuned_branches.json),
[public option combinations](evidence/ten_percent_tuned_combinations.json),
[guarded/package authentication](evidence/ten_percent_branch_verification.json).
The approximately 10% goal for each library remains active and unachieved.

## Optional ZX0 repeated-match tail refill (2026-10-19)

`inline_tail_refill=True` costs three code bytes and retains the same data,
copy boundaries and caller ABI. At an exhausted repeated-match gamma
reservoir, inline refill plus CALL NC to the aligned reader replaces CALL to
the refill reader plus its RET: stop-one path 55 ->37 T (-18); stop-zero
path 49+G ->44+G T (-5), with G the unchanged aligned reader including RET.
Normal nonzero-reservoir paths stay exact. All 417 native cases verify the
per-execution sum independently and have no slower block/slice. Real 364-block
CPU falls another 359,963 T per resident/coroutine profile: branch-tuned Fast
153,706,279 ->153,346,316 T (193 ->196 bytes); branch-tuned 256-byte-demand
coroutine 178,657,995 ->178,298,032 T (388 ->391 total bytes). No state/stack
reservation grows. [Detailed counts and limits](TAIL_REFILL.md),
[full per-case evidence](evidence/ten_percent_tail_refill.json).

## Full-token LZSA2 dispatch speed bound (2026-10-19)

These are independent test-only raw decoders, not public options or player
changes. Flat CPU counts use the same Zilog instruction timings and complete
authenticated input as item31; injected IRQ work, ULA/ROM/disk latency and
publication timing are excluded.

| Raw profile, 21 real blocks /323,940 decoded bytes | CPU T | Difference from f5a0362c | Code bytes | Rounded code sectors |
| --- | ---: | ---: | ---: | ---: |
| Fast +fast_jumps baseline | 17,765,094 | 0 | 219 | 1 |
| Previous branch_tuned | 17,714,484 | -50,610 | 220 | 1 |
| Expanded full-token dispatch | 15,623,953 | -2,141,141 (-12.052517%) | 6,998 | 28 |
| Shared LL prefixes /64 bodies | 15,869,483 | -1,895,611 (-10.670425%) | 3,446 | 14 |

Both code counts include the 512-byte table. Starting at 9103h needs 253
alignment bytes: total 7,251 /3,699 bytes, with identical CPU counts. Maximum
caller stack use is six bytes versus four. No state or payload byte is added.
Sharing saves 3,552 code bytes and adds 245,530 T. Neither meets the preferred
approximately 10% code-growth tradeoff; do not promote them based on CPU alone.

The table lookup plus register restoration costs 58 T: LD A,(HL)7 +INC HL6
+EXX4 +LD L,A4 +LD H,n7 +LD A,(HL)7 +INC H4 +LD H,(HL)7 +LD L,A4
+JP (HL)4 +handler EXX4. Only HL' is scratch; entry EXX/PUSH HL/EXX costs
19 T, EOF EXX/POP HL/EXX costs 18 T, so alternate-HL preservation adds 37 T
per block. Fixed one/two literals use one/two LDIs (16/32 T); two LDIs save
5 T over two-byte LDIR37. New-offset handlers may omit LD C,n7 because their
parser replaces temporary wrapped BC before it is consumed. Repeated-offset
handlers retain the initialization. Shared nonempty literal prefixes add JP10.

Opcode-fetch probes also verify complete classification/length work before
PUSH HL for a two-byte repeat-offset match:

| Literal count | Baseline T | Expanded T /delta | Shared T /delta |
| --- | ---: | ---: | ---: |
| 0 | 116 | 75 /-41 | 75 /-41 |
| 1 | 145 | 98 /-47 | 108 /-37 |
| 2 | 166 | 114 /-52 | 124 /-42 |

The baseline includes a taken JR12 at MatchLen, not JP10. The initial manual
sum was corrected by the native timing assertion. All real blocks improve;
expanded/shared variants slow 21/22 directed corpus cases by up to 20/30 T.
The native evidence includes all 95 cases and 580 additional directed cases
per profile with relocation and register-preserving IRQ probes. This covers
every 256-token handler in both cache phases, all offset nibbles and exact
single-nibble EOF. Coroutine/partial-input modes and physical delivery remain
unmeasured. [Complete report and repro hashes](evidence/ten_percent_full_token_dispatch.json),
[reproducer](tests/measure_full_token_dispatch.py).

## Public wide service-memory accounting (2026-10-19)

The user authorizes the raw full-token layouts under a hard **10,000-byte
service** cap. Input/output/history are counted separately. Public wide and
wide-shared bytes/timings exactly match the preceding independent profiles;
the earlier preferred code-growth rejection is historical, not this cap.

| Public raw profile | Code/table/embedded variables at 8000h | Maximum caller stack including return | Service at 8000h | Service at 9103h | Worst alignment service |
| --- | ---: | ---: | ---: | ---: | ---: |
| wide | 6,998 | 6 | 7,004 | 7,257 | 7,259 |
| wide-shared | 3,446 | 6 | 3,452 | 3,705 | 3,707 |

The 512 table bytes and two writable offset bytes are inside the code count;
do not add them again. External state, scratch and internal buffers are zero.
Add actual IRQ/hardware stack headroom separately; the register-preserving
IM1 test handler needs another six bytes. Real blocks require up to 8,198
input bytes and 15,872 output/history bytes outside this service budget.
No shared-buffer packing or sector-delivery improvement is claimed.

Real resident CPU stays **15,623,953 /15,869,483 T**, saving 12.052517% /
10.670425% from the same f5a0362c 17,765,094-T baseline. Native replays match
all 95 frozen corpus counts plus 580 directed cases per public variant with
relocation/IRQ, while preserving every reported slow case. All 27 library
tests preserve default/resource hashes; isolated wheel/API/CLI/ORG-DB exports
pass. Coroutine/guarded integration and movie timing remain separate work.
[Public native evidence](evidence/wide_profiles.json),
[service-memory/package authentication](evidence/wide_profiles_verification.json).

## Optional Mega offset-register audit (2026-10-19)

Four phase-specific offset-Elias `RL B` instructions write a dead B value:
the offset consumer overwrites it with `LD B,C`, while the following ADD A,A
replaces flags. Removing them costs -8 bytes and -8 T per loop iteration:
nonrefilling body 34 ->26 T, refilling body 47 ->39 T. The frozen real corpus
executes 76,838 iterations, saving 614,704 T, 674 ->666 bytes including the
already existing startup fast jump. The necessary word shifts in other gamma
readers remain. Four separate reuse-tail JR NC ->JP changes save another
105,547 real T at +4 bytes; alone they slow 32 complete cases (31 real,
maximum156T). Their individual untaken exit always costs +3 T.

The combined `mega_tuned` candidate improves every complete retained case:
real existing-Mega 146,421,546 ->145,701,295 T (-720,251,0.491902%), 674 ->670
bytes, no larger stack or changed data. All417cases, relocation andIRQ pass;
all per-case changes match independently observed instruction counts. This
is an optional resident API/CLI profile with no coroutine equivalent. Public
bytes/labels equal the independent measured prototype. Service memory674bytes
includes670code/embedded offset and4maximum decoder stack (caller return
included); exampleIRQ adds6stack/13handler code for693bytes. Input/output
history is separate, as authorized by the user.
Do not count the old Mega gain toward the new goal or claim movie/player
qualification. [Full audit and reproduction](MEGA_OFFSET_AUDIT.md).

## Ordinary wide coroutine timing and service memory (2026-10-20)

The token-boundary quota comparisons and cold continuation preserve ordinary
Fast's complete-input feature set. CPU deltas from f5a0362c match the raw
decoder deltas; there is no quota removal or input-format change. The hot
boundary uses the same LD/CP/JP/JR paths as Fast +fast_jumps, including JP10
after suspension. The 58-T table lookup and 37-T alternate-HL block overhead
retain the preceding derivation.

| Profile, real21 /256-byte demands | CPU T | Difference | Code/table/state bytes | Private stack | Caller stack | Service bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fast +fast_jumps baseline | 19,407,004 | 0 | 386 | unchanged baseline | unchanged baseline | separately retained baseline |
| wide-coroutine | 17,265,863 | -2,141,141 (-11.032826%) | 7,165 | 16 | 4 | 7,185 |
| wide-shared-coroutine | 17,511,393 | -1,895,611 (-9.767664%) | 3,613 | 16 | 4 | 3,633 |

The wrapper and quota code add167 region bytes to either raw profile. Fifteen
state bytes/four mutable operands are already inside those regions. Caller
peak four includes the return word and CALL sync's return; private peak16
includes the saved raw HL', yield return and live register frame. Both are
measured by protected stack writes, not inferred from the maximum output case.
At9103h add253 alignment bytes: service7,438 /3,886. Worst alignment adds255:
7,440 /3,888, below10,000. Actual IRQ headroom is separate (test handler13
code bytes and6 stack bytes); input/output/history are also separate.

All95 full cases and580 directed cases per profile pass. Returned output
cursors match baseline for every demand, including relocation/IRQ and custom
target granularity. Expanded/shared have21/28 slower directed slices, max
+20/+30 T; none is real. The additional580 token/cache probes contain3/4
slower blocks and3/324 slower slices, also at most +20/+30 T; their individual
counts are retained. Thirty library tests and isolated-wheel export checks
retain31 old default profiles/six resources. Flat CPU excludes injected IRQ,
ROM/ULA/disk latency and publication scheduling. Partial-input/guarded producer
integration is not implemented by this milestone. [Native evidence](evidence/wide_coroutine.json),
[service/package authentication](evidence/wide_coroutine_verification.json).

## ZX0 gamma-depth maximum-speed frontier (2026-10-20)

`zx0.maximum.build` adds build-time count-depth specialization and safe LDI
prefixes. CopyN>P bytes: old21N-5T; new21N-5-5P+10T. Omit8T RL B only before
the eighth data bit; gamma bodies34 ->26T or47 ->39T withrefill. Retain word
loops and their extra10T join. Phase7reuse indirect offset load adds6T; changed
conditionalJR exits becomeJP, -2T taken/+3T untaken. Every measured block
matches the independent executed-instruction formula in[ZX0_MAXIMUM.md](ZX0_MAXIMUM.md).

Real364-block CPU145,701,295T from tunedMega670B becomes141,618,798 /140,680,558 /
140,193,198T at caps31/63/127. Code4450/5986/7522B; complete service4454/5990/
7526B, or4473/6009/7545including the13B/6-extra-stack probeIRQ. New best gain
is3.780404% versus tunedMega; originalFast156,012,520T comparison10.139777%
includes the oldMega gain. Preserve original unmodifiedMega673B/146,422,274T
and startupfast-jumpMega674B/146,421,546T as distinct baselines. All417cases
percap have zero slower completeblocks and passIRQ/relocation; no coroutine.
CPU counts exclude IRQservice/ULA/WAIT/ROM/disk; payload/required input sectors
stay exact. Larger resident code's application allocation is unmeasured.

## ZX0 shared word-copy suffix (2026-10-20)

After6759dedf, gamma-proven BC>=256paths copy100/101extra LDI bytes then share
the existing127-LDI suffix after match setup. The same10-T word join remains,
so each additional byte changes21T LDIR to16T LDI: -500/-505T perwordentry.
141all-case/46real/45high-word entries give exact differences70,500/23,000/
22,500T atcap227and71,205/23,230/22,725T atcap228versus cap127. RealCPU
140,193,198 ->140,170,198 /140,169,968T. Combined best gain versus tunedMega
145,701,295T is3.796347%; originalFast156,012,520T comparison10.154667%
includes pre-existingMega gains. There are no slower completecases.

Cap227code9962+stack4=9966B; cap228code9986+stack4=9990B. Actual minimal
EI/RETI handler3code+2extra-stack totals9971/9995B respectively. The larger
diagnosticAF/AF' handler13code+6extra-stack totals9985/10009B, so itscap228
application is explicitly outside10,000B; use227for that handler. Cap255
assembly gives10634code+4stack, outside the library cap, no nativequalification.
All473cases×2caps also pass twoIRQ handlers/relocation; all deltas match
instruction observers. [Full service accounting and proof](ZX0_WORD_PREFIX.md).

## Guarded wide coroutine paths (2026-10-20)

`streaming=True` retains the existing32-byte token prefix and long-literal
extent+7 guards. `direct_header=True` uses the same dead-AF direct header
guard as Fast; AF' retains its nibble. The ready header costs96 T with CALL
or46 T direct, exactly as before. The literal guard's ready CALL path costs
135 T: CALL17, PUSH AF11/PUSH HL11, ADD HL,BC11, untaken carry JR7,
LD/ADD/LD/ADC22, untaken carry JR7, CP7/taken ready JR12,
POP HL10/POP AF10/RET10. New wide long-literal JP hooks cost10 T each
when executed; all are included in complete-block totals. The original
58-T dispatch, token-boundary comparisons and37-T saved-HL' block overhead
remain intact. No original raw or ordinary coroutine machine bytes change.

| Aligned profile | Code/table/embedded state | Private stack | Caller stack | Consumer service |
| --- | ---: | ---: | ---: | ---: |
| wide guarded call | 7,316 | 24 | 4 | 7,344 |
| wide guarded direct | 7,308 | 24 | 4 | 7,336 |
| wide-shared guarded call | 3,764 | 24 | 4 | 3,792 |
| wide-shared guarded direct | 3,756 | 24 | 4 | 3,784 |

Relative to ordinary wide/shared, guarded code adds151 bytes call or143
direct, including the57/54-byte callable `update_guards` helper. Private
stack adds8 bytes for the nested literal-helper/guard/input-wait continuation;
caller stack stays4 bytes. State grows15 ->19 bytes, already embedded in
the code total. Code contains18 mutable guard/offset/frontier bytes in call
mode or17 direct; do not add them again. The maximum alignment padding is255.
The service cap applies to all required work: add the actual supplier's
code/state/carry/stacks, IRQ code/vectors/headroom and other required scratch.
The separate reference inventory counts its unchanged inline patcher even
though the consumer also exports a callable copy. Compressed input and
complete output/history are the explicit separate buffers.

The replay counts deterministic instructions separately from mocked TR-DOS
ROM service, physical disk delay and ULA contention. A reserved workspace
range demonstrates available RAM; it does not measure ROM execution or its
stack use. No movie publication/cadence claim follows from this component.

| Real21 guarded mode | Baseline decoder T | Expanded T /saved | Shared T /saved |
| --- | ---: | ---: | ---: |
| call | 23,961,774 | 21,822,661 /8.927190% | 22,068,191 /7.902516% |
| direct | 21,756,088 | 19,616,975 /9.832250% | 19,862,505 /8.703693% |

Real producer work is unchanged at1,283,578 T call or1,275,713 direct.
Including it gives25,245,352 ->23,106,239 /23,351,769 T call, and23,031,801
->20,892,688 /21,138,218 T direct. All63 original producer cases preserve772
once-only reads, waits, carry and protected banks. Each mode also passes675
native cases at six placements with exact publication cursors, relocation
and IRQ. Native real slices can slow12 times expanded or18 shared (max22 T).
The separate9E00h core proof moves live tables/handlers down512 bytes;
the9F03h probe independently covers253 alignment bytes. Both preserve exact
publication/input waits and flat T-states on all675 cases per mode.
The original producer stream has no slower real expanded slice; shared
real-3 slice8 costs+3 T. Full-case maximum regression is43 T. Every individual
delta and actual stack peak is retained. [Native/producer evidence](evidence/wide_guarded_native.json.gz),
[live table/handler relocation](evidence/wide_guarded_relocation.json.gz),
[service inventory and package proof](evidence/wide_guarded_verification.json).

## Same-quota ZX0 Maximum coroutine (2026-10-20)

Explicit optional Spectrum IX-half profile: CP IXH/IXL is 8 T versus immediate
CP7 T; retain caller IX per entry and restore at every return. High/low-ready
checks 29/57 ->30/59 T; sync 112 ->97 regular/102 final; begin 216 ->258/263;
resume 279 ->304/309; no-op demand 195 ->180/185; yield 114 ->134; finish 95 ->135.
Every native block proves raw Maximum T plus every actual added instruction.
Cap 127 real 140,193,198 raw +25,812,259 wrapper/check =166,005,457 T, versus
same-feature Fast coroutine 180,610,040 T (-8.086252%). No raw-only gain claim.
Caps 31/63 real 167,431,057 /166,492,817 T. All complete cases improve, while
32/18/12 of 12,542 main slices slow(max 348/188/71 T). Service 4901/6437/7973
bytes includes all code/state/caller 4/private 12; sample IRQ totals 4926/6462/7998.
The explicit undocumented-IX contract is absent from existing default profiles.
[Full costs, rejected strategies and native proofs](ZX0_MAXIMUM_COROUTINE.md).
