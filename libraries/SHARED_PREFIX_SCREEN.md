# ZX0 selective LDI suffix-sharing screen

Completed 2026-10-20 from `b99dd123`. This first bounded attempt reduces
duplicate prefix code in the resident Maximum decoder. It is a test-only
tradeoff, not a replacement for the fastest public implementation.

Each selected shorter prefix jumps into the existing 127-LDI suffix. Its
original final 10-T JP is still executed, so the new entry adds exactly
10 T. The literal >=4 entry already reached by a conditional JP can target
the suffix directly at zero additional cost. Original small LDIR paths and
the existing large word prefix remain unchanged. State, tables, scratch,
internal buffers and extra stack are zero; totals include the four-byte
caller/source stack. Compressed input and output/history stay separate.

## Complete main-corpus screen

All eight profiles decode the same 417 blocks, including 364 real blocks.
Every block satisfies `candidate - same-cap Maximum = 10 * shared-entry hits`.
The real same-cap baselines are 140,193,198 T (127) and 140,169,968 T (228).

| Cap | Minimum shared prefix | Service B | Real CPU T | Added T vs same cap |
| --- | ---: | ---: | ---: | ---: |
| 127 | 3 | 4,658 | 141,163,088 | 969,890 |
| 127 | 15 | 4,910 | 140,421,498 | 228,300 |
| 127 | 31 | 5,270 | 140,303,478 | 110,280 |
| 127 | 63 | 6,014 | 140,236,608 | 43,410 |
| 228 | 3 | 7,122 | 141,139,858 | 969,890 |
| 228 | 15 | 7,374 | 140,398,268 | 228,300 |
| 228 | 31 | 7,734 | 140,280,248 | 110,280 |
| 228 | 63 | 8,478 | 140,213,378 | 43,410 |

The cap127/min15 point saves 2,616 service bytes versus cap127 but adds
228,300 real T (about 0.163%). Compared with fastest cap228 it saves 5,080 B
and adds 251,530 T (about 0.179%). It improves intermediate size/speed choices,
but does not meet the proposed same-speed shrink. All 364 real blocks slow
versus their same-cap baseline; retain the complete slower-case lists.

## Verification and decision

The cap127/min15 finalist additionally passes all 417 main cases with IRQ
and 9103h relocation, and all 56 high-word cases with IRQ and 0703h relocation
in the existing disjoint layout. High-word cases include 32,767/32,768/49,151
counts, new/reused offsets and overlapping distance-1/2 history. Plain stack
is at most 4 B; the diagnostic IRQ adds 13 code/6 stack bytes separately.
Every changed execution satisfies the independent 10-T jump count.

Retain this measured test-only tradeoff and its reproducer. Keep public
generators/defaults unchanged (0 T). A separately scoped layout can clone
short continuations to move, rather than add, the entry jump. This report
does not claim its outcome. No coroutine, guarded input, physical disk or
movie publication timing is qualified here.

- [Eight-profile screen](evidence/shared_prefix_screen.json.gz).
- [Main IRQ/relocation proof](evidence/shared_prefix_native.json.gz).
- [High-word IRQ/relocation proof](evidence/shared_prefix_high_word.json.gz).
- [Prototype](tests/mega_prefix_profile.py), [reproducer](tests/measure_shared_prefix.py).

```powershell
python libraries/tests/measure_shared_prefix.py --output libraries/evidence/shared_prefix_screen.json
python libraries/tests/measure_shared_prefix.py --caps 127 --thresholds 15 --verify --output libraries/evidence/shared_prefix_native.json
python libraries/tests/measure_shared_prefix.py --caps 127 --thresholds 15 --verify --high-word --output libraries/evidence/shared_prefix_high_word.json
```

Use the existing native `z80==1.2.0` dependency and worktree-local TMP/TEMP.
All timing is deterministic instruction CPU, excluding IRQ execution,
contention, WAIT, physical disk and ROM latency. Compressed bytes/sectors
are unchanged; no application decoder promotion is implied.
