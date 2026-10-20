# Codec speed and total service-memory frontier

Updated 2026-10-20. The cap is **10,000 bytes of library service memory**:
all emitted hot/cold code, mutable state, tables, alignment, required caller
and private stacks, scratch and internal buffers. Count embedded operands
once. The user excludes compressed input and decoded output/history, which
must be reported separately. Application IRQ requirements are additional.

Compare unchanged data and the same ABI. The goal baseline is `f5a0362c`
Fast, with the earlier `fast_jumps` included for LZSA2. Counts below are
complete deterministic CPU T-states on the frozen real corpus; IRQ execution,
ULA contention, ROM and physical disk latency are separate. Ordinary
coroutines use 256-byte demands and preserve every publication cursor.

[Initialization accounting](BENCHMARK_INITIALIZATION.md) confirms all resident
and ordinary begin/setup work is included. For guarded profiles, use the
variant table's producer+decoder total: it includes producer initialization,
initial/repeated guard patching and decoder begin/sync/EOF. The historical
decoder-only timing is retained as a component. Expanded CALL/direct totals
are23,106,239/20,892,688 real T,8.4733%/9.2876% less than same-mode pass Fast.

For direct links to each public builder and implementation file, copyable
selection arguments and comparisons with both original Fast and this pass's
baseline, see [Decoder variants](DECODER_VARIANTS.md). That table also retains
the slower Standard/Small choices with the lowest measured service memory.

The latest user request explicitly includes minimum size, maximum speed and
nondominated intermediate tradeoffs. [The next pass](NEXT_TRICKS_PLAN.md)
therefore qualifies useful faster/larger E02/E03 screens and audits the
smallest decoders. [F00](NEXT_F00_HOT_PATHS.md) is now complete: all three
optional LZSA2 hot profiles pass native and package gates. Every block's44 T
entry setup and28 T EOF restoration/RET are included; required external
target preparation is0 T. Future one-time preparation must enter cold-start
and batch totals. The linked variant table identifies all nondominated
resident points on the measured real aggregate, with function/file links.

[S01](NEXT_S01_MINIMUM.md) keeps ZX0 Standard's74-B minimum, adds compact
75/78-B gamma/SMC choices and reduces LZSA2 Small145 ->144 B. Every entry
initializer is included; SMC's43-T startup includes its20-T offset reset.
The74-call table preserves prior choices and all slower-case lists.

## Current resident choices

The later E01 optional modes improve both time and service memory against
their same-feature predecessors. [ZX0](NEXT_E01_ZX0_BRANCHES.md) offers three
branch policies; [LZSA2](NEXT_E01_LZSA.md) offers a cold escape layout. Retain
their complete non-real regression lists; every real block is no slower.

| Codec/profile | Total service | Real CPU T | Gain vs Fast |
| --- | ---: | ---: | ---: |
| ZX0 Small gamma-JP | **75 B** | 199,881,370 | -28.118801% |
| ZX0 Small SMC | **78 B** | 189,794,309 | -21.653255% |
| ZX0 Fast tuned | **197 B** | 153,706,279 | 1.478241% |
| ZX0 Fast tuned +literal prefix +tail refill | **202 B** | 152,776,831 | 2.073993% |
| ZX0 Mega tuned +fast jumps | **674 B** | 145,701,295 | 6.609229% |
| ZX0 Maximum shared prefix 31 | **2,810 B** | 141,342,108 | 9.403356% |
| ZX0 Maximum shared prefix 63 | **3,578 B** | 140,403,868 | 10.004743% |
| ZX0 Maximum shared prefix 127 | **5,114 B** | 139,916,508 | 10.317128% |
| ZX0 Maximum shared prefix 227 | **7,554 B** | 139,893,048 | 10.332166% |
| ZX0 Maximum shared prefix 228 | **7,578 B** | 139,892,818 | 10.332313% |
| ZX0 E01 shared127, `policy='fast'` | **5,053 B** | 139,576,574 | 10.535017% |
| ZX0 E01 shared228, `policy='fast'` | **7,517 B** | 139,552,884 | 10.550202% |
| LZSA2 Fast jumps +compact branches | **222 B** | 17,724,654 | 0.227637% |
| LZSA2 Small compact EOF | **144 B** | 20,423,420 | -14.963760% |
| LZSA2 Fast jumps +tuned branches +nibble prefill | **228 B** | 17,635,500 | 0.729487% |
| LZSA2 Wide shared | **3,452 B** | 15,869,483 | 10.670425% |
| LZSA2 Wide expanded | **7,004 B** | 15,623,953 | 12.052517% |
| LZSA2 Shared +short new/repeated | **4,228 B** | 15,188,829 | 14.501837% |
| LZSA2 Hybrid compact | **4,999 B** | 15,048,469 | 15.291926% |
| LZSA2 Hybrid balanced | **6,500 B** | 14,983,119 | 15.659782% |
| LZSA2 Hybrid fast | **9,500 B** | 14,944,429 | 15.877569% |
| LZSA2 E01 Hybrid compact | **4,998 B** | 15,030,346 | 15.393940% |
| LZSA2 E01 Hybrid balanced | **6,499 B** | 14,964,996 | 15.761797% |
| LZSA2 E01 Hybrid fast | **9,499 B** | 14,926,306 | 15.979583% |
| LZSA2 Hot nibble | **9,515 B** | 14,918,596 | 16.022983% |
| LZSA2 Hot literals | **9,529 B** | 14,913,435 | 16.052034% |
| LZSA2 Hot combined | **9,545 B** | 14,905,725 | 16.095434% |

