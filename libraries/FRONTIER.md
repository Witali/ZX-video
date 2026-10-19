# Codec speed and total service-memory frontier

Updated 2026-10-19. The user's current goal has three directions:

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
