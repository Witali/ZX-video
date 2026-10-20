# Next Z80 decoder experiments

Research and testing plan, 2026-10-20. Baseline: `9c28b01f`, branch
`codex/codec-speed-pass3`, worktree `.worktree/codec-speed-pass3`.
Status: **E00..E04/F00/S01 complete; E05..E07 pending**.
[ZX0 E01](NEXT_E01_ZX0_BRANCHES.md) completes six optional public branch
layouts, bound to17,028 complete native replays plus six FFFFh probes.
[LZSA2 E01](NEXT_E01_LZSA.md) completes12 optional cold-escape layouts with
48,600 candidate native runs+8,100 independent baseline observations.
[Public authentication](evidence/next_e01_public_verification.json) binds
current APIs/wheels/exports to those proofs. All retain non-real regression
lists and exact previous defaults. E02 starts from these accepted raw modes;
baseline observer runs and predicted deltas alone do not qualify another gain.
[E02](NEXT_E02_LONG_LITERALS.md) measures and rejects all three bounded LL3
constructions: +79 B/+92,530 real T, +30 B/-12,871 T, -2 B/+2,028 T. All
675 cases per candidate pass flat guarded screening and the independent timing
model; none reduces both metrics. The accepted baseline stays E01.
[E03](NEXT_E03_NIBBLE_STATES.md) rejects full phase tables by an optimistic
memory bound and measures two prototypes: +16 B/-7,710 real T and
-1,443 B/+1,560,964 T. All675 cases,114,688 state/byte/flag checks,56 hot-family
edge inputs, resident reset tests and256 origins pass their screening models.
These screens used the earlier strict-both rule. The latest user request
supersedes that rule: minimum size, maximum speed and Pareto intermediates
are all targets. [F00](NEXT_F00_HOT_PATHS.md) now qualifies exactly three
optional hot profiles:9,515/9,529/9,545 service B and14,918,596/14,913,435/
14,905,725 real T. All13,257 native configurations and public package gates
pass; retain the four supplemental+10T word-literal regressions for clones.
Every block's44T entry setup and28T restoration/RET are included, with no
external target initializer.
[S01](NEXT_S01_MINIMUM.md) keeps ZX0's74-B minimum and adds75/78-B compact
points at199,881,370/189,794,309 real T. LZSA2 minimum becomes144 B at
20,423,420 T. All9,801 useful protected configurations and public gates pass;
retain643 non-real LZSA2 regressions and different-reference ZX0 lists.
Entry initialization34/43/24T is included.
[E04](NEXT_E04_PREFIX255.md) qualifies one shared cap255-fast endpoint at
8,165 B/139,546,674 real T: +648 B/-6,210 T against accepted cap228-fast.
All473 frozen cases are equal or faster; all3,054 protected configurations
plus nine FFFFh probes pass, including36 boundary combinations. Its46-T entry
includes the20-T reset on every block, with0T external preparation. The75-call
table and public package proof retain all74 prior calls. E05..E07 remain pending.
[E00 evidence and selected hypotheses](NEXT_E00_BASELINE.md) authenticate
the fixed inputs, all target layouts and a new minimum-safe overlap runner.
The additionally requested local Spectrum/C-core test platform is a separate
infrastructure qualification before it supplies candidate evidence.
The user requested additional internet research and a concrete testing plan.
The proposed applications are our deductions from the sources and current
generators, not measured improvements or claims made by their authors.

## Scope and fixed comparisons

Keep forward ZX0 v2 and raw LZSA2 formats, frozen compressed inputs and exact
outputs. Start with resident decoders; qualify coroutine/guarded equivalents
only in the final, separate stage. Each experiment ends with a decision,
saved evidence, root changelog and focused commit before another starts.
Independent source review can run in parallel; do not combine unverified
changes. No default promotion, main merge/push or movie rebuild belongs here.

