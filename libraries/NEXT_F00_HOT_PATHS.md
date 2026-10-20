# F00 — Qualified LZSA2 hot-path tradeoffs

Completed 2026-10-20 in `codex/codec-speed-pass3`. The user's latest objective
retains minimum size, maximum speed under 10,000 service bytes, and useful
intermediate tradeoffs. This supersedes the strict-both rule of the earlier
[E02](NEXT_E02_LONG_LITERALS.md) and [E03](NEXT_E03_NIBBLE_STATES.md) screens.
This stage qualifies exactly their two useful speed candidates and the sum.

## Complete results and selection

The predecessor is E01 `lzsa.hybrid.build('fast', cold_match_extension=True)`:
9,499 aligned service B and 14,926,306 T on the same 21 real compressed blocks.
All counts include required block initialization and exact EOF return.

| Public function call | Emitted code, tables and embedded state B | Stack B | Total aligned service B | Real CPU T | Delta vs E01 T | Less CPU vs E01 / pass Fast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `lzsa.hot.build('nibble')` | 9,509 | 6 | 9,515 | 14,918,596 | -7,710 | 0.051654% / 16.022983% |
| `lzsa.hot.build('literals')` | 9,523 | 6 | 9,529 | 14,913,435 | -12,871 | 0.086230% / 16.052034% |
| `lzsa.hot.build('combined')` | 9,539 | 6 | 9,545 | 14,905,725 | -20,581 | 0.137884% / 16.095434% |

Pass Fast is 17,765,094 T, with `fast_jumps=True`. Original adapted Fast and
all exact function/file links remain in [DECODER_VARIANTS.md](DECODER_VARIANTS.md).
These are CPU-time percentages, rather than reciprocal throughput percentages.
Each point is nondominated on the measured real aggregate: reducing memory
selects a slower point. They remain optional, with unchanged existing defaults.
The fastest tested LZSA2 resident point is now `combined`; no global optimum
or ten-percent incremental gain over E01 is established.

The 512-byte static dispatch table and two-byte mutable offset are already
inside the emitted region. There are no extra variables, private stack,
scratch or internal buffers. The six caller-stack bytes include the return
word, saved alternate HL and the existing match/helper peak. Input and full
output/history are external caller buffers, excluded as authorized. The real
fixture requires up to 8,198 input and 15,872 output/history B; the full
95-case corpus has a 15,878-byte literal-only input. Supplemental valid word
counts also remain in the separate proof.

Page alignment adds 0..255 B. Maximum service with the diagnostic IRQ's
13 code and six extra stack bytes is 9,789 / 9,803 / 9,819 B for nibble /
literals / combined. Thus all 256 alignments fit this example within 10,000 B.
Actual applications must account for their own IRQ and memory map.

```python
from lzsa.hot import build
from lzsa.export import export

profile = build('combined', core=0x8000, core_limit=0xb000)
export('build/lzsa-hot', *profile)
```

The installed generator is [hot.build](lzsa/src/lzsa/hot.py). CLI equivalents
are `hot-nibble-block`, `hot-literals-block` and `hot-combined-block`:

```powershell
python -m lzsa build --profile hot-combined-block --core 0x8000 --core-limit 0xb000 --output build/lzsa-hot
```

Call the generated `start` with HL=input, DE=output and a valid caller stack.
IX/IY and alternate BC/DE/HL survive; AF/AF'/BC/DE/HL may change. The offset
operand needs writable nonreentrant code. IRQ preserves both live register
sets, including the cache in AF'. Complete input/history and nonwrapping
output are required. Quota/guarded wrappers remain unqualified and unavailable
through this API. Neither the packet format nor compressed bytes change.

## Initialization and complete-path accounting

Required target initialization is part of the benchmark, as explicitly
requested by the user. The actual common entry is:

```asm
; Preserve caller HL', initialize B and the empty AF' reservoir, enter dispatch.
; 4 + 11 + 4 + 7 + 4 + 4 + 10 = 44 T per block.
exx
push hl
exx
ld b,0
scf
ex af,af'
jp ReadToken
```

EOF restores HL' and returns with `EXX; POP HL; EXX; RET`, costing 28 T.
Both sequences are inside the native entry-through-RET measurement: 924 T
entry setup and 588 T restoration/return across 21 real blocks. The public
verifier checks their actual bytes. There is no separate required target
initializer: **0 additional T**. Dispatch tables are static image bytes.
Dirty offset startup and fresh full calls require no external state reset.

The historical convention excludes the caller's CALL instruction; count
another 17 T per invocation if accounting for that instruction, or 357 T
across these 21 blocks, equally for the predecessor and candidates. Host
binary/input loading and offline Python generation are fixture/build work.
The IRQ configuration's 26-T bootstrap and injected IRQ work are retained
separately from deterministic decoder CPU. For any future runtime preparation,
record its one-time cost in cold-start and batch totals, plus every per-call
setup. Do not initialize required library state outside the benchmark for free.

## Independent models and regressions

