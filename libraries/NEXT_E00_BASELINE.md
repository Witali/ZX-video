# E00: authenticated decoder baseline and remaining hotspots

2026-10-20. Fixed decoder revision `9c28b01f`, worktree
`.worktree/codec-speed-pass3`, branch `codex/codec-speed-pass3`.
This stage changes no decoder bytes, formats, defaults or input data (0 T).
New branch-selection numbers below are predictions, not accepted candidates.
The [execution plan](NEXT_TRICKS_PLAN.md) requires both lower complete real
CPU and lower total service memory before promoting any subsequent change.

## Fixed baseline authentication

[Verifier](tests/verify_next_baseline.py) and
[immutable manifest](evidence/next_e00_baseline.json.gz) authenticate 49 saved
source hashes, all 31 legacy layouts and 11 public shared-ZX0/hybrid-LZSA2
calls. Current public regions match the archived proofs, including the
measured normal, relocated and ZX0 high-word placements. Public source files
also match the fixed decoder revision. The old native IRQ/relocation and
wheel/integration runs are reused with their original hashes and scope;
this verifier does not claim to rerun them.

The verifier builds five current target profiles at all 256 low-byte origins
(1,280 builds). All service allocations count emitted code and embedded state,
external state, tables, padding, scratch/internal buffers and required stack;
compressed input and output/history remain separate.

| Profile | Aligned intrinsic service B | Worst alignment B | With worst alignment and diagnostic IRQ B |
| --- | ---: | ---: | ---: |
| ZX0 shared127 | 5,114 | 5,114 | 5,133 |
| ZX0 shared228 | 7,578 | 7,578 | 7,597 |
| LZSA2 hybrid compact | 4,999 | 5,254 | 5,273 |
| LZSA2 hybrid balanced | 6,500 | 6,755 | 6,774 |
| LZSA2 hybrid fast | 9,500 | 9,755 | 9,774 |

The test IRQ adds 13 code and six additional stack bytes. Actual application
IRQ/supplier requirements must still be counted separately. No physical
disk, ULA/WAIT or movie-publication timing is asserted here.

## ZX0 observers

[Profiler](tests/profile_next_zx0.py),
[full evidence](evidence/next_e00_zx0_profile.json.gz) and
[authentication summary](evidence/next_e00_zx0_verification.json).

Two caps each replay all 417 main and 56 high-word cases, for 946 fresh
protected native runs. Per-case CPU and exact source/output/register/stack
checks match the frozen proof. Real totals remain 139,892,818 T (228) and
139,916,508 T (127). Source/region/input hashes and independent label maps
bind the old IRQ/relocation evidence; those older runs are not relabeled as
fresh observer runs. Direct literal4 entries are independently confirmed at
27,669 real hits for each cap; shared228 has 46 real word-prefix entries.

Conditional JP costs 10 T for either outcome; JR costs 7 not taken and
12 taken. Each eligible conversion removes one byte with exact CPU delta
`2*taken - 3*not_taken`. The observer computes final spans after every
selected contraction. It proposes these three bounded E01 alternatives for
each cap:

| Predicted selection | Sites / service delta B | Real CPU delta T | Slower real cases | Slower complete cases / maximum |
| --- | ---: | ---: | ---: | ---: |
| All profitable reachable sites | 61 / -61 | -339,934 | 0 | 103 / +38 T |
| Each site individually safe on every real block | 13 / -13 | -214,864 | 0 | 38 / +11 T |
| Each site individually safe on every corpus case | 3 / -3 | -970 | 0 | 0 / 0 T |

These are measured baseline outcomes plus a cost model. E01 must emit the
candidate, prove final instruction/label relocation and reconcile every
complete-case delta, then pass IRQ and minimum-safe compressed overlap.
The profiler saves full slower-case lists, gamma depth/phase, prefix lengths
and bit-reservoir refills for later bounded experiments.

## LZSA2 observers

[Profiler](tests/profile_next_lzsa.py),
[summary](evidence/next_e00_lzsa.json) and
[full evidence](evidence/next_e00_lzsa_full.json.gz).

