# Private Wide LZSA2 sharing frontier

Measured 2026-10-20 on the existing frozen 21 real blocks. These are private
test emitters. Public Wide/Shared code, old defaults, compressed bytes and
caller contracts remain unchanged; this is not player or movie qualification.

`tests/wide_hybrid_profile.py` partitions each offset/length body’s four LL
forms into groups. Each member keeps its original literal parser. One member
falls through into the unchanged body; every other member pays exactly one
10-T JP. Singleton groups are complete specialization. All 256 token forms,
both nibble phases, legal short word escapes and exact EOF remain present.

The private fully shared arrangement reproduces the public Shared bytes.
Its fully specialized arrangement matches Expanded's 7,004-byte service
size; public Expanded is the directly measured 15,623,953-T baseline.
Public Shared uses 3,452 bytes and
15,869,483 T. Token-entry callbacks count unchanged native execution; every
shared hit costs exactly 10 T, including directed cases.

The best fallthrough can differ for each body. The offline selector ranks LL
forms by the frozen real token counts. For a body of B bytes, another copy
costs B-3 bytes because it replaces one three-byte shared JP. A three-byte
body consisting only of JP can therefore split at zero size cost. A bounded
multiple-choice knapsack chooses one through four bodies per token base;
it retains all cold token forms and does not add a runtime table or profiler.
The selected parameters and input hashes are saved in the reports. These
frequency-specific layouts do not promise the same gain on a different corpus.

| Layout | Service bytes | Real CPU T | Compared with public Shared |
| --- | ---: | ---: | ---: |
| Public Shared | 3,452 | 15,869,483 | baseline |
| Hot fallthrough and free splits | 3,452 | 15,822,353 | -47,130 T |
| Budget 4,500 | 4,499 | 15,683,583 | -185,900 T |
| Budget 5,500 | 5,500 | 15,643,493 | -225,990 T |
| Public Expanded | 7,004 | 15,623,953 | -245,530 T |

All three private points above pass the complete 95-case corpus plus 580
directed cases, plain/IRQ execution and relocation to 9103h. The directed
set covers every token byte in both reservoir phases, all 64 offset-nibble
forms, literal word lengths one/two and single-nibble EOF. Actual caller
stack peaks are six bytes plain and twelve with the benchmark IRQ.
All real blocks improve against Shared. Some directed blocks are 10 T slower
when an old zero-literal fallthrough changes: 18/14/7 cases respectively.
The complete model and slower-case names are retained, not hidden by totals.

Expanding just LL1/LL2 is less efficient: both use 5,820 bytes and 15,672,653 T,
dominated by the tailored 5,500-byte point. The saved screen also includes
LL1-only, LL2-only, paired groups and 4,000/5,000/6,000-byte budgets.

The second experiment combines these groups with the separate
`wide_short_profile.py` helpers: new-offset lengths 2..8 and positive-gain
repeat lengths 4..8. Every existing offset store is retained. Relative to
Expanded, new-offset short kernels save `5*n-4` T and repeat kernels save
`5*n-16` T. A shared hit still adds exactly 10 T; these independent terms
match every complete corpus/directed block. Long forms and escaped short
word lengths keep their old paths.

| Hybrid plus short kernels | Service bytes | Real CPU T |
| --- | ---: | ---: |
| Fully shared kernels | 4,228 | 15,188,829 |
| Budget 5,000 | 4,999 | 15,048,469 |
| Budget 6,500 | 6,500 | 14,983,119 |
| Budget 9,500 | 9,500 | 14,944,429 |

The 4,999/6,500/9,500 points each have the same full 675-case IRQ/relocation
proof. The completely unshared short-kernel CPU floor is 14,943,299 T on
these inputs, so the 9,500-byte point pays 1,130 T for the retained sharing.
The fully unshared kernels exceed the 10,000-byte service cap; this measured
point keeps all token forms while sharing less-used bodies. Per-case
regressions against both public bookends are retained in the short report.
At 9,500 bytes, four directed cases are 4 T slower than Expanded:
token-e0-empty, token-e1-empty, token-e0-full and token-e1-full. No case is
slower than Shared, and no real block is slower than either bookend. The
4,999/6,500 points have 208/83 slower cases versus Expanded (maximum 196/14 T)
and four/two versus Shared (maximum 4 T).

All service sizes include code, the existing 512-byte dispatch table, encoded
alignment padding, the two embedded offset bytes and the required six-byte
caller stack. There is no external state, extra table, scratch buffer or
internal input buffer. Input, output and match history are separate. The
benchmark IRQ adds six stack bytes plus thirteen code bytes. Relocation to
9103h adds 253 alignment bytes, so the largest proved point uses 9,772 bytes
including that IRQ: below the 10,000-byte all-service cap. Actual application
IRQ and producer allocations still require their own accounting.

- [Basic report and all 675-case hit audit](evidence/wide_hybrid/wide_hybrid_experiment.json.gz).
- [Short-kernel combinations and all 675-case hit audit](evidence/wide_hybrid/wide_hybrid_experiment_short.json.gz).
- [Frozen selector vectors and exact byte reconstruction](evidence/wide_hybrid_experiment_selectors.json).
- Earlier screen files preserve every bounded real-corpus trial.

The selector file is ready for a fixed public profile module: `body_bases`
orders XYZ=0..7, then MMM=0..7; each profile supplies a 64-element
`group_counts` vector and corresponding four-element LL rankings. For body
base `b`, ranking `r`, and group count `g`, construct singleton groups for
`r[:g-1]`, followed by one group `r[g-1:]`. Pass those groups and rankings
to the private builder. Within a group, emit sorted members except its
highest-ranked member first, then that member immediately before the body.
This reconstructs the exact measured bytes at both checked addresses.

```python
vectors = json.loads(Path("libraries/evidence/wide_hybrid_experiment_selectors.json").read_text())
policy = vectors["profiles"]["short-budget-9500"]
groups, ranks = {}, {}
for base, rank, count in zip(vectors["body_bases"], policy["ll_rank_by_body"], policy["group_counts"]):
    groups[base] = tuple((v,) for v in rank[:count-1]) + (tuple(rank[count-1:]),)
    ranks[base] = rank
profile = wide_hybrid_profile.build(groups_by_body=groups, fallthrough_order=ranks,
    short_lengths=policy["short_lengths"], repeat_lengths=policy["repeat_lengths"])
```

Reproduce with the existing native dependencies and package/test/toolkit
paths, using TMP/TEMP under the worktree:

```powershell
python libraries/tests/measure_wide_hybrid.py --output libraries/evidence/wide_hybrid_experiment.json
python libraries/tests/measure_wide_hybrid.py --audit-hits --output libraries/evidence/wide_hybrid_experiment.json
python libraries/tests/measure_wide_hybrid.py --verify-only --output libraries/evidence/wide_hybrid_experiment.json
python libraries/tests/measure_wide_hybrid.py --short-kernels --output libraries/evidence/wide_hybrid_experiment_short.json
python libraries/tests/measure_wide_hybrid.py --audit-hits --output libraries/evidence/wide_hybrid_experiment_short.json
python libraries/tests/measure_wide_hybrid.py --verify-only --output libraries/evidence/wide_hybrid_experiment_short.json
```

The byte verifier preserves the original run hashes and separately records
current source hashes after reconstructing every saved profile and relocated
finalist. No commit or public API adoption belongs to this private experiment.