Baselines:156,012,520 T /364 real ZX0 blocks and 17,765,094 T /21 real LZSA2
blocks. Totals include four caller-stack bytes; gamma-JP/Wide need six and
Small LZSA2 needs eight;
the caller return counts. All static state,512-byte Wide tables and alignment
padding already emitted in the code regions count once. Wide totals above
assume aligned code; arbitrary alignment adds at most 255 B (3,707/7,259 B).

The 197-byte ZX0 and 222-byte LZSA2 profiles are smaller and faster than their
211/223-service-byte Fast baselines. The compact combinations spend a few
more bytes for further gains. Tuned Mega and shared Wide are useful middle
choices. Shared prefix 127 keeps almost all tested ZX0 maximum speed with
4,886 B left under the cap. Shared 228 spends 2,464 more bytes to save
23,690 T beyond shared 127; E01 saves another339,934 T and61 B from either
cap with its fastest policy. E01 Hybrid fast is the fastest measured resident
LZSA2 profile. A finite measured frontier does not prove global optimality.

The optional [fixed LZSA2 hybrids](LZSA_HYBRID.md) use
`lzsa.hybrid.build(profile='compact'/'balanced'/'fast')`. Compact saves
2,005 service bytes and 3.683344% CPU time versus old Expanded; fast gains
4.349245%. Six fixed base/short profiles each pass all 95+580 cases with IRQ,
relocation and exact per-token cycle models. Fast has four directed +4-T
regressions versus Expanded; compact/balanced retain their full slower-case
lists. These new options are resident-only. Ordinary/guarded profiles below
retain their earlier complete proofs. Fast at9103h plus the diagnostic IRQ
uses 9,772 service B; application producer/buffer needs remain separate.

The optional [shared-prefix layout](ZX0_SHARED_PREFIXES.md) reduces cap228
from 9,990 to 7,578 service B and saves another 277,150 real T (0.197724%).
All five caps pass 417+56 cases, IRQ, relocation and exact per-block cycle
proofs. Select `zx0.maximum.build(shared_prefixes=True)` or resident CLI
`--shared-prefixes`; ordinary coroutines keep their separate implementation.

Unshared Maximum API/CLI still defaults to prefix 228. Its 9,986 code/embedded-state bytes
plus four stack bytes fit the service cap. The 13-byte AF/AF' preserving IRQ
example plus six extra stack bytes raises its total to **10,009 B**;
prefix 227 fits that example at **9,985 B**. An actually replayed minimal
`EI; RETI` handler adds three code/two hardware-stack bytes, giving prefix 228
**9,995 B**. Declare the actual application's handler requirements through
`irq_code_bytes`/`irq_stack_bytes`; the builder checks the combined reservation.

The historical Mega used 673 code bytes/146,422,274 real T, or 674/146,421,546
with its old startup jump. Its old advantage over Fast is not a new gain.
The best shared Maximum improves the separately tuned Mega 145,701,295 baseline
by **3.986565%**, so the 10.332313% Fast comparison does not establish another
10% over the strongest existing Mega. [Mega audit](MEGA_OFFSET_AUDIT.md),
[Maximum phases/prefixes](ZX0_MAXIMUM.md), [word suffix and IRQ limits](ZX0_WORD_PREFIX.md).

## Current ordinary coroutine choices

