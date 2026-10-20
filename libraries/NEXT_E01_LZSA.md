# E01: LZSA2 cold match-length escape

Completed native experiment, 2026-10-20. The opt-in
`cold_match_extension=True` is available in [wide.build](lzsa/src/lzsa/wide.py)
and [hybrid.build](lzsa/src/lzsa/hybrid.py). Defaults remain byte/label/metadata
exact. The raw LZSA2 format and caller buffers do not change.

## Complete-path results

These are complete deterministic instruction counts on the same 21 real
blocks, excluding IRQ/ULA/WAIT/physical disk/ROM. Every profile saves exactly
18,123 real T and one service byte against its immediately preceding accepted
implementation. Code, the 512-byte table, embedded offset, alignment and six
caller-stack bytes are included; input/output/history are separate.

| Public selection | Before service B | Opt-in service B | Before real T | Opt-in real T |
| --- | ---: | ---: | ---: | ---: |
| `hybrid.build('compact')` | 4,999 | 4,998 | 15,048,469 | 15,030,346 |
| `hybrid.build('balanced')` | 6,500 | 6,499 | 14,983,119 | 14,964,996 |
| `hybrid.build('fast')` | 9,500 | 9,499 | 14,944,429 | 14,926,306 |
| `hybrid.build('compact-base')` | 3,452 | 3,451 | 15,822,353 | 15,804,230 |
| `hybrid.build('balanced-base')` | 4,499 | 4,498 | 15,683,583 | 15,665,460 |
| `hybrid.build('fast-base')` | 5,500 | 5,499 | 15,643,493 | 15,625,370 |
| `wide.build()` | 7,004 | 7,003 | 15,623,953 | 15,605,830 |
| `wide.build(shared_literals=True)` | 3,452 | 3,451 | 15,869,483 | 15,851,360 |
| Shared, `short_lengths=range(2,9)` | 4,138 | 4,137 | 15,221,490 | 15,203,367 |
| Shared, new2..8 + `repeat_lengths=range(4,9)` | 4,228 | 4,227 | 15,188,829 | 15,170,706 |
| Expanded, `short_lengths=range(3,9)` | 9,524 | 9,523 | 14,999,606 | 14,981,483 |
| Expanded, `short_lengths=range(2,9)` | 9,748 | 9,747 | 14,975,960 | 14,957,837 |

Append `cold_match_extension=True` to every call above. The exact calls and
function/file links also appear in [DECODER_VARIANTS.md](DECODER_VARIANTS.md).
For example:

```python
from lzsa.hybrid import build
from lzsa.export import export
export("build/lzsa", *build("fast", cold_match_extension=True))
```

All 21 real blocks improve, individually by 298..1,090 T. Across the complete
675 cases, 89 improve and 586 slow, with maximum regression 37 T at
`random-19`; the full per-case lists are retained. This is a measured corpus
choice, not a universal speed improvement. Relative to Hybrid fast, the new
real CPU saving is 0.121269%; previous Hybrid/short-kernel gains are separate.

## Layout and independent timing model

Previously the nibble-length parser used `JP C CopyMatchA`: 10 T on either
outcome, followed by the 15-byte extended-length parser. The opt-in moves
that parser after the terminal raw `RET`, inverts the condition to
`JR NC ColdExtendedMatch` and lets the common nibble case fall through.
Its final displacement is +26 at every accepted alignment. The original
`CP 24` flags choose the same paths, with no intervening flag-changing command.

The nibble path costs 7 T (-3); byte/word/EOF escape costs 12 T (+2).
Every complete case must satisfy `delta = -3*short + 2*extended`, using
independently observed baseline outcomes. All remaining relative branch
displacements are unchanged. The moved parser retains exact EOF before dummy
word reads and legal short escaped word lengths. AF/AF' cache ownership,
forward overlapping copies, caller registers and six-byte stack maximum are
unchanged. No extra table, state, scratch, internal buffer or stack is added.

All 256 low-byte origins are inventoried per profile. Fast needs at most
9,754 intrinsic B, or 9,773 B with the diagnostic 13-code/6-extra-stack IRQ.
Expanded new2..8 now fits exactly 10,000 intrinsic B at low-byte origin03h
(253 padding bytes); it leaves no room for that IRQ. Origins01h/02h still
reject. Counts include the offset operand once, inside emitted code.

## Verification and decision

The [full native report](evidence/next_e01_lzsa_full.json.gz) contains all
12 profiles x675 cases, with independent baseline observation and six
candidate modes: protected disjoint plain/IRQ/relocated and actual host-
minimum compressed-input/output overlap plain/IRQ/relocated. This is 8,100
classic observations plus 48,600 candidate native runs, with exact output,
byte EOF, cursors, code-patch permissions, dirty offset, preserved registers
and stack. Every overlap read-order digest equals the independent host trace.
Plain stack <=6 B; diagnostic IRQ stack <=12 B. The qualified original
`z80==1.2.0` backend supplies all these runs.

The [default snapshot](evidence/next_e01_lzsa_defaults.json.gz) preserves all
3,069 accepted classic layouts across the 12x256 alignment inventory; other
origins correctly reject. Full native source hashes are frozen and checked
at completion. The [summary](evidence/next_e01_lzsa.json) retains regression
counts and alignment results; full named lists are in the native archive.
Shared's 580 directed baseline counts were
initially reconstructed from saved Expanded/token equations, then independently
executed and checked here; its other 95 counts bind the saved Shared proof.

Accept this optional raw change under the current faster-and-smaller rule.
Other short/repeat combinations and coroutine/guard hooks reject until
separately qualified in E07. Installed API/export authentication is recorded
in [the public proof](evidence/next_e01_public_verification.json); it binds
current bytes to these runs without claiming a new native benchmark.

```powershell
python libraries/tests/measure_next_cold_extension.py --output libraries/evidence/next_e01_lzsa.json
```

The [reproducer](tests/measure_next_cold_extension.py) also writes the full
gzip archive. It authenticates the archived default snapshot before each
alignment check; preserve that snapshot when reproducing the candidate.