Costs use [Z80_TIMINGS.md](Z80_TIMINGS.md), without WAIT/ULA/disk/ROM time.
The hot token248 nibble literal clone removes CALL17+RET10, saving 27 T.
Byte/word escapes retain `ManyLiterals` through a cold continuation, adding
10 T. Across real inputs the independent E00 counts are 483 nibble and
17 byte entries: `-27*483 + 10*17 = -12,871 T`. The clone adds 30 code B.
Its nibble path handles counts 3..17; legal word literals 1/2 keep LDIR.

For body167_0, a cached first offset nibble proves that the second nibble
reader is empty. Duplicate offset setup and direct entry past SCF/EX/JR
change the full pair 155 -> 140 T, on 514 real hits: `-15*514 = -7,710 T`.
This adds 16 B and no state/stack. Refill-first handling is unchanged.
Combining the sites adds 46 B; their independently observed deltas sum
exactly on every full case.

| Mode | Faster / equal among 675 frozen cases | Slower frozen cases | Slower supplemental cases |
| --- | ---: | ---: | --- |
| nibble | 22 / 653 | 0 | 0 |
| literals | 23 / 652 | 0 | Four at +10 T |
| combined | 24 / 651 | 0 | Four at +10 T |

The four valid supplemental cases are `clone-word-1-cached`,
`clone-word-2-cached`, `clone-word-1-refill`, `clone-word-2-refill`.
All data, EOF and six configurations pass; slower CPU is retained explicitly.
The 56 other supplemental cases cover hot-family nibble/byte/word exits,
EOF and both cache phases. Preserve earlier E01 and Hybrid regression lists
against their own predecessors; these incremental lists do not erase them.

## Qualification and evidence provenance

The [full native proof](evidence/next_f00_full.json.gz), SHA256
`00b1facac131ba65f880989af84e0a013958bec9fe66a24733f7c09873c5ad66`, records:

- The qualified local C core reproduces all 675 frozen E01 original-backend
  baseline counts. Each of three candidates passes 675+60 C cases with exact
  independent E00 sum models and authenticated input/output hashes.
- Original protected backend replays each candidate's 675+60 inputs in six
  configurations: disjoint plain/IRQ/relocated and actual minimum-safe
  compressed-input overlap plain/IRQ/relocated. Add nine FFFFh output-cursor
  probes per candidate: **13,257 complete configurations** in total.
- Every output byte, exact input/EOF, source frontier, changed-code permission,
  dirty offset, IX/IY/alternate pairs, SP and stack pass. Minimum input starts
  and native/host write-cursor digests match. Of 675 frozen cases, 674 overlap;
  the empty-output EOF cannot overlap output. Peak stack is six plain and
  twelve with IRQ. Each profile receives 1,632 injected interrupts.
- All 3*256 alignment inventories match, including the IRQ example.

The private disjoint runner adds only the missing IY sentinel to the original
runner and poisons the two declared mutable bytes in the supplied code image.
The source transform/hash is recorded; shared native runners were unchanged.
Original launch and final source hashes agree. The C DLL is the previously
qualified `21e89129d040c6c29112c8977b5cb28573ae09f75632f5b993308204a76b2db8`.

Public integration uses a local fixed assembler factory in Wide/Hybrid;
existing default builders instantiate the same ordinary assembler as before.
The installed hot emitter has no AST, exec, test/evidence or corpus dependency.
It validates its exact replacement events, canonical whole-code/fixup/label
fingerprint and all 256 final token targets. Current public bytes and every
label match the frozen private proof at both native origins and all alignments.
The [prior-source archive](evidence/next_f00_prior_sources.json.gz) preserves
the old Wide/Hybrid and 68-call table sources; native evidence is reused by
byte identity, without relabelling the historical executed sources.

[Public authentication](evidence/next_f00_public_verification.json) verifies
93 library tests, 24 selected toolkit tests, 31 legacy layouts, six upstream
resources, all preceding 68 table calls and exact E01 metadata. Both isolated
wheels match current sources/resources; 74 API exports and three new CLI
profiles reconstruct exact ORG/DB bytes. All 71 table calls are checked again
by the [table reproducer](tests/document_decoder_variants.py), which identifies
the measured resident Pareto points. Logs are under
[next_f00_public](evidence/next_f00_public/next-f00-library-tests.log.gz).
The first wheel attempt encountered an inaccessible default sandbox TEMP;
the successful retry used worktree-local TEMP/TMP. The isolated CLI fixture
also needed a stable export-root variable before replacing its argument list;
the final authentication rerun keeps all exports inside its temporary folder.
No candidate changed.

Reproduce the private matrix with the qualified DLL explicitly selected:

```powershell
$env:CODEC_EMULATOR_DLL=(Resolve-Path .tmp/codec-cpu-qualified/codec_cpu.dll).Path
python libraries/tests/next_f00_measure.py --output .tmp/next-f00-replay/next_f00_full.json.gz
python -m unittest discover -s libraries/tests -v
```

The integration reproducer is [verify_next_f00_public.py](tests/verify_next_f00_public.py);
pass `--zx0-wheel`, `--lzsa-wheel` and `--output` after rebuilding both wheels
and recording its three named worktree-local logs. This stage qualifies raw
resident code only. Coroutine/guarded input, ULA contention, physical disk/ROM
and movie publication remain separate gates. F00 is complete; S01/E04..E07
remain pending in [the bounded queue](NEXT_TRICKS_PLAN.md).