| Profile | Total service | Real CPU T | Gain vs same-feature Fast |
| --- | ---: | ---: | ---: |
| ZX0 tuned +tail refill | **407 B** | 178,298,032 | 1.280110% |
| ZX0 tuned +literal prefix +tail refill | **437 B** | 178,029,731 | 1.428663% |
| ZX0 Maximum coroutine prefix 31 | **4,901 B** | 167,431,057 | 7.296927% |
| ZX0 Maximum coroutine prefix 63 | **6,437 B** | 166,492,817 | 7.816411% |
| ZX0 Maximum coroutine prefix 127 | **7,973 B** | 166,005,457 | 8.086252% |
| LZSA2 compact branches +prefill +compact sync +jumps | **402 B** | 19,252,552 | 0.795857% |
| LZSA2 tuned branches +prefill +compact sync +jumps | **404 B** | 19,242,382 | 0.848261% |
| LZSA2 Wide shared | **3,633 B** | 17,511,393 | 9.767664% |
| LZSA2 Wide expanded | **7,185 B** | 17,265,863 | 11.032826% |

Baselines:180,610,040 T ZX0 /19,407,004 T LZSA2. Totals include all wrappers,
state, four caller-stack bytes and 12 ZX0/14 compact LZSA2/16 Wide private
stack bytes. Wide arbitrary alignment adds up to 255 B:3,888/7,440 worst
totals. The sample 13-byte IRQ with six extra bytes on each active stack
adds 25 B to an ordinary coroutine. Other handlers need separate accounting.

Maximum ZX0 coroutine is an explicit Spectrum Z80 option requiring
undocumented `CP IXH`/`CP IXL` (8 T each). It saves caller IX on entry and
restores it on every return; IRQ must preserve live IX. Its total includes
7,957 emitted code/state bytes, four caller-stack bytes and 12 private-stack
bytes. With the sample IRQ it uses 7,998 bytes; the stronger tested 21-byte
IX-clobbering IRQ with eight-byte headroom per stack makes 8,010 bytes.
All 417 main and 56 high-word cases per cap preserve every Fast output/EOF
return. There are no slower complete blocks; cap 127 has 12 slower slices
(two real), maximum +71 T. Another 1,251 minimum-safe in-place comparisons,
25,918 zero/repeated/final-demand returns and 198,374 IRQs pass. A dedicated
final integration test also covers valid output ending exactly at FFFFh.
[Algorithm, rejected quota strategies and full proof](ZX0_MAXIMUM_COROUTINE.md).

Keep slower cases explicit. Maximum has no slower complete case across 417
normal and 56 high-word cases against retained Fast/tuned Mega. The compact
ZX0 combination has one slower directed resident block and 35 directed
coroutine blocks, plus 942 slower slices (145 real); all real complete blocks
improve. Literal prefix alone slows two real blocks by 617/17 T. Expanded/shared
Wide have 21/22 slower directed corpus blocks (max 20/30 T),21/28 ordinary
corpus slices and 3/324 additional probe slices; no real ordinary slice slows.
The original per-profile reports retain every case and their own comparison
baseline; do not relabel a compact-sync-only slice delta as a goal-baseline delta.

## Guarded-input LZSA2

| Profile | Consumer service | Full reference service | Real decoder CPU T | Gain |
| --- | ---: | ---: | ---: | ---: |
| Wide expanded, CALL guard | 7,344 B | **9,881 B** | 21,822,661 | 8.927190% |
| Wide expanded, direct guard | 7,336 B | **9,870 B** | 19,616,975 | 9.832250% |
| Wide shared, CALL guard | 3,792 B | **6,329 B** | 22,068,191 | 7.902516% |
| Wide shared, direct guard | 3,784 B | **6,318 B** | 19,862,505 | 8.703693% |

CALL/direct same-feature real baselines are 23,961,774 /21,756,088 T.
Consumer totals include the embedded 57/54-byte final-input guard patcher,
all state/table/padding and four caller/24 private stack bytes. They explicitly
exclude the caller's input supplier. Carry is not intrinsic to every supplier:
incrementally published input may simply remain resident until consumed.

The retained in-place supplier separately needs a 256-byte carry buffer,
its code/state and additional caller/disk stacks. Full reference totals above
also include 365 bytes of I/O code/state, the conservative 1,280-byte mock ROM
workspace and the explicit 13-byte IRQ/six-byte headroom on all three stacks.
These are aligned reference service subtotals. Arbitrary padding can add up
to 255 bytes and exceed the full-example cap; check the actual placement.
Compressed input and output/history remain separate. Physical ROM workspace
needs, disk latency and full movie timing have not been qualified here.

