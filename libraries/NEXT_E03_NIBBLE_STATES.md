# E03: LZSA2 nibble-state specialization

Completed bounded screen, 2026-10-20. Baseline: accepted E01
`lzsa.hybrid.build('fast', cold_match_extension=True)`, 9,499 aligned service
bytes and 14,926,306 T on the unchanged 21 real blocks. E02 rejected its
three constructions and did not alter this baseline. Only the three bounded
designs below belong to E03; none is an installed library option.

## State and complete-path accounting

The current inline reader occupies 15 bytes. AF' holds the pending byte:
carry1 means empty and carry0 means a cached low nibble is available.
`SCF; EX AF,AF'` marks the next state empty while retrieving the old state.
On refill, `LD A,(HL); OR A; EX AF,AF'` stores the byte with carry clear;
the reader rereads that same byte, advances HL once and rotates its high
nibble down. It returns `F0|n`, carry0, to the existing offset/length code.
AF' must survive EXX and IRQ handlers throughout these transitions.

E00 independently measured 19,752 cached and 19,760 refill reads on real
inputs, at 27/66 T: 1,837,464 T in total. Eight refills remain unpaired at
EOF; unconditional prefetch or assumed pairing would change the contract.
The caller validates complete resident input/output/history; input and
output/history are excluded from service memory. All code, tables, state,
padding, scratch and required stacks are included, with embedded operands
counted once. Diagnostic IRQ execution and ULA/disk latency are separate.

## Three bounded designs

1. **Two full phase-specific dispatch tables.** With state in control flow,
   the ideal cached/empty reader fragments need 3+10 bytes instead of the
   current 15. There are 123/75/48 reader sites in fast/balanced/compact.
   Even granting free consumer clones, free additional dispatch code and
   removal of the original two-byte startup, a full second 512-byte table
   grows service by at least `512 - 2*sites - 2`: **264/360/414 B**.
   A separately duplicated 11-byte lookup makes these **275/371/425 B**.
   This bound applies to the specified full-table architecture, not every
   possible compressed dispatch. Ideal reader times11/47 T become21/57 T
   with explicit JP continuations; further state routing still costs work.
2. **One hot two-reader family.** In `body_167_0`, a cached offset nibble
   guarantees an empty cache for the following extended match length.
   Entering the existing refill after SCF/EX/JR costs51 T instead of66.
   Duplicate the14-byte intervening offset setup plus its2-byte OR tail:
   **+16 service B**. The complete pair changes155 ->140 T on514 real hits,
   predicting **-7,710 real T**. The refill-first path retains its original
   flow; existing AF' carry ownership and source reads remain intact.
3. **One shared SMC phase reader.** Replace inline readers by CALLs and use
   a writable JP operand to choose cached/refill code. CALL17 +JP10 +phase
   update20 +core11/47 +RET10 gives **68/104 T**, versus27/66. Reset its
   phase at every block:20 T instead of8, including blocks ending with a
   pending cached nibble. This predicts **+1,560,964 real T**, including21
   reset differences. Stack rises6 ->8 B because LL3 already has a live
   helper return. The phase operand is inside emitted code and counts once.
   Actual emission confirms **-1,443 B**, including the two added stack bytes;
   both phase entries fit one page without extra padding at all256 origins.

## Native measurements

The two emitted prototypes give these complete real-input results:

| Test-only design | Service B | Real CPU T | Delta service B | Delta real T |
| --- | ---: | ---: | ---: | ---: |
| Accepted E01 fast | 9,499 | 14,926,306 | 0 | 0 |
| Hot known-empty pair | 9,515 | 14,918,596 | +16 | -7,710 |
| Shared SMC reader | 8,056 | 16,487,270 | -1,443 | +1,560,964 |

The hot pair improves22 complete cases and leaves653 equal, with no slower
case. The shared reader slows all675 cases, maximum80,908 T. Stack peaks are6/8 B. The
qualified local C guarded core reproduces all675 accepted E01 baseline CPU
counts, independently matching frozen E00 nibble/phase/hot-family counts.
Every candidate complete-case delta matches `-15*hot_cached_hits` or
`41*cached_reads + 38*refill_reads + 12` respectively.

Component enumeration covers all256 byte values, both cache states, all64
documented main-flag combinations and both relevant alternate carries:
114,688 guarded micro-executions. Returned values, output flags, significant
cached byte, semantic phase, input advance and absence of prefetch pass.
AF' carry is the state only in the original/protocol-preserving design; the
SMC design's phase is its declared code operand. Other alternate input flags
do not reach control flow and are overwritten before output.

Same-resident-CPU tests retain the phase operand between odd/even blocks and
execute the actual20-T reset, rather than repairing it from the host. Full
decoder calls also reuse their resident code without restoring mutable
operands. All256 emitted origins preserve the measured service differences.

There are56 additional A7 hot-family inputs, each executed by the baseline
and both candidates: all15 nibble lengths, byte escapes0/1/230/231, word
counts2/3/8/9/23/24/255/256 and exact EOF, in both initial phases. Match
counts start at2 as specified by the pinned
[LZSA2 format](https://raw.githubusercontent.com/emmanuel-marty/lzsa/15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5/BlockFormat_LZSA2.md).
Word-literal1/2 remain covered by the frozen675 suite; the host trace's
permissive acceptance of match1 does not make it a format-valid match.

Each candidate also passes36 mixed repeated full-block calls on one resident
CPU. Eight microblocks alternate odd/even nibble counts using the real20-T
reset, without host repair of the phase/cache. All256 origins have services
9,499..9,754 B baseline, 9,515..9,770 B hot and8,056..8,311 B shared.
Launch/final source hashes agree; the exact qualified DLL/build are recorded.

## Decision and reproduction

Under the then-active strict faster-and-smaller rule, all three designs
were rejected: full tables grow memory, the hot prototype grows memory,
and the shared prototype grows CPU. The archived verdicts retain that rule.
The user's later request for minimum size, maximum speed and intermediate
Pareto choices supersedes it. The hot prototype now merits full qualification
alongside E02's hot literal clone; neither is an installed mode yet. The
shared fast prototype is dominated by the already qualified compact profile
(4,998 B/15,030,346 T), which is both smaller and faster. The full-table
architecture has not been emitted/timed and has only a memory bound.

Retain E01 as the current public implementation. IRQ, actual compressed
overlap and relocated runtime promotion matrices are explicitly unperformed
for these failed candidates. Static all-origin builds are not relabeled as
relocated runtime proof; no coroutine/guarded/ULA/disk/movie claim is made.

Initial inventory/label/evidence-root harness mistakes were corrected before
the final proof. A prior successful675-case/state screen is retained as a
summary/source-hash record; the final rerun additionally covers the explicit
hot-family edges and reset sequence. No target instruction change was needed
for those harness/coverage corrections.

[Summary](evidence/next_e03.json),
[complete proof](evidence/next_e03_full.json.gz),
[reproducer](tests/next_e03_measure.py),
[private emitters](tests/next_e03_profiles.py),
[six focused tests](tests/test_next_e03.py) and
[test log](evidence/next_e03_tests.log.gz).

```powershell
$env:CODEC_EMULATOR_DLL=(Resolve-Path .tmp/codec-cpu-qualified/codec_cpu.dll).Path
python -m unittest discover -s libraries/tests -p test_next_e03.py -v
python libraries/tests/next_e03_measure.py
```

The full reproducer authenticates the recorded qualified DLL. A different
build needs its own platform qualification and a new evidence pin.