The latest user instruction (2026-10-20) requests **minimum service memory,
maximum speed under10,000 service bytes, and useful Pareto intermediates**.
It supersedes the strict-both acceptance used by the initial E00..E03 screens.
Compare the same ABI/features, frozen inputs and placement. A dominates B
only when A is no larger and no slower, with at least one strict improvement.
Retain qualifying nondominated faster/larger and smaller/slower points;
remove dominated points from recommendations while preserving their history.
Also report the fixed baseline below. No global optimum is established by
a finite candidate set; call results the best tested choices.
An unchanged input/output format and all correctness gates are mandatory.
Real aggregate CPU improvement does not imply every block improves: report
every slower block/slice and retain a no-slower selection when available.

The user additionally requires all preliminary library initialization time
in the benchmark. Measure from the first required Z80 initialization opcode
through final decode return. Per-block initialization belongs in every call;
any separate one-time preparation must appear once in batch totals and in
cold-start latency, with its cost shown explicitly. Report setup/decode
components as well as their sum; do not assume prebuilt runtime state for
free. Static tables emitted in the library image need no runtime generation.
Keep the existing entry-through-RET CPU reference convention explicit; caller
CALL overhead and actual IRQ work are separate stated components.

| Fixed initial public call | Intrinsic service B | Real CPU T | Frozen proof |
| --- | ---: | ---: | --- |
| `zx0.maximum.build(prefix_cap=228, shared_prefixes=True)` | 7,578 | 139,892,818 | [ZX0 native](evidence/shared_zero_prefix_native.json.gz) |
| `zx0.maximum.build(prefix_cap=127, shared_prefixes=True)` | 5,114 | 139,916,508 | Same proof |
| `lzsa.hybrid.build('fast')` | 9,500 | 14,944,429 | [Hybrid native](evidence/wide_hybrid/wide_hybrid_experiment_short.json.gz) |
| `lzsa.hybrid.build('balanced')` | 6,500 | 14,983,119 | Same proof |
| `lzsa.hybrid.build('compact')` | 4,999 | 15,048,469 | Same proof |

The accepted E01 predecessors for new candidates are
`zx0.maximum_branches.build(prefix_cap=228, policy='fast')` at7,517 service B/
139,552,884 real T and `lzsa.hybrid.build('fast', cold_match_extension=True)`
at9,499 B/14,926,306 T. Keep the initial table above as the fixed cumulative
comparison; use these E01 calls for incremental comparisons.

Use the exact builder calls/source links in [DECODER_VARIANTS.md](DECODER_VARIANTS.md).
ZX0 has 364 real blocks and LZSA2 has 21; their totals are not a cross-codec
comparison. Report incremental gain against the immediately preceding accepted
implementation and cumulative gain against fixed `9c28b01f`. Retain original/
pass Fast and stronger Mega comparisons separately; do not count older gains
as new improvements.

The cap is **10,000 B of total service memory**: all executable/cloned code,
embedded and external state, tables, padding, scratch/internal buffers and
required caller/private stack. Count embedded operands once. Input and
output/history are excluded as authorized, but still report their sizes.
Add actual application IRQ code/state/headroom and, for guarded examples,
the supplier/carry/I/O/workspace inventory. E01 fast LZSA2 leaves501 B;
after worst table padding255 and diagnostic IRQ13+6, only **227 B** remain.
E01 ZX0 shared228-fast leaves **2,464 B** after that IRQ. These budgets determine
which clones/tables fit; nominal code size alone is insufficient.

## Sources reviewed