Each profile passes 675 cases at six input placements, additional genuine
live-code relocation by -512 bytes with IRQs, and the original 63-case
supplier replay with 772 once-only sector reads and unchanged producer costs,
waits and cursors. Retain slower slices: native real maxima are +22 T;
all-case maximum is +43 T. Shared CALL also slows one original real stream
slice by three T. These results fall short of a strict 10% guarded gain.
[Native proof](evidence/wide_guarded_native.json.gz),
[complete service inventory and authentication](evidence/wide_guarded_verification.json).

## Current integration verification

The combined generators match 25 saved complete native profile proofs exactly,
including emitted regions, labels/patch locations where recorded, and unchanged
input hashes. Original source/wheel authentication remains historical; the
new report binds current generated code separately. All 56 library and 67
toolkit/player regression tests pass. All 31 legacy layouts and six pinned
resources remain exact. Both isolated installed wheels exercise API/CLI/export,
five resident/three coroutine Maximum profiles, all eight Wide profiles,
and compact branch/sync combinations
without converter imports.

Normal corpora need at most 15,878 resident compressed-input bytes and 15,872
output/history bytes separately. Maximum's high-word supplement deliberately
tests much larger output, including 49,151-byte matches. These are tested
maxima, not universal format limits or a promise that arbitrary buffers fit
in 64 KiB. Guarded input has its own mandatory patcher/carry/supplier/stacks
accounting; its separate verification is recorded above. Resident gains do
not substitute for the independently measured coroutine/input features.
The broader approximately ten-percent objective remains active.

[Current integration authentication](evidence/frontier_completed_profiles_verification.json),
[earlier 18-profile checkpoint](evidence/frontier_integration_verification.json),
[persistent instruction timing reference](Z80_TIMINGS.md).

```powershell
python libraries/tests/verify_frontier_integration.py --extended --library-tests 56 --output libraries/evidence/frontier_completed_profiles_verification.json
```

The verifier consumes `.tmp/frontier-integration-{library,toolkit}.log`, wheels
in `.tmp/frontier-integration-wheels/`, and isolated reports in
`.tmp/frontier-integration-smoke-{zx0,lzsa}/`. No default player, format,
release disk, or physical playback qualification changes here.

## Archived compact checkpoint — 2026-10-19

The following retains the earlier checkpoint and its dated evidence. Its
future-work statements describe that point in time; current options are above.
The user's three directions at that checkpoint were:

1. Maximum speed within **10,000 bytes of total service memory**.
2. Faster execution together with less service memory.
3. Useful intermediate speed/memory tradeoffs.

The user explicitly includes code and variables, and excludes compressed input
and output/history from the service cap. Count all executable/cold code, mutable
state, tables, padding, caller/private decoder stack and internal scratch buffers.
Self-modifying operands and state already emitted in code/data regions are
included once. Caller return addresses are part of stack use. Report input,
output/history and application IRQ requirements separately; do not hide them.
An output buffer already contains its history, so do not count those bytes twice.

Keep ABI/feature-equivalent comparisons. Resident, ordinary coroutine and guarded
input are separate frontiers. Report complete unchanged real-corpus CPU and
slower cases/slices; an isolated primitive or partial run cannot establish the
best decoder. The approximately ten-percent objective remains active; a finite
set of measured candidates is not proof of a global optimum.

## Compact features integrated at this checkpoint

The goal baseline is `f5a0362c` Fast with LZSA2 fast_jumps already included.
The current snapshot combines measured branch layouts, ZX0 literal prefixes
and repeat-gamma tail refill, plus LZSA2 nibble prefill. All flags remain opt-in.

| Profile | Real baseline T | Real selected T | Gain | Emitted code/data | Stack | Total service |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZX0 resident combined | 156,012,520 | 152,776,831 | 2.073993% | 198 | 4 | **202 B** |
| ZX0 coroutine combined, 256-byte demands | 180,610,040 | 178,029,731 | 1.428663% | 421 | 4 caller +12 private | **437 B** |
| LZSA2 resident combined | 17,765,094 | 17,635,500 | 0.729487% | 224 | 4 | **228 B** |
| LZSA2 coroutine combined, 256-byte demands | 19,407,004 | 19,277,410 | 0.667769% | 391 | 4 caller +14 private | **409 B** |