All 675 cases are freshly replayed for fast/balanced/compact, for 2,025
protected native runs. All per-case CPU counts match their original frozen
proofs. Real totals remain 14,944,429 /14,983,119 /15,048,469 T. Each real
profile executes 45,247 tokens and 4,870 LL3 helper calls. Nibble reads split
into 19,752 cached (27 T each) and 19,760 refill (66 T each), totaling
1,837,464 T before caller parsing. The observers check reader values/state,
input advancement and full helper CALL/body/RET paths, including all three
literal exits. Startup is 44 T and final exit 28 T per block.

No currently laid-out conditional JP-to-JR singleton is both smaller and
faster on the real corpus. E01 will also screen a bounded structural lead:
move the existing extended match-length parser after an unconditional exit,
invert its preceding conditional, and let the common short-length path fall
through. All existing cold exits must remain intact. Its current predicted
delta is -18,123 real T and -1 code byte; no candidate has been assembled.
Per-context LL3/nibble histograms in the full report bound E02/E03 work.

## Actual compressed input/output overlap

[Dedicated runner](tests/native_inplace_block.py) and
[boundary tests](tests/test_native_inplace_block.py) distinguish consumed
input and produced history from the live unread input frontier. Input/output
are the only allocations allowed to overlap. The runner checks exact byte
EOF, return cursors/registers/stack, dirty-offset startup, permitted code
patches and a digest of the input cursor at every output write against the
independent host trace. Current history classification is explicitly limited
to LDI/LDIR; new history-load forms require a reviewed extension.

Five directed tests cover both codecs at the host minimum, minimum-minus-one
unread-input rejection, literal same-arena decoding, single-nibble EOF,
allocation collisions, live EOF/code-write negatives and plain/IRQ timing
equality with the disjoint runner. The standalone command initially needed
package import paths; the test now sets them explicitly and all five pass.
This import-path fix changes no native replay logic.

The [complete in-place proof](evidence/next_e00_inplace_baseline.json.gz)
passes 473 ZX0 +675 LZSA2 cases, each plain/IRQ/relocated: **3,444 new native
replays**. Actual compressed-input overlap occurs in all 473 ZX0 and674
LZSA2 cases; empty EOF has no output. Every minimum and per-write cursor
digest equals the independent host trace in all three modes. Plain CPU,
input/output hashes and both emitted placements match the original disjoint
archives. Real CPU remains 139,892,818 /14,944,429 T. Injected IRQ counts are
1,407 /760; peak stack plain/IRQ is4/10 B ZX0 and6/12 B LZSA2. The report
keeps executed and final reporting source hashes separately because metadata
and the standalone test import path were finalized after replay.

## Decision and next action

E00 is complete: the immutable baseline, missing hotspot observers and the
actual compressed-overlap gate are authenticated. No new decoder is promoted.
E01 will test the three predicted ZX0 selection strategies and one LZSA2
cold-extension layout, with every slower case retained. The user additionally
requests a locally developed Spectrum adaptation of the Z80 Tester C core;
that host test-infrastructure change is separately qualified before it is
used for candidate evidence. Keep the existing native backend as an independent
reference and compare identical bytes/inputs/T/ABI before claiming acceleration.

## Reproduction

Use the project native dependency environment and run from the worktree:

```powershell
python libraries/tests/verify_next_baseline.py --output libraries/evidence/next_e00_baseline.json.gz
python libraries/tests/profile_next_zx0.py --output libraries/evidence/next_e00_zx0_profile.json.gz --summary-output libraries/evidence/next_e00_zx0_verification.json
python libraries/tests/profile_next_lzsa.py --output libraries/evidence/next_e00_lzsa.json
python -m unittest discover -s libraries/tests -p test_native_inplace_block.py -v
python libraries/tests/native_inplace_block.py --output libraries/evidence/next_e00_inplace_baseline.json.gz
```

The profiler scripts authenticate their pinned baseline; after a subsequent
accepted default/source change use its committed E00 snapshot rather than
silently overwriting this evidence. The historical test logs retain their
actual 58/61 library and 24 selected toolkit counts. This stage does not
relabel the older 67-test selection or qualify new wrapper implementations.
