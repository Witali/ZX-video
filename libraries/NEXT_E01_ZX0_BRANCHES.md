# E01 ZX0 branch contractions: native experiment complete

2026-10-20. Fixed baseline `9c28b01f`; unchanged resident Maximum with shared
prefixes. This is a test-only experiment. Its accepted candidates still need
public package/export integration; existing ZX0 generator/default bytes have
not changed. [E00](NEXT_E00_BASELINE.md) supplied the frozen input/outcome
observations, without which no new speed claim was made.

## Complete measured results

All figures exclude compressed input and output/history from service memory.
The same input data is used for old/new complete native runs. Real totals are
for the same 364 blocks, not a comparison with the LZSA2 corpus.

| Shared cap / selection | Service B before -> after | Real CPU T before -> after | Faster | Slower cases / max T |
| --- | ---: | ---: | ---: | ---: |
| 228 / all profitable reachable | 7,578 -> 7,517 | 139,892,818 -> 139,552,884 | 0.242996% | 103 / +38 |
| 228 / each site safe on real corpus | 7,578 -> 7,565 | 139,892,818 -> 139,677,954 | 0.153592% | 38 / +11 |
| 228 / each site safe on full corpus | 7,578 -> 7,575 | 139,892,818 -> 139,891,848 | 0.000693% | 0 / 0 |
| 127 / all profitable reachable | 5,114 -> 5,053 | 139,916,508 -> 139,576,574 | 0.242955% | 103 / +38 |
| 127 / each site safe on real corpus | 5,114 -> 5,101 | 139,916,508 -> 139,701,644 | 0.153566% | 38 / +11 |
| 127 / each site safe on full corpus | 5,114 -> 5,111 | 139,916,508 -> 139,915,538 | 0.000693% | 0 / 0 |

Selections remove 61/13/3 service bytes and save 339,934/214,864/970 real T
for either cap. No real block slows. The 103 slower complete cases split into
47 main non-real cases and 56 high-word cases; the38 split 19/19. They are not
all directed cases. The full report preserves every name/delta. Selection
criteria refer to the frozen corpus; no universal no-slower claim is made.

Service is code plus the embedded two-byte offset operand, counted once,
and four caller-stack bytes including return/live source. No extra state,
tables, alignment, scratch or internal buffer is introduced. For example,
fast228 is 7,513 code/state+4 stack=7,517 B; diagnostic IRQ 13+6 raises it to
7,536 B, versus 7,597 B before. All256 low-byte origins have identical service
sizes. Actual caller IRQ requirements remain separately accounted.

## Independent checks and exact cost model

[Private emitter](tests/next_zx0_branches_profile.py) compiles the public
source in a per-call private namespace. It replaces only selected conditional
JP encodings with JR of the same condition. No package/global assembler is
patched; no input, copy, gamma, register or flag semantics is changed.

JP costs 10 T for either outcome; JR costs 7/12 T. Every complete-case delta
is independently checked as `2*taken - 3*not_taken` against frozen E00
outcomes. One byte is removed per site. All branches fit after the complete
layout contraction. An independent binary oracle rewrites old instructions,
internal absolute operands and every label and must exactly equal the new
emitter at each tested origin; it does not reuse its fixup algorithm.

Each of six candidates passes all 417 main+56 high-word cases in six modes:
protected disjoint plain/IRQ/relocated, and actual host-minimum compressed
input/output overlap plain/IRQ/relocated. That is 17,028 new native replays,
plus six explicit FFFFh output-end probes. Normal code origins8000h/9103h
and high-word0800h/0703h have independently checked allocation maps. All1,536
low-byte alignment builds also match the binary/label oracle.

Exact output, byte EOF, input cursors, code-patch permissions, dirty offset,
caller/alternate registers and stack pass. Every overlap minimum/per-write
input-cursor digest equals the independent host trace. Plain stack<=4 B,
IRQ<=10 B; disjoint/in-place IRQ CPU totals agree. The original protected
`z80==1.2.0` backend is used throughout; the separately developed C/Spectrum
platform is not used to qualify these candidates.

## Decision, reproduction and remaining integration

Accept the six candidates for optional public integration because each
strictly lowers real decode CPU and complete service memory against its
same-cap predecessor, with all regressions retained. The middle policy has
less speed/size gain but fewer non-real regressions; the third retains no
slower tested case. Do not replace old defaults or infer wrapper qualification.
The [execution plan](NEXT_TRICKS_PLAN.md) still has the LZSA2 part of E01 and
E02..E07 pending.

```powershell
python libraries/tests/measure_next_zx0_branches.py --output libraries/evidence/next_e01_zx0_branches.json.gz
```

[Reproducer](tests/measure_next_zx0_branches.py) and
[complete evidence/source hashes](evidence/next_e01_zx0_branches.json.gz).
Public integration must bind installed current bytes/labels to this proof,
test old defaults/resources and isolated API/CLI/ORG-DB exports, then add exact
public function/file links to the variant table. A test-only builder is not
an installed library feature.