The coroutine emitted totals already contain 15 state-array bytes and all
patched target/offset operands. The JSON distinguishes state arrays from
self-modifying operand cells without adding either twice. These four profiles
have no extra data tables, alignment padding or internal scratch/input buffers.
Their nonrecursive call structure bounds stack use: raw has one live saved
word/CALL plus caller return; coroutine cold CALL needs four caller bytes and
the deepest suspended decoder frame needs 12 ZX0/14 LZSA2 bytes. The complete
corpus exercises each bound. These are library stack reserves, not the rest of
an application's call stack.

For the tested 13-byte AF/AF' preserving IM1 handler, reserve six extra bytes
on every stack that may be active. Total service plus that handler/headroom is
221/462/247/434 B respectively. Reported observed IRQ high-water marks can be
lower than that conservative reserve; they are not substituted for it. Other
application IRQ/NMI handlers require their own code/stack accounting.

All retained tests require at most 15,878 bytes of resident compressed input
and 15,872 bytes of output/history, separately from the service cap. These are
test-corpus maxima, not a new universal format bound or a smaller streaming
input buffer. Compressed payloads are unchanged.

All real blocks improve versus the goal baseline in these combined profiles.
There are still directed regressions: resident ZX0 one slower block; coroutine
ZX0 35 slower directed blocks and 942 slower slices (145 real); LZSA2 seven
slower directed blocks per profile, including tiny EOF probes, and 23 slower
ordinary slices. Preserve full per-case differences. In particular, adding
literal_prefix to the already-tuned ZX0 coroutine alone slows two real blocks
by 617/17 T; the tail optimization offsets that in the combined baseline
comparison. [Individual prefix tradeoff](LITERAL_PREFIX.md),
[tail refill](TAIL_REFILL.md), [nibble cache](NIBBLE_PREFILL.md).

The smaller ZX0 coroutine with branch_tuned+inline_tail_refill, without the
literal prefix, retains the separately measured 178,298,032-T real result at
391 emitted bytes. Its same fixed-depth stacks make 407 service bytes, versus
437 for the slightly faster combined option. Keep both as intermediate choices.
The earlier Standard/Small and Mega profiles remain available and measured;
do not erase them or count their old gains as a newly discovered optimization.

## Maximum-speed work under the clarified cap

The earlier [full-token LZSA2 experiment](evidence/ten_percent_full_token_dispatch.json)
measures 12.052517% /10.670425% resident gains with expanded/shared handlers.
Emitted sizes are 6,998/3,446 B including a 512-byte table, plus six stack bytes:
7,004/3,452 service bytes at aligned placement. Unaligned placement adds padding.
Its historical rejection used the earlier code-growth preference; the user's
new maximum-speed direction supersedes that size rejection. Preserve the old
evidence as history while public packaging and coroutine/guarded equivalents
are completed in separate focused worktrees. Raw-only evidence does not prove
those additional feature profiles.

The tuned Mega and larger ZX0 phase-specialization experiments are likewise
separate work. Compare their new results against both their stronger previous
Mega baseline and the same-ABI Fast goal baseline, with all service memory
accounted. No player defaults, physical disk timing or movie release is changed.

## Complete integration evidence and reproduction

The compact combination passes 1,028 complete before/after profile comparisons:
417 ZX0 and 97 LZSA2 cases in resident/coroutine modes. Candidate IRQ and 9103h
relocation give 4,112 native runs. Every coroutine return cursor matches.
All 34 library and 67 toolkit tests pass (101); 31 old byte/address/label
profiles and six upstream resources remain exact. Both independently installed
wheels export every compact flag and both combined API/CLI profiles with exact
ORG/DB regions and no converter imports. Existing guarded results remain those
of the individually retained LZSA2 experiment; no new guarded integration run
or physical delivery proof is claimed by this ordinary-coroutine comparison.

- [Full CPU, memory, input hashes and slower cases](evidence/compact_frontier.json).
- [Authenticated sources, tests, wheels and archived logs](evidence/compact_frontier_verification.json).
- [Instruction timing reference](Z80_TIMINGS.md).

```powershell
python libraries/tests/measure_compact_frontier.py --output libraries/evidence/compact_frontier.json
python libraries/tests/verify_compact_frontier.py --directory .tmp --output libraries/evidence/compact_frontier_verification.json
```

The verifier additionally consumes `.tmp/compact-codec-integration-library.log`
(34 tests), `.tmp/compact-frontier-toolkit.log` (67), the pip-built wheels in
`.tmp/compact-frontier-wheels/` and isolated smoke reports in
`.tmp/compact-frontier-smoke-{zx0,lzsa}/`. Keep these checkpoint hashes rather
than relabeling historical measurements after later feature changes.