- [Zilog CPU manual](https://www.zilog.com/docs/z80/um0080.pdf): instruction
  semantics/base CPU timing; cross-check with [our timing table](Z80_TIMINGS.md).
- [WikiTI code flow](https://wikiti.brandonw.net/index.php?title=Z80_Optimization#Code_Flow)
  and [table alignment](https://wikiti.brandonw.net/index.php?title=Z80_Optimization#Table_alignment):
  starting points for examining new continuation and lookup sites.
- [Original LZSA2 Z80 source](https://github.com/emmanuel-marty/lzsa/blob/master/asm/z80/unlzsa2_fast.asm)
  and [format](https://github.com/emmanuel-marty/lzsa/blob/master/BlockFormat_LZSA2.md):
  references for reservoir ownership, field transitions and legal escapes.
- [Original ZX0](https://github.com/einar-saukas/ZX0): reference for bit-coded
  lengths/offsets and compatible decoder families.
- [Grauw's loops](https://map.grauw.nl/articles/fast_loops.php): context for
  bounded unrolling; its MSX timing assumptions are not our base-Z80 costs.

No copied DI/EI, platform-specific IRQ convention or undocumented opcode is
automatically suitable. Ordinary Z80 timing here is LDI 16, repeating LDIR 21,
terminating LDIR 16, CALL 17, RET 10, JP 10 and conditional JR 7/12 T. Keep IRQ,
ULA contention, WAIT and physical disk/ROM time separate.

## Ordered experiments

The sequence below is a queue, not a promise that every technique can meet
the acceptance rule. Limit each experiment to at most three alternatives;
finish its evidence and decision before selecting the next implementation.
Baseline profiling/source review may run in parallel without changing any
decoder. E06 uses only accepted kernels, and E07 applies only to accepted
resident changes; if there are none, explicitly record that dependency.

| Stage | Question to answer | Required completion artifact |
| --- | --- | --- |
| F00 | Do measured E02/E03 speed tradeoffs survive full qualification, separately and together? | Three fixed candidates, all native/package gates, Pareto comparison; no promoted screen-only mode |
| S01 | Can the smallest retained resident decoders use less service RAM? | At most three bounded candidates per codec, full valid-format tests, complete CPU/size and dominance decisions |
| E00 | Do the current bytes, inputs, CPU totals and service inventories match their proofs? Where is the remaining cost? | Authenticated baseline and hotspot report; bounded E01 selections |
| E01 | Can new-layout branches/fallthroughs be both faster and smaller? | Exact per-branch/per-case deltas, final spans and accept/reject decision |
| E02 | Can LL3 call/return work be removed without increasing total service memory? | Complete helper-exit model, selected continuations and decision |
| E03 | Does known nibble-cache state remove more work/state than specialization adds? | Exhaustive state screen, full-path counts and decision |
| E04 | What does shared ZX0 cap255 actually cost and save? | One bounded measured candidate; full promotion gates if nondominated and within the cap |
| E05 | Can a two/four-bit Elias lookup beat parsing after all table/index costs? | Exhaustive lookup/fallback screen and decision |
| E06 | Do accepted kernels allow better fixed compact/balanced/fast selectors? | Self-contained selectors, all alignments and same-profile comparisons |
| E07 | Do the accepted gains survive coroutine/guarded features? | Same-feature CPU/memory and full suspension/producer qualification |

F00 follows the committed E03 screen. Qualify exactly E02 hot literals, E03
hot nibble pair and their combination, starting from E01 cold Hybrid fast.
The initially predicted services9,529/9,515/9,545 B and real CPU14,913,435/
14,918,596/14,905,725 T are now measured and fully qualified. Minimum-safe
overlap, IRQ, relocation, FFFFh output end, byte EOF, dirty offset and
IY/alternate registers pass. The package is self-contained and keeps all
existing defaults exact. [F00](NEXT_F00_HOT_PATHS.md) records the complete gates.
E02's -2B/+2,028T cold-tail point remains for E06 dominance/refit review;
shared-fast SMC is already dominated by compact, despite reducing its size.

S01 audited ZX0 Standard74 service B and LZSA2 Small145 B before final selection.
Inspect actual code/state/stack minima; do not silently replace their valid
format/ABI with a narrower shortcut. For each codec choose at most three
concrete peephole/helper/stack layouts. Count any CPU increase and preserved
register cost, test legal short escaped literals and exact EOF, then apply
all common promotion gates to useful points. A measured/proven rejection
is complete; current minimum choices remain when no candidate improves them.
The completed result is ZX0 Standard74 B unchanged, LZSA2 compact EOF144 B,
plus two fully qualified faster/larger ZX0 intermediates; see the S01 report.

### E00 — Freeze evidence and profile the remaining work

- Authenticate current public regions/labels, input hashes and the exact
  totals above using existing [ZX0](tests/verify_shared_zero_prefix.py)
  and [LZSA2](tests/verify_hybrid_public.py) verifiers. Reuse complete saved
  runs when the relevant source/binary/input is unchanged.
- Add only missing observers: branch outcomes on new layouts, LL3 helper
  paths, nibble refill/cached states, Elias depth/phase and copy lengths.
  Count all entry/exit/synchronization work, not just the kernel.
- Reuse archived token counts: 45,247 real LZSA2 tokens include 4,870 LL3
  calls; real ZX0 has 46 word-prefix entries. These are saved counts, not a
  new benchmark. Confirm them when attaching new observers.
- Rank sites by full-corpus saved-T upper bound per added service byte.
  Select at most three bounded alternatives for one experiment. Record the
  hypothesis and rejection condition before changing its decoder.

Deliverable: immutable baseline manifest, hotspot report and selected E01
sites. Profiling must reproduce the original totals before it judges code.

### E01 — Retune branches and fallthroughs in the new layouts

Target [Maximum/shared continuations](zx0/src/zx0/_shared_prefixes.py) and
[Hybrid/Wide](lzsa/src/lzsa/wide.py), not the already-audited old Fast sites.
Cloning/sharing changed branch distances and path frequencies.

1. For each eligible JP cc, count taken probability p. Only NZ/Z/NC/C have
   corresponding JR forms. JR costs 7+5p T
   versus JP 10; it helps on this input mix only when p<0.6. Unconditional
   JP 10 must not become slower JR 12 as a purported speed win.
2. Try branch inversion plus a hot fallthrough, then conditional JR only
   within the final -128..127 range. Recalculate all spans after layout
   changes and preserve both outcomes' register/flag semantics.
3. Verify each complete-block delta from taken/not-taken counts, including
   every added trampoline/jump. Report all slower outcomes/cases.

Gate: a fitting nondominated size/speed point with valid relocation and all
correctness gates. Count setup costs; save every per-case regression even
when aggregate CPU improves. Historical E01 already passed the stronger rule.

### E02 — Clone selected LZSA2 long-literal continuations

Target `literal_prefix(LL=3)` and `LongLiterals` in
[wide.py](lzsa/src/lzsa/wide.py). Every current LL3 prefix calls the helper
before continuing into its offset/length body.

1. Start with one or two hottest LL3 body contexts from E00. Duplicate only
   the necessary literal helper/continuation, retaining every exit.
2. Test moving CALL/RET overhead to direct entry/continuation flow. Local
   hypotheses: CALL 17+RET 10=27 T versus JP 10+JP 10=20 (-7), or JP 10 plus
   fallthrough=10 (-17). These require a correct complete control-flow graph;
   replacing CALL with JP alone loses the return continuation.
3. Count clone bytes, every branch/return path, cache/refill behavior and
   source stack. At most 82,790 real T (4,870*17) are available from removing
   this overhead alone before other costs. Do not promise a percentage gain.

Test ordinary/extended/word literal forms, especially legal word counts1/2,
all subsequent offset classes, both nibble phases and EOF after literals.
Gate: exact byte/EOF/stack/IRQ behavior and a fitting nondominated point.
Cloning normally grows code; count sharing/removal and stack explicitly.
Growth alone no longer rejects a faster clone. Historical E02 needs F00
qualification for its newly useful speed tradeoff.

### E03 — Specialize LZSA2 nibble-cache states

Target `nibble()` and hot nibble-consuming bodies in
[wide.py](lzsa/src/lzsa/wide.py). The present local cached/refill reader costs
27/66 T, excluding caller parsing; E00 must confirm its actual hit mix.

1. Prototype separate known-empty/known-full entries for one hot family,
   carrying cache state in control flow rather than testing it repeatedly.
   Preserve the nibble value as well as the state.
2. Account for transitions, cache storage, dispatch selection, refill reads,
   register saves and every table/page. Start with compact/balanced if a
   duplicate table cannot fit the fast profile.
3. Expand only if the complete path beats the existing reader. Enumerate
   every byte value, initial cache state and relevant flag input, then run
   the codec matrix. Never prefetch beyond exact EOF/input frontier.

Gate: full-path costs, preserved AF/AF' and IRQ contracts, no hidden state or
input reads, and a fitting nondominated point. Report every table/transition
cost. E03's measured hot pair now proceeds through F00; a smaller but slower
SMC variant must also beat existing compact choices to be useful.

### E04 — Bounded ZX0 prefix-budget extension

Target [maximum.py](zx0/src/zx0/maximum.py) with shared suffixes enabled.
The earlier cap255 size rejection applied to the old layout; sharing changed
that premise. First test only cap255 before another depth policy.

- Extending twelve chains from E01 228-fast to255 predicts648 extra code B:
  27*12*2. Predicted intrinsic service is8,165 B, or8,184 B with diagnostic IRQ.
  Actual assembly must confirm these counts.
- At the existing >=256 entry, 255 LDIs leave BC>=1. Never let BC=0 enter
  LDIR. The saved 46 real word entries predict only 6,210 T saved: 27*46*5,
  with predicted total139,546,674 T. This is an estimate, not a run.
- Test 255/256/257 and long new/reused counts at all phases; reconcile the
  exact extra-LDI cost. Preserve the public cap228 option.

Gate: measure the hypothesis and apply full promotion gates if it supplies
a fitting nondominated speed point. The larger layout is allowed by the
latest user request; growth alone does not reject it. Low expected payoff limits this to
one initial candidate. Deeper >=512 or per-family caps need
a separately justified hotspot/size bound, not an unbounded parameter sweep.

### E05 — Small Elias lookahead table in ZX0

Target depth/phase parsing in [maximum.py](zx0/src/zx0/maximum.py). Begin with
a bounded fragment already present in A, not an unconditional source prefetch.
This is a new structural hypothesis, not the adopted depth unroll.

1. Generate a small transition table for a fixed two/four-bit window and
   enumerate reservoir/phase, partial-count and refill states explicitly.
   Maximum carries reservoir phase in control flow; A=0 can contain valid
   unconsumed zero bits and is not an empty-buffer sentinel.
2. Try only an entry that finishes a short count or returns to the existing
   exact fallback. Include indexing, register pressure, tables, padding and
   entry/exit costs. A faster bit operation is insufficient by itself.
3. Prove no consumed bit/byte or word-count bound changes. Test every table
   key and fallback/refill boundary before all 417+56 complete cases.

Gate: complete CPU/service costs and dominance against all relevant existing
size points, including smaller prefix caps. Pointer preservation/lookup cost
and table bytes must be included. A smaller/slower candidate may still qualify.
A complete static dominance-bound rejection is a useful result;
label it as analysis rather than a native measurement.

### E06 — Refit fixed hybrids after accepted kernel changes

Target [hybrid.py](lzsa/src/lzsa/hybrid.py) and the existing
[offline selector](tests/measure_wide_hybrid.py). Use actual new body sizes
and full path costs; old selector weights may no longer describe them.
Keep every LL/XYZ/MMM form and self-contained installed selector constants.
No input-specific omission or runtime profiling.

Freeze optimization inputs and report existing random/directed cases
separately. Retain at most compact/balanced/fast new frontier points; compare
against every current same-ABI point. Do not mix unverified techniques to
manufacture a combined gain. Check regenerated constants and emitted bytes/
labels at both native placements and all alignment sizes. Promote each
replacement only if it supplies a fitting nondominated point for the same
feature set; preserve useful preceding points rather than forcing one winner.

### E07 — Qualify accepted changes for coroutines and guarded input

Start after the corresponding resident change is accepted and committed.
Compare against each existing same-feature wrapper, not the resident table.
New options keep rejecting hooks until the equivalent profile is fully proved.

Preserve zero/repeated/final demands, exact publication/input cursors, EOF,
saved registers/stack, suspension before unsafe reads and guard restoration.
Replay relevant 63 producer cases at six placements, supplier/carry and
live-code relocation. Count complete producer+consumer service and CPU;
include I/O/workspace assumptions. Qualify fitting compact/balanced options
if the largest raw core leaves insufficient producer memory. Physical disk
and full-movie deadlines remain a later application release gate.

## Common test gates for every implementation

1. **Static/micro:** write inputs, outputs, clobbers, flags and bounds. Count
   old/new absolute T and delta from [Z80_TIMINGS.md](Z80_TIMINGS.md). Enumerate
   finite bit/nibble/flag states; prove BC never underflows a copy. Keep major
   routine/non-obvious-block comments in generators and exported assembly.
2. **Complete native inputs:** ZX0 all 417 main+56 high-word cases; LZSA2 all 95
   main+580 directed cases. Authenticate hashes. Verify every output byte,
   exact input/EOF, changed-code permissions, dirty-offset startup, stack and
   caller/alternate registers. Include output end cursor FFFFh and boundary
   lengths/offsets, single-nibble EOF and short word escapes.
3. **Overlap/placement/IRQ:** distance 1/2 history is necessary but does not
   prove overlapping compressed input/output. Use a dedicated minimum-safe
   in-place runner; `native_block.execute` rejects overlapping allocations.
   Validate that runner against the baseline/host overlap proof before reuse.
   Check measured relocated origins and every low-byte alignment for size.
   Inject register-preserving IRQs, including new cache/EXX/SMC transitions.
   Check live source/code/stack/output allocations remain disjoint except
   explicitly permitted in-place input/output.
4. **Cost reconciliation:** prove each complete-case delta from independent
   counters; include beginning/end/dispatch/sync work. Save every slower case
   with its actual baseline, max difference and real/directed classification.
   IRQ cost remains separately reported.
5. **Integration:** exact 31 legacy layouts/six resources, relevant library
   tests (74 at E01, plus three E02 and six E03 focused checks) and
   recorded 24 selected toolkit integration tests.
   Add meaningful regressions only for changed behavior. Build isolated
   wheels, exercise exposed API/CLI and reconstruct ORG/DB exports. Keep the
   earlier 67-test evidence historical unless that selection is rerun.
6. **Decision:** no correctness failure or unaccounted byte is acceptable.
   Accept a fitting nondominated candidate among same-feature measured choices,
   including faster/larger and smaller/slower tradeoffs. Keep dominated and
   failed candidates in evidence without promoting them. Publish every real-case
   regression; aggregate gain is not a universal per-block gain. Keep defaults
   exact until separately qualified. Otherwise record rejection/reason;
   preserve unsuccessful/partial evidence without promotion.

## Experiment record and completion

Each stage creates an English report, reproducer, compressed complete-case
JSON evidence and authentication manifest. Record baseline commit/builder
arguments, source/region/input SHA256, absolute CPU before/after, delta versus
immediate/fixed baselines, all service components, external buffers, slower
cases, IRQ/relocation/overlap coverage, default/resource/test/wheel/export
results and limitations. The [variant table](DECODER_VARIANTS.md) gets direct
function/file links and exact selection calls for accepted modes.

Finish the report and root CHANGELOG in the same focused commit, then select
the next pending stage. A failed experiment is a completed decision; a screen
or partial replay is not a qualified implementation. The broader 10%-per-feature
goal is separate from completion of any one bounded experiment.

The pass is complete when F00 has resolved the three speed candidates and S01
has audited both minimum-size profiles, E00 has authenticated the baseline, E01..E05 each
have an explicit measured or proven rejection/acceptance decision, E06 has
reconciled the accepted set (or recorded no applicable change), and E07 has
qualified each promoted same-feature wrapper or recorded why it remains
unqualified. The final table must include exact function/file links, builder
arguments, old/new T and percentage, old/new code/state/table/padding/stack
and total service bytes, all regressions and evidence links. Do not mark a
pending native replay or wrapper proof as passed.
